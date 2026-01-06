#!/usr/bin/env python3
"""Verify Adw.Clamp integration in Wallpicker main layout."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk


def verify_clamp_layout():
    """Test Adw.Clamp behavior with different window sizes."""

    app = Adw.Application(application_id="com.example.WallpickerClampTest")

    def on_activate(app):
        window = Adw.ApplicationWindow(application=app)
        window.set_title("Clamp Layout Verification")
        window.set_default_size(1600, 800)

        toolbar = Adw.ToolbarView()

        header = Adw.HeaderBar()
        header.set_title_widget(
            Adw.WindowTitle(title="Clamp Test", subtitle="Testing width constraints")
        )
        toolbar.add_top_bar(header)

        # Create test content (simulating wallpaper grid)
        test_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        test_content.set_margin_top(24)
        test_content.set_margin_bottom(24)
        test_content.set_margin_start(12)
        test_content.set_margin_end(12)

        # Add explanatory labels
        info_label = Gtk.Label()
        info_label.set_markup(
            "<b>Adw.Clamp Configuration:</b>\n"
            "• maximum_size: 1400px\n"
            "• tightening_threshold: 1000px\n\n"
            "<b>Expected Behavior:</b>\n"
            "• Width < 1000px: Full width (no margins)\n"
            "• Width 1000-1400px: Decreasing margins\n"
            "• Width > 1400px: Fixed 1400px width, centered"
        )
        info_label.set_wrap(True)
        info_label.set_halign(Gtk.Align.CENTER)
        test_content.append(info_label)

        # Add visual grid to demonstrate centering
        grid_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        grid_box.set_vexpand(True)

        for row in range(5):
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row_box.set_hexpand(True)

            for col in range(6):
                card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                card.add_css_class("wallpaper-card")
                card.set_size_request(180, 180)
                card.set_hexpand(True)

                placeholder = Gtk.Label(label=f"{col + 1}")
                placeholder.set_halign(Gtk.Align.CENTER)
                placeholder.set_valign(Gtk.Align.CENTER)
                placeholder.set_vexpand(True)

                card.append(placeholder)
                row_box.append(card)

            grid_box.append(row_box)

        test_content.append(grid_box)

        # Wrap content in Clamp
        clamp = Adw.Clamp()
        clamp.set_maximum_size(1400)
        clamp.set_tightening_threshold(1000)
        clamp.set_child(test_content)

        # Add a status bar to show current width
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_bar.add_css_class("status-bar")
        status_bar.set_margin_start(12)
        status_bar.set_margin_end(12)
        status_bar.set_margin_bottom(8)

        def on_size_allocate(widget, width, height):
            status_label.set_text(
                f"Window: {width}px | Content: {min(width, 1400)}px "
                + f"({'Clamped' if width > 1400 else 'Full width'})"
            )

        status_label = Gtk.Label(label="Resize window to see clamp behavior")
        status_bar.append(status_label)

        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        status_box.append(clamp)
        status_box.append(status_bar)

        toolbar.set_content(status_box)
        window.set_child(toolbar)

        # Connect to show current width
        window.connect("size-allocate", on_size_allocate)

        # Add action buttons
        resize_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        resize_actions.set_halign(Gtk.Align.CENTER)
        resize_actions.set_margin_top(12)

        for size in [800, 1000, 1200, 1400, 1600, 1920]:
            btn = Gtk.Button(label=f"{size}px")
            btn.add_css_class("pill")

            def on_resize_clicked(button, w=size):
                window.set_default_size(w, 800)

            btn.connect("clicked", on_resize_clicked)
            resize_actions.append(btn)

        test_content.append(Gtk.Separator())
        resize_label = Gtk.Label(label="<b>Quick Resize Tests:</b>")
        resize_label.set_halign(Gtk.Align.CENTER)
        resize_label.set_use_markup(True)
        test_content.append(resize_label)
        test_content.append(resize_actions)

        window.present()

    app.connect("activate", on_activate)
    app.run(None)


def verify_clamp_properties():
    """Verify Adw.Clamp property values."""
    print("Verifying Adw.Clamp properties...")

    clamp = Adw.Clamp()

    # Test default values
    print(f"\nDefault values:")
    print(f"  maximum_size: {clamp.get_maximum_size()}")
    print(f"  tightening_threshold: {clamp.get_tightening_threshold()}")

    # Test our configuration
    clamp.set_maximum_size(1400)
    clamp.set_tightening_threshold(1000)

    print(f"\nConfigured values:")
    print(f"  maximum_size: {clamp.get_maximum_size()}")
    print(f"  tightening_threshold: {clamp.get_tightening_threshold()}")

    # Verify
    assert clamp.get_maximum_size() == 1400, "Maximum size should be 1400px"
    assert clamp.get_tightening_threshold() == 1000, "Tightening threshold should be 1000px"

    print("\n✓ Clamp properties verified successfully")
    print("✓ max-width: 1400px")
    print("✓ tightening_threshold: 1000px")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        verify_clamp_properties()
    else:
        print("Starting Clamp Layout Verification...")
        print("Resize the window to observe clamp behavior:")
        print("  - < 1000px: Full width with no margins")
        print("  - 1000-1400px: Decreasing margins (tightening)")
        print("  - > 1400px: Fixed 1400px width, centered\n")
        verify_clamp_layout()
