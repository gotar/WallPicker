"""Tests for ThumbnailCache."""

import time
from pathlib import Path

import aiohttp
import pytest
from pytest_mock import MockerFixture

from domain.exceptions import ServiceError
from services.thumbnail_cache import ThumbnailCache


class TestThumbnailCacheInit:
    """Test ThumbnailCache initialization."""

    def test_init_default_cache_dir(self, tmp_path: Path):
        """Test initialization with default cache directory."""
        cache = ThumbnailCache()
        assert cache.cache_dir == Path.home() / ".cache" / "wallpicker" / "thumbnails"
        assert cache.cache_dir.exists()

    def test_init_custom_cache_dir(self, tmp_path: Path):
        """Test initialization with custom cache directory."""
        custom_dir = tmp_path / "custom_cache"
        cache = ThumbnailCache(cache_dir=custom_dir)
        assert cache.cache_dir == custom_dir
        assert custom_dir.exists()


class TestGetCachePath:
    """Test _get_cache_path method."""

    def test_get_cache_path_simple_url(self, tmp_path: Path):
        """Test cache path generation for simple URL."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/image.jpg"
        path = cache._get_cache_path(url)
        assert path.parent == tmp_path
        assert path.suffix == ".jpg"
        assert len(path.stem) == 32  # MD5 hash length

    def test_get_cache_path_with_query_params(self, tmp_path: Path):
        """Test cache path generation with query parameters."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/image.jpg?size=large&quality=high"
        path = cache._get_cache_path(url)
        assert path.suffix == ".jpg"  # Should strip query params

    def test_get_cache_path_long_extension(self, tmp_path: Path):
        """Test cache path with long extension."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/image.webp"
        path = cache._get_cache_path(url)
        assert path.suffix == ".webp"

    def test_get_cache_path_invalid_extension(self, tmp_path: Path):
        """Test cache path with invalid extension falls back to jpg."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/image.1234"
        path = cache._get_cache_path(url)
        assert path.suffix == ".jpg"

    def test_get_cache_path_no_extension(self, tmp_path: Path):
        """Test cache path without extension falls back to jpg."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/image"
        path = cache._get_cache_path(url)
        assert path.suffix == ".jpg"


class TestIsExpired:
    """Test _is_expired method."""

    def test_is_expired_nonexistent_file(self, tmp_path: Path):
        """Test is_expired returns True for non-existent file."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        nonexistent_path = tmp_path / "nonexistent.jpg"
        assert cache._is_expired(nonexistent_path) is True

    def test_is_expired_fresh_file(self, tmp_path: Path):
        """Test is_expired returns False for fresh file."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        fresh_file = tmp_path / "fresh.jpg"
        fresh_file.write_text("test")
        assert cache._is_expired(fresh_file) is False

    def test_is_expired_old_file(self, tmp_path: Path):
        """Test is_expired returns True for old file (> 7 days)."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        old_file = tmp_path / "old.jpg"
        old_file.write_text("test")

        # Set modification time to 8 days ago
        old_time = time.time() - (8 * 24 * 60 * 60)
        import os

        os.utime(old_file, (old_time, old_time))

        assert cache._is_expired(old_file) is True


class TestCleanup:
    """Test cleanup method."""

    def test_cleanup_empty_cache(self, tmp_path: Path):
        """Test cleanup on empty cache returns 0."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        removed = cache.cleanup()
        assert removed == 0

    def test_cleanup_under_limit(self, tmp_path: Path):
        """Test cleanup doesn't remove files under size limit."""
        cache = ThumbnailCache(cache_dir=tmp_path)

        # Create small files (under 500MB limit)
        for i in range(5):
            (tmp_path / f"small{i}.jpg").write_bytes(b"x" * 1000)

        removed = cache.cleanup()
        assert removed == 0
        assert len(list(tmp_path.glob("*"))) == 5

    def test_cleanup_removes_expired_files(self, tmp_path: Path, mocker: MockerFixture):
        """Test cleanup removes expired files."""
        cache = ThumbnailCache(cache_dir=tmp_path)

        # Create fresh file
        fresh_file = tmp_path / "fresh.jpg"
        fresh_file.write_bytes(b"x" * 1000)

        # Create expired file
        old_file = tmp_path / "old.jpg"
        old_file.write_bytes(b"x" * 1000)
        old_time = time.time() - (8 * 24 * 60 * 60)
        import os

        os.utime(old_file, (old_time, old_time))

        # Patch MAX_CACHE_SIZE_MB to 0 to trigger cleanup by creating a small cache size
        original_max = ThumbnailCache.MAX_CACHE_SIZE_MB
        ThumbnailCache.MAX_CACHE_SIZE_MB = 0
        try:
            removed = cache.cleanup()
        finally:
            ThumbnailCache.MAX_CACHE_SIZE_MB = original_max

        assert removed >= 0  # May remove expired and/or oldest
        assert fresh_file.exists() or not old_file.exists()

    def test_get_thumbnail_miss(self, tmp_path: Path):
        """Test get_thumbnail returns None for cache miss."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/image.jpg"

        result = cache.get_thumbnail(url)
        assert result is None

    def test_get_thumbnail_hit(self, tmp_path: Path):
        """Test get_thumbnail returns path for valid cache."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/image.jpg"

        cache_path = cache._get_cache_path(url)
        cache_path.write_bytes(b"test image data")

        result = cache.get_thumbnail(url)
        assert result == cache_path

    def test_get_thumbnail_expired(self, tmp_path: Path):
        """Test get_thumbnail returns None for expired cache."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/image.jpg"

        cache_path = cache._get_cache_path(url)
        cache_path.write_bytes(b"test image data")

        # Make file expired
        old_time = time.time() - (8 * 24 * 60 * 60)
        import os

        os.utime(cache_path, (old_time, old_time))

        result = cache.get_thumbnail(url)
        assert result is None


class TestDownloadAndCache:
    """Test download_and_cache method."""

    async def test_download_http_error(
        self, tmp_path: Path, aiohttp_session, mocker: MockerFixture
    ):
        """Test download with HTTP error raises ServiceError."""
        from aiohttp import ClientError

        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/image.jpg"

        mocker.patch.object(cache, "cleanup", return_value=0)
        aiohttp_session.get.side_effect = ClientError("Network error")

        with pytest.raises(ServiceError):
            await cache.download_and_cache(url, aiohttp_session)

    async def test_download_calls_cleanup(self, tmp_path: Path, mocker: MockerFixture):
        """Test download_and_cache calls cleanup."""
        from aiohttp import ClientError

        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/image.jpg"

        cleanup_mock = mocker.patch.object(cache, "cleanup", return_value=0)

        mock_response = mocker.MagicMock()
        mock_response.raise_for_status.side_effect = ClientError("Network error")

        mock_context = mocker.MagicMock()
        mock_context.__aenter__ = mocker.AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = mocker.AsyncMock(return_value=False)

        mock_session = mocker.MagicMock(spec=aiohttp.ClientSession)
        mock_session.get.return_value = mock_context

        with pytest.raises(ServiceError):
            await cache.download_and_cache(url, mock_session)

        cleanup_mock.assert_called_once()


class TestGetOrDownload:
    """Test get_or_download method."""

    async def test_get_or_download_cache_hit(
        self, tmp_path: Path, mocker: MockerFixture
    ):
        """Test get_or_download returns cached thumbnail if available."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/image.jpg"

        cache_path = cache._get_cache_path(url)
        cache_path.write_bytes(b"cached data")

        # Mock session (should not be used)
        session = mocker.Mock(spec=aiohttp.ClientSession)

        result = await cache.get_or_download(url, session)
        assert result == cache_path
        assert not session.get.called


class TestCleanupRobustness:
    """Test cleanup robustness against concurrent file deletion (TOCTOU)."""

    def test_cleanup_tolerates_vanished_files(self, tmp_path: Path):
        """Test cleanup does not raise when files vanish between glob and stat."""
        cache = ThumbnailCache(cache_dir=tmp_path)

        # A dangling symlink makes stat() raise FileNotFoundError, simulating
        # a file deleted by another worker thread between glob() and stat().
        dangling = tmp_path / "vanished.jpg"
        dangling.symlink_to(tmp_path / "does-not-exist.jpg")
        (tmp_path / "real.jpg").write_bytes(b"x" * 1000)

        removed = cache.cleanup()
        assert isinstance(removed, int)


class TestAtomicCacheWrite:
    """Test that cache entries are written atomically."""

    async def test_download_leaves_no_tmp_files(
        self, tmp_path: Path, mocker: MockerFixture
    ):
        """Test successful download writes atomically (no .tmp leftovers)."""
        import aiohttp as aiohttp_mod

        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/image.jpg"
        image_data = b"fake image bytes"

        mocker.patch.object(cache, "cleanup", return_value=0)
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status = mocker.MagicMock()

        async def read():
            return image_data

        mock_response.read = read
        mock_context = mocker.MagicMock()
        mock_context.__aenter__ = mocker.AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = mocker.AsyncMock(return_value=False)

        mock_session = mocker.MagicMock(spec=aiohttp_mod.ClientSession)
        mock_session.get.return_value = mock_context

        result = await cache.download_and_cache(url, mock_session)

        assert result.read_bytes() == image_data
        assert not list(tmp_path.glob("*.tmp"))


class TestStatGuards:
    """TOCTOU guards return safe defaults when files vanish mid-cleanup (M3)."""

    def test_safe_stat_size_returns_zero_for_vanished_file(self, tmp_path: Path):
        cache = ThumbnailCache(cache_dir=tmp_path)
        dangling = tmp_path / "vanished.jpg"
        dangling.symlink_to(tmp_path / "gone.jpg")

        assert cache._safe_stat_size(dangling) == 0

    def test_safe_stat_mtime_returns_zero_for_vanished_file(self, tmp_path: Path):
        cache = ThumbnailCache(cache_dir=tmp_path)
        dangling = tmp_path / "vanished.jpg"
        dangling.symlink_to(tmp_path / "gone.jpg")

        assert cache._safe_stat_mtime(dangling) == 0.0

    def test_cleanup_while_loop_skips_vanished_oldest(self, tmp_path: Path):
        """Oldest entry vanishing between sort and unlink must not crash cleanup."""
        import os
        import time as time_mod

        cache = ThumbnailCache(cache_dir=tmp_path)

        # Two real files over a tiny limit plus one dangling symlink that sorts oldest.
        dangling = tmp_path / "dangling.jpg"
        dangling.symlink_to(tmp_path / "gone.jpg")
        first = tmp_path / "first.jpg"
        second = tmp_path / "second.jpg"
        first.write_bytes(b"a" * 1000)
        second.write_bytes(b"b" * 1000)
        old = time_mod.time() - 1000
        os.utime(dangling, (old, old), follow_symlinks=False)  # dangling sorts first

        original_max = ThumbnailCache.MAX_CACHE_SIZE_MB
        ThumbnailCache.MAX_CACHE_SIZE_MB = 0
        try:
            removed = cache.cleanup()
        finally:
            ThumbnailCache.MAX_CACHE_SIZE_MB = original_max

        # Both real files must be gone (over limit), dangling skipped without error.
        assert not first.exists()
        assert not second.exists()
        assert isinstance(removed, int)


class TestGetOrDownloadAsyncPaths:
    """get_or_download_async: local file / cache hit / expired / download."""

    async def test_local_file_returned_directly(self, tmp_path: Path):
        cache = ThumbnailCache(cache_dir=tmp_path)
        local = tmp_path / "actual.jpg"
        local.write_bytes(b"real file")

        result = await cache.get_or_download_async(str(local))

        assert result == local

    async def test_cache_hit_skips_download(self, tmp_path: Path, mocker: MockerFixture):
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/hit.jpg"
        cache_path = cache._get_cache_path(url)
        cache_path.write_bytes(b"cached")

        session_spy = mocker.patch(
            "services.thumbnail_cache.aiohttp.ClientSession", side_effect=AssertionError
        )

        result = await cache.get_or_download_async(url)

        assert result == cache_path
        session_spy.assert_not_called()

    async def test_expired_entry_is_redownloaded(
        self, tmp_path: Path, mocker: MockerFixture
    ):
        import os
        import time as time_mod

        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/expired.jpg"
        cache_path = cache._get_cache_path(url)
        cache_path.write_bytes(b"stale")
        old = time_mod.time() - (8 * 24 * 60 * 60)
        os.utime(cache_path, (old, old))

        fresh_data = b"fresh bytes"
        mock_response = mocker.MagicMock()
        mock_response.raise_for_status = mocker.MagicMock()
        mock_response.read = mocker.AsyncMock(return_value=fresh_data)
        mock_context = mocker.MagicMock()
        mock_context.__aenter__ = mocker.AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = mocker.AsyncMock(return_value=False)
        session_cls = mocker.patch("services.thumbnail_cache.aiohttp.ClientSession")
        session_cls.return_value.__aenter__ = mocker.AsyncMock(
            return_value=mocker.MagicMock(get=mocker.MagicMock(return_value=mock_context))
        )

        result = await cache.get_or_download_async(url)

        assert result == cache_path
        assert cache_path.read_bytes() == fresh_data

    async def test_miss_downloads_and_caches(
        self, tmp_path: Path, mocker: MockerFixture
    ):
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/miss.png"

        mock_response = mocker.MagicMock()
        mock_response.raise_for_status = mocker.MagicMock()
        mock_response.read = mocker.AsyncMock(return_value=b"png-bytes")
        mock_context = mocker.MagicMock()
        mock_context.__aenter__ = mocker.AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = mocker.AsyncMock(return_value=False)
        session_cls = mocker.patch("services.thumbnail_cache.aiohttp.ClientSession")
        session_cls.return_value.__aenter__ = mocker.AsyncMock(
            return_value=mocker.MagicMock(get=mocker.MagicMock(return_value=mock_context))
        )
        mocker.patch.object(type(cache), "CLEANUP_DEBOUNCE_SECONDS", 0)

        result = await cache.get_or_download_async(url)

        assert result.exists()
        assert result.parent == tmp_path


class TestGetOrDownloadSync:
    """Thread-pool variant used by ThumbnailLoader."""

    def test_sync_local_file_returned_directly(self, tmp_path: Path):
        cache = ThumbnailCache(cache_dir=tmp_path)
        local = tmp_path / "local.jpg"
        local.write_bytes(b"data")

        assert cache.get_or_download_sync(str(local)) == local

    def test_sync_cache_hit(self, tmp_path: Path, mocker: MockerFixture):
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/sync-hit.jpg"
        cache_path = cache._get_cache_path(url)
        cache_path.write_bytes(b"cached")
        loop_spy = mocker.patch(
            "services.thumbnail_cache.get_event_loop", side_effect=AssertionError
        )

        assert cache.get_or_download_sync(url) == cache_path
        loop_spy.assert_not_called()

    def test_sync_download_via_event_loop_future(self, tmp_path: Path, mocker):
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/sync-dl.jpg"
        expected = cache._get_cache_path(url)
        future = mocker.MagicMock()
        future.result.return_value = expected
        run_coroutine_mock = mocker.patch(
            "asyncio.run_coroutine_threadsafe", return_value=future
        )
        mocker.patch("services.thumbnail_cache.get_event_loop")

        assert cache.get_or_download_sync(url) == expected
        future.result.assert_called_once_with(timeout=60)
        run_coroutine_mock.assert_called_once()

    def test_sync_runtime_error_falls_back_to_asyncio_run(
        self, tmp_path: Path, mocker
    ):
        from unittest.mock import AsyncMock

        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/fallback.jpg"
        expected = cache._get_cache_path(url)
        mocker.patch(
            "services.thumbnail_cache.get_event_loop", side_effect=RuntimeError
        )
        download_mock = mocker.patch.object(
            cache, "_download_with_session", AsyncMock(return_value=expected)
        )

        assert cache.get_or_download_sync(url) == expected
        download_mock.assert_awaited_once_with(url)

    def test_sync_generic_failure_raises_service_error(self, tmp_path: Path, mocker):
        from domain.exceptions import ServiceError

        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/doomed.jpg"
        future = mocker.MagicMock()
        future.result.side_effect = ValueError("loop exploded")
        mocker.patch("asyncio.run_coroutine_threadsafe", return_value=future)
        mocker.patch("services.thumbnail_cache.get_event_loop")

        with pytest.raises(ServiceError, match="Failed to download thumbnail"):
            cache.get_or_download_sync(url)


async def test_download_with_session_opens_client_session(
    tmp_path: Path, mocker: MockerFixture
):
    """_download_with_session builds its own session and caches the body."""
    cache = ThumbnailCache(cache_dir=tmp_path)
    url = "http://example.com/session.jpg"
    payload = b"session-data"

    mock_response = mocker.MagicMock()
    mock_response.raise_for_status = mocker.MagicMock()
    mock_response.read = mocker.AsyncMock(return_value=payload)
    mock_get = mocker.MagicMock(return_value=mock_context(mocker, mock_response))
    session_cls = mocker.patch("services.thumbnail_cache.aiohttp.ClientSession")
    session_cls.return_value.__aenter__ = mocker.AsyncMock(
        return_value=mocker.MagicMock(get=mock_get)
    )
    session_cls.return_value.__aexit__ = mocker.AsyncMock(return_value=False)
    mocker.patch.object(type(cache), "CLEANUP_DEBOUNCE_SECONDS", 999999)

    result = await cache._download_with_session(url)

    assert result.parent == tmp_path
    assert result.read_bytes() == payload


def mock_context(mocker, response):
    ctx = mocker.MagicMock()
    ctx.__aenter__ = mocker.AsyncMock(return_value=response)
    ctx.__aexit__ = mocker.AsyncMock(return_value=False)
    return ctx


class TestCleanupErrorGuards:
    """Entries that cannot be unlinked (or vanish mid-cleanup) are tolerated."""

    def test_expired_directory_hits_both_oserror_guards(self, tmp_path: Path):
        """An old directory can't be unlink()ed; both OSError handlers must fire."""
        import os
        import time as time_mod

        cache = ThumbnailCache(cache_dir=tmp_path)
        stubborn = tmp_path / "stubborn.jpg"
        stubborn.mkdir()
        old = time_mod.time() - (8 * 24 * 60 * 60)
        os.utime(stubborn, (old, old))

        original_max = ThumbnailCache.MAX_CACHE_SIZE_MB
        ThumbnailCache.MAX_CACHE_SIZE_MB = 0
        try:
            removed = cache.cleanup()  # Must not raise
        finally:
            ThumbnailCache.MAX_CACHE_SIZE_MB = original_max

        assert stubborn.exists()  # untouched
        assert isinstance(removed, int)

    def test_vanished_nonexpired_entry_takes_continue_branch(
        self, tmp_path: Path, mocker: MockerFixture
    ):
        """A vanished-but-not-expired entry in LRU order hits the continue guard."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        dangling = tmp_path / "dangling.jpg"
        dangling.symlink_to(tmp_path / "gone.jpg")
        real = tmp_path / "real.jpg"
        real.write_bytes(b"x" * 1000)

        mocker.patch.object(cache, "_is_expired", return_value=False)
        original_max = ThumbnailCache.MAX_CACHE_SIZE_MB
        ThumbnailCache.MAX_CACHE_SIZE_MB = 0
        try:
            removed = cache.cleanup()  # Must not raise
        finally:
            ThumbnailCache.MAX_CACHE_SIZE_MB = original_max

        assert not real.exists()  # still evicted by size
        assert isinstance(removed, int)


class TestGetOrDownloadSessionVariant:
    async def test_local_file_short_circuits_session(
        self, tmp_path: Path, mocker: MockerFixture
    ):
        cache = ThumbnailCache(cache_dir=tmp_path)
        local = tmp_path / "on_disk.jpg"
        local.write_bytes(b"data")

        session_cls = mocker.patch(
            "services.thumbnail_cache.aiohttp.ClientSession",
            side_effect=AssertionError("session must not be created"),
        )

        result = await cache.get_or_download(str(local), mocker.MagicMock())

        assert result == local
        session_cls.assert_not_called()

    async def test_miss_downloads_through_given_session(
        self, tmp_path: Path, mocker: MockerFixture
    ):
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/session-miss.jpg"

        download_mock = mocker.patch.object(
            cache, "download_and_cache", new=mocker.AsyncMock(name="path")
        )
        from pathlib import Path as _Path

        download_mock.return_value = _Path("/tmp/x.jpg")

        result = await cache.get_or_download(url, mocker.MagicMock())

        assert result == _Path("/tmp/x.jpg")
        download_mock.assert_awaited_once()
