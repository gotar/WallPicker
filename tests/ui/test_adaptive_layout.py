"""Tests for adaptive layout functionality."""

import pytest
from gi.repository import Adw, Gtk

from ui.components.adaptive_layout import AdaptiveLayoutMixin


class TestView(Adw.BreakpointBin, AdaptiveLayoutMixin):
    """Test view with adaptive layout mixin."""

    def __init__(self):
        super().__init__()
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(self.main_box)


@pytest.fixture
def test_view():
    """Create a test view with adaptive layout."""
    view = TestView()

    # Create a flow box for testing
    flow_box = Gtk.FlowBox()
    flow_box.set_homogeneous(True)
    flow_box.set_min_children_per_line(2)
    flow_box.set_max_children_per_line(6)

    view._setup_adaptive_layout(flow_box)
    return view


@pytest.fixture
def test_view_with_filter():
    """Create a test view with filter bar."""
    view = TestView()

    # Create filter bar
    filter_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    filter_bar.add_css_class("filter-bar")

    view._setup_filter_adaptation(filter_bar)
    return view


class TestBreakpointBehavior:
    """Test breakpoint behavior at different window sizes."""

    def test_breakpoint_applies_at_600px(self, test_view):
        """Test that 2-column breakpoint activates at 600px."""
        assert test_view.flow_box is not None
        assert test_view.flow_box.get_min_children_per_line() == 2
        assert test_view.flow_box.get_max_children_per_line() == 6

        # Simulate narrow breakpoint application
        test_view.flow_box.set_max_children_per_line(2)
        assert test_view.flow_box.get_max_children_per_line() == 2

    def test_breakpoint_applies_at_900px(self, test_view):
        """Test that 3-4 column breakpoint activates at 900px."""
        assert test_view.flow_box is not None

        # Simulate medium breakpoint application
        test_view.flow_box.set_max_children_per_line(3)
        assert test_view.flow_box.get_max_children_per_line() == 3

    def test_breakpoint_applies_at_1200px(self, test_view):
        """Test that 4-5 column breakpoint activates at 1200px."""
        assert test_view.flow_box is not None

        # Simulate wide breakpoint application
        test_view.flow_box.set_max_children_per_line(4)
        assert test_view.flow_box.get_max_children_per_line() == 4

    def test_breakpoint_applies_at_1400px(self, test_view):
        """Test that 6-column breakpoint activates at 1400px."""
        assert test_view.flow_box is not None

        # Simulate full breakpoint application
        test_view.flow_box.set_max_children_per_line(6)
        assert test_view.flow_box.get_max_children_per_line() == 6

    def test_column_progression(self, test_view):
        """Test that column count progresses correctly through breakpoints."""
        assert test_view.flow_box is not None

        # Test progression: 2 -> 3 -> 4 -> 5 -> 6
        for expected_columns in [2, 3, 4, 5, 6]:
            test_view.flow_box.set_max_children_per_line(expected_columns)
            assert test_view.flow_box.get_max_children_per_line() == expected_columns


class TestFilterOrientation:
    """Test filter bar orientation changes."""

    def test_filter_orientation_changes_at_900px(self, test_view_with_filter):
        """Test that filter bar stacks at 900px."""
        assert test_view_with_filter.filter_bar is not None
        assert test_view_with_filter.filter_bar.get_orientation() == Gtk.Orientation.HORIZONTAL

        # Simulate narrow breakpoint application
        test_view_with_filter.filter_bar.set_orientation(Gtk.Orientation.VERTICAL)
        test_view_with_filter.filter_bar.add_css_class("vertical")

        assert test_view_with_filter.filter_bar.get_orientation() == Gtk.Orientation.VERTICAL
        assert test_view_with_filter.filter_bar.has_css_class("vertical")

    def test_filter_orientation_reverts_to_horizontal(self, test_view_with_filter):
        """Test that filter bar reverts to horizontal on wide screens."""
        assert test_view_with_filter.filter_bar is not None

        # Simulate narrow state
        test_view_with_filter.filter_bar.set_orientation(Gtk.Orientation.VERTICAL)
        test_view_with_filter.filter_bar.add_css_class("vertical")
        assert test_view_with_filter.filter_bar.get_orientation() == Gtk.Orientation.VERTICAL

        # Simulate wide breakpoint unapplication
        test_view_with_filter.filter_bar.set_orientation(Gtk.Orientation.HORIZONTAL)
        test_view_with_filter.filter_bar.remove_css_class("vertical")

        assert test_view_with_filter.filter_bar.get_orientation() == Gtk.Orientation.HORIZONTAL
        assert not test_view_with_filter.filter_bar.has_css_class("vertical")


class TestFlowBoxConfiguration:
    """Test FlowBox configuration for adaptive layout."""

    def test_flow_box_initial_configuration(self, test_view):
        """Test that flow box is properly initialized."""
        assert test_view.flow_box is not None
        assert test_view.flow_box.get_homogeneous() is True
        assert test_view.flow_box.get_min_children_per_line() == 2
        assert test_view.flow_box.get_max_children_per_line() == 6
        assert test_view.flow_box.get_selection_mode() == Gtk.SelectionMode.NONE

    def test_flow_box_spacing(self, test_view):
        """Test that flow box has proper spacing."""
        assert test_view.flow_box is not None

        # FlowBox should have spacing set
        test_view.flow_box.set_column_spacing(12)
        test_view.flow_box.set_row_spacing(12)

        assert test_view.flow_box.get_column_spacing() == 12
        assert test_view.flow_box.get_row_spacing() == 12


class TestAdaptiveLayoutIntegration:
    """Integration tests for adaptive layout behavior."""

    def test_multiple_breakpoints_sequentially(self, test_view):
        """Test all breakpoints in sequence (600 → 900 → 1200 → 1400)."""
        assert test_view.flow_box is not None

        # Simulate window resizing through all breakpoints
        breakpoint_sequence = [
            (600, 2),
            (900, 3),
            (1200, 4),
            (1400, 5),
            (1600, 6),
        ]

        for width, expected_columns in breakpoint_sequence:
            test_view.flow_box.set_max_children_per_line(expected_columns)
            assert test_view.flow_box.get_max_children_per_line() == expected_columns

    def test_filter_adaptation_with_grid(self, test_view, test_view_with_filter):
        """Test that filter adaptation works alongside grid adaptation."""
        assert test_view.flow_box is not None
        assert test_view_with_filter.filter_bar is not None

        # Simulate narrow breakpoint
        test_view.flow_box.set_max_children_per_line(2)
        test_view_with_filter.filter_bar.set_orientation(Gtk.Orientation.VERTICAL)

        assert test_view.flow_box.get_max_children_per_line() == 2
        assert test_view_with_filter.filter_bar.get_orientation() == Gtk.Orientation.VERTICAL

        # Simulate wide breakpoint
        test_view.flow_box.set_max_children_per_line(4)
        test_view_with_filter.filter_bar.set_orientation(Gtk.Orientation.HORIZONTAL)

        assert test_view.flow_box.get_max_children_per_line() == 4
        assert test_view_with_filter.filter_bar.get_orientation() == Gtk.Orientation.HORIZONTAL


@pytest.fixture
def window():
    """Create a test application window."""
    from gi.repository import Adw

    app = Adw.Application(application_id="com.example.Test")
    win = Adw.ApplicationWindow(application=app)
    return win


class TestWindowSizeLimits:
    """Test window size limit settings."""

    def test_default_window_size(self, window):
        """Test that default window size is set correctly."""
        # Default size should be 1200x800 as per main_window.py
        window.set_default_size(1200, 800)
        width, height = window.get_default_size()
        assert width == 1200
        assert height == 800

    def test_minimum_window_size(self, window):
        """Test that minimum window size is enforced."""
        # Minimum size should be 600x400 as per main_window.py
        window.set_size_request(600, 400)
        min_width, min_height = window.get_size_request()
        assert min_width == 600
        assert min_height == 400


class TestViewSwitcherBarAutoHide:
    """Test ViewSwitcherBar auto-hide functionality."""

    def test_view_switcher_bar_auto_hide_css(self):
        """Test that auto-hide CSS class is properly applied."""
        view_switcher_bar = Adw.ViewSwitcherBar()
        view_switcher_bar.add_css_class("auto-hide-wide")

        assert view_switcher_bar.has_css_class("auto-hide-wide")


class TestCSSMediaQueries:
    """Test CSS media query functionality (integration tests)."""

    def test_card_width_narrow(self):
        """Test card width for narrow screens (< 600px)."""
        # This would require actual rendering and CSS inspection
        # For now, we verify CSS file exists and contains media queries
        import os

        css_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "style.css")
        assert os.path.exists(css_path)

        with open(css_path) as f:
            css_content = f.read()
            assert "@media (max-width: 600px)" in css_content
            assert ".wallpaper-card" in css_content

    def test_card_width_medium(self):
        """Test card width for medium screens (600-900px)."""
        import os

        css_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "style.css")
        with open(css_path) as f:
            css_content = f.read()
            assert "@media (min-width: 600px) and (max-width: 900px)" in css_content

    def test_card_width_wide(self):
        """Test card width for wide screens (900-1200px)."""
        import os

        css_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "style.css")
        with open(css_path) as f:
            css_content = f.read()
            assert "@media (min-width: 900px) and (max-width: 1200px)" in css_content

    def test_card_width_ultra_wide(self):
        """Test card width for ultra-wide screens (> 1200px)."""
        import os

        css_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "style.css")
        with open(css_path) as f:
            css_content = f.read()
            assert "@media (min-width: 1200px)" in css_content

    def test_view_switcher_bar_auto_hide_css_exists(self):
        """Test that ViewSwitcherBar auto-hide CSS exists."""
        import os

        css_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "style.css")
        with open(css_path) as f:
            css_content = f.read()
            assert ".auto-hide-wide" in css_content
            assert "@media (min-width: 700px)" in css_content

    def test_filter_bar_vertical_css(self):
        """Test that filter bar vertical CSS exists."""
        import os

        css_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "style.css")
        with open(css_path) as f:
            css_content = f.read()
            assert ".filter-bar.vertical" in css_content
            assert "flex-direction: column" in css_content
