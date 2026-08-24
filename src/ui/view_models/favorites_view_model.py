"""
ViewModel for favorites management
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gi.repository import GLib, GObject  # type: ignore

from core.asyncio_integration import get_event_loop, schedule_async
from domain.favorite import Favorite
from domain.wallpaper import (
    Resolution,
    Wallpaper,  # noqa: E402
    WallpaperPurity,
    WallpaperSource,
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
        toast_service=None,
    ) -> None:
        super().__init__()
        self.favorites_service = favorites_service
        self.wallpaper_setter = wallpaper_setter
        self.config_service = config_service
        self.wallhaven_service = wallhaven_service
        self.toast_service = toast_service

        self._favorites: list[Favorite] = []
        self._search_query: str = ""
        self._set_wallpaper_lock = asyncio.Lock()
        # Monotonic generation counter to discard stale load/search completions.
        self._load_generation = 0

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

    def _set_favorites(self, favorites: list[Favorite]) -> bool:
        self._favorites = favorites
        self.notify("favorites")
        return False

    @GObject.Property(type=str, default="")
    def search_query(self) -> str:
        return self._search_query

    @search_query.setter
    def search_query(self, value: str) -> None:
        self._search_query = value
        if value:
            schedule_async(self.search_favorites(value))
        else:
            schedule_async(self.load_favorites())

    async def load_favorites(self) -> None:
        try:
            self._load_generation += 1
            generation = self._load_generation
            self._push_busy()
            self._set_property_idle("error_message", None)

            favorites = await asyncio.to_thread(self.favorites_service.get_favorites)
            if generation != self._load_generation:
                logger.debug("Discarding stale favorites load")
                return
            GLib.idle_add(self._set_favorites, favorites)
            logger.info(f"Loading favorites, found {len(favorites)} items")

        except Exception as e:
            self._set_property_idle(
                "error_message", f"Failed to load favorites: {e}"
            )
            if generation == self._load_generation:
                GLib.idle_add(self._set_favorites, [])
        finally:
            self._pop_busy()

    async def search_favorites(self, query: str = "") -> None:
        try:
            generation = self._load_generation
            self._push_busy()
            self._set_property_idle("error_message", None)
            self._search_query = query
            if not query or query.strip() == "":
                await self.load_favorites()
                return

            self._load_generation += 1
            generation = self._load_generation

            results = await asyncio.to_thread(
                self.favorites_service.search_favorites, query
            )

            # search_favorites always returns list[Wallpaper] now; map back
            # to the Favorite records for the view.
            all_favorites = await asyncio.to_thread(
                self.favorites_service.get_favorites
            )
            favorites_by_id = {
                favorite.wallpaper_id: favorite for favorite in all_favorites
            }
            matched_favorites = [
                favorites_by_id[wallpaper.id]
                for wallpaper in results
                if wallpaper.id in favorites_by_id
            ]

            if generation != self._load_generation:
                logger.debug("Discarding stale favorites search result")
                return
            GLib.idle_add(self._set_favorites, matched_favorites)

        except Exception as e:
            self._set_property_idle(
                "error_message", f"Failed to search favorites: {e}"
            )
            if generation == self._load_generation:
                GLib.idle_add(self._set_favorites, [])
        finally:
            self._pop_busy()

    def add_favorite_sync(
        self,
        wallpaper_id: str,
        full_url: str,
        path: str,
        source: str,
        tags: str,
    ) -> bool:
        """Synchronous version of add_favorite using global event loop."""
        try:
            loop = get_event_loop()
            future = asyncio.run_coroutine_threadsafe(
                self.add_favorite(wallpaper_id, full_url, path, source, tags),
                loop,
            )
            return future.result(timeout=30)
        except RuntimeError:
            # Event loop not set up, run synchronously (last resort)
            return asyncio.run(
                self.add_favorite(wallpaper_id, full_url, path, source, tags)
            )
        except Exception as e:
            logger.error(f"Failed to add favorite synchronously: {e}")
            return False

    async def add_favorite(
        self,
        wallpaper_id: str,
        full_url: str,
        path: str,
        source: str,
        tags: str,
    ) -> bool:
        try:
            self._push_busy()
            self._set_property_idle("error_message", None)

            try:
                wallpaper_source = WallpaperSource(source)
            except ValueError:
                wallpaper_source = WallpaperSource.LOCAL

            wallpaper = Wallpaper(
                id=wallpaper_id,
                url=full_url,
                path=path,
                resolution=Resolution(0, 0),
                source=wallpaper_source,
                category="favorites",
                purity=WallpaperPurity.SFW,
                tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
            )

            await asyncio.to_thread(self.favorites_service.add_favorite, wallpaper)
            schedule_async(self.load_favorites())
            self._show_toast("Added to favorites", "success")
            return True

        except Exception as e:
            self._set_property_idle("error_message", f"Failed to add favorite: {e}")
            self._show_toast(f"Failed to add favorite: {e}", "error")
            return False
        finally:
            self._pop_busy()

    async def remove_favorite(self, wallpaper_id: str | Favorite) -> bool:
        try:
            self._push_busy()
            self._set_property_idle("error_message", None)

            target_wallpaper_id = (
                wallpaper_id.wallpaper_id
                if isinstance(wallpaper_id, Favorite)
                else wallpaper_id
            )

            await asyncio.to_thread(
                self.favorites_service.remove_favorite, target_wallpaper_id
            )
            schedule_async(self.load_favorites())
            self._show_toast("Removed from favorites", "success")

            return True

        except Exception as e:
            self._set_property_idle(
                "error_message", f"Failed to remove favorite: {e}"
            )
            self._show_toast(f"Failed to remove favorite: {e}", "error")
            return False
        finally:
            self._pop_busy()

    async def set_wallpaper(self, favorite: Favorite) -> tuple[bool, str]:
        try:
            self._push_busy()
            self._set_property_idle("error_message", None)

            result = await self.wallpaper_setter.set_wallpaper_async(
                favorite.wallpaper.path
            )

            if result:
                self._emit_idle("wallpaper-set", favorite.wallpaper.id)
                self._show_toast("Wallpaper set successfully", "success")
                return True, "Wallpaper set successfully"

            return False, "Failed to set wallpaper"

        except Exception as e:
            self._set_property_idle("error_message", f"Failed to set wallpaper: {e}")
            self._show_toast(f"Failed to set wallpaper: {e}", "error")
            return False, f"Failed to set wallpaper: {e}"
        finally:
            self._pop_busy()

    async def set_wallpaper_async(self, favorite: Favorite) -> tuple[bool, str]:
        if not self.wallpaper_setter:
            return False, "Wallpaper setter not available"

        async with self._set_wallpaper_lock:
            try:
                self._push_busy()
                self._set_property_idle("error_message", None)

                wallpaper = favorite.wallpaper
                path = wallpaper.path

                if path.startswith(("http://", "https://")):
                    self._show_toast("Downloading wallpaper...", "info")

                    if not self.config_service or not self.wallhaven_service:
                        return False, "Required services not available"

                    config = self.config_service.get_config()
                    if not config:
                        return False, "Configuration not available"

                    filename = f"{wallpaper.id}.{path.rsplit('.', 1)[-1]}"
                    dest_path = (
                        config.local_wallpapers_dir or Path.home() / "Pictures"
                    ) / filename

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

                result = await self.wallpaper_setter.set_wallpaper_async(path)

                if result:
                    self._emit_idle("wallpaper-set", wallpaper.id)
                    return True, "Wallpaper set successfully"
                else:
                    return False, "Failed to set wallpaper"

            except Exception as e:
                self._set_property_idle(
                    "error_message", f"Failed to set wallpaper: {e}"
                )
                logger.error(f"Failed to set wallpaper: {e}", exc_info=True)
                return False, f"Failed to set wallpaper: {e}"
            finally:
                self._pop_busy()

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
        """Reload favorites from disk, clearing any active search.

        Schedules exactly one load - assigning ``search_query`` would trigger
        a second concurrent load through its property setter.
        """
        self._search_query = ""
        schedule_async(self.load_favorites())

    def select_all(self) -> None:
        """Select all favorites."""
        self._selected_wallpapers_list = self.wallpapers.copy()
        self._update_selection_state()

    def _show_toast(self, message: str, msg_type: str = "info"):
        """Show a toast via the injected ToastService (main thread safe)."""
        if not self.toast_service:
            logger.debug(f"No toast service available; dropping toast: {message}")
            return
        try:
            if msg_type == "success":
                self.toast_service.show_success(message)
            elif msg_type == "error":
                self.toast_service.show_error(message)
            elif msg_type == "warning":
                self.toast_service.show_warning(message)
            else:
                self.toast_service.show_info(message)
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"Could not show toast notification: {e}")
