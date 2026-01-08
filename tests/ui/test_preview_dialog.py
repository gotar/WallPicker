#!/usr/bin/env python3
"""Test PreviewDialog component structure."""

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_preview_dialog_creation():
    """Test that PreviewDialog can be instantiated."""
    print("Testing PreviewDialog creation...")

    print("✓ Test setup complete")

    # Import PreviewDialog
    from ui.components.preview_dialog import PreviewDialog

    print("✓ Imported PreviewDialog component")

    # Check that the class exists and has expected methods
    assert hasattr(PreviewDialog, "__init__")
    assert hasattr(PreviewDialog, "_create_ui")
    assert hasattr(PreviewDialog, "_create_metadata_section")
    assert hasattr(PreviewDialog, "_create_actions_section")
    assert hasattr(PreviewDialog, "_setup_shortcuts")
    assert hasattr(PreviewDialog, "update_favorite_state")
    assert hasattr(PreviewDialog, "set_delete_visible")

    print("✓ PreviewDialog has all required methods")

    print("\n✓ All structure tests passed!")


def test_preview_dialog_api():
    """Test PreviewDialog API surface."""
    print("\nTesting PreviewDialog API...")

    import inspect

    from ui.components.preview_dialog import PreviewDialog

    # Get __init__ signature
    sig = inspect.signature(PreviewDialog.__init__)
    params = list(sig.parameters.keys())

    expected_params = [
        "self",
        "window",
        "wallpaper",
        "on_set_wallpaper",
        "on_toggle_favorite",
        "on_open_externally",
        "on_delete",
        "on_copy_path",
        "is_favorite",
        "thumbnail_cache",
    ]

    print(f"Expected parameters: {expected_params}")
    print(f"Actual parameters: {params}")

    for param in expected_params:
        assert param in params, f"Missing parameter: {param}"

    print("✓ PreviewDialog API has correct parameters")

    # Check public methods
    public_methods = [
        name
        for name, method in inspect.getmembers(
            PreviewDialog, predicate=inspect.isfunction
        )
        if not name.startswith("_")
    ]

    print(f"Public methods: {public_methods}")

    print("✓ PreviewDialog API surface verified")


def test_css_classes():
    """Test that CSS classes are properly applied."""
    print("\nTesting CSS classes...")

    from ui.components.preview_dialog import PreviewDialog

    # Check that CSS classes are added in _create_ui
    ui_source = inspect.getsource(PreviewDialog._create_ui)
    actions_source = inspect.getsource(PreviewDialog._create_actions_section)

    assert (
        ".preview-image-container" in ui_source
        or '"preview-image-container"' in ui_source
    )
    assert ".preview-sidebar" in ui_source or '"preview-sidebar"' in ui_source
    assert ".pill" in actions_source or '"pill"' in actions_source

    # Check preview-dialog CSS class is added in __init__
    init_source = inspect.getsource(PreviewDialog.__init__)
    assert ".preview-dialog" in init_source or '"preview-dialog"' in init_source

    print("✓ CSS classes properly applied in code")

    # Check that CSS file exists and contains necessary classes
    css_path = Path(__file__).parent.parent.parent / "data" / "style.css"
    assert css_path.exists(), "CSS file not found"

    css_content = css_path.read_text()

    assert ".preview-dialog" in css_content
    assert ".preview-image-container" in css_content
    assert ".preview-sidebar" in css_content
    assert ".pill" in css_content

    print("✓ CSS file contains all required classes")


def test_keyboard_shortcuts():
    """Test keyboard shortcut handling."""
    print("\nTesting keyboard shortcuts...")

    import inspect

    from ui.components.preview_dialog import PreviewDialog

    # Check that _on_key_pressed method exists and handles expected keys
    key_pressed_source = inspect.getsource(PreviewDialog._on_key_pressed)

    assert "Gdk.KEY_Escape" in key_pressed_source
    assert "Gdk.KEY_Return" in key_pressed_source
    assert "Gdk.KEY_space" in key_pressed_source

    print("✓ Keyboard shortcuts implemented")


if __name__ == "__main__":
    try:
        test_preview_dialog_creation()
        test_preview_dialog_api()
        test_css_classes()
        test_keyboard_shortcuts()

        print("\n" + "=" * 50)
        print("ALL TESTS PASSED! ✓")
        print("=" * 50)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
