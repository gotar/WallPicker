"""Tests for selection functionality in ViewModels."""



class TestSelection:
    """Test multi-selection functionality."""

    def test_toggle_selection_adds_to_selected_list(self, local_view_model, tmp_path):
        """Test toggling selection adds wallpaper to selected list."""
        from services.local_service import LocalWallpaper

        wallpaper = LocalWallpaper(
            path=tmp_path / "test1.jpg",
            filename="test1.jpg",
            size=1000,
            modified_time=1000000.0,
        )

        local_view_model.toggle_selection(wallpaper)

        selected = local_view_model.get_selected_wallpapers()
        assert wallpaper in selected
        assert local_view_model.selected_count == 1

    def test_toggle_selection_removes_from_selected_list(
        self, local_view_model, tmp_path
    ):
        """Test toggling selection removes wallpaper from selected list."""
        from services.local_service import LocalWallpaper

        wallpaper = LocalWallpaper(
            path=tmp_path / "test1.jpg",
            filename="test1.jpg",
            size=1000,
            modified_time=1000000.0,
        )

        local_view_model.toggle_selection(wallpaper)
        local_view_model.toggle_selection(wallpaper)

        selected = local_view_model.get_selected_wallpapers()
        assert wallpaper not in selected
        assert local_view_model.selected_count == 0

    async def test_select_all_selects_all_wallpapers(
        self, local_view_model, mock_local_service
    ):
        """Test select all selects all wallpapers."""
        await local_view_model.load_wallpapers()

        local_view_model.select_all()

        selected = local_view_model.get_selected_wallpapers()
        assert len(selected) == len(local_view_model.wallpapers)
        assert local_view_model.selected_count == len(local_view_model.wallpapers)

    async def test_deselect_all_clears_selection(
        self, local_view_model, mock_local_service
    ):
        """Test deselect all clears selection."""
        await local_view_model.load_wallpapers()
        local_view_model.select_all()

        local_view_model.deselect_all()

        selected = local_view_model.get_selected_wallpapers()
        assert len(selected) == 0
        assert local_view_model.selected_count == 0

    async def test_clear_selection_exits_selection_mode(
        self, local_view_model, mock_local_service
    ):
        """Test clear selection deselects and exits selection mode."""
        await local_view_model.load_wallpapers()
        local_view_model.select_all()

        local_view_model.clear_selection()

        assert local_view_model.selected_count == 0
        assert local_view_model.selection_mode is False

    def test_selected_count_updates_correctly(self, local_view_model, tmp_path):
        """Test selected count updates correctly."""
        from services.local_service import LocalWallpaper

        wallpapers = [
            LocalWallpaper(
                path=tmp_path / f"test{i}.jpg",
                filename=f"test{i}.jpg",
                size=1000 * i,
                modified_time=1000000.0 + i,
            )
            for i in range(3)
        ]

        for wp in wallpapers:
            local_view_model.toggle_selection(wp)

        assert local_view_model.selected_count == 3

    def test_selected_wallpapers_property_returns_list(
        self, local_view_model, tmp_path
    ):
        """Test selected_wallpapers property returns list of selected wallpapers."""
        from services.local_service import LocalWallpaper

        wallpaper1 = LocalWallpaper(
            path=tmp_path / "test1.jpg",
            filename="test1.jpg",
            size=1000,
            modified_time=1000000.0,
        )
        wallpaper2 = LocalWallpaper(
            path=tmp_path / "test2.jpg",
            filename="test2.jpg",
            size=2000,
            modified_time=1000001.0,
        )

        local_view_model.toggle_selection(wallpaper1)
        local_view_model.toggle_selection(wallpaper2)

        selected = local_view_model.selected_wallpapers
        assert wallpaper1 in selected
        assert wallpaper2 in selected
        assert len(selected) == 2

    def test_selection_mode_activates_on_selection(self, local_view_model, tmp_path):
        """Test selection mode activates when wallpaper is selected."""
        from services.local_service import LocalWallpaper

        wallpaper = LocalWallpaper(
            path=tmp_path / "test1.jpg",
            filename="test1.jpg",
            size=1000,
            modified_time=1000000.0,
        )

        assert local_view_model.selection_mode is False

        local_view_model.toggle_selection(wallpaper)

        assert local_view_model.selection_mode is True


class TestWallhavenViewModelSelection:
    """Test selection functionality in WallhavenViewModel."""

    async def test_wallhaven_selection_with_wallpapers(
        self, wallhaven_view_model, mock_wallhaven_service
    ):
        """Test selection works with Wallhaven wallpapers."""
        await wallhaven_view_model.search_wallpapers(query="test")

        wallpapers = wallhaven_view_model.wallpapers
        if wallpapers:
            wallhaven_view_model.toggle_selection(wallpapers[0])

            selected = wallhaven_view_model.get_selected_wallpapers()
            assert len(selected) == 1
            assert wallpapers[0] in selected


class TestSelectionPruning:
    """Selection must never reference wallpapers that are no longer visible (L10)."""

    async def test_delete_wallpaper_prunes_selection(
        self, local_view_model, mock_local_service
    ):
        """Deleting a selected wallpaper shrinks the selection."""
        await local_view_model.load_wallpapers()
        remaining = local_view_model.wallpapers[1]
        deleted = local_view_model.wallpapers[0]
        local_view_model.toggle_selection(deleted)
        local_view_model.toggle_selection(remaining)
        assert local_view_model.selected_count == 2

        success, _ = await local_view_model.delete_wallpaper(deleted)
        assert success is True

        assert local_view_model.selected_count == 1
        assert local_view_model.get_selected_wallpapers() == [remaining]
        assert deleted not in local_view_model.get_selected_wallpapers()

    async def test_reload_drops_stale_selection_entries(
        self, local_view_model, mock_local_service, tmp_path, mocker
    ):
        """Reloading with a different list drops selection entries that vanished."""
        from services.local_service import LocalWallpaper

        await local_view_model.load_wallpapers()
        local_view_model.select_all()
        old_count = len(local_view_model.wallpapers)
        assert local_view_model.selected_count == old_count

        fresh = [
            LocalWallpaper(
                path=tmp_path / "fresh.jpg",
                filename="fresh.jpg",
                size=42,
                modified_time=1.0,
                tags=[],
            )
        ]
        mock_local_service.get_wallpapers_async = mocker.AsyncMock(return_value=fresh)

        await local_view_model.load_wallpapers()

        # Old wallpaper objects are gone from view; stale entries must drop.
        assert local_view_model.get_selected_wallpapers() == []
        assert local_view_model.selected_count == 0

    def test_select_all_still_works_after_reload(
        self, local_view_model, mock_local_service
    ):
        """select_all keeps operating on the current wallpaper list (L10)."""
        local_view_model._set_wallpapers(local_view_model.local_service
                                         .get_wallpapers_async.return_value)

        local_view_model.select_all()

        assert (
            local_view_model.selected_count == len(local_view_model.wallpapers) == 3
        )


class TestFavoritesViewModelSelection:
    """Test selection functionality in FavoritesViewModel."""

    async def test_favorites_selection_with_favorites(self, favorites_view_model):
        """Test selection works with favorites."""
        await favorites_view_model.load_favorites()

        favorites = favorites_view_model.favorites
        if favorites:
            favorites_view_model.toggle_selection(favorites[0].wallpaper)

            selected = favorites_view_model.get_selected_wallpapers()
            assert len(selected) == 1
            assert favorites[0].wallpaper in selected
