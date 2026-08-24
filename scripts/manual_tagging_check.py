#!/usr/bin/env python3
"""Manual smoke check for TagGenerationService against a real image.

Not a unit test: it hits the real CLIP model / clip-cpp binary and expects an
image on disk. Run from the repository root:

    python scripts/manual_tagging_check.py [path/to/image.jpg]
"""

import asyncio
import sys
from pathlib import Path

# Allow running from a checkout without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from services.tag_generation import TagGenerationService  # noqa: E402

DEFAULT_IMAGE = Path("/home/gotar/Wallpapers/00700_yellowlilly_1680x1050.jpg")


async def test_tagging(image_path: Path):
    try:
        service = TagGenerationService()
        print("TagGenerationService imported successfully")
    except Exception as e:
        print(f"Import error: {e}")
        return

    if not image_path.exists():
        print(f"Image not found: {image_path}")
        return

    print(f"Testing AI tagging on {image_path}")
    try:
        tags, confidences = await service.generate_tags_async(image_path)
        print("Tags generated successfully:")
        print(f"Tags: {tags}")
        print(f"Confidences: {confidences}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IMAGE
    asyncio.run(test_tagging(target))
