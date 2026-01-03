"""
Thumbnail Cache Service
Handles disk-based caching of thumbnail images for faster loading
"""

import hashlib
import os
import time
from pathlib import Path
from typing import Optional
from gi.repository import Gdk, GLib
import requests


class ThumbnailCache:
    """Service for caching thumbnail images to disk"""

    CACHE_DIR = Path.home() / ".cache" / "wallpicker" / "thumbnails"
    CACHE_EXPIRY_DAYS = 7  # Cache expires after 7 days
    MAX_CACHE_SIZE_MB = 500  # Maximum cache size in MB

    def __init__(self):
        self.cache_dir = self.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, url: str) -> Path:
        """Generate cache file path from URL using hash"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = url.split(".")[-1].split("?")[0][:4]  # Get extension, max 4 chars
        if len(ext) > 4 or not ext.isalpha():
            ext = "jpg"
        return self.cache_dir / f"{url_hash}.{ext}"

    def _is_expired(self, cache_path: Path) -> bool:
        """Check if cache entry has expired"""
        if not cache_path.exists():
            return True
        file_age = time.time() - cache_path.stat().st_mtime
        return file_age > (self.CACHE_EXPIRY_DAYS * 24 * 60 * 60)

    def _cleanup_old_cache(self):
        """Clean up expired cache entries if cache is too large"""
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*"))
        max_size_bytes = self.MAX_CACHE_SIZE_MB * 1024 * 1024

        if total_size > max_size_bytes:
            for cache_file in self.cache_dir.glob("*"):
                if self._is_expired(cache_file):
                    cache_file.unlink()

            files = list(self.cache_dir.glob("*"))
            files.sort(key=lambda f: f.stat().st_mtime)

            while total_size > max_size_bytes * 0.9 and files:
                oldest = files.pop(0)
                total_size -= oldest.stat().st_size
                oldest.unlink()

    def get_cached_thumbnail(self, url: str) -> Optional[bytes]:
        """
        Get thumbnail from cache if available and not expired

        Args:
            url: Thumbnail URL

        Returns:
            Image bytes if cached and valid, None otherwise
        """
        cache_path = self._get_cache_path(url)

        if self._is_expired(cache_path):
            return None

        try:
            with open(cache_path, "rb") as f:
                return f.read()
        except Exception:
            return None

    def cache_thumbnail(self, url: str, image_data: bytes) -> bool:
        """
        Save thumbnail image to cache

        Args:
            url: Thumbnail URL (used as key)
            image_data: Raw image data to cache

        Returns:
            True if cached successfully, False otherwise
        """
        try:
            self._cleanup_old_cache()

            cache_path = self._get_cache_path(url)
            with open(cache_path, "wb") as f:
                f.write(image_data)
            return True
        except Exception:
            return False

    def load_thumbnail_with_cache(
        self, url: str, image_widget, fallback_download: bool = True
    ) -> bool:
        """
        Load thumbnail into widget, using cache if available

        Args:
            url: Thumbnail URL
            image_widget: Gtk.Picture widget to load image into
            fallback_download: If True, download if not in cache

        Returns:
            True if loaded from cache, False if download initiated or failed
        """
        cached_data = self.get_cached_thumbnail(url)
        if cached_data:
            try:
                texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(cached_data))
                image_widget.set_paintable(texture)
                return True
            except Exception:
                pass

        if fallback_download:

            def do_load():
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        data = response.content
                        self.cache_thumbnail(url, data)
                        GLib.idle_add(set_image, data)
                except Exception:
                    pass

            def set_image(data):
                try:
                    texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))
                    image_widget.set_paintable(texture)
                except Exception:
                    pass

            import threading

            threading.Thread(target=do_load, daemon=True).start()

        return False

    def clear_cache(self):
        """Clear all cached thumbnails"""
        for cache_file in self.cache_dir.glob("*"):
            try:
                cache_file.unlink()
            except Exception:
                pass

    def get_cache_info(self) -> dict:
        """
        Get information about cache status

        Returns:
            Dict with 'count', 'size_mb', 'expired_count'
        """
        files = list(self.cache_dir.glob("*"))
        total_size = sum(f.stat().st_size for f in files)
        expired_count = sum(1 for f in files if self._is_expired(f))

        return {
            "count": len(files),
            "size_mb": total_size / (1024 * 1024),
            "expired_count": expired_count,
        }
