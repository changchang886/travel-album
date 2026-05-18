#!/usr/bin/env python3
"""
🎒 AI Travel Photo Album Generator
扔进来一堆旅行照片 → 还你一本排好版的相册 PDF

Usage:
    python main.py /path/to/photos          # 从文件夹生成
    python main.py /path/to/photos --no-ai  # 跳过 AI 筛选，用所有照片
    python main.py /path/to/photos --title "云南之旅"
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from album_generator import AlbumGenerator
from photo_selector import PhotoSelector


def main():
    parser = argparse.ArgumentParser(description="AI Travel Photo Album Generator")
    parser.add_argument("photos_dir", help="Path to your travel photos folder")
    parser.add_argument("--title", default="My Travel Memories", help="Album title")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI photo selection")
    parser.add_argument("--max-photos", type=int, default=40, help="Max photos in album")
    parser.add_argument("--output", default=None, help="Output PDF path")
    args = parser.parse_args()

    photos_dir = Path(args.photos_dir)
    if not photos_dir.exists():
        print(f"❌ Folder not found: {photos_dir}")
        sys.exit(1)

    # Find all photos
    extensions = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".bmp"}
    all_photos = sorted([
        p for p in photos_dir.iterdir()
        if p.suffix.lower() in extensions and not p.name.startswith(".")
    ])

    if not all_photos:
        print(f"❌ No photos found in {photos_dir}")
        sys.exit(1)

    print(f"📸 Found {len(all_photos)} photos")

    # Step 1: AI Photo Selection
    if not args.no_ai and len(all_photos) > args.max_photos:
        print("🤖 AI analyzing and selecting best photos...")
        selector = PhotoSelector()
        selected = selector.select_best(all_photos, max_count=args.max_photos)
        print(f"✅ Selected {len(selected)} best photos")
        print(f"   Filtered out: {len(all_photos) - len(selected)} (blurry/duplicate/low quality)")
    elif not args.no_ai:
        print("🤖 AI analyzing photo quality...")
        selector = PhotoSelector()
        selected = selector.filter_bad(all_photos)
        print(f"✅ {len(selected)} photos passed quality check")
        print(f"   Filtered out: {len(all_photos) - len(selected)} (blurry/low quality)")
    else:
        selected = all_photos[:args.max_photos]
        print(f"📋 Using first {len(selected)} photos (--no-ai mode)")

    if not selected:
        print("❌ No photos remaining after selection!")
        sys.exit(1)

    # Step 2: Generate Album
    print(f"\n📖 Generating album '{args.title}' with {len(selected)} photos...")
    generator = AlbumGenerator()
    output_path = args.output or f"album_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    generator.generate(
        photos=selected,
        title=args.title,
        output_path=output_path,
    )

    print(f"\n🎉 Done! Album saved to: {output_path}")
    print(f"   Pages: {generator.page_count}")
    print(f"   Photos: {len(selected)}")
    print(f"   📤 Ready to print or share!")


if __name__ == "__main__":
    main()
