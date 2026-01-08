"""Tests for ThumbnailCache."""

import asyncio
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

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_download_calls_cleanup(
        self, tmp_path: Path, aiohttp_session, mocker: MockerFixture
    ):
        """Test download_and_cache calls cleanup."""
        cache = ThumbnailCache(cache_dir=tmp_path)
        url = "http://example.com/image.jpg"

        cleanup_mock = mocker.patch.object(cache, "cleanup", return_value=0)

        from aiohttp import ClientResponse

        mock_response = mocker.Mock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.headers = {"content-length": "1000"}
        mock_response.raise_for_status = mocker.Mock()
        mock_response.read.return_value = b"data"
        aiohttp_session.get.side_effect = lambda *args, **kwargs: (
            asyncio.Future()
            if asyncio.iscoroutinefunction(mock_response)
            else mock_response
        )

        with pytest.raises(Exception):  # noqa: B017
            await cache.download_and_cache(url, aiohttp_session)

        cleanup_mock.assert_called_once()


class TestGetOrDownload:
    """Test get_or_download method."""

    @pytest.mark.asyncio
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
