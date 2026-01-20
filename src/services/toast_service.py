"""Toast Service for native Adw.Toast notifications."""

from gi.repository import Adw, GObject


class ToastService(GObject.Object):
    """Service for showing native Adw.Toast notifications."""

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.overlay = Adw.ToastOverlay()
        # Don't set content here - let the caller do it after UI is created

    def wrap_content(self, content):
        """Wrap the given content widget with the toast overlay."""
        self.overlay.set_child(content)
        self.window.set_content(self.overlay)

    def show_success(self, message: str, undo_callback=None):
        """Show success toast with optional undo button."""
        toast = Adw.Toast(title=message)
        toast.set_timeout(4)

        if undo_callback:
            toast.set_button_label("Undo")
            toast.connect("button-clicked", lambda _: undo_callback())

        self.overlay.add_toast(toast)

    def show_error(self, message: str, detail_callback=None):
        """Show error toast with optional details button."""
        toast = Adw.Toast(title=message)
        toast.set_timeout(6)
        toast.set_priority(Adw.ToastPriority.HIGH)

        if detail_callback:
            toast.set_button_label("View Details")
            toast.connect("button-clicked", lambda _: detail_callback())

        self.overlay.add_toast(toast)

    def show_info(self, message: str):
        """Show informational toast."""
        toast = Adw.Toast(title=message)
        toast.set_timeout(3)
        self.overlay.add_toast(toast)

    def show_warning(self, message: str):
        """Show warning toast."""
        toast = Adw.Toast(title=message)
        toast.set_timeout(5)
        toast.set_priority(Adw.ToastPriority.HIGH)
        self.overlay.add_toast(toast)
