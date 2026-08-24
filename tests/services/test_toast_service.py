"""Tests for ToastService main-thread marshalling (C1)."""

from unittest.mock import MagicMock

import pytest

from services.toast_service import ToastService


@pytest.fixture
def toast_service(mocker):
    """Create ToastService with a mocked overlay and immediate idle_add."""
    idle_add = mocker.patch(
        "services.toast_service.GLib.idle_add",
        side_effect=lambda func, *args: func(*args),
    )
    mocker.patch("services.toast_service.Adw.ToastOverlay")
    service = ToastService(MagicMock())
    service.overlay = MagicMock()
    service._idle_add = idle_add
    return service


class TestMainThreadMarshalling:
    def test_show_info_schedules_via_idle_add(self, toast_service):
        toast_service.show_info("hello")

        assert toast_service._idle_add.called

    @pytest.mark.parametrize(
        "method,args",
        [
            ("show_success", ("great",)),
            ("show_error", ("bad",)),
            ("show_warning", ("careful",)),
            ("show_info", ("fyi",)),
        ],
    )
    def test_all_show_methods_marshall_to_main_thread(
        self, toast_service, method, args
    ):
        getattr(toast_service, method)(*args)

        assert toast_service._idle_add.called

    def test_toast_added_to_overlay_with_priority_for_errors(self, toast_service):
        from gi.repository import Adw

        toast_mock = MagicMock()

        # Build the toast inside the idle callback with a mock Adw.Toast
        import services.toast_service as ts_module

        original_toast_cls = ts_module.Adw.Toast
        ts_module.Adw.Toast = MagicMock(return_value=toast_mock)
        try:
            toast_service.show_error("boom")
        finally:
            ts_module.Adw.Toast = original_toast_cls

        toast_mock.set_timeout.assert_called_once()
        toast_mock.set_priority.assert_called_once_with(Adw.ToastPriority.HIGH)
        toast_service.overlay.add_toast.assert_called_once_with(toast_mock)

    def test_success_callback_wiring(self, toast_service):
        import services.toast_service as ts_module

        toast_mock = MagicMock()
        original_toast_cls = ts_module.Adw.Toast
        ts_module.Adw.Toast = MagicMock(return_value=toast_mock)
        try:
            calls = []
            toast_service.show_success("done", undo_callback=lambda: calls.append(1))
        finally:
            ts_module.Adw.Toast = original_toast_cls

        toast_mock.set_button_label.assert_called_once_with("Undo")
        # Simulate the button click signal
        handler = toast_mock.connect.call_args[0][1]
        handler(toast_mock)
        assert calls == [1]
