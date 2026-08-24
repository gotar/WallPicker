"""Headless CLI for WallPicker (no GTK required).

Usage:
    wallpicker set <image-path>   Set the desktop wallpaper
    wallpicker current            Print the current wallpaper path

The CLI shares the exact wallpaper-setting pipeline with the GUI
(services.wallpaper_setter.WallpaperSetter), so testing the CLI exercises
the same omarchy/awww integration the GUI uses.
"""

import asyncio
import sys

from core.logging_setup import setup_logging


def _set(image_path: str) -> int:
    from services.wallpaper_setter import WallpaperSetter

    setter = WallpaperSetter()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        ok = asyncio.run_coroutine_threadsafe(
            setter.set_wallpaper_async(image_path), loop
        ).result(timeout=60)
    else:
        ok = asyncio.run(setter.set_wallpaper_async(image_path))

    if ok:
        print(f"Wallpaper set: {image_path}")
        return 0
    print(f"Failed to set wallpaper: {image_path}", file=sys.stderr)
    return 1


def _current() -> int:
    from services.wallpaper_setter import WallpaperSetter

    current = WallpaperSetter().get_current_wallpaper()
    if current:
        print(current)
        return 0
    print("No wallpaper set", file=sys.stderr)
    return 1


def _version() -> str:
    try:
        from importlib.metadata import version

        return version("wallpicker")
    except Exception:
        return "unknown"


def _gui_usage() -> str:
    return (
        "Usage:\n"
        "  wallpicker [options]          Launch the WallPicker GUI\n\n"
        "Options:\n"
        "  -h, --help                    Show this help and exit\n"
        "  -v, --version                 Show version and exit\n"
        "  --debug                       Enable debug logging\n\n"
        + __doc__.strip()
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: `wallpicker-cli <command> ...`."""
    args = list(sys.argv[1:] if argv is None else argv)
    setup_logging()

    if not args or "-h" in args or "--help" in args:
        print(_gui_usage())
        return 0 if args else 1

    if "-v" in args or "--version" in args:
        print(f"wallpicker {_version()}")
        return 0

    command, *rest = args
    if command == "set" and len(rest) == 1:
        return _set(rest[0])
    if command == "current" and not rest:
        return _current()

    print(f"Unknown command: {' '.join(args)}", file=sys.stderr)
    print(__doc__.strip(), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
