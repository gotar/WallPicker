"""
ViewModel for favorites management
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gi.repository import GObject  # type: ignore

from domain.favorite import Favorite
from domain.wallpaper import (
    Wallpaper,  # noqa: E402
    WallpaperPurity,
)
from services.config_service import ConfigService
from services.favorites_service import FavoritesService
from services.wallhaven_service import WallhavenService
from services.wallpaper_setter import WallpaperSetter
from ui.view_models.base import BaseViewModel

logger = logging.getLogger(__name__)


class FavoritesViewModel(BaseViewModel):
    """ViewModel for favorites management"""

    def __init__(
        self,
        favorites_service: FavoritesService,
        wallpaper_setter: WallpaperSetter,
        config_service: ConfigService | None = None,
        wallhaven_service: WallhavenService | None = None,
    ) -> None:
        super().__init__()
        self.favorites_service = favorites_service
        self.wallpaper_setter = wallpaper_setter
        self.config_service = config_service
        self.wallhaven_service = wallhaven_service

        self._favorites: list[Favorite] = []
        self._search_query: str = ""
        self._set_wallpaper_lock = asyncio.Lock()

    @GObject.Property(type=object)
    def wallpapers(self) -> list[Wallpaper]:
        return [f.wallpaper for f in self._favorites]

    @wallpapers.setter
    def wallpapers(self, value: list[Wallpaper]) -> None:
        pass

    @GObject.Property(type=object)
    def favorites(self) -> list[Favorite]:
        return self._favorites

    @favorites.setter
    def favorites(self, value: list[Favorite]) -> None:
        self._favorites = value

    @GObject.Property(type=str, default="")
    def search_query(self) -> str:
        return self._search_query

    @search_query.setter
    def search_query(self, value: str) -> None:
        self._search_query = value
        if value:
            self.search_favorites(value)
        else:
            self.load_favorites()

    def load_favorites(self) -> None:
        try:
            self.is_busy = True
            self.error_message = None

            favorites = self.favorites_service.get_favorites()
            self.favorites = favorites
            logger.info(f"Loading favorites, found {len(favorites)} items")

        except Exception as e:
            self.error_message = f"Failed to load favorites: {e}"
            self.favorites = []
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
                self.favorites = results

        except Exception as e:
            self.error_message = f"Failed to search favorites: {e}"
            self.favorites = []
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
                self.emit("wallpaper-set", favorite.wallpaper.id)
                self._show_toast("Wallpaper set successfully", "success")

            return result

        except Exception as e:
            self.error_message = f"Failed to set wallpaper: {e}"
            self._show_toast(f"Failed to set wallpaper: {e}", "error")
            return False
        finally:
            self.is_busy = False

    async def set_wallpaper_async(self, favorite: Favorite) -> tuple[bool, str]:
        if not self.wallpaper_setter:
            return False, "Wallpaper setter not available"

        async with self._set_wallpaper_lock:
            try:
                self.is_busy = True
                self.error_message = None

                wallpaper = favorite.wallpaper
                path = wallpaper.path

                if path.startswith(("http://", "https://")):
                    self._show_toast("Downloading wallpaper...", "info")

                    if not self.config_service or not self.wallhaven_service:
                        return False, "Required services not available"

                    config = self.config_service.get_config()
                    filename = f"{wallpaper.id}.{path.rsplit('.', 1)[-1]}"
                    dest_path = config.pictures_dir / filename

                    if not dest_path.exists():
                        logger.info(
                            f"Downloading wallpaper {wallpaper.id} to {dest_path}"
                        )
                        success = await self.wallhaven_service.download(
                            wallpaper, dest_path
                        )
                        if not success:
                            return False, "Failed to download wallpaper"
                    else:
                        logger.info(f"Using cached wallpaper at {dest_path}")

                    path = str(dest_path)

                result = self.wallpaper_setter.set_wallpaper(path)

                if result:
                    self.emit("wallpaper-set", wallpaper.id)
                    return True, "Wallpaper set successfully"
                else:
                    return False, "Failed to set wallpaper"

            except Exception as e:
                self.error_message = f"Failed to set wallpaper: {e}"
                logger.error(f"Failed to set wallpaper: {e}", exc_info=True)
                return False, f"Failed to set wallpaper: {e}"
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
        self._selected_wallpapers_list = self.wallpapers.copy()
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
        except (AttributeError, RuntimeError) as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.debug(f"Could not show toast notification: {e}")
