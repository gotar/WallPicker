"""Tests for BannerService."""

import pytest
from unittest.mock import MagicMock, Mock, patch
from gi.repository import GObject

from services.banner_service import (
    BannerService,
    BannerPriority,
    BannerType,
)


@pytest.fixture
def mock_window():
    """Create a mock application window."""
    return MagicMock()


@pytest.fixture
def banner_service(mock_window):
    """Create a BannerService instance for testing."""
    with patch("services.banner_service.Adw"):
        service = BannerService(mock_window)
        return service


class TestBannerServiceInitialization:
    """Tests for BannerService initialization."""

    def test_init_creates_banner_container(self, banner_service):
        """Test that banner container is created."""
        assert hasattr(banner_service, "banner_container")

    def test_init_sets_initial_state(self, banner_service):
        """Test that initial properties are correct."""
        assert banner_service.current_banner_type == ""
        assert not banner_service.is_visible
        assert len(banner_service._banner_queue) == 0

    def test_init_signals_connected(self, banner_service):
        """Test that banner signals are connected."""
        # Banner should be a mock with connect method
        banner_container_mock = banner_service.banner_container
        assert banner_container_mock.connect.called


class TestBannerPriority:
    """Tests for BannerPriority enum."""

    def test_priority_order(self):
        """Test that priority levels have correct order."""
        assert BannerPriority.LOW < BannerPriority.MEDIUM < BannerPriority.HIGH


class TestShowSelectionBanner:
    """Tests for selection banner display."""

    def test_show_selection_banner_with_count(self, banner_service):
        """Test showing selection banner with count > 0."""
        callback = MagicMock()

        with patch.object(banner_service, "_show_banner") as mock_show:
            banner_service.show_selection_banner(5, callback)

            mock_show.assert_called_once()
            call_args = mock_show.call_args[1]

            assert "5 wallpapers selected" in call_args["title"]
            assert call_args["button_text"] == "Set All"
            assert call_args["callback"] == callback
            assert call_args["priority"] == BannerPriority.MEDIUM
            assert call_args["banner_type"] == BannerType.SELECTION
            assert call_args["css_class"] == "selection-banner"

    def test_show_selection_banner_single(self, banner_service):
        """Test showing selection banner with count = 1."""
        callback = MagicMock()

        with patch.object(banner_service, "_show_banner") as mock_show:
            banner_service.show_selection_banner(1, callback)

            call_args = mock_show.call_args[1]
            assert "1 wallpaper selected" in call_args["title"]

    def test_show_selection_banner_zero_hides(self, banner_service):
        """Test that count = 0 hides selection banner."""
        with patch.object(banner_service, "hide_selection_banner") as mock_hide:
            banner_service.show_selection_banner(0, MagicMock())
            mock_hide.assert_called_once()

    def test_show_selection_banner_negative_hides(self, banner_service):
        """Test that count < 0 hides selection banner."""
        with patch.object(banner_service, "hide_selection_banner") as mock_hide:
            banner_service.show_selection_banner(-1, MagicMock())
            mock_hide.assert_called_once()


class TestShowStorageWarning:
    """Tests for storage warning banner."""

    def test_show_storage_warning(self, banner_service):
        """Test showing storage warning."""
        callback = MagicMock()

        with patch.object(banner_service, "_show_banner") as mock_show:
            banner_service.show_storage_warning(450, 500, callback)

            mock_show.assert_called_once()
            call_args = mock_show.call_args[1]

            assert "Storage space low" in call_args["title"]
            assert "450 MB / 500 MB" in call_args["title"]
            assert call_args["button_text"] == "Clear Cache"
            assert call_args["callback"] == callback
            assert call_args["priority"] == BannerPriority.HIGH
            assert call_args["banner_type"] == BannerType.STORAGE
            assert call_args["css_class"] == "warning-banner"


class TestShowApiWarning:
    """Tests for API warning banner."""

    def test_show_api_warning_with_button(self, banner_service):
        """Test showing API warning with button."""
        callback = MagicMock()

        with patch.object(banner_service, "_show_banner") as mock_show:
            banner_service.show_api_warning(
                "Rate limit approaching",
                "Upgrade Account",
                callback,
            )

            mock_show.assert_called_once()
            call_args = mock_show.call_args[1]

            assert call_args["title"] == "Rate limit approaching"
            assert call_args["button_text"] == "Upgrade Account"
            assert call_args["callback"] == callback
            assert call_args["priority"] == BannerPriority.MEDIUM
            assert call_args["banner_type"] == BannerType.API
            assert call_args["css_class"] == "warning-banner"

    def test_show_api_warning_without_button(self, banner_service):
        """Test showing API warning without button."""
        with patch.object(banner_service, "_show_banner") as mock_show:
            banner_service.show_api_warning("Rate limit approaching")

            call_args = mock_show.call_args[1]

            assert call_args["title"] == "Rate limit approaching"
            assert call_args["button_text"] is None
            assert call_args["callback"] is None


class TestShowInfoBanner:
    """Tests for info banner."""

    def test_show_info_banner_with_button(self, banner_service):
        """Test showing info banner with button."""
        callback = MagicMock()

        with patch.object(banner_service, "_show_banner") as mock_show:
            banner_service.show_info_banner("Update available", "Update Now", callback)

            call_args = mock_show.call_args[1]

            assert call_args["title"] == "Update available"
            assert call_args["button_text"] == "Update Now"
            assert call_args["callback"] == callback
            assert call_args["priority"] == BannerPriority.LOW
            assert call_args["banner_type"] == BannerType.INFO
            assert call_args["css_class"] == "info-banner"

    def test_show_info_banner_without_button(self, banner_service):
        """Test showing info banner without button."""
        with patch.object(banner_service, "_show_banner") as mock_show:
            banner_service.show_info_banner("Settings saved")

            call_args = mock_show.call_args[1]

            assert call_args["title"] == "Settings saved"
            assert call_args["button_text"] is None
            assert call_args["callback"] is None


class TestClearBanner:
    """Tests for clearing banners."""

    def test_clear_banner_when_visible(self, banner_service):
        """Test clearing banner when visible."""
        banner_service.is_visible = True

        with patch.object(banner_service, "_clear_current_banner") as mock_clear:
            with patch.object(banner_service, "_process_next_banner") as mock_process:
                banner_service.clear_banner()

                mock_clear.assert_called_once()
                mock_process.assert_called_once()

    def test_clear_banner_when_not_visible(self, banner_service):
        """Test clearing banner when not visible."""
        banner_service.is_visible = False

        with patch.object(banner_service, "_clear_current_banner") as mock_clear:
            banner_service.clear_banner()

            mock_clear.assert_not_called()


class TestHideSelectionBanner:
    """Tests for hiding selection banner."""

    def test_hide_selection_banner_in_queue(self, banner_service):
        """Test hiding selection banner when in queue."""
        banner_service._banner_queue = [
            {
                "title": "Test",
                "button_text": None,
                "callback": None,
                "priority": BannerPriority.MEDIUM,
                "type": BannerType.SELECTION,
                "css_class": None,
            }
        ]

        banner_service.hide_selection_banner()

        assert len(banner_service._banner_queue) == 0

    def test_hide_selection_banner_current(self, banner_service):
        """Test hiding selection banner when currently visible."""
        banner_service.current_banner_type = BannerType.SELECTION
        banner_service.is_visible = True

        with patch.object(banner_service, "clear_banner") as mock_clear:
            banner_service.hide_selection_banner()

            mock_clear.assert_called_once()


class TestPriorityQueue:
    """Tests for priority queue management."""

    def test_add_to_queue_by_priority(self, banner_service):
        """Test that banners are added in priority order."""
        entry_low = {
            "title": "Low",
            "button_text": None,
            "callback": None,
            "priority": BannerPriority.LOW,
            "type": BannerType.INFO,
            "css_class": None,
        }
        entry_high = {
            "title": "High",
            "button_text": None,
            "callback": None,
            "priority": BannerPriority.HIGH,
            "type": BannerType.STORAGE,
            "css_class": None,
        }

        banner_service._add_to_queue(entry_low)
        banner_service._add_to_queue(entry_high)

        assert banner_service._banner_queue[0]["priority"] == BannerPriority.HIGH
        assert banner_service._banner_queue[1]["priority"] == BannerPriority.LOW

    def test_remove_from_queue_by_type(self, banner_service):
        """Test removing banners of specific type."""
        entry1 = {
            "title": "Selection",
            "button_text": None,
            "callback": None,
            "priority": BannerPriority.MEDIUM,
            "type": BannerType.SELECTION,
            "css_class": None,
        }
        entry2 = {
            "title": "Info",
            "button_text": None,
            "callback": None,
            "priority": BannerPriority.LOW,
            "type": BannerType.INFO,
            "css_class": None,
        }

        banner_service._banner_queue = [entry1, entry2]
        banner_service._remove_from_queue_by_type(BannerType.SELECTION)

        assert len(banner_service._banner_queue) == 1
        assert banner_service._banner_queue[0]["type"] == BannerType.INFO

    def test_replace_banner_of_same_type(self, banner_service):
        """Test that new banner replaces existing banner of same type."""
        entry1 = {
            "title": "Selection 1",
            "button_text": None,
            "callback": None,
            "priority": BannerPriority.MEDIUM,
            "type": BannerType.SELECTION,
            "css_class": None,
        }
        entry2 = {
            "title": "Selection 2",
            "button_text": None,
            "callback": None,
            "priority": BannerPriority.MEDIUM,
            "type": BannerType.SELECTION,
            "css_class": None,
        }

        banner_service._add_to_queue(entry1)
        banner_service._add_to_queue(entry2)

        assert len(banner_service._banner_queue) == 1
        assert banner_service._banner_queue[0]["title"] == "Selection 2"


class TestAutoDismiss:
    """Tests for auto-dismiss functionality."""

    def test_info_banner_auto_dismiss_scheduled(self, banner_service):
        """Test that info banners schedule auto-dismiss."""
        entry = {
            "title": "Info",
            "button_text": None,
            "callback": None,
            "priority": BannerPriority.LOW,
            "type": BannerType.INFO,
            "css_class": "info-banner",
        }

        with patch.object(banner_service, "_schedule_auto_dismiss") as mock_schedule:
            with patch.object(banner_service, "_apply_css_class"):
                with patch.object(banner_service, "_cancel_auto_dismiss"):
                    banner_service._display_banner_entry(entry)

                    mock_schedule.assert_called_once_with(10)


class TestCleanup:
    """Tests for cleanup operations."""

    def test_cleanup_clears_all(self, banner_service):
        """Test that cleanup clears all state."""
        banner_service._banner_queue = [{"test": "entry"}]
        banner_service._dismiss_timeout = 12345
        banner_service.is_visible = True

        banner_service.cleanup()

        assert len(banner_service._banner_queue) == 0
        assert banner_service._dismiss_timeout is None
        assert not banner_service.is_visible


class TestGetBannerWidget:
    """Tests for getting banner widget."""

    def test_get_banner_widget(self, banner_service):
        """Test getting banner widget."""
        widget = banner_service.get_banner_widget()
        assert widget == banner_service.banner_container
