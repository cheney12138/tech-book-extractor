#!/usr/bin/env python3
"""
complexity_scanner.py — Stage 1 预处理脚本

客观计算技术书各小节的复杂度指标，输出 complexity-meta.json。
由 Stage 1 Skill 调用，替代 LLM 对复杂度的主观推断。

支持格式：txt / epub / pdf（需安装 poppler-utils）
扫描件 PDF 无法处理，退回 LLM 推断（会在输出中标注）。

用法：
  python complexity_scanner.py <书的路径> [输出路径]

输出示例：
  {
    "sec_1": {
      "title": "第1章 引言",
      "words": 1200,
      "footnotes": 1,
      "cross_refs": 0,
      "complexity": "low"
    },
    ...
  }
"""

import json
import re
import sys
from pathlib import Path


# ── 文本提取 ──────────────────────────────────────────────────────────────────

def extract_text_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_text_epub(path: Path) -> str:
    import zipfile
    from html.parser import HTMLParser

    class _Stripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self._parts = []

        def handle_data(self, d):
            self._parts.append(d)

        def get_data(self):
            return "\n".join(self._parts)

    texts = []
    try:
        with zipfile.ZipFile(path, "r") as z:
            for name in sorted(z.namelist()):
                if name.endswith((".html", ".xhtml", ".htm")):
                    html = z.read(name).decode("utf-8", errors="ignore")
                    s = _Stripper()
                    s.feed(html)
                    texts.append(s.get_data())
    except Exception as e:
        print(f"[WARN] epub 解析失败: {e}", file=sys.stderr)
    return "\n".join(texts)


def extract_text_pdf(path: Path) -> str:
    import subprocess

    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return result.stdout
        print(f"[WARN] pdftotext 失败: {result.stderr}", file=sys.stderr)
    except FileNotFoundError:
        print(
            "[WARN] 未找到 pdftotext，请安装 poppler-utils（brew install poppler）",
            file=sys.stderr,
        )
    except subprocess.TimeoutExpired:
        print("[WARN] pdftotext 超时", file=sys.stderr)
    return ""


def extract_text(path: str) -> tuple[str, bool]:
    """
    返回 (文本内容, is_scan)。
    is_scan=True 表示扫描件或提取失败，复杂度指标不可信。
    """
    p = Path(path)
    suffix = p.suffix.lower()

    if suffix == ".txt":
        return extract_text_txt(p), False
    elif suffix == ".epub":
        text = extract_text_epub(p)
        return text, len(text.strip()) == 0
    elif suffix == ".pdf":
        text = extract_text_pdf(p)
        # 扫描件特征：文本极少（每页平均 < 50 字符）
        try:
            import subprocess
            pages_result = subprocess.run(
                ["pdfinfo", str(p)], capture_output=True, text=True, timeout=10
            )
            pages_line = next(
                (l for l in pages_result.stdout.splitlines() if "Pages:" in l), ""
            )
            pages = int(pages_line.split(":")[-1].strip()) if pages_line else 1
        except Exception:
            pages = max(1, len(text) // 2000)

        is_scan = len(text.strip()) < pages * 50
        return text, is_scan
    else:
        text = p.read_text(encoding="utf-8", errors="ignore")
        return text, False


# ── 章节分割 ──────────────────────────────────────────────────────────────────

_HEADING_RE = re.compile(
    r"("
    r"^第[零一二三四五六七八九十百千\d]+[章节篇][\s　].{0,60}"  # 中文章节
    r"|^(?:Chapter|CHAPTER|PART|Part)\s+[\dA-Za-z].{0,60}"       # 英文 Chapter/Part
    r"|^\d{1,2}(?:\.\d{1,2}){0,2}[\s　]\S.{0,60}"               # 1 / 1.2 / 1.2.3 编号
    r"|^#{1,3}\s+\S.{0,60}"                                       # Markdown 标题
    r")",
    re.MULTILINE,
)


def split_sections(text: str) -> list[dict]:
    parts = _HEADING_RE.split(text)
    if len(parts) < 3:
        return [{"id": "whole", "title": "whole", "content": text}]

    sections = []
    idx = 1
    while idx < len(parts) - 1:
        title = parts[idx].strip()
        content = parts[idx + 1] if idx + 1 < len(parts) else ""
        sections.append(
            {"id": f"sec_{len(sections) + 1}", "title": title, "content": content}
        )
        idx += 2
    return sections


# ── 指标计算 ──────────────────────────────────────────────────────────────────

_FOOTNOTE_RE = re.compile(
    r"\[\d{1,3}\]"           # [1]
    r"|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮]"  # 圈数字
    r"|^\s*注[：:].+",        # 注：…（行首）
    re.MULTILINE,
)

_CROSS_REF_RE = re.compile(
    r"第[零一二三四五六七八九十百千\d]+[章节篇]"
    r"|Chapter\s+\d+"
    r"|见\s*[第§§]\s*\S+"
    r"|参[见考]\s*[第§]\s*\S+"
    r"|如前[所述文章]"
    r"|后文[将会]介绍",
    re.IGNORECASE,
)


def word_count(text: str) -> int:
    chinese = len(re.findall(r"[一-鿿]", text))
    english = len(re.findall(r"\b[a-zA-Z]+\b", text))
    return chinese + english


def count_footnotes(text: str) -> int:
    return len(_FOOTNOTE_RE.findall(text))


def count_cross_refs(text: str) -> int:
    return len(_CROSS_REF_RE.findall(text))


def classify_complexity(words: int, footnotes: int, cross_refs: int) -> str:
    hits = (
        (1 if words > 3000 else 0)
        + (1 if footnotes > 3 else 0)
        + (1 if cross_refs > 2 else 0)
    )
    if hits == 3:
        return "high"
    if hits >= 1:
        return "medium"
    return "low"


# ── 主流程 ────────────────────────────────────────────────────────────────────

def scan(book_path: str, output_path: str | None = None) -> str:
    print(f"[INFO] 扫描: {book_path}")
    text, is_scan = extract_text(book_path)

    if not text.strip():
        print("[ERROR] 文本提取失败或为空", file=sys.stderr)
        sys.exit(1)

    if is_scan:
        print(
            "[WARN] 检测到扫描件 PDF，无法客观计算复杂度指标。"
            " Stage 1 Skill 将退回 LLM 推断，请在 JSON 中注意 scan_fallback 标记。",
            file=sys.stderr,
        )

    print(f"[INFO] 总字符数: {len(text):,}")
    sections = split_sections(text)
    print(f"[INFO] 识别小节数: {len(sections)}")

    meta: dict = {"_meta": {"scan_fallback": is_scan, "total_sections": len(sections)}}

    for sec in sections:
        words = word_count(sec["content"])
        footnotes = count_footnotes(sec["content"])
        cross_refs = count_cross_refs(sec["content"])
        complexity = "unknown" if is_scan else classify_complexity(words, footnotes, cross_refs)

        meta[sec["id"]] = {
            "title": sec["title"],
            "words": words,
            "footnotes": footnotes,
            "cross_refs": cross_refs,
            "complexity": complexity,
        }

    if output_path is None:
        stem = Path(book_path).stem
        output_path = str(Path(book_path).parent / f"{stem}-complexity-meta.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    high = sum(1 for k, v in meta.items() if k != "_meta" and v["complexity"] == "high")
    medium = sum(1 for k, v in meta.items() if k != "_meta" and v["complexity"] == "medium")
    low = sum(1 for k, v in meta.items() if k != "_meta" and v["complexity"] == "low")
    print(f"[INFO] 复杂度分布 — high: {high}  medium: {medium}  low: {low}")
    print(f"[INFO] 输出: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python complexity_scanner.py <书的路径> [输出路径]")
        sys.exit(1)

    scan(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
