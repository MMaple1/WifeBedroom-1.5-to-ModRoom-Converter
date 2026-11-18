#!/usr/bin/env python3
"""Fix Deeproom partners whose deepthroat sprite sits too high.

Converter versions before 2026-11-17 added a [deepthroat] block to every partner they converted for Deeproom
(origin_y 150, v1.5's default, or a v1.5 value copied unchanged), so Deeproom drew the deepthroat sprite
66-70 px too high. This finds those blocks in custom_data.spouse files and fixes them; hand-made blocks are
left alone. Dry run unless --apply; with --apply the originals go to a backup zip next to the folder.

  python Repair_Deepthroat.py "<game>/custom_stuff/custom_wives"            list what would change
  python Repair_Deepthroat.py "<game>/custom_stuff/custom_wives" --apply    fix it
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "core"))
import wbconv  # noqa: E402

if __name__ == "__main__":
    sys.exit(wbconv.repair_deepthroat_main())
