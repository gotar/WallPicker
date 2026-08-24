"""Extended tests for WallhavenViewModel: downloads, pagination, favorites, staleness."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError

from domain.wallpaper import Wallpaper


async def _true_async(*args, **kwargs):
    return True


async def _false_async(*args, **kwargs):
    return False


async def _raise_oserror(*args, **kwargs):
    raise OSError("disk full")


@pytest.fixture
def dl_config(tmp_path, mock_config_service):
    """Config service pointing local_wallpapers_dir at a tmp directory."""
    mock_config_service.get_config.return_value = SimpleNamespace(
        local_wallpapers_dir=tmp_path
    )
    return mock_config_service


@pytest.fixture
def wh_vm(mock_wallhaven_service, dl_config, mock_idle_add):
    """WallhavenViewModel with a tmp download dir."""
    from unittest.mock import MagicMock

    from ui.view_models.wallhaven_view_model import WallhavenViewModel

    vm = WallhavenViewModel(
        wallhaven_service=mock_wallhaven_service,
        wallpaper_setter=MagicMock(),
        config_service=dl_config,
    )
    vm.wallpaper_setter.set_wallpaper_async = MagicMock()
    return vm


def make_wallpaper(wallpaper_id="wh_x", path="/tmp/wh_x.jpg"):
    from domain.wallpaper import Resolution, WallpaperPurity, WallpaperSource

    return Wallpaper(
        id=wallpaper_id,
        url=f"https://wallhaven.cc/w/{wallpaper_id}",
        path=path,
        resolution=Resolution(1920, 1080),
        source=WallpaperSource.WALLHAVEN,
        category="general",
        purity=WallpaperPurity.SFW,
    )


class TestPaginationBounds:
    async def test_load_next_page_at_last_page_is_noop(
        self, wh_vm, mock_wallhaven_service
    ):
        await wh_vm.search_wallpapers(query="test")
        wh_vm.total_pages = 5
        wh_vm.current_page = 5
        mock_wallhaven_service.search.reset_mock()

        await wh_vm.load_next_page()

        mock_wallhaven_service.search.assert_not_called()
        assert wh_vm.current_page == 5

    async def test_load_prev_page_before_first_is_noop(
        self, wh_vm, mock_wallhaven_service
    ):
        await wh_vm.search_wallpapers(query="test", page=1)
        mock_wallhaven_service.search.reset_mock()

        await wh_vm.load_prev_page()

        mock_wallhaven_service.search.assert_not_called()
        assert wh_vm.current_page == 1

    async def test_can_load_helpers(self, wh_vm):
        wh_vm._current_page = 2
        wh_vm._total_pages = 3
        assert wh_vm.can_load_next_page() is True
        assert wh_vm.can_load_prev_page() is True

        wh_vm._current_page = 3
        assert wh_vm.can_load_next_page() is False
        assert wh_vm.has_prev_page() is True

    async def test_total_wallpapers_property_roundtrip(self, wh_vm):
        wh_vm.total_wallpapers = 42
        assert wh_vm.total_wallpapers == 42

    async def test_select_all_updates_selection_state(self, wh_vm):
        await wh_vm.search_wallpapers(query="test")
        wh_vm.select_all()
        assert wh_vm.selected_count == 3
        assert len(wh_vm.get_selected_wallpapers()) == 3

    async def test_append_results_merges_pages(
        self, wh_vm, mock_wallhaven_service
    ):
        await wh_vm.search_wallpapers(query="test")
        await wh_vm.search_wallpapers(query="test", page=2, append_results=True)
        assert len(wh_vm.wallpapers) == 6

    async def test_overlapping_search_is_skipped_newest_waits(
        self, wh_vm, mock_wallhaven_service
    ):
        """While a search holds the lock, a second request is dropped."""
        release = asyncio.Event()

        async def slow_search(*args, **kwargs):
            await release.wait()

        mock_wallhaven_service.search = AsyncMock(side_effect=slow_search)

        first = asyncio.create_task(wh_vm.search_wallpapers(query="first"))
        await asyncio.sleep(0)
        assert wh_vm._search_lock.locked()

        await wh_vm.search_wallpapers(query="second")

        # Only the first search reached the service
        mock_wallhaven_service.search.assert_called_once()
        release.set()
        await first


class TestLoadInitialWallpapers:
    async def test_load_initial_passes_current_filters(
        self, wh_vm, mock_wallhaven_service
    ):
        wh_vm.search_query = "nature"
        wh_vm.sorting = "views"
        wh_vm.top_range = "1M"

        await wh_vm.load_initial_wallpapers()

        _, kwargs = mock_wallhaven_service.search.call_args
        assert kwargs["query"] == "nature"
        assert kwargs["page"] == 1
        # Initial load forces SFW and no minimum resolution (L11 behavior)
        assert kwargs["purity"] == "100"
        assert kwargs["atleast"] == ""
        assert kwargs["sorting"] == "views"


class TestDownloadWallpaper:
    async def test_download_success_returns_dest_path(
        self, wh_vm, mock_wallhaven_service, tmp_path
    ):
        mock_wallhaven_service.download = AsyncMock(side_effect=_true_async)
        wp = make_wallpaper()

        result = await wh_vm.download_wallpaper(wp)

        assert result == str(tmp_path / "wh_x.jpg")
        expected_dest = tmp_path / "wh_x.jpg"
        mock_wallhaven_service.download.assert_awaited_once_with(wp, expected_dest)

    async def test_download_skips_when_file_already_exists(
        self, wh_vm, mock_wallhaven_service, tmp_path
    ):
        (tmp_path / "wh_x.jpg").write_bytes(b"data")
        wp = make_wallpaper()

        result = await wh_vm.download_wallpaper(wp)

        assert result == str(tmp_path / "wh_x.jpg")
        mock_wallhaven_service.download.assert_not_called()

    async def test_download_without_url_returns_none(self, wh_vm, tmp_path):
        wp = make_wallpaper()
        wp.url = ""

        assert await wh_vm.download_wallpaper(wp) is None

    async def test_download_failure_sets_error_and_restores_busy(
        self, wh_vm, mock_wallhaven_service
    ):
        mock_wallhaven_service.download = AsyncMock(side_effect=_false_async)
        wp = make_wallpaper()

        result = await wh_vm.download_wallpaper(wp)

        assert result is None
        assert "Failed to download wallpaper wh_x" in wh_vm.error_message
        assert wh_vm.is_busy is False

    async def test_download_oserror_sets_error_and_restores_busy(
        self, wh_vm, mock_wallhaven_service
    ):
        mock_wallhaven_service.download = AsyncMock(side_effect=_raise_oserror)
        wp = make_wallpaper()

        result = await wh_vm.download_wallpaper(wp)

        assert result is None
        assert "Download error:" in wh_vm.error_message
        assert wh_vm.is_busy is False


class TestDownloadWallpaperAsync:
    async def test_success_emits_signal_via_idle(self, wh_vm, mock_wallhaven_service):
        mock_wallhaven_service.download = AsyncMock(side_effect=_true_async)
        received = []
        wh_vm.connect(
            "wallpaper-downloaded", lambda _s, path: received.append(path)
        )

        path, message = await wh_vm.download_wallpaper_async(make_wallpaper())

        assert path is not None
        assert message == "Downloaded successfully"
        assert received == [path]
        assert wh_vm.is_busy is False

    async def test_failure_returns_none_message(
        self, wh_vm, mock_wallhaven_service
    ):
        mock_wallhaven_service.download = AsyncMock(side_effect=_false_async)

        path, message = await wh_vm.download_wallpaper_async(make_wallpaper())

        assert path is None
        assert message == "Failed to download wallpaper"

    async def test_client_error_from_service_is_contained(
        self, wh_vm, mock_wallhaven_service
    ):
        """download_wallpaper catches ClientError internally and reports failure."""

        async def boom(*args, **kwargs):
            raise ClientError("connection reset")

        mock_wallhaven_service.download = AsyncMock(side_effect=boom)

        path, message = await wh_vm.download_wallpaper_async(make_wallpaper())

        assert path is None
        assert message == "Failed to download wallpaper"
        assert "Download error: connection reset" in wh_vm.error_message
    async def test_unexpected_download_error_is_reported(
        self, wh_vm, mocker
    ):
        """download_wallpaper_async guards against errors from the wrapper itself."""
        mocker.patch.object(
            type(wh_vm),
            "download_wallpaper",
            autospec=True,
            side_effect=OSError("disk on fire"),
        )

        path, message = await wh_vm.download_wallpaper_async(make_wallpaper())

        assert path is None
        assert message == "Download error: disk on fire"
        assert "Download error: disk on fire" in wh_vm.error_message


class TestSetWallpaperVariants:
    async def test_set_wallpaper_success(self, wh_vm, mock_wallhaven_service):
        mock_wallhaven_service.download = AsyncMock(side_effect=_true_async)
        wh_vm.wallpaper_setter.set_wallpaper_async = AsyncMock(side_effect=_true_async)

        ok, message = await wh_vm.set_wallpaper(make_wallpaper())

        assert ok is True
        assert message == "Wallpaper set successfully"
        assert wh_vm.is_busy is False

    async def test_set_wallpaper_download_failure(self, wh_vm, mock_wallhaven_service):
        mock_wallhaven_service.download = AsyncMock(side_effect=_false_async)

        ok, message = await wh_vm.set_wallpaper(make_wallpaper())

        assert ok is False
        assert message == "Failed to download wallpaper"

    async def test_set_wallpaper_setter_failure(self, wh_vm, mock_wallhaven_service):
        mock_wallhaven_service.download = AsyncMock(side_effect=_true_async)
        wh_vm.wallpaper_setter.set_wallpaper_async = AsyncMock(side_effect=_false_async)

        ok, message = await wh_vm.set_wallpaper(make_wallpaper())

        assert ok is False
        assert message == "Failed to set wallpaper"

    async def test_set_wallpaper_exception_reported(
        self, wh_vm, mock_wallhaven_service
    ):
        """A failing download surfaces as a set_wallpaper failure tuple."""
        mock_wallhaven_service.download = AsyncMock(side_effect=_raise_oserror)

        ok, message = await wh_vm.set_wallpaper(make_wallpaper())

        assert ok is False
        assert message == "Failed to download wallpaper"
        assert wh_vm.is_busy is False

    async def test_set_wallpaper_async_success(self, wh_vm, mock_wallhaven_service):
        mock_wallhaven_service.download = AsyncMock(side_effect=_true_async)
        wh_vm.wallpaper_setter.set_wallpaper_async = AsyncMock(side_effect=_true_async)

        ok, message = await wh_vm.set_wallpaper_async(make_wallpaper())

        assert ok is True
        assert message == "Wallpaper set successfully"

    async def test_set_wallpaper_async_setter_failure(
        self, wh_vm, mock_wallhaven_service
    ):
        mock_wallhaven_service.download = AsyncMock(side_effect=_true_async)
        wh_vm.wallpaper_setter.set_wallpaper_async = AsyncMock(side_effect=_false_async)

        ok, message = await wh_vm.set_wallpaper_async(make_wallpaper())

        assert ok is False
        assert message == "Failed to set wallpaper"

    async def test_set_wallpaper_setter_exception_sets_error(
        self, wh_vm, mock_wallhaven_service
    ):
        """Unexpected setter exceptions are reported via error_message."""
        mock_wallhaven_service.download = AsyncMock(side_effect=_true_async)
        wh_vm.wallpaper_setter.set_wallpaper_async = AsyncMock(
            side_effect=RuntimeError("gtk gone")
        )

        ok, message = await wh_vm.set_wallpaper(make_wallpaper())

        assert ok is False
        assert message == "gtk gone"
        assert "gtk gone" in wh_vm.error_message

    async def test_set_wallpaper_async_download_failure(
        self, wh_vm, mock_wallhaven_service
    ):
        mock_wallhaven_service.download = AsyncMock(side_effect=_false_async)
        wh_vm.wallpaper_setter.set_wallpaper_async = AsyncMock(side_effect=_true_async)

        ok, message = await wh_vm.set_wallpaper_async(make_wallpaper())

        assert ok is False
        assert message == "Failed to download wallpaper"
        wh_vm.wallpaper_setter.set_wallpaper_async.assert_not_awaited()

    async def test_set_wallpaper_async_catches_value_error(
        self, wh_vm, mock_wallhaven_service
    ):
        """ValueError raised while setting (not downloading) is caught here."""
        mock_wallhaven_service.download = AsyncMock(side_effect=_true_async)

        async def bad_setter(*args, **kwargs):
            raise ValueError("bad purity")

        wh_vm.wallpaper_setter.set_wallpaper_async = AsyncMock(
            side_effect=bad_setter
        )

        ok, message = await wh_vm.set_wallpaper_async(make_wallpaper())

        assert ok is False
        assert "Failed to set wallpaper: bad purity" == message


class TestAddToFavoritesAsync:
    async def test_without_service_reports_error(self, wh_vm):
        wh_vm.favorites_service = None

        ok, message = await wh_vm.add_to_favorites_async(make_wallpaper())

        assert ok is False
        assert message == "Favorites service not available"

    async def test_already_favorite_short_circuits(self, wh_vm, mocker):
        fav_service = mocker.MagicMock()
        fav_service.is_favorite.return_value = True
        wh_vm.favorites_service = fav_service

        ok, message = await wh_vm.add_to_favorites_async(make_wallpaper())

        assert (ok, message) == (False, "Already in favorites")
        fav_service.add_favorite.assert_not_called()
        assert wh_vm.is_busy is False

    async def test_success_adds_wallpaper(self, wh_vm, mocker):
        fav_service = mocker.MagicMock()
        fav_service.is_favorite.return_value = False
        wh_vm.favorites_service = fav_service
        wp = make_wallpaper()

        ok, message = await wh_vm.add_to_favorites_async(wp)

        assert (ok, message) == (True, "Added to favorites")
        fav_service.add_favorite.assert_called_once_with(wp)

    async def test_failure_sets_error_message(self, wh_vm, mocker):
        fav_service = mocker.MagicMock()
        fav_service.is_favorite.return_value = False
        fav_service.add_favorite.side_effect = OSError("disk full")
        wh_vm.favorites_service = fav_service

        ok, message = await wh_vm.add_to_favorites_async(make_wallpaper())

        assert ok is False
        assert "Failed to add to favorites: disk full" == message
        assert "disk full" in wh_vm.error_message
