"""Tests for BaseViewModel."""

from pathlib import Path

import pytest
from gi.repository import Gdk, GObject
from pytest_mock import MockerFixture

from ui.view_models.base import BaseViewModel


class MockBaseViewModel(BaseViewModel):
    """Mock ViewModel for testing BaseViewModel."""

    def __init__(self):
        super().__init__()


class TestBaseViewModelInit:
    """Test BaseViewModel initialization."""

    def test_init_creates_properties(self):
        """Test initialization creates default properties."""
        vm = MockBaseViewModel()

        assert hasattr(vm, "is_busy")
        assert vm.is_busy is False

    def test_init_creates_executor(self):
        """Test initialization creates thread pool executor."""
        vm = MockBaseViewModel()

        assert hasattr(vm, "_executor")
        assert vm._executor is not None


class TestIsBusyProperty:
    """Test is_busy property."""

    def test_is_busy_default_false(self):
        """Test is_busy property defaults to False."""
        vm = MockBaseViewModel()

        assert vm.is_busy is False

    def test_set_is_busy_true(self):
        """Test setting is_busy to True."""
        vm = MockBaseViewModel()

        vm.is_busy = True
        assert vm.is_busy is True

    def test_set_is_busy_false(self):
        """Test setting is_busy to False."""
        vm = MockBaseViewModel()

        vm.is_busy = True
        vm.is_busy = False
        assert vm.is_busy is False


class TestErrorMessageProperty:
    """Test error_message property."""

    def test_error_message_default_none(self):
        """Test error_message property defaults to None."""
        vm = MockBaseViewModel()

        # GObject.Property with default=None returns None initially
        assert vm.error_message is None or vm.error_message == ""

    def test_set_error_message(self):
        """Test setting error_message."""
        vm = MockBaseViewModel()

        vm.error_message = "Test error"
        assert vm.error_message == "Test error"


class TestBindProperty:
    """Test bind_property method."""

    def test_bind_property_creates_binding(self, mocker: MockerFixture):
        """Test bind_property creates GObject binding."""
        vm = MockBaseViewModel()
        mock_widget = mocker.Mock()
        mock_bind = mocker.patch.object(
            GObject.Object,
            "bind_property",
            return_value=mocker.Mock(),
        )

        binding = vm.bind_property("is_busy", mock_widget, "visible")

        assert binding is not None
        mock_bind.assert_called_once_with(
            vm, "is_busy", mock_widget, "visible", GObject.BindingFlags.DEFAULT
        )


class TestEmitPropertyChanged:
    """Test emit_property_changed method."""

    def test_emit_property_changed(self, mocker: MockerFixture):
        """Test emit_property_changed emits notify signal."""
        vm = MockBaseViewModel()
        mock_notify = mocker.patch.object(vm, "notify", autospec=True)

        vm.emit_property_changed("is_busy")

        mock_notify.assert_called_once_with("is_busy")


class TestClearError:
    """Test clear_error method."""

    def test_clear_error_sets_error_message_to_none(self):
        """Test clear_error sets error_message to None."""
        vm = MockBaseViewModel()

        vm.error_message = "Test error"
        vm.clear_error()

        assert vm.error_message is None


class TestCleanup:
    """Test cleanup methods."""

    def test_del_shutdowns_executor(self, mocker: MockerFixture):
        """Test __del__ shuts down executor."""
        vm = MockBaseViewModel()
        mock_shutdown = mocker.patch.object(vm._executor, "shutdown")

        # Trigger __del__
        vm.__del__()

        mock_shutdown.assert_called_once_with(wait=False)


class TestIntegrationBaseViewModel:
    """Integration tests for BaseViewModel."""

    @pytest.mark.integration
    def test_full_error_workflow(self):
        """Test complete error workflow: set → clear."""
        vm = MockBaseViewModel()

        # Initially no error (None or empty string per GObject default)
        initial_error = vm.error_message
        assert initial_error is None or initial_error == ""

        # Set error
        vm.error_message = "Test error"
        assert vm.error_message == "Test error"

        # Clear error
        vm.clear_error()
        # After clear, should be None or empty string
        assert vm.error_message is None or vm.error_message == ""

    @pytest.mark.integration
    def test_busy_workflow(self):
        """Test busy state workflow."""
        vm = MockBaseViewModel()

        # Initially not busy
        assert vm.is_busy is False

        # Set busy
        vm.is_busy = True
        assert vm.is_busy is True

        # Clear busy
        vm.is_busy = False
        assert vm.is_busy is False
