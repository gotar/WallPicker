#!/usr/bin/env python3
import asyncio
from pathlib import Path

from src.services.tag_generation import TagGenerationService


async def test_tagging():
    try:
        service = TagGenerationService()
        print("TagGenerationService imported successfully")
    except Exception as e:
        print(f"Import error: {e}")
        return

    image_path = Path("/home/gotar/Wallpapers/00700_yellowlilly_1680x1050.jpg")

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
    asyncio.run(test_tagging())
