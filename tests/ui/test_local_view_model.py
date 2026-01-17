"""Tests for LocalViewModel."""

import pytest

from services.local_service import LocalWallpaper


@pytest.fixture
def local_view_model(mocker, tmp_path):
    """Create LocalViewModel with mocked dependencies."""
    from ui.view_models.local_view_model import LocalViewModel

    mock_service = mocker.MagicMock()
    mock_setter = mocker.MagicMock()

    # Configure async method mocks
    wallpapers = [
        LocalWallpaper(
            path=tmp_path / f"wallpaper_{i}.jpg",
            filename=f"wallpaper_{i}.jpg",
            size=1000 * i,
            modified_time=1000000.0 + i,
        )
        for i in range(3)
    ]
    mock_service.get_wallpapers_async = mocker.AsyncMock(return_value=wallpapers)
    mock_service.search_wallpapers_async = mocker.AsyncMock(return_value=wallpapers[:1])
    mock_service.delete_wallpaper_async = mocker.AsyncMock(return_value=True)

    # Mock GLib.idle_add to execute callback immediately
    mocker.patch(
        "ui.view_models.local_view_model.GLib.idle_add", side_effect=lambda func, *args: func(*args)
    )

    return LocalViewModel(local_service=mock_service, wallpaper_setter=mock_setter)


class TestLocalViewModelInit:
    """Test LocalViewModel initialization."""

    def test_init_with_services(self, local_view_model):
        """Test that ViewModel initializes with required services."""
        assert local_view_model.local_service is not None
        assert local_view_model.wallpaper_setter is not None

    def test_init_default_state(self, local_view_model):
        """Test initial state values."""
        assert local_view_model.wallpapers == []
        assert local_view_model.search_query == ""
        assert local_view_model.is_busy is False
        assert not local_view_model.error_message


class TestLocalViewModelLoadWallpapers:
    """Test load_wallpapers method."""

    @pytest.mark.asyncio
    async def test_load_wallpapers_success(self, local_view_model, mocker):
        """Test successful wallpaper loading."""
        await local_view_model.load_wallpapers()

        assert len(local_view_model.wallpapers) == 3
        assert local_view_model.is_busy is False

    @pytest.mark.asyncio
    async def test_load_wallpapers_sets_busy(self, local_view_model):
        """Test that is_busy is managed during loading."""
        await local_view_model.load_wallpapers()
        assert local_view_model.is_busy is False


class TestLocalViewModelSearchWallpapers:
    """Test search_wallpapers method."""

    @pytest.mark.asyncio
    async def test_search_empty_query_loads_all(self, local_view_model):
        """Test that empty search loads all wallpapers."""
        await local_view_model.search_wallpapers("")

        assert len(local_view_model.wallpapers) == 3

    @pytest.mark.asyncio
    async def test_search_with_query(self, local_view_model):
        """Test search with actual query."""
        await local_view_model.search_wallpapers("test")

        assert local_view_model.search_query == "test"

    @pytest.mark.asyncio
    async def test_search_updates_wallpapers(self, local_view_model):
        """Test that search results update wallpapers list."""
        await local_view_model.search_wallpapers("test")

        assert len(local_view_model.wallpapers) == 1


class TestLocalViewModelDeleteWallpaper:
    """Test delete_wallpaper method."""

    @pytest.mark.asyncio
    async def test_delete_wallpaper_success(self, local_view_model):
        """Test successful wallpaper deletion."""
        await local_view_model.load_wallpapers()
        wallpaper = local_view_model.wallpapers[0]

        success, message = await local_view_model.delete_wallpaper(wallpaper)

        assert success is True
        assert "Deleted" in message

    @pytest.mark.asyncio
    async def test_delete_removes_from_list(self, local_view_model):
        """Test that deleted wallpaper is removed from list."""
        await local_view_model.load_wallpapers()
        initial_count = len(local_view_model.wallpapers)
        wallpaper = local_view_model.wallpapers[0]

        await local_view_model.delete_wallpaper(wallpaper)

        assert len(local_view_model.wallpapers) == initial_count - 1


class TestLocalViewModelRefresh:
    """Test refresh_wallpapers method."""

    @pytest.mark.asyncio
    async def test_refresh_clears_search(self, local_view_model):
        """Test that refresh clears search query."""
        local_view_model.search_query = "test"

        await local_view_model.refresh_wallpapers()

        assert local_view_model.search_query == ""
