"""Unit tests for touch gesture functionality."""

import pytest
from unittest.mock import MagicMock, patch, Mock
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gi.repository import Gdk


class TestSwipeGestures:
    """Test swipe gesture for tab switching."""

    @patch("ui.main_window.LocalViewModel")
    @patch("ui.main_window.FavoritesViewModel")
    @patch("ui.main_window.WallhavenViewModel")
    def test_swipe_left_switches_tab(self, mock_wall_vm, mock_fav_vm, mock_local_vm):
        """Test swipe left switches to next tab."""
        from ui.main_window import WallPickerWindow

        window = WallPickerWindow(
            application=Mock(),
            local_view_model=mock_local_vm.return_value,
            favorites_view_model=mock_fav_vm.return_value,
            wallhaven_view_model=mock_wall_vm.return_value,
        )

        window.stack.set_visible_child_name("local")
        gesture = Mock()

        window._on_swipe(gesture, -150, 0)

        assert window.stack.get_visible_child_name() == "wallhaven"

    @patch("ui.main_window.LocalViewModel")
    @patch("ui.main_window.FavoritesViewModel")
    @patch("ui.main_window.WallhavenViewModel")
    def test_swipe_right_switches_tab(self, mock_wall_vm, mock_fav_vm, mock_local_vm):
        """Test swipe right switches to previous tab."""
        from ui.main_window import WallPickerWindow

        window = WallPickerWindow(
            application=Mock(),
            local_view_model=mock_local_vm.return_value,
            favorites_view_model=mock_fav_vm.return_value,
            wallhaven_view_model=mock_wall_vm.return_value,
        )

        window.stack.set_visible_child_name("wallhaven")
        gesture = Mock()

        window._on_swipe(gesture, 150, 0)
        assert window.stack.get_visible_child_name() == "local"


class TestKeyboardShortcuts:
    """Test keyboard shortcuts equivalent to swipe gestures."""

    @patch("ui.main_window.LocalViewModel")
    @patch("ui.main_window.FavoritesViewModel")
    @patch("ui.main_window.WallhavenViewModel")
    def test_ctrl_bracket_next_tab(self, mock_wall_vm, mock_fav_vm, mock_local_vm):
        """Test Ctrl+] switches to next tab."""
        from ui.main_window import WallPickerWindow

        window = WallPickerWindow(
            application=Mock(),
            local_view_model=mock_local_vm.return_value,
            favorites_view_model=mock_fav_vm.return_value,
            wallhaven_view_model=mock_wall_vm.return_value,
        )

        window.stack.set_visible_child_name("local")
        result = window._on_key_pressed(
            Mock(), Gdk.KEY_bracketright, 0, Gdk.ModifierType.CONTROL_MASK
        )
        assert result is True
        assert window.stack.get_visible_child_name() == "wallhaven"

    @patch("ui.main_window.LocalViewModel")
    @patch("ui.main_window.FavoritesViewModel")
    @patch("ui.main_window.WallhavenViewModel")
    def test_ctrl_bracket_prev_tab(self, mock_wall_vm, mock_fav_vm, mock_local_vm):
        """Test Ctrl+[ switches to previous tab."""
        from ui.main_window import WallPickerWindow

        window = WallPickerWindow(
            application=Mock(),
            local_view_model=mock_local_vm.return_value,
            favorites_view_model=mock_fav_vm.return_value,
            wallhaven_view_model=mock_wall_vm.return_value,
        )

        window.stack.set_visible_child_name("wallhaven")
        result = window._on_key_pressed(
            Mock(), Gdk.KEY_bracketleft, 0, Gdk.ModifierType.CONTROL_MASK
        )
        assert result is True
        assert window.stack.get_visible_child_name() == "local"
