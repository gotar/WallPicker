"""Toast Service for native Adw.Toast notifications."""

from collections.abc import Callable

from gi.repository import Adw, GLib, GObject

# Toast timeout (seconds) per message kind
_TOAST_TIMEOUTS = {
    "success": 4,
    "error": 6,
    "info": 3,
    "warning": 5,
}


class ToastService(GObject.Object):
    """Service for showing native Adw.Toast notifications.

    All toasts are marshalled to the GTK main thread via GLib.idle_add so
    they are safe to call from coroutines running on the asyncio thread.
    """

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.overlay = Adw.ToastOverlay()
        # Don't set content here - let the caller do it after UI is created

    def wrap_content(self, content):
        """Wrap the given content widget with the toast overlay."""
        self.overlay.set_child(content)
        self.window.set_content(self.overlay)

    def _show_toast_idle(
        self,
        kind: str,
        message: str,
        button_label: str | None = None,
        callback: Callable[[], None] | None = None,
    ) -> bool:
        """Build and add the toast. Must run on the GTK main thread."""
        toast = Adw.Toast(title=message)
        toast.set_timeout(_TOAST_TIMEOUTS.get(kind, 3))

        if kind in ("error", "warning"):
            toast.set_priority(Adw.ToastPriority.HIGH)

        if button_label and callback:
            toast.set_button_label(button_label)
            toast.connect("button-clicked", lambda _toast: callback())

        self.overlay.add_toast(toast)
        return False

    def show_success(self, message: str, undo_callback=None):
        """Show success toast with optional undo button."""
        GLib.idle_add(
            self._show_toast_idle, "success", message, "Undo", undo_callback
        )

    def show_error(self, message: str, detail_callback=None):
        """Show error toast with optional details button."""
        GLib.idle_add(
            self._show_toast_idle, "error", message, "View Details", detail_callback
        )

    def show_info(self, message: str):
        """Show informational toast."""
        GLib.idle_add(self._show_toast_idle, "info", message)

    def show_warning(self, message: str):
        """Show warning toast."""
        GLib.idle_add(self._show_toast_idle, "warning", message)
