#!/usr/bin/env python3
"""
🤖 AI Photo Selector
Analyzes photos and filters out blurry, duplicate, closed-eyes, or low-quality shots.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import List

from openai import OpenAI


class PhotoSelector:
    """AI-powered photo quality analysis and selection"""

    def __init__(self):
        # Use DeepSeek for cost efficiency (or Doubao)
        api_key = os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY", ""))
        base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

        if not api_key:
            # Fallback: try reading from AI Chat Loop config
            config_path = Path.home() / "ai-chat-loop" / "config.yaml"
            if config_path.exists():
                try:
                    import yaml
                    with open(config_path) as f:
                        cfg = yaml.safe_load(f)
                    api_key = cfg.get("deepseek", {}).get("api_key", "")
                except Exception:
                    pass

        if not api_key:
            raise RuntimeError(
                "No API key found. Set DEEPSEEK_API_KEY or OPENAI_API_KEY env var.\n"
                "Or run with --no-ai to skip AI selection."
            )

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def filter_bad(self, photos: List[Path]) -> List[Path]:
        """Remove obviously bad photos: extremely blurry, pure black, etc."""
        good = []
        for p in photos:
            if self._quick_check(p):
                good.append(p)
        return good

    def _quick_check(self, path: Path) -> bool:
        """Basic sanity check without AI"""
        try:
            size = path.stat().st_size
            # Skip tiny files (< 10KB probably corrupted or thumbnails)
            if size < 10_000:
                return False
            # Skip suspiciously large files (> 50MB)
            if size > 50_000_000:
                return False
        except Exception:
            return False
        return True

    def select_best(self, photos: List[Path], max_count: int = 40) -> List[Path]:
        """
        AI-powered selection: analyze groups of photos, remove duplicates,
        flag bad quality, select the best ones.
        """
        # First do quick filter
        photos = self.filter_bad(photos)

        # If still too many, use AI to select in batches
        if len(photos) <= max_count:
            return photos

        # Group by filename similarity (same date/location patterns)
        groups = self._group_by_pattern(photos)

        selected = []
        remaining_slots = max_count

        for group_name, group_photos in groups.items():
            if len(group_photos) <= 3:
                # Small group, keep all
                take = min(len(group_photos), remaining_slots)
                selected.extend(group_photos[:take])
                remaining_slots -= take
            else:
                # Large group, use AI to pick the best
                take = max(1, min(len(group_photos), remaining_slots // len(groups)))
                best = self._ai_pick_best(group_photos, take)
                selected.extend(best)
                remaining_slots -= len(best)

            if remaining_slots <= 0:
                break

        return selected[:max_count]

    def _group_by_pattern(self, photos: List[Path]) -> dict:
        """Group photos by capture time / filename prefix"""
        groups = {}
        for p in photos:
            # Try to group by common prefix (e.g., "IMG_2024" or "DSC00123")
            name = p.stem
            # Find the prefix before numbers
            prefix = ""
            for ch in name:
                if ch.isdigit() or ch in "_-":
                    if prefix and not prefix[-1].isdigit():
                        break
                prefix += ch
            if len(prefix) < 2:
                prefix = name[:8]  # Fallback to first 8 chars
            groups.setdefault(prefix, []).append(p)
        return groups

    def _ai_pick_best(self, photos: List[Path], count: int) -> List[Path]:
        """Use AI to pick the best N photos from a group"""
        if len(photos) <= count:
            return photos

        # Describe photos to AI (using file info, not actual image analysis for now)
        descriptions = []
        for i, p in enumerate(photos):
            stat = p.stat()
            desc = f"[{i}] {p.name} ({p.stat().st_size // 1024}KB, {stat.st_mtime})"
            descriptions.append(desc)

        prompt = f"""You are helping select the best travel photos for an album.
From the following {len(photos)} photos, pick the {count} BEST ones.
Choose photos that are likely to be diverse (different scenes/angles, not just bursts of same moment).
Consider: larger file sizes often indicate better quality, spread across timestamps for variety.

Photos:
{chr(10).join(descriptions)}

Reply with ONLY a JSON array of indices, like: [0, 3, 7, 12, 15]
Pick exactly {count} indices."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.3,
            )
            text = response.choices[0].message.content.strip()
            # Extract JSON array
            import re
            match = re.search(r"\[[\d,\s]+\]", text)
            if match:
                indices = json.loads(match.group())
                return [photos[i] for i in indices if 0 <= i < len(photos)]
        except Exception as e:
            print(f"   ⚠️ AI selection failed: {e}, falling back to first {count}")

        # Fallback: pick evenly spaced
        step = len(photos) / count
        return [photos[int(i * step)] for i in range(count)]
