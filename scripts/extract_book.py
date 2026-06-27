#!/usr/bin/env python3
"""
extract_book.py — 整本书文本提取脚本
=======================================
直接从 PDF 文字层提取全书文本（不需要 OCR/GPU），输出 Markdown 文件，
可直接喂给 book-map skill（Mode B）。

原理：PyMuPDF 直接读取 PDF 内嵌的文本层，和 PDF 阅读器里 Ctrl+C 一样。
      对扫描件 PDF（文字层为空），脚本会检测并提示。

用法：
  python extract_book.py ./深入理解Java虚拟机.pdf
  python extract_book.py ./book.pdf --output ./note/book/
  python extract_book.py ./book.pdf --max-pages 20   # 测试用
  python extract_book.py ./book.pdf --export-images    # 同时导出嵌入图片

输出：
  {output_dir}/{书名}/{书名}-fulltext.md
  {output_dir}/{书名}/images/          # 仅 --export-images 时
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
)


def main():
    parser = argparse.ArgumentParser(
        description="整本书文本提取 — 从 PDF 文字层直接提取，对接 book-map skill",
        epilog="注意：仅适用于文字版 PDF（排版导出的），扫描件 PDF 请用 OCR 工具。",
    )
    parser.add_argument("pdf", help="PDF 文件路径")
    parser.add_argument(
        "--output", "-o", default="./note/book/",
        help="输出根目录（默认: ./note/book/）",
    )
    parser.add_argument(
        "--max-pages", type=int, default=0,
        help="最多处理多少页（0=全部，用于测试）",
    )
    parser.add_argument(
        "--start-page", type=int, default=1,
        help="起始页码（1-based，默认: 1）",
    )
    parser.add_argument(
        "--export-images", action="store_true",
        help="同时导出 PDF 中的嵌入图片到 images/ 目录",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        sys.exit(f"❌ PDF 文件不存在: {pdf_path}")

    # 书名 & 输出路径
    book_name = extract_book_name(pdf_path.name)
    output_dir = Path(args.output) / book_name
    output_path = output_dir / f"{book_name}-fulltext.md"
    image_dir = str(output_dir / "images") if args.export_images else ""

    # 页码范围
    total_pages = pdf_page_count(pdf_path)
    end_page = total_pages
    if args.max_pages > 0:
        end_page = min(args.start_page + args.max_pages - 1, total_pages)

    print(f"📖 {book_name}")
    print(f"   总页数: {total_pages}")
    print(f"   处理范围: 第 {args.start_page}-{end_page} 页")
    print(f"   输出: {output_path}")
    if args.export_images:
        print(f"   图片: {image_dir}/")
    print()

    # 提取
    print(f"🔍 提取文本 ({end_page - args.start_page + 1} 页) ...")
    results = extract_pages(
        pdf_path,
        page_range=(args.start_page, end_page),
        export_images=args.export_images,
        image_dir=image_dir,
    )

    # 保存
    save_results(results, output_path, title=book_name)

    # 下一步提示
    print(f"""
📎 下一步 — 生成知识骨架:
   用 book-map skill，选择 Mode B（全书全文），把以下文件内容贴进去：
   {output_path.resolve()}
""")


if __name__ == "__main__":
    main()
