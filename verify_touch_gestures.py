#!/usr/bin/env python3
"""Verification script for touch gesture implementation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def check_main_window():
    """Check main window for swipe and keyboard shortcuts."""
    print("Checking main_window.py for touch gestures...")

    try:
        with open("src/ui/main_window.py", "r") as f:
            content = f.read()

        checks = {
            "_setup_gestures": "Gesture setup method",
            "_setup_swipe_gestures": "Swipe gesture setup",
            "_on_swipe": "Swipe gesture handler",
            "_setup_keyboard_shortcuts": "Keyboard shortcuts setup",
            "_on_key_pressed": "Keyboard shortcuts handler",
            "_next_tab": "Next tab navigation",
            "_prev_tab": "Previous tab navigation",
        }

        for method, description in checks.items():
            if f"def {method}" in content:
                print(f"  ✓ {description}")
            else:
                print(f"  ✗ {description} - MISSING")

        # Check imports
        if "from gi.repository import Adw, Gdk, GLib, Gtk" in content:
            print("  ✓ All required imports present")
        else:
            print("  ✗ Required imports incomplete")

    except FileNotFoundError:
        print("  ✗ File not found")
    except Exception as e:
        print(f"  ✗ Error: {e}")


def check_view(view_name):
    """Check view for pull-to-refresh gesture."""
    print(f"\nChecking {view_name} for pull-to-refresh...")

    try:
        with open(f"src/ui/views/{view_name}.py", "r") as f:
            content = f.read()

        checks = {
            "_setup_pull_to_refresh": "Pull-to-refresh setup",
            "_on_pull_swipe": "Pull gesture handler",
            "_reset_refresh_flag": "Refresh flag reset",
        }

        for method, description in checks.items():
            if f"def {method}" in content:
                print(f"  ✓ {description}")
            else:
                print(f"  ✗ {description} - MISSING")

    except FileNotFoundError:
        print("  ✗ File not found")
    except Exception as e:
        print(f"  ✗ Error: {e}")


def check_wallhaven_view():
    """Check Wallhaven view for scroll snap."""
    print("\nChecking wallhaven_view.py for scroll snap...")

    try:
        with open("src/ui/views/wallhaven_view.py", "r") as f:
            content = f.read()

        checks = {
            "_setup_scroll_snap": "Scroll snap setup",
            "_on_scroll": "Scroll handler",
            "_refresh_current_search": "Search refresh method",
        }

        for method, description in checks.items():
            if f"def {method}" in content:
                print(f"  ✓ {description}")
            else:
                print(f"  ✗ {description} - MISSING")

    except FileNotFoundError:
        print("  ✗ File not found")
    except Exception as e:
        print(f"  ✗ Error: {e}")


def check_wallpaper_card():
    """Check wallpaper card for long-press gesture."""
    print("\nChecking wallpaper_card.py for long-press...")

    try:
        with open("src/ui/components/wallpaper_card.py", "r") as f:
            content = f.read()

        checks = {
            "Gtk.GestureLongPress": "Long press gesture import",
            "_on_long_press": "Long press handler",
            "touch-feedback": "Touch feedback CSS class",
        }

        for item, description in checks.items():
            if item in content:
                print(f"  ✓ {description}")
            else:
                print(f"  ✗ {description} - MISSING")

    except FileNotFoundError:
        print("  ✗ File not found")
    except Exception as e:
        print(f"  ✗ Error: {e}")


def check_preview_dialog():
    """Check preview dialog for pinch-zoom."""
    print("\nChecking preview_dialog.py for pinch-zoom...")

    try:
        with open("src/ui/components/preview_dialog.py", "r") as f:
            content = f.read()

        checks = {
            "Gtk.GestureZoom": "Zoom gesture import",
            "_on_zoom_changed": "Zoom handler",
            "current_scale": "Zoom level tracking",
            'self.image.add_css_class(f"zoom-': "CSS zoom class application",
        }

        for item, description in checks.items():
            if item in content:
                print(f"  ✓ {description}")
            else:
                print(f"  ✗ {description} - MISSING")

    except FileNotFoundError:
        print("  ✗ File not found")
    except Exception as e:
        print(f"  ✗ Error: {e}")


def check_css():
    """Check CSS for touch-friendly styles."""
    print("\nChecking style.css for touch styles...")

    try:
        with open("data/style.css", "r") as f:
            content = f.read()

        checks = {
            "min-height: 44px": "Touch-friendly button height",
            "min-width: 44px": "Touch-friendly button width",
            "min-width: 88px": "Action button width",
            ".zoom-100": "Zoom 100% class",
            ".zoom-200": "Zoom 200% class",
            ".zoom-500": "Zoom 500% class",
            ":active {": "Active touch states",
            "transform: scale": "Transform animations",
        }

        for pattern, description in checks.items():
            if pattern in content:
                print(f"  ✓ {description}")
            else:
                print(f"  ✗ {description} - MISSING")

    except FileNotFoundError:
        print("  ✗ File not found")
    except Exception as e:
        print(f"  ✗ Error: {e}")


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("TOUCH GESTURE IMPLEMENTATION VERIFICATION")
    print("=" * 60)

    check_main_window()
    check_view("local_view")
    check_view("favorites_view")
    check_wallhaven_view()
    check_wallpaper_card()
    check_preview_dialog()
    check_css()

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
