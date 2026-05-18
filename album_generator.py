#!/usr/bin/env python3
"""
📖 Album Generator
Creates a beautifully laid-out photo album PDF from selected photos.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List

from fpdf import FPDF
from openai import OpenAI


class AlbumGenerator:
    """Generate a printable photo album PDF"""

    PAGE_W = 210  # A4 width in mm
    PAGE_H = 297  # A4 height in mm
    MARGIN = 12   # Page margin

    def __init__(self):
        self.pdf = FPDF("P", "mm", "A4")
        self.page_count = 0
        self._setup_fonts()
        self._setup_ai()
        self._story_cache = {}  # Cache AI stories to avoid redundant API calls

    def _setup_fonts(self):
        """Add Chinese-capable fonts"""
        font_paths = [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Light.ttc",
            "/System/Library/Fonts/Supplemental/Songti.ttc",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                self.pdf.add_font("CN", "", fp)
                self.pdf.add_font("CN", "B", fp)
                return
        # Fallback: no Chinese font, use built-in
        print("⚠️ No Chinese font found, using built-in font. Titles may not render correctly.")

    def generate(self, photos: List[Path], title: str, output_path: str):
        """Generate the complete album"""
        self.pdf.set_auto_page_break(False)  # Manual page management for layouts
        self.output_path = output_path
        self.album_title = title

        # Pre-generate all stories for the photos
        self._generate_stories(photos, title)

        # Page 1: Cover
        self._add_cover(title, len(photos))

        # Photo pages
        photos_per_page = 2  # 2 photos per page with captions
        for i in range(0, len(photos), photos_per_page):
            batch = photos[i:i + photos_per_page]
            self._add_photo_page(batch, i // photos_per_page + 1)

        # Back cover
        self._add_back_cover(title)

        # Save
        self.pdf.output(output_path)

    def _add_cover(self, title: str, photo_count: int):
        """Generate album cover page"""
        self.pdf.add_page()
        self.page_count += 1
        w, h = self.PAGE_W, self.PAGE_H

        # Full-page dark background
        self.pdf.set_fill_color(15, 23, 42)  # Dark navy
        self.pdf.rect(0, 0, w, h, "F")

        # Decorative top bar
        self.pdf.set_fill_color(56, 189, 248)  # Sky blue
        self.pdf.rect(0, 0, w, 6, "F")

        # Title area
        self.pdf.set_y(h * 0.35)
        self.pdf.set_font("CN", "B", 32)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.cell(0, 16, title, align="C", new_x="LMARGIN", new_y="NEXT")

        # Decorative line
        self.pdf.set_y(self.pdf.get_y() + 4)
        self.pdf.set_draw_color(56, 189, 248)
        self.pdf.set_line_width(0.5)
        line_w = 60
        x = (w - line_w) / 2
        self.pdf.line(x, self.pdf.get_y(), x + line_w, self.pdf.get_y())

        # Subtitle
        self.pdf.set_y(self.pdf.get_y() + 10)
        self.pdf.set_font("CN", "", 14)
        self.pdf.set_text_color(148, 163, 184)
        self.pdf.cell(0, 10, f"{photo_count} photos · {datetime.now().strftime('%Y.%m')}", align="C", new_x="LMARGIN", new_y="NEXT")

        # Bottom text
        self.pdf.set_y(h - 40)
        self.pdf.set_font("CN", "", 10)
        self.pdf.set_text_color(71, 85, 105)
        self.pdf.cell(0, 8, "Made with AI · Travel Photo Album", align="C")

    def _add_photo_page(self, photos: List[Path], page_num: int):
        """Add a page with 1-2 photos in an elegant layout"""
        self.pdf.add_page()
        self.page_count += 1
        w, h = self.PAGE_W, self.PAGE_H
        m = self.MARGIN

        if len(photos) == 2:
            self._layout_two_photos(photos, w, h, m)
        elif len(photos) == 1:
            self._layout_one_photo(photos[0], w, h, m)

        # Page number
        self.pdf.set_y(h - 12)
        self.pdf.set_font("CN", "", 8)
        self.pdf.set_text_color(150, 150, 150)
        self.pdf.cell(0, 8, str(page_num), align="C")

    def _layout_two_photos(self, photos, w, h, m):
        """Two photos side by side with captions"""
        usable_w = w - 2 * m
        gap = 8
        photo_w = (usable_w - gap) / 2
        photo_h = photo_w * 0.75  # 4:3 aspect ratio

        y_top = m + 10

        for idx, photo_path in enumerate(photos):
            x = m + idx * (photo_w + gap)

            # Photo
            self._place_photo(str(photo_path), x, y_top, photo_w, photo_h)

            # Caption below photo
            name = self._photo_caption(photo_path)
            self.pdf.set_y(y_top + photo_h + 4)
            self.pdf.set_font("CN", "", 9)
            self.pdf.set_text_color(80, 80, 80)
            self.pdf.set_x(x)
            self.pdf.cell(photo_w, 8, name[:25], align="C")

        # AI-generated story at bottom
        y_bottom = y_top + photo_h + 30
        if y_bottom < h - 25:
            # Combine stories from both photos
            stories = []
            for p in photos:
                story = self._story_cache.get(str(p), "")
                if story:
                    stories.append(story)
            combined = "  |  ".join(stories) if stories else "Travel memory captured"
            
            # Story box
            self.pdf.set_y(y_bottom + 8)
            self.pdf.set_fill_color(248, 250, 252)
            self.pdf.set_draw_color(226, 232, 240)
            self.pdf.set_x(m)
            
            # Calculate story height
            self.pdf.set_font("CN", "", 9)
            self.pdf.set_text_color(80, 80, 80)
            self.pdf.multi_cell(usable_w, 6, combined, align="C", fill=True)

    def _layout_one_photo(self, photo_path, w, h, m):
        """Single large photo layout"""
        usable_w = w - 2 * m
        photo_w = min(usable_w * 0.9, 170)
        photo_h = photo_w * 0.67  # ~3:2

        x = (w - photo_w) / 2
        y = m + 20

        self._place_photo(str(photo_path), x, y, photo_w, photo_h)

    def _place_photo(self, path: str, x: float, y: float, w: float, h: float):
        """Place a photo in the PDF with a subtle border/shadow effect"""
        # Shadow/border
        self.pdf.set_fill_color(240, 240, 245)
        self.pdf.set_draw_color(220, 220, 230)
        self.pdf.rect(x - 1, y - 1, w + 2, h + 2, "DF")

        # White mat
        self.pdf.set_fill_color(255, 255, 255)
        self.pdf.rect(x + 1, y + 1, w - 2, h - 2, "F")

        # Place image (centered and fitted)
        try:
            self.pdf.image(path, x=x + 3, y=y + 3, w=w - 6, h=h - 6)
        except Exception as e:
            # Fallback: placeholder
            self.pdf.set_fill_color(200, 200, 210)
            self.pdf.rect(x + 3, y + 3, w - 6, h - 6, "F")
            self.pdf.set_font("CN", "", 10)
            self.pdf.set_text_color(100, 100, 100)
            self.pdf.set_xy(x, y + h / 2)
            self.pdf.cell(w, 10, f"📷 {Path(path).name}", align="C")

    def _photo_caption(self, path: Path) -> str:
        """Generate a simple caption from filename"""
        name = path.stem
        for prefix in ["IMG_", "DSC_", "DSC0", "PANO_", "VID_"]:
            if name.startswith(prefix):
                name = name[len(prefix):]
        for suffix in ["_COVER", "_THUMB", "_original"]:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
        return name[:30] if name else path.name[:30]

    def _setup_ai(self):
        """Initialize AI client for story generation"""
        self.ai_client = None
        api_key = os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
        base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
        
        if not api_key:
            config_path = Path.home() / "ai-chat-loop" / "config.yaml"
            if config_path.exists():
                try:
                    import yaml
                    with open(config_path) as f:
                        cfg = yaml.safe_load(f)
                    api_key = cfg.get("deepseek", {}).get("api_key", "")
                except Exception:
                    pass
        
        if api_key:
            self.ai_client = OpenAI(api_key=api_key, base_url=base_url)
            self.ai_model = model

    def _generate_stories(self, photos: List[Path], album_title: str):
        """Generate AI travel stories for all photos"""
        if not self.ai_client:
            print("   💡 No AI key configured, skipping story generation")
            return
        
        print("   ✍️  AI writing travel stories...")
        
        # Generate in batches of 5 to avoid huge prompts
        batch_size = 5
        for i in range(0, len(photos), batch_size):
            batch = photos[i:i + batch_size]
            
            desc_list = []
            for idx, p in enumerate(batch):
                global_idx = i + idx + 1
                # Get basic file info
                stat = p.stat()
                date_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d")
                desc_list.append(f"[Photo {global_idx}] {p.stem[:30]} (taken around {date_str})")
            
            prompt = f"""You are writing captions for a travel photo album titled "{album_title}".

For each photo below, write a SHORT (12-18 words) warm, personal caption in Chinese.
Make it feel like a real travel memory - specific, sensory, emotional.
NOT generic or AI-sounding. Like a friend writing in a photo album.

Photos:
{chr(10).join(desc_list)}

Reply ONLY with a JSON object mapping photo index to caption:
{{"1": "caption for photo 1", "2": "caption for photo 2"}}"""

            try:
                response = self.ai_client.chat.completions.create(
                    model=self.ai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.8,
                )
                text = response.choices[0].message.content.strip()
                
                # Parse JSON response
                json_match = re.search(r'\{[^}]+\}', text.replace('\n', ' '))
                if json_match:
                    captions = json.loads(json_match.group())
                    for photo_idx_str, caption in captions.items():
                        try:
                            idx = int(photo_idx_str) - 1
                            if 0 <= idx < len(photos):
                                self._story_cache[str(photos[idx])] = caption.strip()
                        except ValueError:
                            pass
                
                print(f"   ✓ Stories generated for photos {i+1}-{min(i+batch_size, len(photos))}")
            except Exception as e:
                print(f"   ⚠️ Story generation failed: {e}")

    def _add_back_cover(self, title: str):
        """Add a back cover page"""
        self.pdf.add_page()
        self.page_count += 1
        w, h = self.PAGE_W, self.PAGE_H

        # Same dark bg
        self.pdf.set_fill_color(15, 23, 42)
        self.pdf.rect(0, 0, w, h, "F")

        # Bottom bar
        self.pdf.set_fill_color(56, 189, 248)
        self.pdf.rect(0, h - 6, w, 6, "F")

        self.pdf.set_y(h * 0.45)
        self.pdf.set_font("CN", "", 14)
        self.pdf.set_text_color(148, 163, 184)
        self.pdf.cell(0, 10, title, align="C", new_x="LMARGIN", new_y="NEXT")

        self.pdf.set_y(self.pdf.get_y() + 6)
        self.pdf.set_font("CN", "", 11)
        self.pdf.set_text_color(100, 116, 139)
        self.pdf.cell(0, 8, "Every journey deserves to be remembered.", align="C", new_x="LMARGIN", new_y="NEXT")

        self.pdf.set_y(self.pdf.get_y() + 4)
        self.pdf.set_font("CN", "", 10)
        self.pdf.set_text_color(71, 85, 105)
        self.pdf.cell(0, 8, f"Generated {datetime.now().strftime('%B %d, %Y')}", align="C")
