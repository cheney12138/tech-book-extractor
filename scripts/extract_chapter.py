#!/usr/bin/env python3
"""
extract_chapter.py — 单章文本提取脚本
========================================
从 PDF 中提取指定页码范围的文本，输出 Markdown 文件，
可直接喂给 chapter-drill skill。

用法：
  # 提取第 45-78 页（第 3 章）
  python extract_chapter.py ./book.pdf --pages 45-78 --chapter "ch03"

  # 指定输出目录
  python extract_chapter.py ./book.pdf --pages 45-78 --chapter "ch03" --output ./note/book/

  # 同时导出嵌入图片
  python extract_chapter.py ./book.pdf --pages 45-78 --chapter "ch03" --export-images

输出：
  {output_dir}/{书名}/chapters/{chapter_id}-raw.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pdf_extract_utils import (
    pdf_page_count,
    extract_pages,
    save_results,
    extract_book_name,
    parse_page_range,
)


def main():
    parser = argparse.ArgumentParser(
        description="单章文本提取 — 从 PDF 提取指定页码范围，对接 chapter-drill skill",
    )
    parser.add_argument("pdf", help="PDF 文件路径")
    parser.add_argument(
        "--pages", required=True,
        help="页码范围，如 '45-78' 或 '45'（单页）",
    )
    parser.add_argument(
        "--chapter", "-c", default="",
        help="章节标识，如 'ch03'。输出文件名: ch03-raw.md",
    )
    parser.add_argument(
        "--output", "-o", default="./note/book/",
        help="输出根目录（默认: ./note/book/）",
    )
    parser.add_argument(
        "--export-images", action="store_true",
        help="同时导出 PDF 中的嵌入图片到 images/ 目录",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        sys.exit(f"❌ PDF 文件不存在: {pdf_path}")

    # 页码范围
    page_start, page_end = parse_page_range(args.pages)
    if page_start > page_end:
        page_start, page_end = page_end, page_start

    total_pages = pdf_page_count(pdf_path)
    if page_end > total_pages:
        print(f"⚠️  页码范围超出（PDF 共 {total_pages} 页），自动截断")
        page_end = total_pages

    # 章节标识
    chapter_id = args.chapter if args.chapter else f"p{page_start}-{page_end}"

    # 书名 & 输出路径
    book_name = extract_book_name(pdf_path.name)
    output_dir = Path(args.output) / book_name / "chapters"
    output_path = output_dir / f"{chapter_id}-raw.md"
    image_dir = str(Path(args.output) / book_name / "images") if args.export_images else ""

    page_count = page_end - page_start + 1
    print(f"📖 {book_name}")
    print(f"   章节: {chapter_id}  (第 {page_start}-{page_end} 页, 共 {page_count} 页)")
    print(f"   输出: {output_path}")
    print()

    # 提取
    print(f"🔍 提取文本 ({page_count} 页) ...")
    results = extract_pages(
        pdf_path,
        page_range=(page_start, page_end),
        export_images=args.export_images,
        image_dir=image_dir,
    )

    # 保存
    chapter_title = f"{book_name} · {chapter_id}"
    save_results(results, output_path, title=chapter_title)

    # 下一步提示
    print(f"""
📎 下一步 — 深度萃取:
   用 chapter-drill skill，将以下文件内容作为章节全文输入：
   {output_path.resolve()}

   同时提供 Stage 1 骨架片段（type, weight, keyQuestions 等）。
""")


if __name__ == "__main__":
    main()
