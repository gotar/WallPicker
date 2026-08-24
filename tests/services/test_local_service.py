"""
Tests for LocalWallpaperService
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.local_service import LocalWallpaper, LocalWallpaperService
from services.tag_storage import TagStorageService


@pytest.fixture(autouse=True)
def _reset_class_level_tag_storage():
    """LocalWallpaper caches a TagStorageService on the class; isolate per test."""
    yield
    if hasattr(LocalWallpaper, "_tag_storage"):
        del LocalWallpaper._tag_storage


class TestLocalWallpaperModel:
    """Test LocalWallpaper model"""

    def test_create_local_wallpaper(self):
        """Test creating LocalWallpaper object"""
        path = Path("/test/image.jpg")
        wallpaper = LocalWallpaper(
            path=path,
            filename="image.jpg",
            size=1024,
            modified_time=1234567890.0,
        )

        assert wallpaper.path == path
        assert wallpaper.filename == "image.jpg"
        assert wallpaper.size == 1024
        assert wallpaper.modified_time == 1234567890.0

    def test_gobject_subclass(self):
        """Test LocalWallpaper is GObject subclass"""
        wallpaper = LocalWallpaper(
            path=Path("/test/image.jpg"),
            filename="image.jpg",
            size=1024,
            modified_time=1234567890.0,
        )

        assert wallpaper.__gtype_name__ == "LocalWallpaper"


class TestLocalWallpaperServiceInit:
    """Test LocalWallpaperService initialization"""

    def test_init_default_pictures_dir(self):
        """Test initialization with default Pictures directory"""
        service = LocalWallpaperService()

        expected_dir = Path.home() / "Pictures"
        assert service.pictures_dir == expected_dir

    def test_init_custom_pictures_dir(self, tmp_path):
        """Test initialization with custom directory"""
        custom_dir = tmp_path / "wallpapers"
        custom_dir.mkdir()

        service = LocalWallpaperService(pictures_dir=custom_dir)

        assert service.pictures_dir == custom_dir

    def test_init_fallback_to_default(self, tmp_path):
        """Test fallback to default when custom dir doesn't exist"""
        # Create a non-existent path
        non_existent = tmp_path / "does_not_exist"

        service = LocalWallpaperService(pictures_dir=non_existent)

        # Should fall back to default Pictures directory
        assert service.pictures_dir == Path.home() / "Pictures"

    def test_get_pictures_dir(self, tmp_path):
        """Test getting pictures directory"""
        service = LocalWallpaperService(pictures_dir=tmp_path)

        assert service.get_pictures_dir() == tmp_path


class TestGetWallpapers:
    """Test get_wallpapers method"""

    def test_get_wallpapers_recursive(self, tmp_path):
        """Test getting wallpapers recursively"""
        # Create test files
        (tmp_path / "image1.jpg").touch()
        (tmp_path / "image2.png").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "image3.webp").touch()
        (tmp_path / "not_image.txt").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers(recursive=True)

        assert len(wallpapers) == 3
        assert all(isinstance(w, LocalWallpaper) for w in wallpapers)
        filenames = [w.filename for w in wallpapers]
        assert "image1.jpg" in filenames
        assert "image2.png" in filenames
        assert "image3.webp" in filenames

    def test_get_wallpapers_non_recursive(self, tmp_path):
        """Test getting wallpapers non-recursively"""
        # Create test files
        (tmp_path / "image1.jpg").touch()
        (tmp_path / "image2.png").touch()
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        (subdir / "image3.webp").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers(recursive=False)

        assert len(wallpapers) == 2
        filenames = [w.filename for w in wallpapers]
        assert "image1.jpg" in filenames
        assert "image2.png" in filenames
        assert "image3.webp" not in filenames

    def test_get_wallpapers_sorted_by_modified_time(self, tmp_path):
        """Test that wallpapers are sorted by modification time (newest first)"""
        import time

        # Create files with different timestamps
        (tmp_path / "old.jpg").touch()
        time.sleep(0.1)
        (tmp_path / "new.jpg").touch()
        time.sleep(0.1)
        (tmp_path / "newest.jpg").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers()

        assert len(wallpapers) == 3
        # Newest should be first
        assert wallpapers[0].filename == "newest.jpg"
        assert wallpapers[1].filename == "new.jpg"
        assert wallpapers[2].filename == "old.jpg"

    def test_get_wallpapers_supported_extensions(self, tmp_path):
        """Test that only supported image extensions are included"""
        supported = [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"]
        unsupported = [".txt", ".pdf", ".doc"]

        for ext in supported:
            (tmp_path / f"image{ext}").touch()

        for ext in unsupported:
            (tmp_path / f"file{ext}").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers()

        assert len(wallpapers) == len(supported)
        for w in wallpapers:
            assert w.path.suffix.lower() in service.SUPPORTED_EXTENSIONS

    def test_get_wallpapers_case_insensitive_extensions(self, tmp_path):
        """Test that extension matching is case-insensitive"""
        (tmp_path / "IMAGE1.JPG").touch()
        (tmp_path / "image2.PNG").touch()
        (tmp_path / "Image3.WebP").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers()

        assert len(wallpapers) == 3

    def test_get_wallpapers_empty_directory(self, tmp_path):
        """Test getting wallpapers from empty directory"""
        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers()

        assert wallpapers == []

    def test_get_wallpapers_directory_not_exists(self, tmp_path):
        """Test getting wallpapers from non-existent directory"""
        non_existent = tmp_path / "does_not_exist"
        service = LocalWallpaperService(pictures_dir=non_existent)

        # Should return empty list (not raise exception)
        wallpapers = service.get_wallpapers()
        assert wallpapers == []

    def test_get_wallpapers_includes_metadata(self, tmp_path):
        """Test that wallpapers include correct file metadata"""
        test_file = tmp_path / "test.jpg"
        test_file.touch()
        test_file.write_bytes(b"x" * 1024)  # 1KB file

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers()

        assert len(wallpapers) == 1
        wallpaper = wallpapers[0]
        assert wallpaper.path == test_file
        assert wallpaper.filename == "test.jpg"
        assert wallpaper.size == 1024
        assert isinstance(wallpaper.modified_time, float)


class TestDeleteWallpaper:
    """Test delete_wallpaper method"""

    def test_delete_wallpaper_success(self, tmp_path):
        """Test successful deletion with mocked send2trash"""
        test_file = tmp_path / "delete_me.jpg"
        test_file.write_bytes(b"test content")  # Write content so file exists

        service = LocalWallpaperService(pictures_dir=tmp_path)

        with patch("services.local_service.send2trash") as mock_send2trash:
            result = service.delete_wallpaper(test_file)

            assert result is True
            mock_send2trash.assert_called_once_with(str(test_file))

    def test_delete_wallpaper_non_existent(self, tmp_path):
        """Test deleting non-existent file"""
        non_existent = tmp_path / "does_not_exist.jpg"

        service = LocalWallpaperService(pictures_dir=tmp_path)
        result = service.delete_wallpaper(non_existent)

        assert result is False

    def test_delete_wallpaper_with_mock_send2trash(self, tmp_path):
        """Test that send2trash is called correctly"""
        test_file = tmp_path / "test.jpg"
        test_file.touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)

        with patch("services.local_service.send2trash") as mock_send2trash:
            result = service.delete_wallpaper(test_file)

            mock_send2trash.assert_called_once_with(str(test_file))
            assert result is True


class TestSearchWallpapers:
    """Test search_wallpapers method"""

    def test_search_empty_query(self, tmp_path):
        """Test search with empty query returns all wallpapers"""
        (tmp_path / "anime.jpg").touch()
        (tmp_path / "nature.png").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("")

        assert len(results) == 2

    def test_search_whitespace_query(self, tmp_path):
        """Test search with whitespace query returns all wallpapers"""
        (tmp_path / "anime.jpg").touch()
        (tmp_path / "nature.png").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("   ")

        assert len(results) == 2

    def test_search_with_results(self, tmp_path):
        """Test search with matching results"""
        (tmp_path / "anime_girl.jpg").touch()
        (tmp_path / "anime_boy.png").touch()
        (tmp_path / "nature.jpg").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("anime")

        assert len(results) == 2
        filenames = [w.filename for w in results]
        assert "anime_girl.jpg" in filenames
        assert "anime_boy.png" in filenames
        assert "nature.jpg" not in filenames

    def test_search_no_results(self, tmp_path):
        """Test search with no matching results"""
        (tmp_path / "anime.jpg").touch()
        (tmp_path / "nature.jpg").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("mountain")

        assert results == []

    def test_search_partial_match(self, tmp_path):
        """Test fuzzy matching with partial strings"""
        (tmp_path / "beautiful_landscape.jpg").touch()
        (tmp_path / "land_scape.png").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("scape")

        # Should match both with "scape" substring
        assert len(results) >= 1

    def test_search_with_custom_wallpaper_list(self):
        """Test search with provided wallpaper list"""
        wallpapers = [
            LocalWallpaper(
                path=Path("/anime.jpg"),
                filename="anime.jpg",
                size=1024,
                modified_time=1234567890.0,
            ),
            LocalWallpaper(
                path=Path("/nature.jpg"),
                filename="nature.jpg",
                size=2048,
                modified_time=1234567891.0,
            ),
        ]

        service = LocalWallpaperService()
        results = service.search_wallpapers("anime", wallpapers=wallpapers)

        assert len(results) == 1
        assert results[0].filename == "anime.jpg"

    def test_search_custom_list_empty(self, tmp_path):
        """Test search with empty custom wallpaper list"""
        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("anime", wallpapers=[])

        assert results == []

    def test_search_score_threshold(self, tmp_path):
        """Test that only results with score >= 50 are returned"""
        (tmp_path / "anime_girl.jpg").touch()
        (tmp_path / "nature.jpg").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("anime")

        # "anime_girl.jpg" should match with high score
        # "nature.jpg" should not match (score < 50)
        assert len(results) == 1
        assert results[0].filename == "anime_girl.jpg"

    def test_search_sort_by_relevance(self, tmp_path):
        """Test that results are sorted by relevance score"""
        (tmp_path / "anime_girl.jpg").touch()
        (tmp_path / "anime.jpg").touch()
        (tmp_path / "something_anime_related.png").touch()

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("anime")

        # All should match "anime"
        assert len(results) == 3
        # Results should be sorted by relevance (fuzzy matching)
        # The exact match "anime.jpg" might not be first due to fuzzy scoring
        filenames = [w.filename for w in results]
        assert "anime.jpg" in filenames
        assert "anime_girl.jpg" in filenames
        assert "something_anime_related.png" in filenames


class TestSupportedExtensions:
    """Test supported extensions configuration"""

    def test_supported_extensions_set(self):
        """Test that SUPPORTED_EXTENSIONS includes common image formats"""
        service = LocalWallpaperService()

        expected_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
        assert service.SUPPORTED_EXTENSIONS == expected_extensions


class TestResolutionLazyLoading:
    """Resolution is decoded lazily from the real image file."""

    def test_resolution_read_from_real_image(self, tmp_path):
        img = tmp_path / "photo.jpg"
        Image.new("RGB", (64, 48), (1, 2, 3)).save(img, "PNG")  # PNG content, .jpg name

        wp = LocalWallpaper(
            path=img,
            filename="photo.jpg",
            size=img.stat().st_size,
            modified_time=0.0,
        )

        assert wp.resolution == "64x48"

    def test_resolution_is_cached_after_first_access(self, tmp_path, mocker):
        img = tmp_path / "photo.png"
        Image.new("RGB", (10, 20)).save(img)
        wp = LocalWallpaper(
            path=img,
            filename="photo.png",
            size=1,
            modified_time=0.0,
        )

        open_spy = mocker.spy(Image, "open")
        assert wp.resolution == "10x20"
        _ = wp.resolution  # second access

        assert open_spy.call_count == 1

    def test_resolution_failure_yields_empty_string(self, tmp_path):
        broken = tmp_path / "broken.jpg"
        broken.write_bytes(b"garbage")

        wp = LocalWallpaper(path=broken, filename="broken.jpg", size=7, modified_time=0.0)

        assert wp.resolution == ""

    def test_ensure_metadata_loaded_eagerly(self, tmp_path):
        img = tmp_path / "eager.png"
        Image.new("RGB", (8, 8)).save(img)
        wp = LocalWallpaper(path=img, filename="eager.png", size=1, modified_time=0.0)

        wp.ensure_metadata_loaded()

        assert wp.resolution == "8x8"
        assert wp._tags_loaded is True


class TestTagsCaching:
    """Tags come from TagStorageService exactly once per wallpaper (L2)."""

    @pytest.fixture
    def storage(self, tmp_path):
        storage = TagStorageService(cache_dir=tmp_path / "tags")
        # Pre-seed the class-level cache so no real ~/.cache path is touched.
        LocalWallpaper._tag_storage = storage
        return storage

    def test_tags_loaded_from_storage(self, storage, tmp_path):
        img = tmp_path / "tagged.png"
        img.write_bytes(b"x")
        storage.save_tags(img, ["nature", "sunset"])

        wp = LocalWallpaper(path=img, filename="tagged.png", size=1, modified_time=0.0)

        assert wp.tags == ["nature", "sunset"]
        assert wp._tags_loaded is True

    def test_second_access_does_not_reread_disk(self, storage, tmp_path, mocker):
        img = tmp_path / "once.png"
        img.write_bytes(b"x")
        storage.save_tags(img, ["nature"])
        wp = LocalWallpaper(path=img, filename="once.png", size=1, modified_time=0.0)

        get_spy = mocker.spy(storage, "get_tags")
        first = wp.tags
        second = wp.tags  # must be served from memory

        assert first == second == ["nature"]
        assert get_spy.call_count == 1

    def test_negative_result_is_not_reread(self, storage, tmp_path, mocker):
        """An empty tag cache must not trigger a disk read on every access (L2)."""
        img = tmp_path / "untagged.png"
        img.write_bytes(b"x")
        wp = LocalWallpaper(path=img, filename="untagged.png", size=1, modified_time=0.0)

        get_spy = mocker.spy(storage, "get_tags")
        assert wp.tags == []
        assert wp.tags == []
        assert wp.tags == []

        assert get_spy.call_count == 1

    def test_preloaded_tags_skip_storage_entirely(self, storage, tmp_path, mocker):
        create_spy = mocker.spy(TagStorageService, "get_tags")
        wp = LocalWallpaper(
            path=tmp_path / "pre.png",
            filename="pre.png",
            size=1,
            modified_time=0.0,
            tags=["anime"],
        )

        assert wp.tags == ["anime"]
        assert wp._tags_loaded is True
        assert create_spy.call_count == 0

    def test_tags_setter_marks_loaded(self, storage, tmp_path):
        wp = LocalWallpaper(path=tmp_path / "s.png", filename="s.png", size=1,
                            modified_time=0.0)

        wp.tags = ["manual"]

        assert wp._tags_loaded is True
        assert wp.tags == ["manual"]

    def test_storage_failure_falls_back_to_empty_list(self, tmp_path, mocker):
        mocker.patch(
            "services.tag_storage.TagStorageService",
            side_effect=RuntimeError("boom"),
        )
        if hasattr(LocalWallpaper, "_tag_storage"):
            del LocalWallpaper._tag_storage

        wp = LocalWallpaper(path=tmp_path / "f.png", filename="f.png", size=1,
                            modified_time=0.0)

        assert wp.tags == []
        assert wp._tags_loaded is True


class TestScanRobustness:
    def test_scan_ignores_directories_named_like_images(self, tmp_path):
        (tmp_path / "fake.jpg").mkdir()
        (tmp_path / "real.jpg").write_bytes(b"x")

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = service.get_wallpapers()

        assert [w.filename for w in wallpapers] == ["real.jpg"]

    def test_get_wallpapers_async_preloads_metadata(self, tmp_path):
        img = tmp_path / "a.png"
        Image.new("RGB", (6, 4)).save(img)
        subdir = tmp_path / "nested"
        subdir.mkdir()
        nested = subdir / "b.png"
        Image.new("RGB", (5, 5)).save(nested)

        service = LocalWallpaperService(pictures_dir=tmp_path)
        wallpapers = asyncio.run(service.get_wallpapers_async())

        assert len(wallpapers) == 2
        resolutions = {w.filename: w.resolution for w in wallpapers}
        assert resolutions["a.png"] == "6x4"
        assert resolutions["b.png"] == "5x5"

    def test_search_tag_only_match_is_included_and_ranked(self, tmp_path):
        """A tag hit qualifies a file whose name doesn't match at all."""
        by_tag = LocalWallpaper(
            path=tmp_path / "x0947.jpg",
            filename="x0947.jpg",
            size=1,
            modified_time=1.0,
            tags=["sunset"],
        )
        by_name = LocalWallpaper(
            path=tmp_path / "sunset_cliff.jpg",
            filename="sunset_cliff.jpg",
            size=1,
            modified_time=2.0,
            tags=[],
        )

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = service.search_wallpapers("sunset", wallpapers=[by_tag, by_name])

        filenames = [w.filename for w in results]
        # Filename match scores higher (100 vs tag bonus 80), tag-only still included.
        assert filenames == ["sunset_cliff.jpg", "x0947.jpg"]


class TestDeleteAsync:
    async def test_delete_wallpaper_async_trashes_file(self, tmp_path, mocker):
        send2trash_mock = mocker.patch("services.local_service.send2trash")
        test_file = tmp_path / "gone.jpg"
        test_file.write_bytes(b"data")

        service = LocalWallpaperService(pictures_dir=tmp_path)
        result = await service.delete_wallpaper_async(test_file)

        assert result is True
        send2trash_mock.assert_called_once_with(str(test_file))


class TestErrorPaths:
    """Defensive error handling keeps the UI alive on I/O failures."""

    def test_resolution_setter_stores_value(self, tmp_path):
        wp = LocalWallpaper(path=tmp_path / "s.png", filename="s.png", size=1,
                            modified_time=0.0)

        wp.resolution = "1920x1080"

        assert wp.resolution == "1920x1080"

    def test_scan_error_is_swallowed_and_returns_partial(self, tmp_path, mocker):
        mocker.patch("pathlib.Path.glob", side_effect=OSError("permission denied"))

        service = LocalWallpaperService(pictures_dir=tmp_path)

        assert service.get_wallpapers() == []

    def test_delete_wallpaper_send2trash_failure_returns_false(
        self, tmp_path, mocker
    ):
        existing = tmp_path / "doomed.jpg"
        existing.write_bytes(b"data")
        mocker.patch("services.local_service.send2trash",
                     side_effect=OSError("trash unavailable"))

        service = LocalWallpaperService(pictures_dir=tmp_path)

        assert service.delete_wallpaper(existing) is False

    async def test_search_wallpapers_async_delegates_to_sync(self, tmp_path):
        (tmp_path / "anime.jpg").write_bytes(b"x")

        service = LocalWallpaperService(pictures_dir=tmp_path)
        results = await service.search_wallpapers_async("anime")

        assert [w.filename for w in results] == ["anime.jpg"]
