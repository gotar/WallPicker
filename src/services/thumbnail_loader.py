"""Thumbnail loading service for async thumbnail operations.

This service handles the GTK-specific thumbnail loading logic that was
previously in BaseViewModel, properly separating concerns.
"""

import hashlib
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")

from gi.repository import Gdk, GLib  # noqa: E402

logger = logging.getLogger(__name__)

# Thumbnail cache directory
_THUMBNAIL_CACHE_DIR = Path.home() / ".cache" / "wallpicker" / "thumbnails"
_THUMBNAIL_SIZE = (200, 160)


class ThumbnailLoader:
    """Service for loading thumbnails asynchronously."""

    def __init__(self, thumbnail_cache=None, max_workers: int = 4):
        """Initialize thumbnail loader.

        Args:
            thumbnail_cache: ThumbnailCache instance for caching remote thumbnails
            max_workers: Maximum number of worker threads
        """
        self._thumbnail_cache = thumbnail_cache
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._local_thumbnail_cache = {}  # In-memory cache for local thumbnails
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Ensure thumbnail cache directory exists."""
        try:
            _THUMBNAIL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create thumbnail cache directory: {e}")

    def _get_local_thumbnail_path(self, file_path: str) -> Path:
        """Get the path for a local thumbnail file."""
        # Use stable MD5 of the path as cache key (builtin hash() is salted per
        # process, which would invalidate the disk cache on every restart).
        path = Path(file_path)
        cache_key = f"{path.stat().st_mtime}_{path.stat().st_size}"
        path_hash = hashlib.md5(str(file_path).encode()).hexdigest()
        return (
            _THUMBNAIL_CACHE_DIR
            / f"local_{path_hash}_{cache_key}.jpg"
        )

    def _generate_thumbnail(self, file_path: str) -> bytes | None:
        """Generate a thumbnail for a local image file.

        Returns:
            JPEG bytes of the thumbnail, or None on failure.
        """
        try:
            from PIL import Image

            path = Path(file_path)
            if not path.exists():
                return None

            # Check if thumbnail already exists and is up to date
            thumb_path = self._get_local_thumbnail_path(file_path)
            if thumb_path.exists():
                # Check if source is older than thumbnail
                if path.stat().st_mtime <= thumb_path.stat().st_mtime:
                    return thumb_path.read_bytes()

            # Generate thumbnail
            with Image.open(path) as img:
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                img.thumbnail(_THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

                # Save to cache
                thumb_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(thumb_path, "JPEG", quality=80, optimize=True)

                # Return bytes
                import io

                buffer = io.BytesIO()
                img.save(buffer, "JPEG", quality=80, optimize=True)
                return buffer.getvalue()

        except ImportError:
            logger.warning("PIL not available, falling back to direct loading")
        except Exception as e:
            logger.error(
                f"Failed to generate thumbnail for {file_path}: {e}", exc_info=True
            )

        return None

    def load_thumbnail_async(
        self,
        path_or_url: str,
        callback: Callable[[Gdk.Texture | None], None],
        allow_retry: bool = True,
    ) -> None:
        """Load thumbnail asynchronously and invoke callback on main thread.

        Args:
            path_or_url: Local file path or remote URL
            callback: Function to call with Gdk.Texture or None on failure
            allow_retry: When True (default), a decode failure of cached bytes
                invalidates the corrupt entry and retries exactly once.
        """

        def _load_thumbnail(retry_allowed: bool = allow_retry):
            try:
                # Handle remote URLs with caching
                if path_or_url.startswith(("http://", "https://")):
                    self._load_remote(path_or_url, callback, allow_retry=retry_allowed)
                    return

                # Handle local files - use thumbnail generation
                path = Path(path_or_url)
                if path.exists():
                    # Check in-memory cache first
                    if path_or_url in self._local_thumbnail_cache:
                        data = self._local_thumbnail_cache[path_or_url]
                        if data:

                            def create_cached_texture():
                                try:
                                    texture = Gdk.Texture.new_from_bytes(
                                        GLib.Bytes.new(data)
                                    )
                                    callback(texture)
                                except Exception:
                                    if retry_allowed:
                                        # Corrupt in-memory bytes: drop the entry
                                        # and reload from disk exactly once.
                                        logger.warning(
                                            f"Cached thumbnail for {path_or_url} "
                                            "failed to decode; regenerating"
                                        )
                                        self._local_thumbnail_cache.pop(
                                            path_or_url, None
                                        )
                                        self._executor.submit(
                                            _load_thumbnail, False
                                        )
                                    else:
                                        callback(None)

                            GLib.idle_add(create_cached_texture)
                            return

                    # Generate or load thumbnail in worker thread
                    thumbnail_data = self._generate_thumbnail(path_or_url)

                    if thumbnail_data:
                        # Cache in memory
                        self._local_thumbnail_cache[path_or_url] = thumbnail_data

                        # Create texture in main thread
                        def create_local_texture():
                            try:
                                texture = Gdk.Texture.new_from_bytes(
                                    GLib.Bytes.new(thumbnail_data)
                                )
                                callback(texture)
                            except Exception:
                                # Corrupt-but-present cache entry: drop it so a
                                # later load regenerates instead of serving the
                                # same broken bytes forever.
                                logger.warning(
                                    f"Thumbnail for {path_or_url} failed to decode; "
                                    "dropping corrupt cache entry"
                                )
                                self._drop_corrupt_local_entry(path_or_url)
                                callback(None)
                        GLib.idle_add(create_local_texture)
                        return

            except (OSError, Exception) as e:
                logger.error(
                    f"Failed to load thumbnail from {path_or_url}: {e}", exc_info=True
                )

            # Invoke callback with None if loading failed
            GLib.idle_add(lambda: callback(None))

        self._executor.submit(_load_thumbnail)

    def _load_remote(self, url: str, callback, allow_retry: bool = True) -> None:
        """Load a remote thumbnail via the disk cache (runs on the executor).

        If Gdk fails to decode the cached bytes, the corrupt cache entry is
        invalidated and the thumbnail re-downloaded exactly once before we
        give up and report failure.
        """
        try:
            if not self._thumbnail_cache:
                GLib.idle_add(lambda: callback(None))
                return

            logger.debug(f"Loading remote thumbnail: {url[:60]}...")
            thumbnail_path = self._thumbnail_cache.get_or_download_sync(url)
            if thumbnail_path and thumbnail_path.exists():
                # Read file bytes in worker thread
                data = thumbnail_path.read_bytes()

                # Schedule texture creation in main thread
                def create_remote_texture():
                    try:
                        texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))
                        callback(texture)
                    except Exception:
                        logger.warning(
                            f"Remote thumbnail for {url[:60]} failed to decode"
                            + ("; retrying after invalidation" if allow_retry else "")
                        )
                        if allow_retry:
                            self._retry_remote_after_decode_failure(url, callback)
                        else:
                            callback(None)

                GLib.idle_add(create_remote_texture)
                return
        except Exception as e:
            logger.error(f"Failed to load remote thumbnail from {url}: {e}", exc_info=True)

        GLib.idle_add(lambda: callback(None))

    def _retry_remote_after_decode_failure(self, url: str, callback) -> None:
        """Invalidate a corrupt remote cache entry and re-download once."""
        cache = self._thumbnail_cache
        if cache is not None and hasattr(cache, "invalidate"):
            try:
                cache.invalidate(url)
            except Exception as e:
                logger.warning(f"Failed to invalidate cache for {url[:60]}: {e}")
        # Heavy work stays off the main thread: resubmit to the worker pool.
        self._executor.submit(self._load_remote, url, callback, False)

    def _drop_corrupt_local_entry(self, path_or_url: str) -> None:
        """Drop a corrupt local thumbnail from the in-memory and disk caches."""
        self._local_thumbnail_cache.pop(path_or_url, None)
        try:
            source = Path(path_or_url)
            if source.exists():
                self._get_local_thumbnail_path(path_or_url).unlink(missing_ok=True)
        except OSError as e:
            logger.warning(f"Failed to remove corrupt thumbnail for {path_or_url}: {e}")

    def shutdown(self) -> None:
        """Shutdown the executor."""
        self._executor.shutdown(wait=False)

    def clear_memory_cache(self) -> None:
        """Clear the in-memory thumbnail cache."""
        self._local_thumbnail_cache.clear()

    def invalidate(self, path_or_url: str) -> None:
        """Drop the cached thumbnail for one path.

        Used when a file changes on disk underneath the same path (e.g. AI
        upscaling), so a reload picks up the new content instead of the
        stale in-memory bytes.
        """
        self._local_thumbnail_cache.pop(path_or_url, None)

    def __del__(self) -> None:
        """Cleanup on destruction."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)
