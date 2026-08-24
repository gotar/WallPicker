"""Tests for LocalViewModel."""

import pytest

from services.local_service import LocalWallpaper


@pytest.fixture
def local_view_model(mocker, tmp_path):
    """Create LocalViewModel with mocked dependencies."""
    from ui.view_models.local_view_model import LocalViewModel

    mock_service = mocker.MagicMock()
    mock_setter = mocker.MagicMock()

    wallpapers = [
        LocalWallpaper(
            path=tmp_path / f"wallpaper_{i}.jpg",
            filename=f"wallpaper_{i}.jpg",
            size=1000 * i,
            modified_time=1000000.0 + i,
            tags=[],
        )
        for i in range(3)
    ]
    mock_service.get_wallpapers_async = mocker.AsyncMock(return_value=wallpapers)
    mock_service.search_wallpapers_async = mocker.AsyncMock(return_value=wallpapers[:1])
    mock_service.delete_wallpaper_async = mocker.AsyncMock(return_value=True)

    mocker.patch(
        "ui.view_models.local_view_model.GLib.idle_add",
        side_effect=lambda func, *args: func(*args),
    )

    return LocalViewModel(
        local_service=mock_service,
        wallpaper_setter=mock_setter,
        toast_service=None,
    )


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


class TestLocalViewModelSorting:
    """Test sorting methods."""

    def test_sort_by_name(self, local_view_model, tmp_path):
        """Test sorting wallpapers by name."""
        local_view_model._wallpapers = [
            LocalWallpaper(
                path=tmp_path / "zebra.jpg",
                filename="zebra.jpg",
                size=100,
                modified_time=1.0,
            ),
            LocalWallpaper(
                path=tmp_path / "alpha.jpg",
                filename="alpha.jpg",
                size=100,
                modified_time=2.0,
            ),
            LocalWallpaper(
                path=tmp_path / "beta.jpg",
                filename="beta.jpg",
                size=100,
                modified_time=3.0,
            ),
        ]

        local_view_model.sort_by_name()

        filenames = [w.filename for w in local_view_model.wallpapers]
        assert filenames == ["alpha.jpg", "beta.jpg", "zebra.jpg"]

    def test_sort_by_date(self, local_view_model, tmp_path):
        """Test sorting wallpapers by date (newest first)."""
        local_view_model._wallpapers = [
            LocalWallpaper(
                path=tmp_path / "old.jpg",
                filename="old.jpg",
                size=100,
                modified_time=1000.0,
            ),
            LocalWallpaper(
                path=tmp_path / "new.jpg",
                filename="new.jpg",
                size=100,
                modified_time=3000.0,
            ),
            LocalWallpaper(
                path=tmp_path / "mid.jpg",
                filename="mid.jpg",
                size=100,
                modified_time=2000.0,
            ),
        ]

        local_view_model.sort_by_date()

        filenames = [w.filename for w in local_view_model.wallpapers]
        assert filenames == ["new.jpg", "mid.jpg", "old.jpg"]

    def test_sort_by_resolution(self, local_view_model, tmp_path):
        """Test sorting wallpapers by resolution (largest first)."""
        wp1 = LocalWallpaper(
            path=tmp_path / "small.jpg",
            filename="small.jpg",
            size=100,
            modified_time=1.0,
        )
        wp1._resolution = "1920x1080"
        wp2 = LocalWallpaper(
            path=tmp_path / "large.jpg",
            filename="large.jpg",
            size=100,
            modified_time=2.0,
        )
        wp2._resolution = "3840x2160"
        wp3 = LocalWallpaper(
            path=tmp_path / "medium.jpg",
            filename="medium.jpg",
            size=100,
            modified_time=3.0,
        )
        wp3._resolution = "2560x1440"

        local_view_model._wallpapers = [wp1, wp2, wp3]

        local_view_model.sort_by_resolution()

        filenames = [w.filename for w in local_view_model.wallpapers]
        assert filenames == ["large.jpg", "medium.jpg", "small.jpg"]


class TestLocalViewModelFiltering:
    """Test filter methods."""

    def test_apply_resolution_filter_all(self, local_view_model, tmp_path):
        """Test resolution filter with 'All' returns everything."""
        wp1 = LocalWallpaper(
            path=tmp_path / "small.jpg",
            filename="small.jpg",
            size=100,
            modified_time=1.0,
        )
        wp1._resolution = "1280x720"
        wp2 = LocalWallpaper(
            path=tmp_path / "large.jpg",
            filename="large.jpg",
            size=100,
            modified_time=2.0,
        )
        wp2._resolution = "3840x2160"

        result = local_view_model._apply_resolution_filter([wp1, wp2], {})

        assert len(result) == 2

    def test_apply_resolution_filter_minimum(self, local_view_model, tmp_path):
        """Test resolution filter with minimum resolution."""
        wp1 = LocalWallpaper(
            path=tmp_path / "small.jpg",
            filename="small.jpg",
            size=100,
            modified_time=1.0,
        )
        wp1._resolution = "1280x720"
        wp2 = LocalWallpaper(
            path=tmp_path / "hd.jpg", filename="hd.jpg", size=100, modified_time=2.0
        )
        wp2._resolution = "1920x1080"
        wp3 = LocalWallpaper(
            path=tmp_path / "4k.jpg", filename="4k.jpg", size=100, modified_time=3.0
        )
        wp3._resolution = "3840x2160"

        result = local_view_model._apply_resolution_filter(
            [wp1, wp2, wp3], {"resolution": "1920x1080"}
        )

        filenames = [w.filename for w in result]
        assert "small.jpg" not in filenames
        assert "hd.jpg" in filenames
        assert "4k.jpg" in filenames

    def test_apply_aspect_filter_16x9(self, local_view_model, tmp_path):
        """Test aspect ratio filter for 16:9."""
        wp1 = LocalWallpaper(
            path=tmp_path / "wide.jpg", filename="wide.jpg", size=100, modified_time=1.0
        )
        wp1._resolution = "1920x1080"
        wp2 = LocalWallpaper(
            path=tmp_path / "square.jpg",
            filename="square.jpg",
            size=100,
            modified_time=2.0,
        )
        wp2._resolution = "1000x1000"
        wp3 = LocalWallpaper(
            path=tmp_path / "ultrawide.jpg",
            filename="ultrawide.jpg",
            size=100,
            modified_time=3.0,
        )
        wp3._resolution = "2560x1080"

        result = local_view_model._apply_aspect_filter(
            [wp1, wp2, wp3], {"ratios": "16x9"}
        )

        filenames = [w.filename for w in result]
        assert "wide.jpg" in filenames
        assert "square.jpg" not in filenames
        assert "ultrawide.jpg" not in filenames

    def test_apply_aspect_filter_square(self, local_view_model, tmp_path):
        """Test aspect ratio filter for 1:1 (square)."""
        wp1 = LocalWallpaper(
            path=tmp_path / "wide.jpg", filename="wide.jpg", size=100, modified_time=1.0
        )
        wp1._resolution = "1920x1080"
        wp2 = LocalWallpaper(
            path=tmp_path / "square.jpg",
            filename="square.jpg",
            size=100,
            modified_time=2.0,
        )
        wp2._resolution = "1000x1000"

        result = local_view_model._apply_aspect_filter([wp1, wp2], {"ratios": "1x1"})

        filenames = [w.filename for w in result]
        assert "square.jpg" in filenames
        assert "wide.jpg" not in filenames

    def test_apply_aspect_filter_all(self, local_view_model, tmp_path):
        """Test aspect ratio filter with 'All' returns everything."""
        wp1 = LocalWallpaper(
            path=tmp_path / "wide.jpg", filename="wide.jpg", size=100, modified_time=1.0
        )
        wp1._resolution = "1920x1080"
        wp2 = LocalWallpaper(
            path=tmp_path / "square.jpg",
            filename="square.jpg",
            size=100,
            modified_time=2.0,
        )
        wp2._resolution = "1000x1000"

        result = local_view_model._apply_aspect_filter([wp1, wp2], {})

        assert len(result) == 2




class TestUpscaleReplaceFailure:
    """Test upscale replace-failure restores the original from backup (C2)."""

    @pytest.mark.asyncio
    async def test_replace_failure_restores_original(
        self, local_view_model, tmp_path, mocker
    ):
        """Test that a failed final rename does not lose the original file."""
        original = tmp_path / "wall.jpg"
        original.write_bytes(b"original bytes")
        wallpaper = LocalWallpaper(
            path=original,
            filename="wall.jpg",
            size=len(b"original bytes"),
            modified_time=1000000.0,
            tags=[],
        )

        # waifu2x available
        mocker.patch(
            "ui.view_models.local_view_model.shutil.which",
            return_value="/usr/bin/waifu2x-ncnn-vulkan",
        )

        # Fake successful subprocess
        mock_process = mocker.MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = mocker.AsyncMock(return_value=(b"", b""))
        mocker.patch(
            "asyncio.create_subprocess_exec", mocker.AsyncMock(return_value=mock_process)
        )

        # Valid upscaled image passes PIL verification (temp file must exist)
        temp_path = tmp_path / "wall_upscaled.jpg"
        temp_path.write_bytes(b"upscaled bytes")
        mock_image = mocker.MagicMock()
        mock_image.__enter__ = mocker.MagicMock(return_value=mocker.MagicMock(size=(200, 200)))
        mock_image.__exit__ = mocker.MagicMock(return_value=False)
        mocker.patch("PIL.Image.open", mocker.MagicMock(return_value=mock_image))

        # Rename of the original to its backup succeeds; rename of the
        # upscaled temp file onto the original location fails with OSError.
        # The restore path then renames backup -> original, which must succeed.
        real_rename = type(original).rename
        backup_path = tmp_path / "wall_backup.jpg"

        def rename_side_effect(path_self, target):
            if path_self == backup_path:
                return real_rename(path_self, target)  # restore must work
            if path_self == original:
                return real_rename(path_self, backup_path)  # backup step
            raise OSError("simulated rename failure")  # upscaled -> original

        mocker.patch.object(
            type(original), "rename", autospec=True, side_effect=rename_side_effect
        )

        success, message = await local_view_model._run_upscale_async(wallpaper)

        assert success is False
        # The original must be restored from the backup
        assert original.exists()
        assert original.read_bytes() == b"original bytes"


class TestUpscaleTagQueues:
    """Test queue counters for upscaling/tagging (H8/H9/L12)."""

    def test_upscale_and_tag_active_counts_are_independent(
        self, local_view_model, mocker, tmp_path
    ):
        """Upscale and tag queues must not share an active counter (H8)."""

        def fake_schedule(coro):
            coro.close()
            return None

        mocker.patch(
            "ui.view_models.local_view_model.schedule_async",
            side_effect=fake_schedule,
        )

        wp_a = LocalWallpaper(
            path=tmp_path / "a.jpg",
            filename="a.jpg",
            size=1,
            modified_time=1.0,
            tags=[],
        )
        wp_b = LocalWallpaper(
            path=tmp_path / "b.jpg",
            filename="b.jpg",
            size=1,
            modified_time=2.0,
            tags=[],
        )

        local_view_model.queue_upscale(wp_a)
        local_view_model.queue_upscale(wp_b)
        assert local_view_model.upscaling_active_count == 2
        assert local_view_model.upscaling_total_count == 2
        assert local_view_model.tagging_active_count == 0

        local_view_model.queue_generate_tags(wp_b)
        assert local_view_model.tagging_active_count == 1
        # Upscale counter unaffected by tagging activity
        assert local_view_model.upscaling_active_count == 2

        local_view_model._finish_upscale(wp_a, True, "ok")
        assert local_view_model.upscaling_active_count == 1

        local_view_model._finish_tag(wp_b, True, "ok")
        assert local_view_model.tagging_active_count == 0

    def test_tag_queue_limit_is_independent(self, local_view_model, mocker, tmp_path):
        """Tagging gets its own MAX_CONCURRENT_TAGGING budget."""

        def fake_schedule(coro):
            coro.close()
            return None

        mocker.patch(
            "ui.view_models.local_view_model.schedule_async",
            side_effect=fake_schedule,
        )

        wps = [
            LocalWallpaper(
                path=tmp_path / f"t{i}.jpg",
                filename=f"t{i}.jpg",
                size=1,
                modified_time=float(i),
                tags=[],
            )
            for i in range(3)
        ]
        for wp in wps:
            local_view_model.queue_generate_tags(wp)

        assert local_view_model.tagging_active_count == (
            local_view_model.MAX_CONCURRENT_TAGGING
        )
        assert len(local_view_model._tag_queue) == 1

    def test_schedule_failure_does_not_leak_active_count(
        self, local_view_model, mocker, tmp_path
    ):
        """If scheduling fails, the active count must be restored (L12)."""

        def failing_schedule(coro):
            coro.close()
            raise RuntimeError("event loop gone")

        mocker.patch(
            "ui.view_models.local_view_model.schedule_async",
            side_effect=failing_schedule,
        )

        wp = LocalWallpaper(
            path=tmp_path / "x.jpg",
            filename="x.jpg",
            size=1,
            modified_time=1.0,
            tags=[],
        )

        queued, message = local_view_model.queue_upscale(wp)

        assert queued is True
        assert local_view_model.upscaling_active_count == 0
        assert local_view_model._failed_count == 1

    def test_finish_upscale_emits_signal_on_main_thread(
        self, local_view_model, mocker, tmp_path
    ):
        """upscaling-complete must be emitted via idle_add (main thread)."""
        idle_add = mocker.patch(
            "ui.view_models.local_view_model.GLib.idle_add",
            side_effect=lambda func, *args: func(*args),
        )

        def fake_schedule(coro):
            coro.close()
            return None

        mocker.patch(
            "ui.view_models.local_view_model.schedule_async",
            side_effect=fake_schedule,
        )

        received = []
        local_view_model.connect(
            "upscaling-complete",
            lambda _o, success, message, path: received.append((success, path)),
        )

        wp = LocalWallpaper(
            path=tmp_path / "y.jpg",
            filename="y.jpg",
            size=1,
            modified_time=1.0,
            tags=[],
        )
        local_view_model.queue_upscale(wp)
        idle_add.reset_mock()

        local_view_model._finish_upscale(wp, True, "done")

        assert received == [(True, str(tmp_path / "y.jpg"))]
        assert idle_add.called


class TestStaleResultDiscard:
    """Test generation-counter staleness guards (M14)."""

    @pytest.mark.asyncio
    async def test_search_discards_stale_result(self, local_view_model, tmp_path, mocker):
        """A search finishing after a newer request started is discarded."""
        sentinel = [
            LocalWallpaper(
                path=tmp_path / "keep.jpg",
                filename="keep.jpg",
                size=1,
                modified_time=1.0,
                tags=[],
            )
        ]
        local_view_model._wallpapers = sentinel

        async def slow_search(query, wallpapers):
            # Simulate a newer request starting while this one is in flight
            local_view_model._load_generation += 1
            return []

        local_view_model.local_service.search_wallpapers_async = mocker.AsyncMock(
            side_effect=slow_search
        )

        await local_view_model.search_wallpapers("stale")

        # Stale completion must not overwrite current state
        assert local_view_model.wallpapers is sentinel
