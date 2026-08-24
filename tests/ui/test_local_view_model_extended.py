"""Extended tests for LocalViewModel: hash lookup, delete, filters, favorites, upscale/tag runs."""

import asyncio
import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.local_service import LocalWallpaper


def make_wp(tmp_path, name="wp.jpg", size=1000, content=None):
    path = tmp_path / name
    if content is not None:
        path.write_bytes(content)
    return LocalWallpaper(
        path=path,
        filename=name,
        size=size,
        modified_time=0.0,
        tags=[],
    )


@pytest.fixture
def lvm(mocker, tmp_path):
    """LocalViewModel with inline GLib marshalling and captured schedule_async."""
    from ui.view_models.local_view_model import LocalViewModel

    mocker.patch(
        "gi.repository.GLib.idle_add",
        side_effect=lambda func, *args: func(*args),
    )
    pending = []
    mocker.patch(
        "ui.view_models.local_view_model.schedule_async",
        side_effect=lambda coro: pending.append(coro),
    )

    service = MagicMock()
    service.get_wallpapers_async = AsyncMock(return_value=[])
    service.search_wallpapers_async = AsyncMock(return_value=[])
    service.delete_wallpaper_async = AsyncMock(return_value=True)

    setter = MagicMock()
    setter.set_wallpaper_async = AsyncMock(return_value=True)
    setter.get_current_wallpaper.return_value = None

    model = LocalViewModel(
        local_service=service,
        wallpaper_setter=setter,
        pictures_dir=tmp_path,
    )
    model._pending_coros = pending  # type: ignore[attr-defined]
    return model


async def drain_first(lvm):
    """Run the oldest captured coroutine to completion."""
    await lvm._pending_coros.pop(0)


class TestLastWallpaperPathConfig:
    def test_last_path_loaded_from_config(self, tmp_path):
        from ui.view_models.local_view_model import LocalViewModel

        config = MagicMock()
        config.last_set_wallpaper_path = "/last/set.jpg"
        config_service = MagicMock()
        config_service.get_config.return_value = config

        model = LocalViewModel(
            local_service=MagicMock(),
            wallpaper_setter=MagicMock(),
            pictures_dir=tmp_path,
            config_service=config_service,
        )
        assert model.current_wallpaper_path == "/last/set.jpg"

    async def test_successful_set_saves_and_publishes_path(self, lvm):
        wp = make_wp(lvm.pictures_dir, "setme.jpg")
        lvm._wallpapers = [wp]

        ok, message = await lvm.set_wallpaper(wp)

        assert ok is True
        assert message == "Wallpaper set successfully"
        assert lvm.current_wallpaper_path == str(wp.path)
        assert lvm.is_busy is False

    async def test_set_failure_returns_message(self, lvm):
        wp = make_wp(lvm.pictures_dir, "nope.jpg")
        lvm.wallpaper_setter.set_wallpaper_async = AsyncMock(return_value=False)

        ok, message = await lvm.set_wallpaper(wp)

        assert ok is False
        assert message == "Failed to set wallpaper"
        assert lvm.current_wallpaper_path is None

    async def test_set_exception_is_reported(self, lvm):
        wp = make_wp(lvm.pictures_dir, "boom.jpg")

        async def explode(*args):
            raise OSError("disk full")

        lvm.wallpaper_setter.set_wallpaper_async = explode

        ok, message = await lvm.set_wallpaper(wp)

        assert ok is False
        assert message == "disk full"
        assert "disk full" in lvm.error_message

    def test_save_last_wallpaper_path_persists_via_config(self, lvm):
        config_service = MagicMock()
        config = MagicMock()
        config.last_set_wallpaper_path = None
        config_service.get_config.return_value = config
        lvm.config_service = config_service

        lvm._save_last_wallpaper_path("/new/path.jpg")

        assert config.last_set_wallpaper_path == "/new/path.jpg"
        config_service.save_config.assert_called_once_with(config)

    def test_refresh_current_wallpaper_reads_setter(self, lvm):
        lvm.wallpaper_setter.get_current_wallpaper.return_value = "/current.jpg"

        lvm.refresh_current_wallpaper()

        assert lvm.current_wallpaper_path == "/current.jpg"


class TestQueueProperties:
    def test_queue_size_properties_reflect_state(self, lvm, tmp_path):
        assert lvm.upscaling_queue_size == 0
        assert lvm.tagging_queue_size == 0

    def test_wallpapers_setter_replaces_list(self, lvm, tmp_path):
        replacement = [make_wp(tmp_path, "replaced.jpg")]
        lvm.wallpapers = replacement
        assert lvm.wallpapers is replacement


class TestFindWallpaperByHash:
    def test_sync_match_found(self, lvm, tmp_path):
        content = b"identical wallpaper bytes" * 100
        target = make_wp(tmp_path, "target.jpg", size=len(content), content=content)
        match = make_wp(tmp_path, "match.jpg", size=len(content), content=content)
        other = make_wp(tmp_path, "other.jpg", size=len(content), content=b"different")
        decoy = make_wp(tmp_path, "decoy.jpg", size=42, content=b"x")
        lvm._wallpapers = [match, other, decoy]

        result = lvm.find_wallpaper_by_hash(str(target.path))

        assert result == str(match.path)

    def test_sync_missing_target_returns_none(self, lvm):
        lvm._wallpapers = [make_wp(lvm.pictures_dir, "a.jpg", content=b"x")]

        assert lvm.find_wallpaper_by_hash("/nonexistent/file.jpg") is None

    def test_sync_no_candidate_matches_hash(self, lvm, tmp_path):
        target = make_wp(tmp_path, "t.jpg", size=10, content=b"target-bytes")
        other = make_wp(tmp_path, "o.jpg", size=10, content=b"other-bytes!!")
        lvm._wallpapers = [other]

        assert lvm.find_wallpaper_by_hash(str(target.path)) is None

    def test_size_prefilter_skips_hashing_differently_sized_files(
        self, lvm, tmp_path, mocker
    ):
        target = make_wp(tmp_path, "t.jpg", size=10, content=b"0123456789")
        small = make_wp(tmp_path, "s.jpg", size=3, content=b"abc")
        same = make_wp(tmp_path, "same.jpg", size=10, content=b"0123456789")
        lvm._wallpapers = [small, same]

        hashes = []
        original = lvm._compute_file_hash

        def counting_hash(path):
            hashes.append(path)
            return original(path)

        mocker.patch.object(lvm, "_compute_file_hash", side_effect=counting_hash)

        result = lvm.find_wallpaper_by_hash(str(target.path))

        assert result == str(same.path)
        # The size-3 file must never be hashed (prefilter), only target+candidate
        assert len(hashes) == 2

    async def test_async_match_found(self, lvm, tmp_path):
        content = b"async hash content" * 50
        target = make_wp(tmp_path, "t.jpg", size=len(content), content=content)
        match = make_wp(tmp_path, "m.jpg", size=len(content), content=content)
        lvm._wallpapers = [match]

        result = await lvm.find_wallpaper_by_hash_async(str(target.path))

        assert result == str(match.path)

    async def test_async_missing_target_returns_none(self, lvm):
        assert await lvm.find_wallpaper_by_hash_async("/gone.jpg") is None

    async def test_async_no_match_returns_none(self, lvm, tmp_path):
        target = make_wp(tmp_path, "t.jpg", size=10, content=b"aaaaaaaaaa")
        other = make_wp(tmp_path, "o.jpg", size=10, content=b"bbbbbbbbbb")
        lvm._wallpapers = [other]

        assert await lvm.find_wallpaper_by_hash_async(str(target.path)) is None

    def test_unhashable_target_returns_none(self, lvm, tmp_path, mocker):
        target = make_wp(tmp_path, "t.jpg", size=10, content=b"aaaa")
        mocker.patch.object(lvm, "_compute_file_hash", return_value=None)

        assert lvm.find_wallpaper_by_hash(str(target.path)) is None

    async def test_async_unhashable_target_returns_none(self, lvm, tmp_path, mocker):
        target = make_wp(tmp_path, "t.jpg", size=10, content=b"aaaa")
        mocker.patch.object(lvm, "_compute_file_hash", return_value=None)

        assert await lvm.find_wallpaper_by_hash_async(str(target.path)) is None

    def test_compute_file_hash_handles_missing_file(self, lvm):
        assert lvm._compute_file_hash("/does/not/exist.jpg") is None


class TestLoadAndSearchBranches:
    async def test_load_empty_directory_yields_empty_list(self, lvm):
        lvm.local_service.get_wallpapers_async = AsyncMock(return_value=[])

        await lvm.load_wallpapers()

        assert lvm.wallpapers == []
        assert lvm.is_busy is False

    async def test_load_scan_failure_reports_error_and_clears(self, lvm):
        lvm.local_service.get_wallpapers_async = AsyncMock(
            side_effect=OSError("permission denied")
        )

        await lvm.load_wallpapers()

        assert "Failed to load wallpapers" in lvm.error_message
        assert lvm.wallpapers == []

    async def test_stale_load_discarded(self, lvm):
        sentinel = [make_wp(lvm.pictures_dir, "keep.jpg")]
        lvm._wallpapers = sentinel

        def bump_generation(recursive=True):
            lvm._load_generation += 1
            return []

        lvm.local_service.get_wallpapers_async = AsyncMock(
            side_effect=bump_generation
        )

        await lvm.load_wallpapers()

        assert lvm.wallpapers is sentinel

    async def test_search_failure_sets_error_and_clears(self, lvm):
        lvm.local_service.search_wallpapers_async = AsyncMock(
            side_effect=ValueError("bad query")
        )

        await lvm.search_wallpapers("query")

        assert "Failed to search wallpapers" in lvm.error_message
        assert lvm.wallpapers == []


class TestDeleteWallpaper:
    async def test_delete_success_removes_from_list(self, lvm):
        wp_a = make_wp(lvm.pictures_dir, "a.jpg")
        wp_b = make_wp(lvm.pictures_dir, "b.jpg")
        lvm._wallpapers = [wp_a, wp_b]
        lvm.local_service.delete_wallpaper_async = AsyncMock(return_value=True)

        ok, message = await lvm.delete_wallpaper(wp_a)

        assert ok is True
        assert message == "Deleted 'a.jpg'"
        assert lvm._wallpapers == [wp_b]

    async def test_delete_cancelled_keeps_wallpaper(self, lvm):
        wp = make_wp(lvm.pictures_dir, "keep.jpg")
        lvm._wallpapers = [wp]
        lvm.local_service.delete_wallpaper_async = AsyncMock(return_value=False)

        ok, message = await lvm.delete_wallpaper(wp)

        assert ok is False
        assert message == "Failed to delete"
        assert lvm._wallpapers == [wp]

    async def test_delete_failure_reports_error(self, lvm):
        wp = make_wp(lvm.pictures_dir, "locked.jpg")

        async def deny(*args):
            raise OSError("file in use")

        lvm.local_service.delete_wallpaper_async = deny

        ok, message = await lvm.delete_wallpaper(wp)

        assert ok is False
        assert message == "file in use"
        assert "Failed to delete wallpaper" in lvm.error_message
        assert lvm.is_busy is False


class TestSortByResolutionEdges:
    def test_unparseable_and_non_string_resolutions_sort_as_zero(
        self, lvm, tmp_path
    ):
        good = LocalWallpaper(
            path=tmp_path / "good.jpg",
            filename="good.jpg",
            size=1,
            modified_time=1.0,
        )
        good.resolution = "1920x1080"
        bad_parts = LocalWallpaper(
            path=tmp_path / "bad.jpg",
            filename="bad.jpg",
            size=1,
            modified_time=2.0,
        )
        bad_parts.resolution = "axb"  # splits into two parts, int() fails
        empty = LocalWallpaper(
            path=tmp_path / "empty.jpg",
            filename="empty.jpg",
            size=1,
            modified_time=3.0,
        )
        empty.resolution = ""  # falsy -> zero score

        lvm._wallpapers = [bad_parts, empty, good]
        lvm.sort_by_resolution()

        assert [w.filename for w in lvm.wallpapers] == [
            "good.jpg",
            "bad.jpg",
            "empty.jpg",
        ]


class TestFilterPipeline:
    async def test_filter_wallpapers_applies_resolution_and_aspect(self, lvm):
        keep = self._wp("keep.jpg", "1920x1080")
        drop_small = self._wp("small.jpg", "1280x720")
        drop_ratio = self._wp("square.jpg", "2000x2000")
        all_wps = [keep, drop_small, drop_ratio]
        lvm.local_service.get_wallpapers_async = AsyncMock(return_value=all_wps)

        lvm.filter_wallpapers({"resolution": "1920x1080", "ratios": "16x9"})
        await drain_first(lvm)  # _apply_filters_async was scheduled

        assert lvm.wallpapers == [keep]

    async def test_filters_combine_with_active_search_query(self, lvm):
        wide_hd = self._wp("wide_hd.jpg", "1920x1080")
        wide_low = self._wp("wide_low.jpg", "800x450")
        lvm.search_query = "wide"
        lvm.local_service.get_wallpapers_async = AsyncMock(
            return_value=[wide_hd, wide_low]
        )
        lvm.local_service.search_wallpapers_async = AsyncMock(
            side_effect=lambda query, wps: wps
        )

        lvm.filter_wallpapers({"resolution": "1920x1080"})
        await drain_first(lvm)

        lvm.local_service.search_wallpapers_async.assert_awaited_once()
        assert lvm.wallpapers == [wide_hd]

    async def test_stale_filter_result_discarded(self, lvm):
        sentinel = [self._wp("keep.jpg", "1920x1080")]
        lvm._wallpapers = sentinel

        async def bump_generation(recursive=True):
            lvm._load_generation += 1
            return [self._wp("new.jpg", "3840x2160")]

        lvm.local_service.get_wallpapers_async = AsyncMock(
            side_effect=bump_generation
        )

        lvm.filter_wallpapers({})
        await drain_first(lvm)

        assert lvm.wallpapers is sentinel

    async def test_filter_error_reported(self, lvm):
        lvm.local_service.get_wallpapers_async = AsyncMock(
            side_effect=OSError("scan boom")
        )

        lvm.filter_wallpapers({})
        await drain_first(lvm)

        assert "Failed to filter" in lvm.error_message

    @staticmethod
    def _wp(name, resolution):
        wp = LocalWallpaper.__new__(LocalWallpaper)
        LocalWallpaper.__init__(
            wp,
            path=f"/tmp/{name}",
            filename=name,
            size=1,
            modified_time=1.0,
        )
        wp.resolution = resolution
        return wp


class TestResolutionFilterEdges:
    def test_invalid_min_resolution_string_returns_input(self, lvm):
        wps = [TestFilterPipeline._wp("a.jpg", "1920x1080")]

        assert lvm._apply_resolution_filter(wps, {"resolution": "huge"}) == wps

    def test_wallpaper_with_bad_resolution_is_skipped(self, lvm):
        bad = TestFilterPipeline._wp("bad.jpg", "not-a-number")
        good = TestFilterPipeline._wp("good.jpg", "1920x1080")

        result = lvm._apply_resolution_filter(
            [bad, good], {"resolution": "1280x720"}
        )

        assert result == [good]


class TestAspectFilterEdges:
    def test_unknown_ratio_key_returns_input(self, lvm):
        wps = [TestFilterPipeline._wp("a.jpg", "1920x1080")]

        assert lvm._apply_aspect_filter(wps, {"ratios": "5x3"}) == wps

    def test_wallpapers_without_parseable_resolution_are_skipped(self, lvm):
        unparseable = TestFilterPipeline._wp("u.jpg", "axb")
        zero_height = TestFilterPipeline._wp("z.jpg", "1920x0")
        matching = TestFilterPipeline._wp("m.jpg", "1920x1080")

        result = lvm._apply_aspect_filter(
            [unparseable, zero_height, matching], {"ratios": "16x9"}
        )

        assert result == [matching]

    def test_resolution_filter_skips_empty_and_unparseable(self, lvm):
        empty = TestFilterPipeline._wp("e.jpg", "")
        unparseable = TestFilterPipeline._wp("u.jpg", "axb")
        good = TestFilterPipeline._wp("g.jpg", "1920x1080")

        result = lvm._apply_resolution_filter(
            [empty, unparseable, good], {"resolution": "1280x720"}
        )

        assert result == [good]

    def test_aspect_filter_skips_empty_resolution(self, lvm):
        empty = TestFilterPipeline._wp("e.jpg", "")
        good = TestFilterPipeline._wp("g.jpg", "1920x1080")

        result = lvm._apply_aspect_filter(
            [empty, good], {"ratios": "16x9"}
        )

        assert result == [good]


class TestSetPicturesDir:
    async def test_updates_services_and_reloads(self, lvm, tmp_path):
        new_dir = tmp_path / "elsewhere"
        new_dir.mkdir()
        config_service = MagicMock()
        config_service.set_pictures_dir = MagicMock()
        lvm.config_service = config_service
        lvm.local_service.get_wallpapers_async = AsyncMock(return_value=[])

        await lvm.set_pictures_dir(new_dir)

        assert lvm.pictures_dir == new_dir
        assert lvm.local_service.pictures_dir == new_dir
        config_service.set_pictures_dir.assert_called_once_with(new_dir)


class TestAddToFavorites:
    async def test_busy_guard_rejects_request(self, lvm):
        lvm._busy_depth = 1
        lvm.is_busy = True

        ok, message = await lvm.add_to_favorites(make_wp(lvm.pictures_dir))

        assert ok is False
        assert message == "Operation in progress"

    async def test_missing_favorites_service_reports_error(self, lvm):
        ok, message = await lvm.add_to_favorites(make_wp(lvm.pictures_dir))

        assert ok is False
        assert message == "Favorites service not available"

    async def test_duplicate_favorite_short_circuits(self, lvm, mocker):
        favs = MagicMock()
        favs.is_favorite.return_value = True
        lvm.favorites_service = favs

        ok, message = await lvm.add_to_favorites(make_wp(lvm.pictures_dir))

        assert (ok, message) == (False, "Already in favorites")
        favs.add_favorite.assert_not_called()

    async def test_add_success_uses_local_id_and_image_size(self, lvm, mocker):
        favs = MagicMock()
        favs.is_favorite.return_value = False
        lvm.favorites_service = favs
        content = b"png-ish bytes"
        wp = make_wp(lvm.pictures_dir, "fav.jpg", size=len(content), content=content)

        # Non-image content falls back to default 1920x1080 in _get_image_size
        ok, message = await lvm.add_to_favorites(wp)

        assert ok is True
        assert "Added 'fav.jpg' to favorites" == message
        domain_wallpaper = favs.add_favorite.call_args[0][0]
        expected_id = (
            "local_" + hashlib.sha256(str(wp.path).encode()).hexdigest()[:16]
        )
        assert domain_wallpaper.id == expected_id
        assert (domain_wallpaper.resolution.width, domain_wallpaper.resolution.height) == (
            1920,
            1080,
        )

    async def test_add_failure_reports_error(self, lvm):
        favs = MagicMock()
        favs.is_favorite.return_value = False
        favs.add_favorite.side_effect = OSError("disk full")
        lvm.favorites_service = favs

        ok, message = await lvm.add_to_favorites(make_wp(lvm.pictures_dir))

        assert ok is False
        assert message == "disk full"
        assert "Failed to add to favorites" in lvm.error_message

    async def test_image_size_uses_pil_when_readable(self, lvm, mocker):
        from PIL import Image

        img_path = lvm.pictures_dir / "real.png"
        Image.new("RGB", (640, 480)).save(img_path)

        assert lvm._get_image_size(img_path) == (640, 480)


class TestUpscaleQueueOverflow:
    async def test_items_wait_when_slots_full_then_start_on_completion(
        self, lvm, tmp_path
    ):
        names = ("a", "b", "c", "d", "e")
        wps = [make_wp(tmp_path, f"{n}.jpg", content=b"x") for n in names]

        messages = [lvm.queue_upscale(wp)[1] for wp in wps]

        # First two fill the slots; the rest wait in the queue
        assert messages[0] == "Upscaling started..."
        assert messages[1] == "Upscaling started..."
        assert messages[3].startswith("Added to queue")
        assert messages[4] == "Added to queue (1 waiting)"
        assert lvm.upscaling_active_count == 2
        assert len(lvm._upscale_queue) == 3

        # Each completion frees a slot and starts the next queued item until
        # the queue is fully drained.
        while lvm._pending_coros:
            await drain_first(lvm)

        assert lvm.upscaling_active_count == 0
        assert len(lvm._upscale_queue) == 0
        assert lvm._failed_count == 5


class TestUpscaleRunPaths:
    @pytest.fixture
    def waifu_available(self, mocker):
        mocker.patch(
            "ui.view_models.local_view_model.shutil.which",
            return_value="/usr/bin/waifu2x-ncnn-vulkan",
        )

    def mock_process(self, mocker, returncode=0, stderr=b"", fail_communicate=None):
        proc = MagicMock()
        proc.returncode = returncode
        if fail_communicate is not None:

            async def boom():
                raise fail_communicate

            proc.communicate = boom
        else:
            proc.communicate = AsyncMock(return_value=(b"", stderr))
        mocker.patch(
            "asyncio.create_subprocess_exec", AsyncMock(return_value=proc)
        )
        return proc

    async def test_missing_binary_fails_fast(self, lvm, tmp_path, mocker):
        mocker.patch(
            "ui.view_models.local_view_model.shutil.which", return_value=None
        )
        wp = make_wp(tmp_path, "w.jpg", content=b"x")

        success, message = await lvm._run_upscale_async(wp)

        assert success is False
        assert "not found in PATH" in message

    async def test_nonzero_exit_code_reports_stderr(
        self, lvm, tmp_path, mocker, waifu_available
    ):
        self.mock_process(mocker, returncode=1, stderr=b"wgpu device lost")
        wp = make_wp(tmp_path, "w.jpg", content=b"x")

        success, message = await lvm._run_upscale_async(wp)

        assert success is False
        assert message == "Upscaling failed: wgpu device lost"

    async def test_zero_exit_but_no_output_file(
        self, lvm, tmp_path, mocker, waifu_available
    ):
        self.mock_process(mocker, returncode=0)
        wp = make_wp(tmp_path, "w.jpg", content=b"x")

        success, message = await lvm._run_upscale_async(wp)

        assert success is False
        assert message == "Upscaling produced no output"

    async def test_invalid_upscaled_image_is_deleted(
        self, lvm, tmp_path, mocker, waifu_available
    ):
        self.mock_process(mocker, returncode=0)
        temp = tmp_path / "w_upscaled.jpg"
        temp.write_bytes(b"garbage")
        mocker.patch("PIL.Image.open", side_effect=ValueError("cannot identify"))
        wp = make_wp(tmp_path, "w.jpg", content=b"x")

        success, message = await lvm._run_upscale_async(wp)

        assert success is False
        assert "Upscaled image is invalid" in message
        assert not temp.exists()

    async def test_successful_upscale_replaces_original(
        self, lvm, tmp_path, mocker, waifu_available
    ):
        original = tmp_path / "w.jpg"
        original.write_bytes(b"o" * 1024)
        temp = tmp_path / "w_upscaled.jpg"
        temp.write_bytes(b"u" * 4096)
        self.mock_process(mocker, returncode=0)

        fake_img = MagicMock()
        fake_img.size = (4000, 2000)
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=fake_img)
        ctx.__exit__ = MagicMock(return_value=False)
        mocker.patch("PIL.Image.open", MagicMock(return_value=ctx))

        wp = make_wp(tmp_path, "w.jpg", size=1024, content=b"o" * 1024)

        success, message = await lvm._run_upscale_async(wp)

        assert success is True
        assert message.startswith("Upscaled 2x")
        # Original replaced by upscaled content; backup and temp are gone
        assert original.read_bytes() == b"u" * 4096
        assert not temp.exists()
        assert not (tmp_path / "w_backup.jpg").exists()
        assert lvm._completed_count == 1

    async def test_too_small_upscaled_image_is_rejected(
        self, lvm, tmp_path, mocker, waifu_available
    ):
        self.mock_process(mocker, returncode=0)
        temp = tmp_path / "w_upscaled.jpg"
        temp.write_bytes(b"tiny")

        fake_img = MagicMock()
        fake_img.size = (50, 50)
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=fake_img)
        ctx.__exit__ = MagicMock(return_value=False)
        mocker.patch("PIL.Image.open", MagicMock(return_value=ctx))
        wp = make_wp(tmp_path, "w.jpg", content=b"x")

        success, message = await lvm._run_upscale_async(wp)

        assert success is False
        assert "Invalid dimensions" in message
        assert not temp.exists()

    async def test_cancellation_cleans_temp_and_reraises(
        self, lvm, tmp_path, mocker, waifu_available
    ):
        self.mock_process(
            mocker, fail_communicate=asyncio.CancelledError()
        )
        temp = tmp_path / "w_upscaled.jpg"
        temp.write_bytes(b"partial")
        wp = make_wp(tmp_path, "w.jpg", content=b"x")

        with pytest.raises(asyncio.CancelledError):
            await lvm._run_upscale_async(wp)

        assert not temp.exists()
        assert lvm._failed_count >= 1

    async def test_generic_subprocess_error_is_reraised(
        self, lvm, tmp_path, mocker, waifu_available
    ):
        temp = tmp_path / "w_upscaled.jpg"
        temp.write_bytes(b"stale partial output")
        mocker.patch(
            "asyncio.create_subprocess_exec",
            AsyncMock(side_effect=RuntimeError("spawn failed")),
        )
        wp = make_wp(tmp_path, "w.jpg", content=b"x")

        with pytest.raises(RuntimeError, match="spawn failed"):
            await lvm._run_upscale_async(wp)

        # Stale partial output must be cleaned up by the handler
        assert not temp.exists()

    async def test_restore_failure_is_logged(
        self, lvm, tmp_path, mocker, waifu_available, caplog
    ):
        """If even the backup restore fails, the error must be logged (C2)."""
        original = tmp_path / "w.jpg"
        original.write_bytes(b"original")
        temp = tmp_path / "w_upscaled.jpg"
        temp.write_bytes(b"upscaled")
        self.mock_process(mocker, returncode=0)

        fake_img = MagicMock()
        fake_img.size = (4000, 2000)
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=fake_img)
        ctx.__exit__ = MagicMock(return_value=False)
        mocker.patch("PIL.Image.open", MagicMock(return_value=ctx))

        real_rename = type(original).rename
        backup_path = tmp_path / "w_backup.jpg"

        def rename_side_effect(path_self, target):
            if path_self == original:
                return real_rename(path_self, backup_path)  # backup step works
            raise OSError("everything is broken")  # replace + restore both fail

        mocker.patch.object(
            type(original),
            "rename",
            autospec=True,
            side_effect=rename_side_effect,
        )
        wp = make_wp(tmp_path, "w.jpg", size=8, content=b"original")

        with caplog.at_level("ERROR", logger="ui.view_models.local_view_model"):
            success, message = await lvm._run_upscale_async(wp)

        assert success is False
        assert "Failed to replace file" in message
        assert any(
            "Failed to restore original" in record.message
            for record in caplog.records
        )
        # The unusable temp output was removed
        assert not temp.exists()


class TestTagRunPaths:
    async def test_unavailable_generator_reports_install_hint(self, lvm, tmp_path, mocker):
        gen_cls = mocker.patch("services.tag_generation.TagGenerationService")
        gen_cls.return_value.is_available.return_value = False
        wp = make_wp(tmp_path, "w.jpg", content=b"x")

        success, message = await lvm._run_tag_async(wp)

        assert success is False
        assert "No tag generator available" in message

    async def test_generated_tags_are_saved_on_wallpaper(self, lvm, tmp_path, mocker):
        gen_cls = mocker.patch("services.tag_generation.TagGenerationService")
        gen_cls.return_value.is_available.return_value = True
        gen_cls.return_value.generate_tags_async = AsyncMock(
            return_value=(["dark", "minimal"], [0.9, 0.8])
        )
        storage_cls = mocker.patch("services.tag_storage.TagStorageService")
        wp = make_wp(tmp_path, "w.jpg", content=b"x")

        success, message = await lvm._run_tag_async(wp)

        assert success is True
        assert message == "Generated 2 tags"
        storage_cls.return_value.save_tags.assert_called_once_with(
            wp.path, ["dark", "minimal"], [0.9, 0.8]
        )
        assert wp.tags == ["dark", "minimal"]

    async def test_empty_tag_result_counts_as_failure(self, lvm, tmp_path, mocker):
        gen_cls = mocker.patch("services.tag_generation.TagGenerationService")
        gen_cls.return_value.is_available.return_value = True
        gen_cls.return_value.generate_tags_async = AsyncMock(return_value=([], []))
        wp = make_wp(tmp_path, "w.jpg", content=b"x")

        success, message = await lvm._run_tag_async(wp)

        assert success is False
        assert message == "No tags generated"

    async def test_generator_exception_is_caught(self, lvm, tmp_path, mocker):
        gen_cls = mocker.patch("services.tag_generation.TagGenerationService")
        gen_cls.return_value.is_available.return_value = True
        gen_cls.return_value.generate_tags_async = AsyncMock(
            side_effect=RuntimeError("model exploded")
        )
        wp = make_wp(tmp_path, "w.jpg", content=b"x")

        success, message = await lvm._run_tag_async(wp)

        assert success is False
        assert message == "model exploded"

    async def test_tag_schedule_failure_releases_slot(self, lvm, tmp_path, mocker):
        def fail_schedule(coro):
            coro.close()
            raise RuntimeError("loop gone")

        mocker.patch(
            "ui.view_models.local_view_model.schedule_async",
            side_effect=fail_schedule,
        )
        queued, _ = lvm.queue_generate_tags(make_wp(tmp_path, "t.jpg", content=b"x"))

        assert queued is True
        assert lvm.tagging_active_count == 0


class TestGenerateTagsForAll:
    async def test_no_untagged_images_is_noop(self, lvm, mocker):
        storage_cls = mocker.patch("services.tag_storage.TagStorageService")
        storage_cls.return_value.get_untagged_images.return_value = []
        wp = make_wp(lvm.pictures_dir, "tagged.jpg", content=b"x")
        lvm._wallpapers = [wp]

        await lvm.generate_tags_for_all_async()

        assert lvm._pending_coros == []

    async def test_untagged_images_are_queued(self, lvm, mocker):
        storage_cls = mocker.patch("services.tag_storage.TagStorageService")
        wp_a = make_wp(lvm.pictures_dir, "a.jpg", content=b"a")
        wp_b = make_wp(lvm.pictures_dir, "b.jpg", content=b"b")
        lvm._wallpapers = [wp_a, wp_b]
        storage_cls.return_value.get_untagged_images.return_value = [
            wp_b.path,
            "/somewhere/unknown.jpg",
        ]

        await lvm.generate_tags_for_all_async()

        assert len(lvm._pending_coros) == 1
        for coro in lvm._pending_coros:
            coro.close()
