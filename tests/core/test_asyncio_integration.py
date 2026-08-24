"""Tests for core.asyncio_integration (M28 done-callbacks, M27 shutdown)."""

import concurrent.futures
import threading
import time

import pytest

from core import asyncio_integration
from core.asyncio_integration import (
    get_event_loop,
    schedule_async,
    setup_event_loop,
    shutdown_event_loop,
)


@pytest.fixture
def event_loop_thread():
    """Set up the background asyncio loop and tear it down after the test."""
    loop = setup_event_loop()
    yield loop
    shutdown_event_loop()


class TestSetupAndShutdown:
    def test_setup_returns_running_loop(self, event_loop_thread):
        loop = get_event_loop()
        assert loop is event_loop_thread
        assert loop.is_running()

    def test_shutdown_stops_loop_thread(self):
        loop = setup_event_loop()
        assert loop.is_running()

        shutdown_event_loop(timeout=5)

        # Loop no longer registered and thread joined
        with pytest.raises(RuntimeError):
            get_event_loop()

    def test_shutdown_without_setup_is_noop(self):
        # Ensure clean state even if another test leaked a loop
        shutdown_event_loop(timeout=1)
        with pytest.raises(RuntimeError):
            get_event_loop()

    def test_shutdown_is_idempotent(self, event_loop_thread):
        shutdown_event_loop(timeout=5)
        shutdown_event_loop(timeout=5)  # must not raise


class TestScheduleAsync:
    def test_returns_concurrent_future(self, event_loop_thread):
        async def coro():
            return 42

        future = schedule_async(coro())

        assert isinstance(future, concurrent.futures.Future)
        assert future.result(timeout=5) == 42

    def test_exception_is_logged_via_done_callback(
        self, event_loop_thread, caplog
    ):
        """Coroutines that fail must not fail silently (M28)."""

        observed = []

        original = asyncio_integration._log_future_exception

        def spy(future):
            original(future)
            observed.append(True)

        async def failing():
            raise ValueError("boom")

        asyncio_integration._log_future_exception = spy
        try:
            future = schedule_async(failing())
            with pytest.raises(ValueError, match="boom"):
                future.result(timeout=5)
            # Wait for the done-callback to run on the loop thread
            deadline = time.monotonic() + 5
            while not observed and time.monotonic() < deadline:
                time.sleep(0.01)
        finally:
            asyncio_integration._log_future_exception = original

        assert observed == [True]

    def test_coroutine_runs_on_background_loop(self, event_loop_thread):
        main_thread = threading.current_thread()

        async def coro():
            return threading.current_thread() is not main_thread

        future = schedule_async(coro())
        assert future.result(timeout=5) is True


class TestCreateTask:
    def test_create_task_schedules_and_logs(self, event_loop_thread):
        async def coro():
            return "done"

        future = asyncio_integration.create_task(coro())

        assert isinstance(future, concurrent.futures.Future)
        assert future.result(timeout=5) == "done"
