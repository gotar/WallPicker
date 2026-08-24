"""Tests for ThumbnailLoader: worker pool, local generation, memory caching."""

import hashlib
import io
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image

import services.thumbnail_loader as thumbnail_loader_module
from services.thumbnail_loader import ThumbnailLoader


@pytest.fixture(autouse=True)
def isolated_cache_dir(tmp_path: Path, monkeypatch) -> Path:
    """Redirect the module-level disk cache to a temp dir."""
    cache_dir = tmp_path / "thumbnails"
    monkeypatch.setattr(thumbnail_loader_module, "_THUMBNAIL_CACHE_DIR", cache_dir)
    return cache_dir


@pytest.fixture
def loader() -> ThumbnailLoader:
    svc = ThumbnailLoader(max_workers=2)
    yield svc
    svc.shutdown()


@pytest.fixture
def sync_idle_add(mocker):
    """Run GLib.idle_add callbacks immediately (matches ui conftest style)."""
    return mocker.patch(
        "gi.repository.GLib.idle_add",
        side_effect=lambda func, *args: func(*args),
    )


def make_image(path: Path, size=(64, 48), color=(10, 200, 30)) -> Path:
    """Create a real small image on disk with Pillow."""
    Image.new("RGB", size, color).save(path, "PNG")
    return path


def load_with_callback(loader: ThumbnailLoader, target: str, timeout: float = 5.0):
    """Run load_thumbnail_async and wait for the callback on the worker pool."""
    done = threading.Event()
    results: list = []

    def callback(texture):
        results.append(texture)
        done.set()

    loader.load_thumbnail_async(target, callback)
    assert done.wait(timeout), "callback was not invoked"
    return results[0]


class TestCacheKeyStability:
    """MD5-based disk cache keys must be stable across instances (M2)."""

    def test_key_stable_across_instances(self, tmp_path: Path):
        img = make_image(tmp_path / "wall.png")
        first = ThumbnailLoader()._get_local_thumbnail_path(str(img))
        second = ThumbnailLoader()._get_local_thumbnail_path(str(img))
        assert first == second

    def test_key_is_md5_of_path(self, tmp_path: Path):
        img = make_image(tmp_path / "wall.png")
        path = ThumbnailLoader()._get_local_thumbnail_path(str(img))
        expected_hash = hashlib.md5(str(img).encode()).hexdigest()
        assert expected_hash in path.name
        assert path.name.startswith("local_")

    def test_different_paths_produce_different_keys(self, tmp_path: Path):
        a_file = make_image(tmp_path / "a.jpg")
        b_file = make_image(tmp_path / "b.jpg")
        loader = ThumbnailLoader()
        a = loader._get_local_thumbnail_path(str(a_file))
        b = loader._get_local_thumbnail_path(str(b_file))
        assert a != b


class TestLocalThumbnailGeneration:
    """Generate thumbnails from real images created with Pillow."""

    def test_generates_jpeg_bytes_and_disk_entry(
        self,
        loader: ThumbnailLoader,
        tmp_path: Path,
        isolated_cache_dir: Path,
    ):
        img = make_image(tmp_path / "photo.png")

        data = loader._generate_thumbnail(str(img))

        assert data is not None
        buffer = io.BytesIO(data)
        with Image.open(buffer) as decoded:
            assert decoded.format == "JPEG"
            # Aspect preserved, fitted into (200, 160)
            assert decoded.size == (64, 48)

        thumb_files = list(isolated_cache_dir.glob("local_*"))
        assert len(thumb_files) == 1

    def test_reuses_fresh_disk_cache_without_regenerating(
        self, loader: ThumbnailLoader, tmp_path: Path
    ):
        img = make_image(tmp_path / "photo.png")
        thumb_path = loader._get_local_thumbnail_path(str(img))
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        planted = b"planted-cache-bytes"
        thumb_path.write_bytes(planted)
        # Thumbnail just written => newer than source; must be served as-is.

        result = loader._generate_thumbnail(str(img))

        assert result == planted
        assert thumb_path.read_bytes() == planted

    def test_missing_file_returns_none(self, loader: ThumbnailLoader, tmp_path: Path):
        assert loader._generate_thumbnail(str(tmp_path / "missing.png")) is None

    def test_corrupt_source_returns_none(
        self, loader: ThumbnailLoader, tmp_path: Path
    ):
        bad = tmp_path / "broken.jpg"
        bad.write_bytes(b"not-an-image-at-all")
        assert loader._generate_thumbnail(str(bad)) is None

    def test_rgba_source_converted_to_rgb(
        self, loader: ThumbnailLoader, tmp_path: Path
    ):
        img = tmp_path / "alpha.png"
        Image.new("RGBA", (32, 32), (255, 0, 0, 128)).save(img, "PNG")

        data = loader._generate_thumbnail(str(img))

        assert data is not None
        with Image.open(io.BytesIO(data)) as decoded:
            assert decoded.mode == "RGB"


class TestMemoryCache:
    """In-memory cache hit / miss / invalidation behaviour."""

    def test_miss_then_hit_skips_regeneration(
        self, loader: ThumbnailLoader, tmp_path: Path, sync_idle_add
    ):
        img = make_image(tmp_path / "cached.png")

        first = load_with_callback(loader, str(img))
        assert first is not None
        assert str(img) in loader._local_thumbnail_cache

        regenerate_spy_on(loader)
        second = load_with_callback(loader, str(img))

        assert second is not None
        assert loader._generate_calls == 0, "second load must come from memory cache"

    def test_clear_memory_cache_forces_regeneration(
        self, loader: ThumbnailLoader, tmp_path: Path, sync_idle_add
    ):
        img = make_image(tmp_path / "cleared.png")
        load_with_callback(loader, str(img))
        loader.clear_memory_cache()

        assert loader._local_thumbnail_cache == {}
        load_with_callback(loader, str(img))
        assert str(img) in loader._local_thumbnail_cache

    def test_invalidate_drops_single_entry(
        self, loader: ThumbnailLoader, tmp_path: Path, sync_idle_add
    ):
        a = make_image(tmp_path / "a.png", color=(255, 0, 0))
        b = make_image(tmp_path / "b.png", color=(0, 0, 255))
        load_with_callback(loader, str(a))
        load_with_callback(loader, str(b))

        loader.invalidate(str(a))

        assert str(a) not in loader._local_thumbnail_cache
        assert str(b) in loader._local_thumbnail_cache

    def test_invalidate_unknown_path_is_noop(self, loader: ThumbnailLoader):
        loader.invalidate("/does/not/exist.png")  # Must not raise


def regenerate_spy_on(loader: ThumbnailLoader) -> None:
    original = loader._generate_thumbnail
    loader._generate_calls = 0

    def counting(path):
        loader._generate_calls += 1
        return original(path)

    loader._generate_thumbnail = counting


class TestWorkerPoolLifecycle:
    def test_shutdown_stops_executor(self, tmp_path: Path, mocker):
        svc = ThumbnailLoader(max_workers=1)
        shutdown_spy = mocker.spy(svc._executor, "shutdown")

        svc.shutdown()

        shutdown_spy.assert_called_once_with(wait=False)

    def test_del_shuts_down_executor_without_error(self, tmp_path: Path):
        svc = ThumbnailLoader(max_workers=1)
        executor = svc._executor
        svc.__del__()  # Explicit call: must not raise
        executor.shutdown(wait=True)


class TestAsyncLoading:
    """End-to-end load_thumbnail_async paths."""

    def test_local_file_produces_texture(
        self, loader: ThumbnailLoader, tmp_path: Path, sync_idle_add
    ):
        img = make_image(tmp_path / "texture.png")

        texture = load_with_callback(loader, str(img))

        assert texture is not None

    def test_nonexistent_local_path_callbacks_none(
        self, loader: ThumbnailLoader, tmp_path: Path, sync_idle_add
    ):
        result = load_with_callback(loader, str(tmp_path / "ghost.png"))
        assert result is None

    def test_remote_url_uses_thumbnail_cache(
        self, loader: ThumbnailLoader, tmp_path: Path, mocker, sync_idle_add
    ):
        remote_thumb = make_image(tmp_path / "remote.jpg")
        cache_mock = mocker.MagicMock()
        cache_mock.get_or_download_sync.return_value = remote_thumb
        loader._thumbnail_cache = cache_mock

        texture = load_with_callback(loader, "https://example.com/thumb.jpg")

        assert texture is not None
        cache_mock.get_or_download_sync.assert_called_once_with(
            "https://example.com/thumb.jpg"
        )

    def test_remote_url_cache_miss_callbacks_none(
        self, loader: ThumbnailLoader, mocker, sync_idle_add
    ):
        cache_mock = mocker.MagicMock()
        cache_mock.get_or_download_sync.return_value = None
        loader._thumbnail_cache = cache_mock

        result = load_with_callback(loader, "https://example.com/thumb.jpg")

        assert result is None

    def test_remote_url_download_failure_callbacks_none(
        self, loader: ThumbnailLoader, mocker, sync_idle_add
    ):
        cache_mock = mocker.MagicMock()
        cache_mock.get_or_download_sync.side_effect = OSError("network down")
        loader._thumbnail_cache = cache_mock

        result = load_with_callback(loader, "https://example.com/thumb.jpg")

        assert result is None


class TestFailureTolerance:
    """Degraded environments must always end in a callback (never a hang)."""

    def test_cache_dir_creation_failure_is_tolerated(self, tmp_path, mocker):
        mocker.patch("pathlib.Path.mkdir", side_effect=OSError("read-only fs"))

        svc = ThumbnailLoader(max_workers=1)  # Must not raise

        svc.shutdown()

    def test_remote_read_failure_callbacks_none(
        self, loader: ThumbnailLoader, tmp_path: Path, mocker, sync_idle_add
    ):
        remote_thumb = make_image(tmp_path / "remote.jpg")
        cache_mock = mocker.MagicMock()
        cache_mock.get_or_download_sync.return_value = remote_thumb
        loader._thumbnail_cache = cache_mock
        mocker.patch("pathlib.Path.read_bytes", side_effect=OSError("read failed"))

        result = load_with_callback(loader, "https://example.com/thumb.jpg")

        assert result is None

    def test_texture_decode_failure_on_fresh_local_callbacks_none(
        self, loader: ThumbnailLoader, tmp_path: Path, mocker, sync_idle_add
    ):
        img = make_image(tmp_path / "fresh.png")
        mocker.patch(
            "gi.repository.Gdk.Texture.new_from_bytes",
            side_effect=Exception("decode failure"),
        )

        result = load_with_callback(loader, str(img))

        assert result is None

    def test_texture_decode_failure_on_cached_local_callbacks_none(
        self, loader: ThumbnailLoader, tmp_path: Path, mocker, sync_idle_add
    ):
        img = make_image(tmp_path / "cached.png")
        load_with_callback(loader, str(img))  # populates memory cache

        mocker.patch(
            "gi.repository.Gdk.Texture.new_from_bytes",
            side_effect=Exception("decode failure"),
        )
        result = load_with_callback(loader, str(img))

        assert result is None

    def test_remote_texture_decode_failure_callbacks_none(
        self, loader: ThumbnailLoader, tmp_path: Path, mocker, sync_idle_add
    ):
        remote_thumb = make_image(tmp_path / "remote2.jpg")
        cache_mock = mocker.MagicMock()
        cache_mock.get_or_download_sync.return_value = remote_thumb
        loader._thumbnail_cache = cache_mock
        mocker.patch(
            "gi.repository.Gdk.Texture.new_from_bytes",
            side_effect=Exception("bad image"),
        )

        result = load_with_callback(loader, "https://example.com/thumb.jpg")

        assert result is None


class TestCorruptCacheInvalidation:
    """M4: decode failure at the consumption point must invalidate the
    corrupt cache entry and re-download / regenerate exactly once."""

    def test_remote_corrupt_cache_invalidated_and_redownloaded(
        self, loader: ThumbnailLoader, tmp_path: Path, mocker, sync_idle_add
    ):
        corrupt_file = tmp_path / "corrupt.jpg"
        corrupt_file.write_bytes(b"garbage-not-an-image")
        good_file = make_image(tmp_path / "good.jpg")
        cache_mock = mocker.MagicMock()
        cache_mock.get_or_download_sync.side_effect = [corrupt_file, good_file]
        loader._thumbnail_cache = cache_mock
        mocker.patch(
            "gi.repository.Gdk.Texture.new_from_bytes",
            side_effect=[Exception("decode failure"), MagicMock()],
        )

        texture = load_with_callback(loader, "https://example.com/thumb.jpg")

        assert texture is not None
        # The corrupt entry was invalidated (by URL) and re-downloaded once.
        cache_mock.invalidate.assert_called_once_with("https://example.com/thumb.jpg")
        assert cache_mock.get_or_download_sync.call_count == 2

    def test_remote_corrupt_twice_gives_up_after_one_retry(
        self, loader: ThumbnailLoader, tmp_path: Path, mocker, sync_idle_add
    ):
        corrupt_a = tmp_path / "corrupt-a.jpg"
        corrupt_a.write_bytes(b"garbage-a")
        corrupt_b = tmp_path / "corrupt-b.jpg"
        corrupt_b.write_bytes(b"garbage-b")
        cache_mock = mocker.MagicMock()
        cache_mock.get_or_download_sync.side_effect = [corrupt_a, corrupt_b]
        loader._thumbnail_cache = cache_mock
        mocker.patch(
            "gi.repository.Gdk.Texture.new_from_bytes",
            side_effect=Exception("still broken"),
        )

        result = load_with_callback(loader, "https://example.com/thumb.jpg")

        assert result is None
        # Exactly one invalidation+retry; no infinite loop.
        cache_mock.invalidate.assert_called_once_with("https://example.com/thumb.jpg")
        assert cache_mock.get_or_download_sync.call_count == 2

    def test_memory_cached_corrupt_bytes_invalidated_and_regenerated(
        self, loader: ThumbnailLoader, tmp_path: Path, mocker, sync_idle_add
    ):
        img = make_image(tmp_path / "regen.png")  # valid source on disk
        loader._local_thumbnail_cache[str(img)] = b"corrupt-memory-bytes"
        mocker.patch(
            "gi.repository.Gdk.Texture.new_from_bytes",
            side_effect=[Exception("decode failure"), MagicMock()],
        )

        texture = load_with_callback(loader, str(img))

        assert texture is not None
        # Corrupt memory entry was dropped and regenerated from disk.
        assert loader._local_thumbnail_cache[str(img)] != b"corrupt-memory-bytes"

    def test_corrupt_disk_thumbnail_is_deleted_on_decode_failure(
        self, loader: ThumbnailLoader, tmp_path: Path, mocker, sync_idle_add
    ):
        img = make_image(tmp_path / "disk-corrupt.png")
        thumb_path = loader._get_local_thumbnail_path(str(img))
        thumb_path.parent.mkdir(parents=True, exist_ok=True)
        thumb_path.write_bytes(b"planted-garbage")  # newer than source => served
        mocker.patch(
            "gi.repository.Gdk.Texture.new_from_bytes",
            side_effect=Exception("decode failure"),
        )
        load_with_callback(loader, str(img))  # callback(None) is fine here

        # The corrupt on-disk thumbnail entry must have been removed so the
        # next load regenerates it instead of serving garbage forever.
        assert not thumb_path.exists()
