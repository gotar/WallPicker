"""
ViewModel for local wallpaper browsing
"""

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import sys
from pathlib import Path

from gi.repository import GObject  # noqa: E402

from domain.wallpaper import WallpaperPurity
from services.favorites_service import FavoritesService
from services.local_service import LocalWallpaper, LocalWallpaperService
from services.wallpaper_setter import WallpaperSetter
from ui.view_models.base import BaseViewModel


class LocalViewModel(BaseViewModel):
    """ViewModel for local wallpaper browsing"""

    def __init__(
        self,
        local_service: LocalWallpaperService,
        wallpaper_setter: WallpaperSetter,
        pictures_dir: Path | None = None,
        favorites_service: FavoritesService | None = None,
        config_service=None,
    ) -> None:
        super().__init__()
        self.local_service = local_service
        self.wallpaper_setter = wallpaper_setter
        self.pictures_dir = pictures_dir
        self.favorites_service = favorites_service
        self.config_service = config_service

        self._wallpapers: list[LocalWallpaper] = []
        self.search_query = ""

    @GObject.Property(type=object)
    def wallpapers(self) -> list[LocalWallpaper]:
        """Wallpapers list property"""
        return self._wallpapers

    @wallpapers.setter
    def wallpapers(self, value: list[LocalWallpaper]) -> None:
        self._wallpapers = value

    def load_wallpapers(self, recursive: bool = True) -> None:
        """Load wallpapers from local directory"""
        try:
            self.is_busy = True
            self.error_message = None

            if self.pictures_dir:
                self.local_service.pictures_dir = self.pictures_dir

            wallpapers = self.local_service.get_wallpapers(recursive=recursive)
            self.wallpapers = wallpapers

        except Exception as e:
            self.error_message = f"Failed to load wallpapers: {e}"
            self.wallpapers = []
        finally:
            self.is_busy = False

    def search_wallpapers(self, query: str = "") -> None:
        """Search wallpapers"""
        try:
            self.is_busy = True
            self.error_message = None
            self.search_query = query

            if not query or query.strip() == "":
                # Load all wallpapers if query is empty
                self.load_wallpapers()
            else:
                results = self.local_service.search_wallpapers(query, self.wallpapers)
                self.wallpapers = results

        except Exception as e:
            self.error_message = f"Failed to search wallpapers: {e}"
            self.wallpapers = []
        finally:
            self.is_busy = False

    def set_wallpaper(self, wallpaper: LocalWallpaper) -> tuple[bool, str]:
        try:
            self.is_busy = True
            self.error_message = None
            result = self.wallpaper_setter.set_wallpaper(str(wallpaper.path))
            if result:
                return True, "Wallpaper set successfully"
            return False, "Failed to set wallpaper"
        except Exception as e:
            self.error_message = str(e)
            return False, str(e)
        finally:
            self.is_busy = False

    def delete_wallpaper(self, wallpaper: LocalWallpaper) -> tuple[bool, str]:
        try:
            self.is_busy = True
            self.error_message = None

            result = self.local_service.delete_wallpaper(wallpaper.path)

            if result:
                if wallpaper in self._wallpapers:
                    self._wallpapers.remove(wallpaper)
                    self.notify("wallpapers")
                return True, f"Deleted '{wallpaper.filename}'"

            return False, "Failed to delete"

        except Exception as e:
            self.error_message = f"Failed to delete wallpaper: {e}"
            return False, str(e)
        finally:
            self.is_busy = False

    def refresh_wallpapers(self) -> None:
        """Refresh wallpaper list from disk"""
        self.search_query = ""
        self.load_wallpapers()

    def sort_by_name(self) -> None:
        """Sort wallpapers by filename (A-Z)"""
        self._wallpapers.sort(key=lambda w: w.filename.lower())
        self.notify("wallpapers")

    def sort_by_date(self) -> None:
        """Sort wallpapers by modification date (newest first)"""
        self._wallpapers.sort(key=lambda w: w.modified_time, reverse=True)
        self.notify("wallpapers")

    def set_pictures_dir(self, path: Path) -> None:
        self.pictures_dir = path
        self.local_service.pictures_dir = path
        if self.config_service:
            self.config_service.set_pictures_dir(path)
        self.load_wallpapers()

    def select_all(self) -> None:
        """Select all wallpapers."""
        self._selected_wallpapers_list = self.wallpapers.copy()
        self._update_selection_state()

    def add_to_favorites(self, wallpaper: LocalWallpaper) -> tuple[bool, str]:
        if self.is_busy:
            return False, "Operation in progress"

        if not self.favorites_service:
            self.error_message = "Favorites service not available"
            return False, "Favorites service not available"

        try:
            self.is_busy = True
            self.error_message = None

            # Use hashlib for deterministic hash (Python's hash() is not stable across sessions)
            path_hash = hashlib.sha256(str(wallpaper.path).encode()).hexdigest()[:16]
            wallpaper_id = f"local_{path_hash}"
            if self.favorites_service.is_favorite(wallpaper_id):
                return False, "Already in favorites"

            from PIL import Image

            from domain.wallpaper import Resolution, Wallpaper, WallpaperSource

            width, height = 1920, 1080
            try:
                with Image.open(wallpaper.path) as img:
                    width, height = img.size
            except (OSError, ValueError) as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(
                    f"Could not read image dimensions from {wallpaper.path}: {e}"
                )

            wallpaper_domain = Wallpaper(
                id=wallpaper_id,
                url=str(wallpaper.path),
                path=str(wallpaper.path),
                resolution=Resolution(width=width, height=height),
                source=WallpaperSource.LOCAL,
                category="general",
                purity=WallpaperPurity.SFW,
            )

            self.favorites_service.add_favorite(wallpaper_domain)
            return True, f"Added '{wallpaper.filename}' to favorites"

        except Exception as e:
            self.error_message = f"Failed to add to favorites: {e}"
            return False, str(e)
        finally:
            self.is_busy = False
