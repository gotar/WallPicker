"""Tests for NotificationService."""

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from services.notification_service import NotificationService


class TestNotificationServiceInit:
    """Test NotificationService initialization."""

    def test_init_default_enabled(self):
        """Test initialization with default enabled=True."""
        service = NotificationService()
        assert service.enabled is True

    def test_init_disabled(self):
        """Test initialization with enabled=False."""
        service = NotificationService(enabled=False)
        assert service.enabled is False


class TestNotificationServiceEnabled:
    """Test enabled property."""

    def test_enabled_getter(self):
        """Test getting enabled state."""
        service = NotificationService(enabled=True)
        assert service.enabled is True

    def test_enabled_setter(self):
        """Test setting enabled state."""
        service = NotificationService(enabled=True)
        service.enabled = False
        assert service.enabled is False


class TestNotify:
    """Test notify method."""

    def test_notify_disabled(self):
        """Test notify when disabled returns False."""
        service = NotificationService(enabled=False)
        result = service.notify("Test", "Test message")
        assert result is False

    @pytest.mark.integration
    def test_notify_success(self, mocker: MockerFixture):
        """Test successful notification."""
        service = NotificationService(enabled=True)
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = None

        result = service.notify("Test Title", "Test message", "test-icon")

        assert result is True
        mock_run.assert_called_once_with(
            ["notify-send", "-i", "test-icon", "Test Title", "Test message"],
            check=False,
            capture_output=True,
        )

    @pytest.mark.integration
    def test_notify_file_not_found(self, mocker: MockerFixture):
        """Test notify when notify-send not found."""
        service = NotificationService(enabled=True)
        mock_run = mocker.patch("subprocess.run", side_effect=FileNotFoundError)

        result = service.notify("Test", "Test message")

        assert result is False

    @pytest.mark.integration
    def test_notify_generic_exception(self, mocker: MockerFixture):
        """Test notify when generic exception occurs."""
        service = NotificationService(enabled=True)
        mock_run = mocker.patch("subprocess.run", side_effect=Exception("Test error"))

        result = service.notify("Test", "Test message")

        assert result is False


class TestNotifyHelpers:
    """Test helper notification methods."""

    @pytest.mark.integration
    def test_notify_success_helper(self, mocker: MockerFixture):
        """Test notify_success helper."""
        service = NotificationService(enabled=True)
        mock_notify = mocker.patch.object(service, "notify", return_value=True)

        result = service.notify_success("Success message")

        assert result is True
        mock_notify.assert_called_once_with("Wallpicker", "Success message", "emblem-ok-symbolic")

    @pytest.mark.integration
    def test_notify_error_helper(self, mocker: MockerFixture):
        """Test notify_error helper."""
        service = NotificationService(enabled=True)
        mock_notify = mocker.patch.object(service, "notify", return_value=True)

        result = service.notify_error("Error message")

        assert result is True
        mock_notify.assert_called_once_with("Wallpicker", "Error message", "dialog-error-symbolic")

    @pytest.mark.integration
    def test_notify_info_helper(self, mocker: MockerFixture):
        """Test notify_info helper."""
        service = NotificationService(enabled=True)
        mock_notify = mocker.patch.object(service, "notify", return_value=True)

        result = service.notify_info("Info message")

        assert result is True
        mock_notify.assert_called_once_with(
            "Wallpicker", "Info message", "dialog-information-symbolic"
        )
