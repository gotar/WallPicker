"""Tests for FavoritesViewModel."""

from datetime import datetime

import pytest

from domain.favorite import Favorite
from domain.wallpaper import Resolution, Wallpaper, WallpaperPurity, WallpaperSource


@pytest.fixture
def favorites_view_model(mocker):
    """Create FavoritesViewModel with mocked dependencies."""
    from ui.view_models.favorites_view_model import FavoritesViewModel

    mock_service = mocker.MagicMock()
    mock_setter = mocker.MagicMock()
    mock_setter.set_wallpaper_async = mocker.AsyncMock(return_value=True)

    favorites = [
        Favorite(
            wallpaper=Wallpaper(
                id=f"wallpaper_{i}",
                url=f"https://example.com/wallpaper_{i}.jpg",
                path=f"/path/to/wallpaper_{i}.jpg",
                source=WallpaperSource.WALLHAVEN,
                category="anime",
                purity=WallpaperPurity.SFW,
                resolution=Resolution(1920, 1080),
            ),
            added_at=datetime.now(),
        )
        for i in range(2)
    ]

    scheduled = []

    def schedule_handler(coro):
        scheduled.append(coro)
        coro.close()

    mocker.patch(
        "ui.view_models.favorites_view_model.schedule_async",
        side_effect=schedule_handler,
    )
    mocker.patch(
        "ui.view_models.favorites_view_model.GLib.idle_add",
        side_effect=lambda func, *args: func(*args),
    )

    mock_service.get_favorites.return_value = favorites
    mock_service.search_favorites.return_value = [favorites[0].wallpaper]
    mock_service.is_favorite.return_value = False
    mock_service.add_favorite.return_value = True
    mock_service.remove_favorite.return_value = True

    view_model = FavoritesViewModel(
        favorites_service=mock_service,
        wallpaper_setter=mock_setter,
    )
    view_model._scheduled_coroutines_for_test = scheduled
    return view_model


class TestFavoritesViewModelInit:
    def test_init_default_state(self, favorites_view_model):
        assert favorites_view_model.favorites == []
        assert favorites_view_model.search_query == ""
        assert favorites_view_model.is_busy is False
        assert not favorites_view_model.error_message


class TestFavoritesViewModelLoadFavorites:
    async def test_load_favorites_success(self, favorites_view_model):
        await favorites_view_model.load_favorites()

        assert len(favorites_view_model.favorites) == 2
        assert favorites_view_model.is_busy is False


class TestFavoritesViewModelSearchFavorites:
    async def test_search_empty_query_loads_all(self, favorites_view_model):
        await favorites_view_model.search_favorites("")

        assert len(favorites_view_model.favorites) == 2

    async def test_search_with_query_updates_results(self, favorites_view_model):
        await favorites_view_model.search_favorites("wallpaper_0")

        assert favorites_view_model.search_query == "wallpaper_0"
        assert len(favorites_view_model.favorites) == 1
        assert favorites_view_model.favorites[0].wallpaper.id == "wallpaper_0"


class TestFavoritesViewModelAddFavorite:
    async def test_add_favorite_success(self, favorites_view_model):
        result = await favorites_view_model.add_favorite(
            wallpaper_id="new_id",
            full_url="https://example.com/new.jpg",
            path="/path/to/new.jpg",
            source="local",
            tags="tag1,tag2",
        )

        assert result is True
        favorites_view_model.favorites_service.add_favorite.assert_called_once()


class TestFavoritesViewModelRemoveFavorite:
    async def test_remove_favorite_by_id_success(self, favorites_view_model):
        result = await favorites_view_model.remove_favorite("wallpaper_0")

        assert result is True
        favorites_view_model.favorites_service.remove_favorite.assert_called_once_with(
            "wallpaper_0"
        )

    async def test_remove_favorite_accepts_favorite_object(self, favorites_view_model):
        await favorites_view_model.load_favorites()
        favorite = favorites_view_model.favorites[0]

        result = await favorites_view_model.remove_favorite(favorite)

        assert result is True
        favorites_view_model.favorites_service.remove_favorite.assert_called_with(
            favorite.wallpaper_id
        )


class TestFavoritesViewModelIsFavorite:
    def test_is_favorite_true(self, favorites_view_model):
        favorites_view_model.favorites_service.is_favorite.return_value = True

        assert favorites_view_model.is_favorite("test_id") is True

    def test_is_favorite_false(self, favorites_view_model):
        assert favorites_view_model.is_favorite("test_id") is False


class TestFavoritesViewModelRefresh:
    def test_refresh_clears_search_and_schedules_load(self, favorites_view_model):
        favorites_view_model.search_query = "test"

        favorites_view_model.refresh_favorites()

        assert favorites_view_model.search_query == ""
        assert len(favorites_view_model._scheduled_coroutines_for_test) >= 2


class TestRefreshFavoritesSingleLoad:
    """refresh_favorites must schedule exactly one reload (M14)."""

    def test_refresh_favorites_schedules_single_load(self, favorites_view_model):
        # Bypass the property setter - assigning search_query schedules its own
        # search; refresh must not add a second concurrent load on top.
        favorites_view_model._search_query = "anime"
        favorites_view_model.refresh_favorites()

        scheduled = favorites_view_model._scheduled_coroutines_for_test
        assert len(scheduled) == 1
        assert favorites_view_model.search_query == ""


class TestToastServiceInjection:
    """_show_toast uses the injected toast service (M16)."""

    def test_show_toast_routes_to_service(self, favorites_view_model):
        shown = []

        class FakeToastService:
            def show_success(self, message):
                shown.append(("success", message))

        favorites_view_model.toast_service = FakeToastService()
        favorites_view_model._show_toast("Added", "success")

        assert shown == [("success", "Added")]

    def test_show_toast_without_service_does_not_crash(self, favorites_view_model):
        favorites_view_model.toast_service = None
        favorites_view_model._show_toast("Ignored", "info")
