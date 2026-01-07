"""
ViewModel for favorites management
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gi.repository import GObject  # type: ignore

from domain.favorite import Favorite
from domain.wallpaper import (
    Wallpaper,  # noqa: E402
    WallpaperPurity,
)
from services.favorites_service import FavoritesService
from services.wallpaper_setter import WallpaperSetter
from ui.view_models.base import BaseViewModel


class FavoritesViewModel(BaseViewModel):
    """ViewModel for favorites management"""

    def __init__(
        self,
        favorites_service: FavoritesService,
        wallpaper_setter: WallpaperSetter,
        thumbnail_cache=None,
    ) -> None:
        super().__init__(thumbnail_cache=thumbnail_cache)
        self.favorites_service = favorites_service
        self.wallpaper_setter = wallpaper_setter

        self._favorites: list[Wallpaper] = []
        self._search_query: str = ""
        # Initialize properties
        self.favorites = []
        self._search_query = ""  # Set directly to avoid triggering search
        self.search_query = ""

    favorites = GObject.Property(type=object)
    search_query = GObject.Property(type=str)

    def get_favorites(self) -> list[Wallpaper]:
        return self._favorites

    def set_favorites(self, value: list[Wallpaper]) -> None:
        self._favorites = value
        self.notify("favorites")

    def get_search_query(self) -> str:
        return self._search_query

    def set_search_query(self, value: str) -> None:
        self._search_query = value
        self.search_favorites(value)

    def get_property(self, prop):
        if prop == "favorites":
            return super().get_property(prop)
        elif prop == "search_query":
            return self._search_query
        else:
            return super().get_property(prop)

    def set_property(self, prop, value):
        if prop == "favorites":
            super().set_property(prop, value)
        elif prop == "search_query":
            self._search_query = value
            if value:  # Only search if there's a query
                self.search_favorites(value)
            self.notify("search_query")
        else:
            super().set_property(prop, value)

    def load_favorites(self) -> None:
        try:
            self.is_busy = True
            self.error_message = None

            favorites = self.favorites_service.get_favorites()
            self._favorites = [f.wallpaper for f in favorites]  # type: ignore
            self.notify("favorites")

        except Exception as e:
            self.error_message = f"Failed to load favorites: {e}"
            self._favorites = []
            self.notify("favorites")
        finally:
            self.is_busy = False

    def search_favorites(self, query: str = "") -> None:
        try:
            self.is_busy = True
            self.error_message = None
            self._search_query = query

            if not query or query.strip() == "":
                self.load_favorites()
            else:
                results = self.favorites_service.search_favorites(query)
                self._favorites = [f.wallpaper for f in results]  # type: ignore
                self.notify("favorites")

        except Exception as e:
            self.error_message = f"Failed to search favorites: {e}"
            self._favorites = []
            self.notify("favorites")
        finally:
            self.is_busy = False

    def add_favorite(
        self,
        wallpaper_id: str,
        full_url: str,
        path: str,
        source: str,
        tags: str,
    ) -> bool:
        try:
            self.is_busy = True
            self.error_message = None

            if self.is_favorite(wallpaper_id):
                self._show_toast("Already in favorites", "warning")
                return False

            from domain.wallpaper import Resolution, Wallpaper, WallpaperSource

            source_enum = source
            if isinstance(source, str):
                if source == "local":
                    source_enum = WallpaperSource.LOCAL
                elif source == "wallhaven":
                    source_enum = WallpaperSource.WALLHAVEN
                elif source == "favorite":
                    source_enum = WallpaperSource.FAVORITE
                else:
                    source_enum = WallpaperSource.LOCAL

            wallpaper = Wallpaper(
                id=wallpaper_id,
                url=full_url,
                path=path,
                resolution=Resolution(width=1920, height=1080),
                purity=WallpaperPurity.SFW,
                category="general",
                source=source_enum,
            )

            self.favorites_service.add_favorite(wallpaper)
            self.load_favorites()
            self._show_toast("Added to favorites", "success")

            return True

        except Exception as e:
            self.error_message = f"Failed to add favorite: {e}"
            self._show_toast(f"Failed to add favorite: {e}", "error")
            return False
        finally:
            self.is_busy = False

    def remove_favorite(self, wallpaper_id: str) -> bool:
        try:
            self.is_busy = True
            self.error_message = None

            self.favorites_service.remove_favorite(wallpaper_id)
            self.load_favorites()
            self._show_toast("Removed from favorites", "success")

            return True

        except Exception as e:
            self.error_message = f"Failed to remove favorite: {e}"
            self._show_toast(f"Failed to remove favorite: {e}", "error")
            return False
        finally:
            self.is_busy = False

    def set_wallpaper(self, favorite: Favorite) -> bool:
        try:
            self.is_busy = True
            self.error_message = None

            result = self.wallpaper_setter.set_wallpaper(favorite.wallpaper.path)

            if result:
                self.emit("wallpaper-set", favorite.wallpaper.name)
                self._show_toast("Wallpaper set successfully", "success")

            return result

        except Exception as e:
            self.error_message = f"Failed to set wallpaper: {e}"
            self._show_toast(f"Failed to set wallpaper: {e}", "error")
            return False
        finally:
            self.is_busy = False

    def is_favorite(self, wallpaper_id: str) -> bool:
        result = self.favorites_service.is_favorite(wallpaper_id)
        return result if result is not None else False

    def get_favorite(self, wallpaper_id: str) -> Favorite:
        favorite = self.favorites_service.is_favorite(wallpaper_id)
        if not favorite:
            raise ValueError(f"Wallpaper {wallpaper_id} not in favorites")
        for fav in self.favorites:
            if fav.wallpaper_id == wallpaper_id:
                return fav
        raise ValueError(f"Wallpaper {wallpaper_id} not in favorites list")

    def refresh_favorites(self) -> None:
        self.search_query = ""
        self.load_favorites()

    def select_all(self) -> None:
        """Select all favorites."""
        self._selected_wallpapers_list = self.favorites.copy()
        self._update_selection_state()

    def _show_toast(self, message: str, msg_type: str = "info"):
        try:
            window = self.get_root()
            if window and hasattr(window, "toast_service"):
                if msg_type == "success":
                    window.toast_service.show_success(message)
                elif msg_type == "error":
                    window.toast_service.show_error(message)
                elif msg_type == "warning":
                    window.toast_service.show_warning(message)
                else:
                    window.toast_service.show_info(message)
        except Exception:
            pass
