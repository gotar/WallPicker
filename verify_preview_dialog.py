#!/usr/bin/env python3
"""Verification script for PreviewDialog component."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk

from domain.wallpaper import Wallpaper, WallpaperSource, WallpaperPurity, Resolution


class TestApp(Adw.Application):
    """Test application for PreviewDialog."""

    def __init__(self):
        super().__init__(application_id="com.wallpicker.previewtest")
        self.window = None

    def do_activate(self):
        if not self.window:
            self.window = Adw.ApplicationWindow(application=self)
            self.window.set_default_size(1200, 800)
            self.window.set_title("Preview Dialog Test")

            # Create main content
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            box.set_margin_top(24)
            box.set_margin_bottom(24)
            box.set_margin_start(24)
            box.set_margin_end(24)

            # Test button
            test_btn = Gtk.Button(label="Open Preview Dialog")
            test_btn.add_css_class("suggested-action")
            test_btn.add_css_class("pill")
            test_btn.set_size_request(200, 50)
            test_btn.connect("clicked", self._on_test_clicked)

            box.append(test_btn)
            self.window.set_child(box)

        self.window.present()

    def _on_test_clicked(self, button):
        """Handle test button click."""
        # Create sample wallpaper
        wallpaper = Wallpaper(
            id="test-123",
            url="https://picsum.photos/1920/1080",
            path="/tmp/test_wallpaper.jpg",
            resolution=Resolution(1920, 1080),
            source=WallpaperSource.LOCAL,
            category="test",
            purity=WallpaperPurity.SFW,
            file_size=2400000,
        )

        # Import dialog here to avoid import errors
        from ui.components.preview_dialog import PreviewDialog

        # Create and show dialog
        dialog = PreviewDialog(
            window=self.window,
            wallpaper=wallpaper,
            on_set_wallpaper=self._on_set_wallpaper,
            on_toggle_favorite=self._on_toggle_favorite,
            on_open_externally=self._on_open_externally,
            on_delete=self._on_delete,
            on_copy_path=self._on_copy_path,
            is_favorite=False,
        )
        dialog.present()

    def _on_set_wallpaper(self):
        print("Set wallpaper callback triggered")

    def _on_toggle_favorite(self, is_favorite):
        print(f"Favorite toggle callback: {is_favorite}")

    def _on_open_externally(self):
        print("Open externally callback triggered")

    def _on_delete(self):
        print("Delete callback triggered")

    def _on_copy_path(self):
        print("Copy path callback triggered")


def main():
    """Run test application."""
    app = TestApp()
    app.run(sys.argv)


if __name__ == "__main__":
    main()
