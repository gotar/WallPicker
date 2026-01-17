"""ViewModel for Wallhaven wallpaper browsing"""

import asyncio
import logging
import sys
from pathlib import Path

import gi
from aiohttp import ClientError

gi.require_version("Gtk", "4.0")
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gi.repository import GObject  # noqa: E402

from domain.wallpaper import Wallpaper  # noqa: E402
from services.favorites_service import FavoritesService  # noqa: E402
from services.wallhaven_service import WallhavenService  # noqa: E402
from ui.view_models.base import BaseViewModel  # noqa: E402

logger = logging.getLogger(__name__)


class WallhavenViewModel(BaseViewModel):
    """ViewModel for Wallhaven wallpaper browsing"""

    __gsignals__ = {
        "wallpaper-downloaded": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    def __init__(
        self,
        wallhaven_service: WallhavenService,
        wallpaper_setter,
        config_service,
    ) -> None:
        super().__init__()
        self.wallhaven_service = wallhaven_service
        self.wallpaper_setter = wallpaper_setter
        self.config_service = config_service
        self.favorites_service: FavoritesService | None = None

        self._wallpapers: list[Wallpaper] = []
        self._current_page = 1
        self._total_pages = 1
        self._total_wallpapers = 0
        self._search_query = ""
        self._category = "111"
        self._purity = "100"
        self._sorting = "toplist"
        self._order = "desc"
        self._resolution = ""
        self._top_range = ""
        self._ratios = ""
        self._colors = ""
        self._resolutions = ""
        self._seed = ""

        # Async lock to prevent concurrent searches
        self._search_lock = asyncio.Lock()

        # Async lock to prevent concurrent add_to_favorites operations
        self._add_to_favorites_lock = asyncio.Lock()

    @GObject.Property(type=object)
    def wallpapers(self) -> list[Wallpaper]:
        return self._wallpapers

    @wallpapers.setter
    def wallpapers(self, value: list[Wallpaper]) -> None:
        self._wallpapers = value

    @GObject.Property(type=int, default=1)
    def current_page(self) -> int:
        return self._current_page

    @current_page.setter
    def current_page(self, value: int) -> None:
        self._current_page = value

    @GObject.Property(type=int, default=1)
    def total_pages(self) -> int:
        return self._total_pages

    @total_pages.setter
    def total_pages(self, value: int) -> None:
        self._total_pages = value

    @GObject.Property(type=int, default=0)
    def total_wallpapers(self) -> int:
        return self._total_wallpapers

    @total_wallpapers.setter
    def total_wallpapers(self, value: int) -> None:
        self._total_wallpapers = value

    @GObject.Property(type=str, default="")
    def search_query(self) -> str:
        return self._search_query

    @search_query.setter
    def search_query(self, value: str) -> None:
        self._search_query = value

    @GObject.Property(type=str, default="111")
    def category(self) -> str:
        return self._category

    @category.setter
    def category(self, value: str) -> None:
        self._category = value

    @GObject.Property(type=str, default="100")
    def purity(self) -> str:
        return self._purity

    @purity.setter
    def purity(self, value: str) -> None:
        self._purity = value

    @GObject.Property(type=str, default="toplist")
    def sorting(self) -> str:
        return self._sorting

    @sorting.setter
    def sorting(self, value: str) -> None:
        self._sorting = value

    @GObject.Property(type=str, default="desc")
    def order(self) -> str:
        return self._order

    @order.setter
    def order(self, value: str) -> None:
        self._order = value

    @GObject.Property(type=str, default="")
    def resolution(self) -> str:
        return self._resolution

    @resolution.setter
    def resolution(self, value: str) -> None:
        self._resolution = value

    @GObject.Property(type=str, default="")
    def top_range(self) -> str:
        return self._top_range

    @top_range.setter
    def top_range(self, value: str) -> None:
        self._top_range = value

    @GObject.Property(type=str, default="")
    def ratios(self) -> str:
        return self._ratios

    @ratios.setter
    def ratios(self, value: str) -> None:
        self._ratios = value

    @GObject.Property(type=str, default="")
    def colors(self) -> str:
        return self._colors

    @colors.setter
    def colors(self, value: str) -> None:
        self._colors = value

    @GObject.Property(type=str, default="")
    def resolutions(self) -> str:
        return self._resolutions

    @resolutions.setter
    def resolutions(self, value: str) -> None:
        self._resolutions = value

    @GObject.Property(type=str, default="")
    def seed(self) -> str:
        return self._seed

    @seed.setter
    def seed(self, value: str) -> None:
        self._seed = value

    async def load_initial_wallpapers(self) -> None:
        """Load initial wallpapers with current parameters"""
        logger.info("Loading initial Wallhaven wallpapers")
        await self.search_wallpapers(
            query=self.search_query,
            page=1,
            category=self.category,
            purity="100",
            sorting=self.sorting,
            order="desc",
            resolution="",
            top_range=self.top_range,
            ratios=self.ratios,
            colors=self.colors,
            resolutions=self.resolutions,
            seed=self.seed,
        )
        logger.info(f"Loaded {len(self.wallpapers)} wallpapers")

    async def search_wallpapers(
        self,
        query: str = "",
        page: int = 1,
        category: str = "111",
        purity: str = "100",
        sorting: str = "toplist",
        order: str = "desc",
        resolution: str = "",
        top_range: str = "",
        ratios: str = "",
        colors: str = "",
        resolutions: str = "",
        seed: str = "",
        append_results: bool = False,
    ) -> None:
        """Search wallpapers on Wallhaven with concurrent search protection"""
        # Try to acquire lock - if another search is running, skip this one
        if self._search_lock.locked():
            logger.debug(
                "Search already in progress, skipping concurrent search request"
            )
            return

        async with self._search_lock:
            try:
                self.is_busy = True
                self.error_message = None
                self.search_query = query
                self.category = category
                self.purity = purity
                self.sorting = sorting
                self.order = order
                self.resolution = resolution
                self.top_range = top_range
                self.ratios = ratios
                self.colors = colors
                self.resolutions = resolutions
                self.seed = seed

                logger.debug(
                    f"Starting search: query='{query}', category={category}, page={page}"
                )

                wallpapers, meta = await self.wallhaven_service.search(
                    query=query,
                    page=page,
                    categories=category,
                    purity=purity,
                    sorting=sorting,
                    order=order,
                    atleast=resolution,
                    top_range=top_range,
                    ratios=ratios,
                    colors=colors,
                    resolutions=resolutions,
                    seed=seed,
                )

                if append_results and self.wallpapers:
                    self.wallpapers = self.wallpapers + wallpapers
                else:
                    self.wallpapers = wallpapers

                self.current_page = meta.get("current_page", page)
                self.total_pages = meta.get("last_page", page + 1)
                self.total_wallpapers = meta.get("total", 0)

                logger.debug(
                    f"Search completed: {len(wallpapers)} wallpapers, page {self.current_page}/{self.total_pages}"
                )

            except (ClientError, ValueError, OSError, Exception) as e:
                error_msg = f"Failed to search wallpapers: {e}"
                self.error_message = error_msg
                self.wallpapers = []
                logger.error(error_msg, exc_info=True)
            finally:
                self.is_busy = False

    async def load_next_page(self) -> None:
        """Load next page of wallpapers"""
        if self.current_page < self.total_pages:
            await self.search_wallpapers(
                query=self.search_query,
                page=self.current_page + 1,
                category=self.category,
                purity=self.purity,
                sorting=self.sorting,
                order=self.order,
                resolution=self.resolution,
                top_range=self.top_range,
                ratios=self.ratios,
                colors=self.colors,
                resolutions=self.resolutions,
                seed=self.seed,
                append_results=False,
            )

    async def load_prev_page(self) -> None:
        """Load previous page of wallpapers"""
        target_page = self.current_page - 1
        if target_page >= 1:
            await self.search_wallpapers(
                query=self.search_query,
                page=target_page,
                category=self.category,
                purity=self.purity,
                sorting=self.sorting,
                order=self.order,
                resolution=self.resolution,
                top_range=self.top_range,
                ratios=self.ratios,
                colors=self.colors,
                resolutions=self.resolutions,
                seed=self.seed,
                append_results=False,
            )

    def has_next_page(self) -> bool:
        """Check if there's a next page"""
        return self.current_page < self.total_pages

    def has_prev_page(self) -> bool:
        """Check if there's a previous page"""
        return self.current_page > 1

    def select_all(self) -> None:
        """Select all wallpapers."""
        self._selected_wallpapers_list = self.wallpapers.copy()
        self._update_selection_state()

    def can_load_next_page(self) -> bool:
        """Check if there's a next page available"""
        return self.current_page < self.total_pages

    def can_load_prev_page(self) -> bool:
        """Check if there's a previous page available"""
        return self.current_page > 1

    def can_navigate(self) -> bool:
        """Check if pagination navigation is available"""
        return self.has_next_page() or self.has_prev_page()

    async def set_wallpaper(self, wallpaper: Wallpaper) -> tuple[bool, str]:
        try:
            self.is_busy = True
            self.error_message = None

            local_path = await self.download_wallpaper(wallpaper)
            if not local_path:
                return False, "Failed to download wallpaper"

            success = await self.wallpaper_setter.set_wallpaper_async(local_path)
            if success:
                return True, "Wallpaper set successfully"
            return False, "Failed to set wallpaper"
        except Exception as e:
            self.error_message = str(e)
            return False, str(e)
        finally:
            self.is_busy = False

    async def add_to_favorites_async(self, wallpaper: Wallpaper) -> tuple[bool, str]:
        """Add wallpaper to favorites. Returns (success, message) tuple."""
        if not self.favorites_service:
            self.error_message = "Favorites service not available"
            return False, "Favorites service not available"

        async with self._add_to_favorites_lock:
            try:
                self.is_busy = True
                self.error_message = None

                if await asyncio.to_thread(
                    self.favorites_service.is_favorite, wallpaper.id
                ):
                    return False, "Already in favorites"

                await asyncio.to_thread(self.favorites_service.add_favorite, wallpaper)
                return True, "Added to favorites"

            except (ValueError, OSError) as e:
                self.error_message = f"Failed to add to favorites: {e}"
                return False, f"Failed to add to favorites: {e}"
            finally:
                self.is_busy = False

    async def set_wallpaper_async(self, wallpaper: Wallpaper) -> tuple[bool, str]:
        """Set wallpaper as desktop background. Returns (success, message) tuple."""
        try:
            self.is_busy = True
            self.error_message = None

            local_path = await self.download_wallpaper(wallpaper)
            if not local_path:
                return False, "Failed to download wallpaper"

            success = await self.wallpaper_setter.set_wallpaper_async(local_path)
            if success:
                return True, "Wallpaper set successfully"
            else:
                return False, "Failed to set wallpaper"

        except (ValueError, OSError) as e:
            self.error_message = f"Failed to set wallpaper: {e}"
            return False, f"Failed to set wallpaper: {e}"
        finally:
            self.is_busy = False

    async def download_wallpaper_async(
        self, wallpaper: Wallpaper
    ) -> tuple[str | None, str]:
        """Download wallpaper and return (path, message) tuple."""
        try:
            self.is_busy = True
            self.error_message = None

            path = await self.download_wallpaper(wallpaper)
            if path:
                # Emit signal that download completed successfully
                self.emit("wallpaper-downloaded", path)
                return path, "Downloaded successfully"
            else:
                return None, "Failed to download wallpaper"

        except (ValueError, OSError, ClientError) as e:
            self.error_message = f"Download error: {e}"
            return None, f"Download error: {e}"
        finally:
            self.is_busy = False

    async def download_wallpaper(self, wallpaper: Wallpaper) -> str | None:
        """Download wallpaper and return the local path, or None on failure."""
        config = self.config_service.get_config()

        if not wallpaper.url:
            return None

        try:
            self.is_busy = True

            filename = f"{wallpaper.id}.{wallpaper.path.rsplit('.', 1)[-1]}"
            dest_path = config.local_wallpapers_dir / filename

            # Check if already downloaded
            if dest_path.exists():
                logger.info(f"Wallpaper {wallpaper.id} already exists at {dest_path}")
                return str(dest_path)

            success = await self.wallhaven_service.download(wallpaper, dest_path)

            if success:
                # DO NOT mutate wallpaper.path - it contains the download URL!
                # The local path is returned directly to the caller
                return str(dest_path)
            else:
                self.error_message = f"Failed to download wallpaper {wallpaper.id}"
                return None

        except (ClientError, OSError, ValueError) as e:
            import traceback

            traceback.print_exc()
            self.error_message = f"Download error: {e}"
            return None
        finally:
            self.is_busy = False
