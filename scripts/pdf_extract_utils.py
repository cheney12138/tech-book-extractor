"""
PDF 文本提取工具库 — 直接读取 PDF 文本层，不依赖 OCR/GPU
==========================================================
为 extract_book.py 和 extract_chapter.py 提供共享能力：
  - 文本提取（PyMuPDF fitz.get_text，CPU 毫秒级）
  - 表格区域检测（基于文字坐标的网格分析）
  - 嵌入图片导出（标记不可读内容）
  - 结果汇总与输出格式化

原理：大多数技术书 PDF 是排版软件导出的，内嵌文字层。
      PyMuPDF 直接读取这层文字，和 Ctrl+C 一个原理。
      对扫描件 PDF（全图片），文字层为空，脚本会检测并提示。
"""

from __future__ import annotations

import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ═══════════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════════

@dataclass
class TextBlock:
    """PDF 中的一个文本块（段落/标题/单元格）"""
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    block_type: str = ""   # "text" | "image"
    font_size: float = 0.0
    font_name: str = ""


@dataclass
class PageResult:
    """单页提取结果"""
    page_num: int                         # 页码（1-based）
    text: str                             # 提取的文本
    tables: list[TableRegion] = field(default_factory=list)   # 检测到的表格
    image_count: int = 0                  # 嵌入图片数
    has_text_layer: bool = True           # 是否有文字层
    elapsed: float = 0.0                  # 耗时（秒）


@dataclass
class TableRegion:
    """检测到的表格区域"""
    y_start: float
    y_end: float
    rows: int              # 估计行数
    cols: int              # 估计列数
    raw_text: str = ""     # 从该区域提取的原始文本
    page_num: int = 0


# ═══════════════════════════════════════════════════════════════════
# PDF 工具
# ═══════════════════════════════════════════════════════════════════

def pdf_page_count(pdf_path: str | Path) -> int:
    """返回 PDF 总页数"""
    import fitz
    doc = fitz.open(str(pdf_path))
    count = len(doc)
    doc.close()
    return count


def _group_blocks_by_line(blocks: list[TextBlock], y_tolerance: float = 4.0) -> list[list[TextBlock]]:
    """
    将文本块按 y 坐标分组为"行"。
    同一行内 block 按 x 坐标从左到右排序。
    """
    if not blocks:
        return []

    # 按 y 排序
    sorted_blocks = sorted(blocks, key=lambda b: (b.y0, b.x0))

    lines: list[list[TextBlock]] = []
    current_line: list[TextBlock] = [sorted_blocks[0]]

    for block in sorted_blocks[1:]:
        # 如果 y0 和上一行的平均 y0 接近，属于同一行
        avg_y = sum(b.y0 for b in current_line) / len(current_line)
        if abs(block.y0 - avg_y) < y_tolerance:
            current_line.append(block)
        else:
            lines.append(sorted(current_line, key=lambda b: b.x0))
            current_line = [block]

    lines.append(sorted(current_line, key=lambda b: b.x0))
    return lines


def _detect_tables(blocks: list[TextBlock]) -> list[TableRegion]:
    """
    基于文本块坐标检测表格区域。

    表格特征：
    1. 多行文本的 x 坐标在列方向上对齐（形成网格）
    2. 行间距均匀（和正文段落的分隔模式不同）
    3. 单行内多个独立 block（多列）

    返回检测到的表格区域列表。
    """
    if len(blocks) < 4:  # 至少 2 行 × 2 列才有表格意义
        return []

    # 过滤掉太小的块（可能是页码、页眉）
    text_blocks = [b for b in blocks if len(b.text.strip()) > 1]
    if len(text_blocks) < 4:
        return []

    lines = _group_blocks_by_line(text_blocks, y_tolerance=5.0)

    tables: list[TableRegion] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 单行有 ≥2 个对齐的 block → 可能是表格行
        if len(line) >= 2:
            # 向后扫描，看有多少连续行有相同数量的 block（列数一致）
            table_lines = [line]
            col_count = len(line)
            j = i + 1
            while j < len(lines) and len(lines[j]) >= 2:
                # 检查列宽是否大致对齐
                if _columns_aligned(table_lines[-1], lines[j], tolerance=10.0):
                    table_lines.append(lines[j])
                    j += 1
                else:
                    break

            if len(table_lines) >= 2:  # 至少 2 行才算表格
                y0 = min(b.y0 for line in table_lines for b in line)
                y1 = max(b.y1 for line in table_lines for b in line)
                # 聚合表格内所有文本（按行组织）
                raw = ""
                for tl in table_lines:
                    cells = [b.text.strip() for b in tl]
                    raw += " | ".join(cells) + "\n"
                tables.append(TableRegion(
                    y_start=y0,
                    y_end=y1,
                    rows=len(table_lines),
                    cols=col_count,
                    raw_text=raw.strip(),
                ))
                i = j
                continue
        i += 1

    # 去重：合并重叠的表格区域
    return _merge_overlapping_tables(tables)


def _columns_aligned(line_a: list[TextBlock], line_b: list[TextBlock], tolerance: float = 10.0) -> bool:
    """
    检查两行文本的列是否对齐。
    比较每列的 x0 坐标是否在容差范围内。
    """
    if len(line_a) != len(line_b):
        return False
    for ba, bb in zip(line_a, line_b):
        if abs(ba.x0 - bb.x0) > tolerance:
            return False
    return True


def _merge_overlapping_tables(tables: list[TableRegion]) -> list[TableRegion]:
    """合并 y 范围有重叠的表格检测结果"""
    if len(tables) <= 1:
        return tables
    sorted_tables = sorted(tables, key=lambda t: t.y_start)
    merged = [sorted_tables[0]]
    for t in sorted_tables[1:]:
        last = merged[-1]
        if t.y_start <= last.y_end + 10:  # 允许小间隙
            last.y_end = max(last.y_end, t.y_end)
            last.rows = max(last.rows, t.rows)
            last.cols = max(last.cols, t.cols)
            last.raw_text += "\n" + t.raw_text
        else:
            merged.append(t)
    return merged


# ═══════════════════════════════════════════════════════════════════
# 核心：单页提取
# ═══════════════════════════════════════════════════════════════════

def extract_page(
    page,
    page_num: int,
    export_images: bool = False,
    image_dir: str = "",
) -> PageResult:
    """
    提取单个 PDF 页面的文本、表格和图片信息。

    Args:
        page: PyMuPDF Page 对象
        page_num: 页码（1-based）
        export_images: 是否导出嵌入图片
        image_dir: 图片导出目录

    Returns:
        PageResult
    """
    import fitz

    t0 = time.time()

    # 1. 提取文本（dict 模式，保留坐标）
    text_dict = page.get_text("dict")
    blocks_raw = text_dict.get("blocks", [])

    # 2. 提取嵌入图片
    image_count = 0
    image_refs: list[str] = []
    try:
        image_list = page.get_images(full=True)
        for img_idx, img_info in enumerate(image_list):
            image_count += 1
            if export_images and image_dir:
                xref = img_info[0]
                base_image = page.parent.extract_image(xref)
                if base_image:
                    ext = base_image["ext"]
                    img_path = os.path.join(image_dir, f"p{page_num:04d}_img{img_idx+1}.{ext}")
                    os.makedirs(os.path.dirname(img_path), exist_ok=True)
                    with open(img_path, "wb") as f:
                        f.write(base_image["image"])
                    image_refs.append(img_path)
    except Exception:
        pass  # 某些 PDF 图片提取可能失败，不阻塞流程

    # 3. 分离文本块和图片块
    text_blocks: list[TextBlock] = []
    for block in blocks_raw:
        if block.get("type") == 0:  # 文本块
            for line in block.get("lines", []):
                line_text = ""
                x0, y0, x1, y1 = float("inf"), float("inf"), 0, 0
                font_size = 0.0
                font_name = ""
                for span in line.get("spans", []):
                    line_text += span.get("text", "")
                    bbox = span.get("bbox", (0, 0, 0, 0))
                    x0 = min(x0, bbox[0])
                    y0 = min(y0, bbox[1])
                    x1 = max(x1, bbox[2])
                    y1 = max(y1, bbox[3])
                    if span.get("size", 0) > font_size:
                        font_size = span.get("size", 0)
                    font_name = span.get("font", "")
                if line_text.strip():
                    text_blocks.append(TextBlock(
                        text=line_text.strip(),
                        x0=x0, y0=y0, x1=x1, y1=y1,
                        block_type="text",
                        font_size=font_size,
                        font_name=font_name,
                    ))

    # 4. 检测表格
    tables = _detect_tables(text_blocks)

    # 5. 构建输出文本
    # 策略：按 y 坐标从上到下排列文本块，表格区域插入特殊标记
    has_text = len(text_blocks) > 0

    if not has_text:
        # 可能是扫描件 PDF — 没有文字层
        elapsed = time.time() - t0
        return PageResult(
            page_num=page_num,
            text=f"> ⚠️ 本页无文字层，可能是扫描件图片。需要 OCR 才能提取文字。\n",
            tables=[],
            image_count=image_count,
            has_text_layer=False,
            elapsed=elapsed,
        )

    # 按 y 坐标排序所有文本块
    sorted_blocks = sorted(text_blocks, key=lambda b: (b.y0, b.x0))

    # 标记哪些 block 属于表格区域
    table_block_indices: set[int] = set()
    for table in tables:
        for idx, block in enumerate(sorted_blocks):
            if table.y_start - 5 <= block.y0 <= table.y_end + 5:
                table_block_indices.add(idx)

    # 生成文本输出
    output_lines: list[str] = []
    output_lines.append(f"\n<!-- 第 {page_num} 页 -->\n")

    prev_y = -100
    prev_was_table = False
    inside_table = False

    for idx, block in enumerate(sorted_blocks):
        in_table = idx in table_block_indices

        # 表格区域开始
        if in_table and not inside_table:
            inside_table = True
            # 找到对应的 TableRegion
            for table in tables:
                if table.y_start - 5 <= block.y0 <= table.y_end + 5:
                    output_lines.append(f"\n> 📊 **表格区域**（{table.rows}行 × {table.cols}列）— 建议查阅原书第 {page_num} 页确认结构\n>\n")
                    # 输出提取的原始文本
                    for line in table.raw_text.split("\n"):
                        output_lines.append(f"> | {line}\n")
                    output_lines.append(f">\n> ⚠️ 上方表格的单元格内容已提取，但行列关系可能不准确\n")
                    break
            prev_was_table = True
            continue

        # 表格区域内的后续行跳过（已在 header 中输出）
        if in_table and inside_table:
            prev_y = block.y0
            continue

        # 离开表格区域
        if not in_table and inside_table:
            inside_table = False
            output_lines.append("\n")

        # 判断是否为标题（字号较大）
        is_heading = block.font_size >= 14.0 and len(block.text) < 80

        # 段落间距判断
        if prev_y > 0 and block.y0 - prev_y > 20:
            output_lines.append("")

        if is_heading and len(block.text) > 2:
            output_lines.append(f"## {block.text}")
        else:
            output_lines.append(block.text)

        prev_y = block.y0
        prev_was_table = False

    # 6. 图片引用
    if image_count > 0:
        output_lines.append(f"\n> 🖼️ 本页含 {image_count} 张嵌入图片，建议查原书\n")

    elapsed = time.time() - t0
    return PageResult(
        page_num=page_num,
        text="".join(output_lines) if output_lines else "",
        tables=tables,
        image_count=image_count,
        has_text_layer=True,
        elapsed=elapsed,
    )


# ═══════════════════════════════════════════════════════════════════
# 批量提取
# ═══════════════════════════════════════════════════════════════════

def extract_pages(
    pdf_path: str | Path,
    page_range: Optional[tuple[int, int]] = None,
    export_images: bool = False,
    image_dir: str = "",
    progress_callback=None,
) -> list[PageResult]:
    """
    从 PDF 批量提取页面文本。

    Args:
        pdf_path: PDF 文件路径
        page_range: (start, end) 1-based，None 表示全部
        export_images: 是否导出嵌入图片
        image_dir: 图片导出目录
        progress_callback: fn(page_num, status)

    Returns:
        [PageResult, ...]
    """
    import fitz

    doc = fitz.open(str(pdf_path))
    total = len(doc)

    start = 1
    end = total
    if page_range:
        start, end = page_range
        start = max(1, start)
        end = min(total, end)

    results: list[PageResult] = []
    scan_pages = 0

    for i in range(start - 1, end):
        page_num = i + 1
        page = doc[i]
        result = extract_page(page, page_num, export_images, image_dir)
        results.append(result)

        if not result.has_text_layer:
            scan_pages += 1

        if progress_callback:
            status = "scan" if not result.has_text_layer else "ok"
            progress_callback(page_num, status)
        else:
            flag = " ⚠️ 扫描件" if not result.has_text_layer else ""
            print(f"  ✓ 第 {page_num} 页 ({result.elapsed:.3f}s){flag}")

    doc.close()

    # 汇总报告
    if scan_pages > 0:
        print(f"\n⚠️  {scan_pages}/{len(results)} 页无文字层（可能是扫描件），需要 OCR。")
        if scan_pages == len(results):
            print("   这本书似乎是纯扫描件 PDF，建议使用 OCR 工具（如 Unlimited-OCR）处理。")

    return results


# ═══════════════════════════════════════════════════════════════════
# 输出格式化
# ═══════════════════════════════════════════════════════════════════

def merge_to_markdown(
    results: list[PageResult],
    title: str = "",
) -> str:
    """
    将多页提取结果合并为一个 Markdown 文档。

    Args:
        results: 按页码排序的结果列表
        title: 文档标题

    Returns:
        完整的 Markdown 文本
    """
    lines = []
    if title:
        lines.append(f"# {title}\n")

    # 报告统计
    total_tables = sum(len(r.tables) for r in results)
    total_images = sum(r.image_count for r in results)
    scan_pages = sum(1 for r in results if not r.has_text_layer)

    if total_tables > 0 or total_images > 0 or scan_pages > 0:
        lines.append("> 📋 **提取报告**\n")
        if total_tables > 0:
            lines.append(f"> - 检测到 {total_tables} 个表格区域，建议查原书验证结构\n")
        if total_images > 0:
            lines.append(f"> - {total_images} 张嵌入图片无法提取文字\n")
        if scan_pages > 0:
            lines.append(f"> - {scan_pages} 页无文字层（扫描件），内容缺失\n")
        lines.append(">\n")

    for r in results:
        lines.append(r.text)
        lines.append("")

    return "\n".join(lines)


def save_results(
    results: list[PageResult],
    output_path: str | Path,
    title: str = "",
) -> str:
    """
    保存提取结果为 Markdown 文件。

    Args:
        results: 提取结果列表
        output_path: 输出文件路径
        title: 文档标题

    Returns:
        实际写入的文件路径
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    markdown = merge_to_markdown(results, title)
    output_path.write_text(markdown, encoding="utf-8")

    total_ok = sum(1 for r in results if r.has_text_layer)
    total_time = sum(r.elapsed for r in results)
    total_tables = sum(len(r.tables) for r in results)
    total_images = sum(r.image_count for r in results)

    print(f"\n✅ 保存到: {output_path}")
    print(f"   文字页: {total_ok}/{len(results)}, "
          f"表格: {total_tables}, 图片: {total_images}, "
          f"耗时: {total_time:.2f}s")

    return str(output_path)


# ═══════════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════════

def extract_book_name(pdf_path: str | Path) -> str:
    """从 PDF 文件名提取书名（去后缀、去特殊字符）"""
    name = Path(pdf_path).stem
    name = re.sub(r"[（(]第?\d+版[）)]", "", name)
    name = re.sub(r"[:：].*", "", name)
    return name.strip()


def parse_page_range(range_str: str) -> tuple[int, int]:
    """
    解析页码范围字符串。

    Examples:
        "45-78" → (45, 78)
        "45"    → (45, 45)
    """
    parts = range_str.split("-")
    if len(parts) == 2:
        return int(parts[0].strip()), int(parts[1].strip())
    return int(parts[0].strip()), int(parts[0].strip())
