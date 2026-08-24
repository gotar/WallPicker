"""Concurrency tests for the upscale/tag queues in LocalViewModel (H8/H9)."""

import threading

import pytest
from pytest_mock import MockerFixture

from services.local_service import LocalWallpaper


@pytest.fixture
def vm(mocker: MockerFixture):
    """LocalViewModel with GLib marshalling executed inline and schedule_async captured."""
    from ui.view_models.local_view_model import LocalViewModel

    mocker.patch(
        "ui.view_models.local_view_model.GLib.idle_add",
        side_effect=lambda func, *args: func(*args),
    )

    # Capture scheduled coroutines instead of running them on a loop.
    pending: list = []
    mocker.patch(
        "ui.view_models.local_view_model.schedule_async",
        side_effect=lambda coro: pending.append(coro),
    )

    model = LocalViewModel(
        local_service=mocker.MagicMock(),
        wallpaper_setter=mocker.MagicMock(),
    )
    model._pending_coros = pending  # type: ignore[attr-defined]
    return model


def make_wp(tmp_path, name="wp.jpg"):
    return LocalWallpaper(
        path=tmp_path / name,
        filename=name,
        size=1000,
        modified_time=0.0,
        tags=[],
    )


async def drain(coro):
    """Run a captured task coroutine to completion."""
    await coro


class TestSeparateCounters:
    """H8: upscale and tag queues must have independent concurrency slots."""

    async def test_upscale_and_tag_active_simultaneously(self, vm, tmp_path):
        """One active upscale must not block tagging (shared counter bug)."""
        vm.queue_upscale(make_wp(tmp_path, "a.jpg"))
        vm.queue_generate_tags(make_wp(tmp_path, "b.jpg"))

        assert vm.upscaling_active_count == 1
        assert vm.tagging_active_count == 1

    async def test_limits_are_enforced_per_queue(self, vm, tmp_path, mocker):
        mocker.patch(
            "ui.view_models.local_view_model.shutil.which", return_value=None
        )
        mock_gen = mocker.patch(
            "services.tag_generation.TagGenerationService"
        ).return_value
        mock_gen.is_available.return_value = False

        wps = [make_wp(tmp_path, f"wp{i}.jpg") for i in range(5)]
        for wp in wps[:3]:
            vm.queue_upscale(wp)
        for wp in wps[3:]:
            vm.queue_generate_tags(wp)

        assert vm.upscaling_active_count == vm.MAX_CONCURRENT_UPSCALING
        assert len(vm._upscale_queue) == 1
        assert vm.tagging_active_count == vm.MAX_CONCURRENT_TAGGING
        assert len(vm._tag_queue) == 0


class TestFailureReleasesSlot:
    """Failures must never leave a stuck spinner or a leaked slot."""

    async def test_failed_upscale_completes_and_drains_queue(self, vm, tmp_path, mocker):
        mocker.patch(
            "ui.view_models.local_view_model.shutil.which", return_value=None
        )

        wps = [make_wp(tmp_path, f"{name}.jpg") for name in ("a", "b", "c")]
        for wp in wps:
            vm.queue_upscale(wp)

        # Both slots filled, third waits in queue.
        assert vm.upscaling_active_count == 2
        assert len(vm._upscale_queue) == 1

        # First task fails (no waifu2x binary); finishing it starts the next one.
        await drain(vm._pending_coros.pop(0))
        assert vm.upscaling_active_count == 2
        assert len(vm._upscale_queue) == 0

        await drain(vm._pending_coros.pop(0))
        await drain(vm._pending_coros.pop(0))
        assert vm.upscaling_active_count == 0
        assert vm.upscaling_total_count == 0
        assert vm._failed_count == 3
        assert vm._completed_count == 0

    async def test_failed_tag_completes_and_drains_queue(self, vm, tmp_path, mocker):
        mock_gen = mocker.patch(
            "services.tag_generation.TagGenerationService"
        ).return_value
        mock_gen.is_available.return_value = False

        wp = make_wp(tmp_path, "a.jpg")
        vm.queue_generate_tags(wp)
        assert vm.tagging_active_count == 1

        await drain(vm._pending_coros.pop(0))
        assert vm.tagging_active_count == 0
        assert len(vm._tag_queue) == 0

    def test_schedule_failure_releases_counter(self, vm, tmp_path, mocker):
        mocker.patch(
            "ui.view_models.local_view_model.schedule_async",
            side_effect=RuntimeError("no event loop"),
        )

        queued, _ = vm.queue_upscale(make_wp(tmp_path))

        assert queued is True
        assert vm.upscaling_active_count == 0
        assert vm._failed_count == 1


class TestQueueLocking:
    """H9: concurrent enqueues must not corrupt queue state."""

    def test_concurrent_tag_enqueues_keep_consistent_state(self, vm, tmp_path):
        # Stub out signal marshalling: idle_add would touch GObject from threads.
        vm._emit_tagging_queue_changed = lambda: None

        errors: list[Exception] = []

        def worker():
            try:
                for i in range(10):
                    vm.queue_generate_tags(make_wp(tmp_path, f"w{threading.get_ident()}_{i}.jpg"))
            except Exception as e:  # pragma: no cover - failure diagnostics only
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        total = len(vm._tag_queue) + vm._tag_active_count
        assert total == 40
        assert vm._tag_active_count == min(40, vm.MAX_CONCURRENT_TAGGING)


class TestQueueSignals:
    async def test_each_queue_emits_its_own_signal(self, vm, tmp_path):
        upscale_events: list[tuple[int, int]] = []
        tag_events: list[tuple[int, int]] = []
        vm.connect(
            "upscaling-queue-changed",
            lambda _s, q, a: upscale_events.append((q, a)),
        )
        vm.connect(
            "tagging-queue-changed",
            lambda _s, q, a: tag_events.append((q, a)),
        )

        vm.queue_upscale(make_wp(tmp_path, "a.jpg"))
        vm.queue_generate_tags(make_wp(tmp_path, "b.jpg"))

        assert (0, 1) in upscale_events
        assert (0, 1) in tag_events
