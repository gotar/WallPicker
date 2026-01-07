"""Asyncio integration utilities for GTK4/PyGObject applications.

This module provides utilities for running async/await code from GTK callbacks
by properly integrating Python's asyncio event loop with GTK's GLib main loop.
"""

import asyncio
from collections.abc import Coroutine
from typing import Any

# Global event loop reference
_loop: asyncio.AbstractEventLoop | None = None


def setup_event_loop() -> asyncio.AbstractEventLoop:
    """Set up and return the asyncio event loop for GTK integration.

    Returns:
        The configured event loop ready for use with GTK.

    This should be called once at application startup, typically in launcher.py.
    The event loop is configured to run continuously alongside GTK's main loop.
    """
    global _loop

    # Create and set the event loop
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)

    # Start the keep-alive task to keep the loop running
    asyncio.run_coroutine_threadsafe(_run_loop_forever(), _loop)

    return _loop


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


def schedule_async(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
    """Schedule a coroutine to run on the asyncio event loop from GTK callbacks.

    This is the proper way to call async methods from GTK signal handlers.
    Use this function instead of asyncio.create_task() in GTK callbacks.

    Example:
        # In a GTK signal handler:
        schedule_async(self.my_view_model.load_async_data())

    Args:
        coro: The coroutine to schedule.

    Returns:
        An asyncio.Task that can be awaited if needed.

    Raises:
        RuntimeError: If the event loop is not properly configured.
    """
    loop = get_event_loop()
    task = asyncio.run_coroutine_threadsafe(coro, loop)

    # Return the task (wrapped as a Future from run_coroutine_threadsafe)
    # For most UI use cases, you don't need to await this
    return task


async def _run_loop_forever() -> None:
    """Keep the event loop running to process tasks.

    This task runs forever (or until the app exits) to ensure the event loop
    remains active and can process scheduled tasks.
    """
    try:
        # Sleep for a long time but wake up for tasks
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        # Gracefully exit when cancelled during app shutdown
        pass


def process_pending() -> None:
    """Process pending asyncio tasks from GTK's main loop.

    This should be called periodically (e.g., via GLib.timeout_add) to
    process any pending asyncio tasks and callbacks.

    Example:
        # In launcher.py or app initialization:
        GLib.timeout_add(10, lambda: (process_pending(), True)[1])
    """
    loop = get_event_loop()
    if loop.is_running():
        # Process any pending asyncio callbacks
        loop.call_soon(loop.stop)
        loop.run_forever()


def create_task(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
    """Create an asyncio task, properly integrated with GTK.

    This is a drop-in replacement for asyncio.create_task() that works
    correctly from GTK callbacks.

    Args:
        coro: The coroutine to create a task for.

    Returns:
        An asyncio.Task.
    """
    loop = get_event_loop()
    return loop.create_task(coro)
