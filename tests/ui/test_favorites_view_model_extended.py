"""Extended tests for FavoritesViewModel: set_wallpaper, remote download, staleness, toasts."""

import asyncio
import threading
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from domain.favorite import Favorite
from domain.wallpaper import Resolution, Wallpaper, WallpaperPurity, WallpaperSource


def make_wallpaper(wallpaper_id="wp_1", path="/path/to/wp_1.jpg"):
    return Wallpaper(
        id=wallpaper_id,
        url=f"https://example.com/{wallpaper_id}.jpg",
        path=path,
        resolution=Resolution(1920, 1080),
        source=WallpaperSource.WALLHAVEN,
        category="general",
        purity=WallpaperPurity.SFW,
    )


def make_favorite(wallpaper=None):
    return Favorite(wallpaper=wallpaper or make_wallpaper(), added_at=datetime.now())


class ToastRecorder:
    """Captures toast calls for all severity levels."""

    def __init__(self):
        self.calls = []

    def show_success(self, message):
        self.calls.append(("success", message))

    def show_error(self, message):
        self.calls.append(("error", message))

    def show_warning(self, message):
        self.calls.append(("warning", message))

    def show_info(self, message):
        self.calls.append(("info", message))


@pytest.fixture
def fav_vm(mocker, tmp_path):
    """FavoritesViewModel with inline idle_add and captured schedule_async."""
    from ui.view_models.favorites_view_model import FavoritesViewModel

    mocker.patch(
        "gi.repository.GLib.idle_add",
        side_effect=lambda func, *args: func(*args),
    )
    scheduled = []
    mocker.patch(
        "ui.view_models.favorites_view_model.schedule_async",
        side_effect=lambda coro: scheduled.append(coro),
    )
    mocker.patch(
        "ui.view_models.favorites_view_model.get_event_loop",
        side_effect=RuntimeError("no loop in tests"),
    )

    service = MagicMock()
    service.get_favorites.return_value = []
    service.is_favorite.return_value = False
    setter = MagicMock()
    setter.set_wallpaper_async = MagicMock()
    config_service = MagicMock()
    config_service.get_config.return_value = SimpleNamespace(
        local_wallpapers_dir=tmp_path
    )
    wallhaven = MagicMock()
    wallhaven.download = MagicMock()

    vm = FavoritesViewModel(
        favorites_service=service,
        wallpaper_setter=setter,
        config_service=config_service,
        wallhaven_service=wallhaven,
    )
    vm._scheduled_for_test = scheduled
    return vm


def async_setter(vm, result=True, exc=None):
    vm.wallpaper_setter.set_wallpaper_async = AsyncMock(
        side_effect=exc, return_value=result
    )


async def drain(vm):
    """Run all captured coroutines to completion."""
    while vm._scheduled_for_test:
        await vm._scheduled_for_test.pop(0)


class TestProperties:
    def test_wallpapers_getter_maps_favorites(self, fav_vm):
        fav_vm._favorites = [make_favorite(), make_favorite(make_wallpaper("wp_2"))]
        assert [w.id for w in fav_vm.wallpapers] == ["wp_1", "wp_2"]

    def test_wallpapers_setter_is_deliberately_noop(self, fav_vm):
        fav_vm.wallpapers = [make_wallpaper("ignored")]
        assert fav_vm.wallpapers == []

    def test_favorites_setter_updates_list(self, fav_vm):
        favorite = make_favorite()
        fav_vm.favorites = [favorite]
        assert fav_vm.favorites == [favorite]

    async def test_search_query_setter_schedules_load_or_search(self, fav_vm):
        fav_vm.search_query = "anime"
        assert len(fav_vm._scheduled_for_test) == 1

        fav_vm.search_query = ""
        assert len(fav_vm._scheduled_for_test) == 2

        # Both captured coroutines run cleanly
        await drain(fav_vm)


class TestLoadFavoritesBranches:
    async def test_stale_load_is_discarded(self, fav_vm):
        await fav_vm.load_favorites()
        assert len(fav_vm.favorites) == 0

        fav_vm.favorites_service.get_favorites.return_value = [make_favorite()]

        def bump_generation_and_return_empty():
            fav_vm._load_generation += 1
            return []

        fav_vm.favorites_service.get_favorites.side_effect = (
            bump_generation_and_return_empty
        )

        await fav_vm.load_favorites()

        # Stale completion must not overwrite the current list
        assert len(fav_vm.favorites) == 0
        assert fav_vm.error_message is None

    async def test_load_failure_sets_error_and_clears(self, fav_vm):
        await fav_vm.load_favorites()
        fav_vm.favorites_service.get_favorites.side_effect = OSError("disk gone")

        await fav_vm.load_favorites()

        assert "Failed to load favorites" in fav_vm.error_message
        assert fav_vm.favorites == []
        assert fav_vm.is_busy is False


class TestSearchFavoritesBranches:
    async def test_search_with_whitespace_only_query_reloads_all(self, fav_vm):
        fav_vm.favorites_service.get_favorites.return_value = [
            make_favorite(),
            make_favorite(make_wallpaper("wp_2")),
        ]

        await fav_vm.search_favorites("   ")

        assert len(fav_vm.favorites) == 2

    async def test_stale_search_result_is_discarded(self, fav_vm):
        await fav_vm.load_favorites()

        def bump_generation(*args, **kwargs):
            fav_vm._load_generation += 1
            return [make_wallpaper("wp_9")]

        fav_vm.favorites_service.search_favorites.side_effect = bump_generation

        await fav_vm.search_favorites("query")

        assert "Discarding stale" not in (fav_vm.error_message or "")
        assert fav_vm.error_message is None

    async def test_search_failure_sets_error_and_clears(self, fav_vm):
        fav_vm.favorites_service.get_favorites.return_value = [make_favorite()]
        await fav_vm.load_favorites()

        fav_vm.favorites_service.search_favorites.side_effect = ValueError("bad query")

        await fav_vm.search_favorites("query")

        assert "Failed to search favorites" in fav_vm.error_message
        assert fav_vm.favorites == []
        assert fav_vm.is_busy is False


class TestAddFavoriteSync:
    async def test_sync_wrapper_runs_coroutine_in_fresh_loop(self, fav_vm, mocker):
        """get_event_loop raising RuntimeError falls back to asyncio.run.

        Runs in a worker thread because the test itself already has a loop.
        """

        def fail_loop():
            raise RuntimeError("no loop")

        mocker.patch(
            "ui.view_models.favorites_view_model.get_event_loop",
            side_effect=fail_loop,
        )

        result = await asyncio.to_thread(
            fav_vm.add_favorite_sync,
            "id1",
            "https://x/1.jpg",
            "/p/1.jpg",
            "local",
            "",
        )

        assert result is True
        fav_vm.favorites_service.add_favorite.assert_called_once()

    async def test_sync_wrapper_schedules_on_global_event_loop(self, fav_vm, mocker):
        """With a live global loop, the coroutine is scheduled via threadsafe."""
        loop = asyncio.new_event_loop()
        worker = threading.Thread(target=loop.run_forever, daemon=True)
        worker.start()
        mocker.patch(
            "ui.view_models.favorites_view_model.get_event_loop",
            return_value=loop,
        )
        try:
            result = await asyncio.to_thread(
                fav_vm.add_favorite_sync,
                "id1",
                "https://x/1.jpg",
                "/p/1.jpg",
                "local",
                "",
            )
        finally:
            loop.call_soon_threadsafe(loop.stop)
            worker.join(timeout=5)
            loop.close()

        assert result is True
        fav_vm.favorites_service.add_favorite.assert_called_once()

    def test_generic_scheduling_failure_returns_false(self, fav_vm, mocker):
        def broken_loop():
            raise ValueError("loop unusable")

        mocker.patch(
            "ui.view_models.favorites_view_model.get_event_loop",
            side_effect=broken_loop,
        )

        result = fav_vm.add_favorite_sync("id1", "https://x/1.jpg", "/p/1.jpg", "local", "")

        assert result is False


class TestAddFavoriteAsync:
    async def test_invalid_source_falls_back_to_local(self, fav_vm):
        ok = await fav_vm.add_favorite("id1", "https://x/1.jpg", "/p/1.jpg", "bogus", " tag1 , , tag2 ")

        assert ok is True
        wallpaper = fav_vm.favorites_service.add_favorite.call_args[0][0]
        assert wallpaper.source == WallpaperSource.LOCAL
        assert wallpaper.tags == ["tag1", "tag2"]

    async def test_valid_source_is_preserved(self, fav_vm):
        ok = await fav_vm.add_favorite(
            "id1", "https://x/1.jpg", "/p/1.jpg", "wallhaven", ""
        )

        assert ok is True
        wallpaper = fav_vm.favorites_service.add_favorite.call_args[0][0]
        assert wallpaper.source == WallpaperSource.WALLHAVEN

    async def test_failure_shows_error_toast_and_message(self, fav_vm):
        recorder = ToastRecorder()
        fav_vm.toast_service = recorder
        fav_vm.favorites_service.add_favorite.side_effect = OSError("disk full")

        ok = await fav_vm.add_favorite("id1", "https://x/1.jpg", "/p/1.jpg", "local", "")

        assert ok is False
        assert "Failed to add favorite: disk full" in fav_vm.error_message
        assert ("error", "Failed to add favorite: disk full") in recorder.calls


class TestRemoveFavoriteFailure:
    async def test_remove_failure_reports_error(self, fav_vm):
        recorder = ToastRecorder()
        fav_vm.toast_service = recorder
        fav_vm.favorites_service.remove_favorite.side_effect = OSError("read-only fs")

        ok = await fav_vm.remove_favorite("wp_1")

        assert ok is False
        assert "Failed to remove favorite" in fav_vm.error_message
        assert ("error", "Failed to remove favorite: read-only fs") in recorder.calls


class TestSetWallpaper:
    async def test_success_emits_signal_and_toast(self, fav_vm):
        recorder = ToastRecorder()
        fav_vm.toast_service = recorder
        async_setter(fav_vm, True)
        received = []
        fav_vm.connect("wallpaper-set", lambda _s, wid: received.append(wid))

        ok, message = await fav_vm.set_wallpaper(make_favorite())

        assert ok is True
        assert message == "Wallpaper set successfully"
        assert received == ["wp_1"]
        assert ("success", "Wallpaper set successfully") in recorder.calls
        assert fav_vm.is_busy is False

    async def test_setter_false_returns_failure_without_toast(self, fav_vm):
        recorder = ToastRecorder()
        fav_vm.toast_service = recorder
        async_setter(fav_vm, False)

        ok, message = await fav_vm.set_wallpaper(make_favorite())

        assert ok is False
        assert message == "Failed to set wallpaper"
        assert recorder.calls == []

    async def test_setter_exception_is_reported(self, fav_vm):
        recorder = ToastRecorder()
        fav_vm.toast_service = recorder
        async_setter(fav_vm, exc=OSError("permission denied"))

        ok, message = await fav_vm.set_wallpaper(make_favorite())

        assert ok is False
        assert "permission denied" in message
        assert "permission denied" in fav_vm.error_message
        assert ("error", message) in recorder.calls


class TestSetWallpaperAsync:
    async def test_missing_setter_short_circuits(self, fav_vm):
        fav_vm.wallpaper_setter = None

        ok, message = await fav_vm.set_wallpaper_async(make_favorite())

        assert ok is False
        assert message == "Wallpaper setter not available"

    async def test_local_path_sets_directly(self, fav_vm):
        async_setter(fav_vm, True)
        received = []
        fav_vm.connect("wallpaper-set", lambda _s, wid: received.append(wid))

        ok, message = await fav_vm.set_wallpaper_async(make_favorite())

        assert ok is True
        fav_vm.wallpaper_setter.set_wallpaper_async.assert_awaited_with("/path/to/wp_1.jpg")
        assert received == ["wp_1"]

    async def test_remote_without_services_fails(self, fav_vm):
        fav_vm.config_service = None
        wp = make_wallpaper(path="https://example.com/wp_1.jpg")

        ok, message = await fav_vm.set_wallpaper_async(make_favorite(wp))

        assert ok is False
        assert message == "Required services not available"

    async def test_remote_with_missing_config_fails(self, fav_vm):
        fav_vm.config_service.get_config.return_value = None
        wp = make_wallpaper(path="https://example.com/wp_1.jpg")

        ok, message = await fav_vm.set_wallpaper_async(make_favorite(wp))

        assert ok is False
        assert message == "Configuration not available"

    async def test_remote_download_failure(self, fav_vm, tmp_path):

        async def fail_download(wallpaper, dest):
            return False

        fav_vm.wallhaven_service.download = fail_download
        wp = make_wallpaper(path="https://example.com/wp_1.jpg")

        ok, message = await fav_vm.set_wallpaper_async(make_favorite(wp))

        assert ok is False
        assert message == "Failed to download wallpaper"

    async def test_remote_cached_file_skips_download(self, fav_vm, tmp_path):
        dest = tmp_path / "wp_1.jpg"
        dest.write_bytes(b"cached")
        async_setter(fav_vm, True)
        wp = make_wallpaper(path="https://example.com/wp_1.jpg")

        ok, _ = await fav_vm.set_wallpaper_async(make_favorite(wp))

        assert ok is True
        fav_vm.wallhaven_service.download.assert_not_called()
        fav_vm.wallpaper_setter.set_wallpaper_async.assert_awaited_with(str(dest))

    async def test_remote_download_then_set(self, fav_vm, tmp_path):
        async_setter(fav_vm, True)
        wp = make_wallpaper(path="https://example.com/wp_1.jpg")

        async def download(wallpaper, dest):
            dest.write_bytes(b"downloaded")
            return True

        fav_vm.wallhaven_service.download = download

        ok, _ = await fav_vm.set_wallpaper_async(make_favorite(wp))

        assert ok is True
        expected_dest = str(tmp_path / "wp_1.jpg")
        fav_vm.wallpaper_setter.set_wallpaper_async.assert_awaited_with(expected_dest)

    async def test_remote_setter_failure(self, fav_vm, tmp_path):
        dest = tmp_path / "wp_1.jpg"
        dest.write_bytes(b"cached")
        async_setter(fav_vm, False)
        wp = make_wallpaper(path="https://example.com/wp_1.jpg")

        ok, message = await fav_vm.set_wallpaper_async(make_favorite(wp))

        assert ok is False
        assert message == "Failed to set wallpaper"

    async def test_setter_exception_is_reported(self, fav_vm):
        async_setter(fav_vm, exc=OSError("disk full"))

        ok, message = await fav_vm.set_wallpaper_async(make_favorite())

        assert ok is False
        assert "disk full" in message
        assert "disk full" in fav_vm.error_message


class TestGetFavorite:
    async def test_returns_matching_record(self, fav_vm):
        fav_vm.favorites_service.get_favorites.return_value = [make_favorite()]
        fav_vm.favorites_service.is_favorite.return_value = True
        await fav_vm.load_favorites()

        favorite = fav_vm.get_favorite("wp_1")

        assert favorite.wallpaper.id == "wp_1"

    async def test_unknown_id_raises(self, fav_vm):
        fav_vm.favorites_service.is_favorite.return_value = None

        with pytest.raises(ValueError, match="not in favorites"):
            fav_vm.get_favorite("missing")

    async def test_id_not_in_current_list_raises(self, fav_vm):
        fav_vm.favorites_service.is_favorite.return_value = True
        fav_vm._favorites = []

        with pytest.raises(ValueError, match="not in favorites list"):
            fav_vm.get_favorite("orphan")


class TestSelectAllAndToasts:
    async def test_select_all_selects_every_wallpaper(self, fav_vm):
        fav_vm.favorites_service.get_favorites.return_value = [
            make_favorite(),
            make_favorite(make_wallpaper("wp_2")),
        ]
        await fav_vm.load_favorites()

        fav_vm.select_all()

        assert fav_vm.selected_count == 2
        assert fav_vm.selection_mode is True

    def test_all_severity_levels_route_to_service(self, fav_vm):
        recorder = ToastRecorder()
        fav_vm.toast_service = recorder

        fav_vm._show_toast("a", "success")
        fav_vm._show_toast("b", "error")
        fav_vm._show_toast("c", "warning")
        fav_vm._show_toast("d", "info")

        assert recorder.calls == [
            ("success", "a"),
            ("error", "b"),
            ("warning", "c"),
            ("info", "d"),
        ]

    def test_broken_service_is_swallowed(self, fav_vm):
        class Broken:
            def show_info(self, message):
                raise AttributeError("gone")

        fav_vm.toast_service = Broken()
        fav_vm._show_toast("msg", "info")  # must not raise
