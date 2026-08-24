"""Tests for TagStorageService: persistence round-trips and corruption tolerance."""

import json
from pathlib import Path

import pytest

from services.tag_storage import TagStorageService


@pytest.fixture
def storage(tmp_path: Path) -> TagStorageService:
    return TagStorageService(cache_dir=tmp_path / "tags")


@pytest.fixture
def image(tmp_path: Path) -> Path:
    img = tmp_path / "wallpaper.jpg"
    img.write_bytes(b"fake image")
    return img


class TestSaveLoadRoundTrip:
    def test_save_then_get_tags(self, storage: TagStorageService, image: Path):
        assert storage.save_tags(image, ["nature", "sunset"]) is True
        assert storage.get_tags(image) == ["nature", "sunset"]

    def test_round_trip_with_confidence(self, storage: TagStorageService, image: Path):
        confidence = {"nature": 0.91, "sunset": 0.72}
        storage.save_tags(image, ["nature", "sunset"], confidence=confidence)

        tags, stored_confidence = storage.get_tags_with_confidence(image)

        assert tags == ["nature", "sunset"]
        assert stored_confidence == pytest.approx(confidence)

    def test_saved_file_is_readable_json_with_path(
        self, storage: TagStorageService, image: Path
    ):
        storage.save_tags(image, ["dark"], confidence={"dark": 0.5})

        tag_file = storage._get_tag_file_path(image)
        data = json.loads(tag_file.read_text())
        assert data["path"] == str(image)
        assert data["tags"] == ["dark"]
        assert data["confidence"] == {"dark": 0.5}

    def test_key_stable_across_instances_and_relative_paths(
        self, storage: TagStorageService, image: Path
    ):
        """Same image reached via a different Path spelling maps to one file."""
        other = TagStorageService(cache_dir=storage.cache_dir)
        first = storage._get_tag_file_path(image)
        second = other._get_tag_file_path(Path(str(image)))
        third = storage._get_tag_file_path(image.resolve())

        assert first == second == third

    def test_sequential_writes_are_isolated(
        self, storage: TagStorageService, tmp_path: Path
    ):
        images = []
        for i in range(5):
            img = tmp_path / f"img_{i}.jpg"
            img.write_bytes(b"x")
            images.append(img)
            storage.save_tags(img, [f"tag{i}"])

        for i, img in enumerate(images):
            assert storage.get_tags(img) == [f"tag{i}"]

    def test_get_tags_missing_image_returns_empty(
        self, storage: TagStorageService, tmp_path: Path
    ):
        assert storage.get_tags(tmp_path / "never_seen.jpg") == []

    def test_save_failure_returns_false(self, storage: TagStorageService, image: Path):
        # A directory at the tag-file path makes open(..., "w") raise OSError.
        tag_file = storage._get_tag_file_path(image)
        tag_file.mkdir(parents=True)

        assert storage.save_tags(image, ["x"]) is False


class TestCorruptJsonTolerance:
    def test_corrupt_json_get_tags_returns_empty(
        self, storage: TagStorageService, image: Path, caplog
    ):
        tag_file = storage._get_tag_file_path(image)
        tag_file.write_text("{not valid json!!")

        assert storage.get_tags(image) == []

    def test_corrupt_json_get_tags_with_confidence_returns_empty(
        self, storage: TagStorageService, image: Path
    ):
        tag_file = storage._get_tag_file_path(image)
        tag_file.write_text("[truncated")

        assert storage.get_tags_with_confidence(image) == ([], {})

    def test_missing_tags_key_defaults_to_empty(
        self, storage: TagStorageService, image: Path
    ):
        tag_file = storage._get_tag_file_path(image)
        tag_file.write_text(json.dumps({"path": str(image)}))

        assert storage.get_tags(image) == []
        assert storage.get_tags_with_confidence(image) == ([], {})


class TestUpdateRemove:
    def test_update_overwrites_previous_tags(
        self, storage: TagStorageService, image: Path
    ):
        storage.save_tags(image, ["old", "stale"])
        storage.save_tags(image, ["fresh"], confidence={"fresh": 0.8})

        tags, confidence = storage.get_tags_with_confidence(image)

        assert tags == ["fresh"]
        assert confidence == {"fresh": 0.8}
        assert "old" not in tags

    def test_delete_existing_tags(self, storage: TagStorageService, image: Path):
        storage.save_tags(image, ["nature"])
        assert storage.has_tags(image) is True

        assert storage.delete_tags(image) is True
        assert storage.has_tags(image) is False
        assert storage.get_tags(image) == []

    def test_delete_missing_tags_succeeds(
        self, storage: TagStorageService, tmp_path: Path
    ):
        assert storage.delete_tags(tmp_path / "absent.jpg") is True

    def test_delete_failure_returns_false(
        self, storage: TagStorageService, image: Path
    ):
        storage.save_tags(image, ["nature"])
        # Replace the JSON file with a directory so unlink() fails with an OSError.
        tag_file = storage._get_tag_file_path(image)
        tag_file.unlink()
        tag_file.mkdir()

        assert storage.delete_tags(image) is False


class TestUntaggedQueries:
    def test_has_tags(self, storage: TagStorageService, image: Path):
        assert storage.has_tags(image) is False
        storage.save_tags(image, ["nature"])
        assert storage.has_tags(image) is True

    def test_get_untagged_images_filters_tagged(
        self, storage: TagStorageService, tmp_path: Path
    ):
        tagged = tmp_path / "tagged.jpg"
        untagged_a = tmp_path / "untagged_a.jpg"
        untagged_b = tmp_path / "untagged_b.jpg"
        for p in (tagged, untagged_a, untagged_b):
            p.write_bytes(b"x")
        storage.save_tags(tagged, ["nature"])

        result = storage.get_untagged_images([tagged, untagged_a, untagged_b])

        assert result == [untagged_a, untagged_b]


class TestMissingFileEdgeCases:
    def test_get_tags_with_confidence_missing_image_returns_empty(
        self, storage: TagStorageService, tmp_path: Path
    ):
        assert storage.get_tags_with_confidence(tmp_path / "absent.jpg") == ([], {})
