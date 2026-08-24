"""Tests for BaseViewModel."""

import pytest
from gi.repository import GObject
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

    def test_init_creates_instance(self):
        """Test initialization creates instance successfully."""
        vm = MockBaseViewModel()

        assert vm is not None
        assert isinstance(vm, BaseViewModel)


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

    def test_del_cleanup(self):
        """Test cleanup leaves the ViewModel in a consistent state."""
        vm = MockBaseViewModel()

        # BaseViewModel defines no __del__ of its own; triggering garbage
        # collection of an instance must not raise and must not corrupt state.
        vm.__del__() if hasattr(vm, "__del__") else None

        assert isinstance(vm, BaseViewModel)
        assert vm.is_busy is False


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


class TestThreadSafeHelpers:
    """Test thread-safe idle helpers (C1: GTK main-thread marshalling)."""

    def test_set_property_idle_dispatches_via_idle_add(self, mocker: MockerFixture):
        """_set_property_idle schedules the write through GLib.idle_add."""
        idle_add = mocker.patch(
            "ui.view_models.base.GLib.idle_add",
            side_effect=lambda func, *args: func(*args),
        )
        vm = MockBaseViewModel()

        vm._set_property_idle("is_busy", True)

        idle_add.assert_called_once()
        assert vm.is_busy is True

    def test_notify_idle_dispatches_via_idle_add(self, mocker: MockerFixture):
        """_notify_idle emits the notify signal on the main thread."""
        idle_add = mocker.patch(
            "ui.view_models.base.GLib.idle_add",
            side_effect=lambda func, *args: func(*args),
        )
        vm = MockBaseViewModel()
        notify_spy = mocker.patch.object(vm, "notify")

        vm._notify_idle("is_busy")

        idle_add.assert_called_once()
        notify_spy.assert_called_once_with("is_busy")

    def test_emit_idle_dispatches_via_idle_add(self, mocker: MockerFixture):
        """_emit_idle emits signals on the main thread."""
        idle_add = mocker.patch(
            "ui.view_models.base.GLib.idle_add",
            side_effect=lambda func, *args: func(*args),
        )
        vm = MockBaseViewModel()
        received = []
        vm.connect("wallpaper-set", lambda _o, path: received.append(path))

        vm._emit_idle("wallpaper-set", "/tmp/wall.jpg")

        idle_add.assert_called_once()
        assert received == ["/tmp/wall.jpg"]

    def test_emit_idle_passes_multiple_args(self, mocker: MockerFixture):
        """_emit_idle forwards all signal arguments unchanged."""
        mocker.patch(
            "ui.view_models.base.GLib.idle_add",
            side_effect=lambda func, *args: func(*args),
        )

        class MultiSignalViewModel(BaseViewModel):
            __gsignals__ = {
                "multi": (GObject.SignalFlags.RUN_FIRST, None, (bool, str, str)),
            }

        vm = MultiSignalViewModel()
        received = []
        vm.connect(
            "multi", lambda _o, a, b, c: received.extend([a, b, c])
        )

        vm._emit_idle("multi", True, "msg", "/path")

        assert received == [True, "msg", "/path"]


class TestBusyDepth:
    """Test busy depth counter (M17)."""

    def test_push_busy_sets_is_busy_once(self, mocker: MockerFixture):
        """First _push_busy marks the VM busy; nested pushes keep it busy."""
        mocker.patch(
            "ui.view_models.base.GLib.idle_add",
            side_effect=lambda func, *args: func(*args),
        )
        vm = MockBaseViewModel()

        vm._push_busy()
        assert vm.is_busy is True

        vm._push_busy()
        assert vm.is_busy is True

    def test_pop_busy_clears_only_at_depth_zero(self, mocker: MockerFixture):
        """Nested operations must not clear the spinner early (M17)."""
        mocker.patch(
            "ui.view_models.base.GLib.idle_add",
            side_effect=lambda func, *args: func(*args),
        )
        vm = MockBaseViewModel()

        vm._push_busy()
        vm._push_busy()

        vm._pop_busy()
        assert vm.is_busy is True

        vm._pop_busy()
        assert vm.is_busy is False

    def test_pop_busy_never_goes_negative(self, mocker: MockerFixture):
        """Unbalanced _pop_busy must not corrupt the counter."""
        mocker.patch(
            "ui.view_models.base.GLib.idle_add",
            side_effect=lambda func, *args: func(*args),
        )
        vm = MockBaseViewModel()

        vm._pop_busy()
        assert vm._busy_depth == 0
        assert vm.is_busy is False
