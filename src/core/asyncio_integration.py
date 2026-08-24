"""Asyncio integration utilities for GTK4/PyGObject applications.

This module provides utilities for running async/await code from GTK callbacks
by properly integrating Python's asyncio event loop with GTK's GLib main loop.
"""

import asyncio
import concurrent.futures
import logging
import threading
from collections.abc import Coroutine
from typing import Any

try:
    from gi.repository import GLib
except ImportError:
    GLib = None

logger = logging.getLogger(__name__)

_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None


def setup_event_loop() -> asyncio.AbstractEventLoop:
    """Set up and return the asyncio event loop for GTK integration.

    Returns:
        The configured event loop ready for use with GTK.

    This should be called once at application startup, typically in launcher.py.
    Uses a background thread to run the asyncio event loop.
    """
    global _loop, _loop_thread

    _loop = asyncio.new_event_loop()

    def run_loop():
        asyncio.set_event_loop(_loop)
        _loop.run_forever()

    _loop_thread = threading.Thread(target=run_loop, daemon=True)
    _loop_thread.start()

    return _loop


def shutdown_event_loop(timeout: float = 5.0) -> None:
    """Gracefully stop the background asyncio event loop thread (M27).

    Safe to call multiple times and when no loop was ever set up.
    Pending tasks are abandoned; callers should close resources (e.g. the
    aiohttp session) before calling this.
    """
    global _loop, _loop_thread

    loop = _loop
    thread = _loop_thread
    _loop = None
    _loop_thread = None

    if loop is None:
        return

    if loop.is_running():
        try:
            loop.call_soon_threadsafe(loop.stop)
        except RuntimeError:
            # Loop already closed on another thread
            pass

    if thread is not None and thread is not threading.current_thread():
        thread.join(timeout=timeout)


def get_event_loop() -> asyncio.AbstractEventLoop:
    """Get the configured event loop.

    Returns:
        The event loop configured by setup_event_loop().

    Raises:
        RuntimeError: If setup_event_loop() has not been called.
    """
    global _loop
    if _loop is None:
        raise RuntimeError("Event loop not initialized. Call setup_event_loop() first.")
    return _loop


def _log_future_exception(future: concurrent.futures.Future) -> None:
    """Log exceptions from scheduled coroutines so they are never silent (M28)."""
    try:
        future.result()
    except concurrent.futures.CancelledError:
        pass
    except Exception:
        logger.exception("Unhandled exception in scheduled coroutine")


def schedule_async(
    coro: Coroutine[Any, Any, Any],
) -> concurrent.futures.Future[Any]:
    """Schedule a coroutine to run on the asyncio event loop from GTK callbacks.

    This properly integrates Python's asyncio with GTK4's GLib main loop.
    Exceptions raised inside the coroutine are logged automatically instead
    of being silently swallowed.

    Example:
        # In a GTK signal handler:
        schedule_async(self.my_view_model.load_async_data())

    Args:
        coro: The coroutine to schedule.

    Returns:
        A concurrent.futures.Future that can be awaited or checked if needed.
    """
    loop = get_event_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    future.add_done_callback(_log_future_exception)
    return future


def create_task(coro: Coroutine[Any, Any, Any]) -> concurrent.futures.Future[Any]:
    """Create an asyncio task, properly integrated with GTK.

    This is a drop-in replacement for asyncio.create_task() that works
    correctly from GTK callbacks. Exceptions are logged automatically.

    Args:
        coro: The coroutine to schedule.

    Returns:
        A concurrent.futures.Future representing the running coroutine.
    """
    return schedule_async(coro)
