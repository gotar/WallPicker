"""Base ViewModel for UI state management."""

import sys
from pathlib import Path

import gi

gi.require_version("GObject", "2.0")
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gi.repository import GLib, GObject  # noqa: E402


class BaseViewModel(GObject.Object):
    """Base ViewModel with observable state"""

    __gtype_name__ = "BaseViewModel"

    __gsignals__ = {
        "wallpaper-set": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    is_busy = GObject.Property(type=bool, default=False)
    error_message = GObject.Property(type=str, default=None)
    selection_mode = GObject.Property(type=bool, default=False)
    selected_count = GObject.Property(type=int, default=0)
    selected_wallpapers = GObject.Property(type=object)

    def __init__(self) -> None:
        super().__init__()
        self._is_busy = False
        self._error_message: str | None = None
        self._selected_wallpapers_list = []
        # Depth counter for concurrent operations sharing the is_busy spinner
        self._busy_depth = 0

    def bind_property(
        self,
        prop_name: str,
        widget,
        widget_prop: str,
        flags=GObject.BindingFlags.DEFAULT,
    ) -> GObject.Binding:
        """Bind ViewModel property to widget property.

        Args:
            prop_name: ViewModel property name
            widget: Target widget
            widget_prop: Widget property name
            flags: GObject binding flags

        Returns:
            GObject.Binding object
        """
        return GObject.Object.bind_property(self, prop_name, widget, widget_prop, flags)

    def emit_property_changed(self, prop_name: str) -> None:
        """Emit notify signal for property change.

        Args:
            prop_name: Name of property that changed
        """
        self.notify(prop_name)

    # ------------------------------------------------------------------
    # Thread-safe helpers.
    #
    # Coroutines run on a background asyncio thread (see
    # core.asyncio_integration); GTK/GObject state must only be touched on
    # the GTK main thread, so all property writes, notify() calls and signal
    # emissions from coroutines must go through these helpers.
    # ------------------------------------------------------------------

    def _set_property_idle(self, prop_name: str, value) -> None:
        """Set a GObject property on the GTK main thread (thread-safe).

        Args:
            prop_name: Name of the property to set
            value: Value to assign
        """
        GLib.idle_add(self._apply_property_idle, prop_name, value)

    def _apply_property_idle(self, prop_name: str, value) -> bool:
        setattr(self, prop_name, value)
        return False

    def _notify_idle(self, prop_name: str) -> None:
        """Emit a property notify signal on the GTK main thread (thread-safe).

        Args:
            prop_name: Name of the property that changed
        """
        GLib.idle_add(self._apply_notify_idle, prop_name)

    def _apply_notify_idle(self, prop_name: str) -> bool:
        self.notify(prop_name)
        return False

    def _push_busy(self) -> None:
        """Increment busy depth and mark the ViewModel busy (thread-safe).

        Nested operations must not clear the spinner when an inner one
        finishes first, so a bare True/False toggle is not enough.
        """
        self._busy_depth += 1
        if self._busy_depth == 1:
            self._set_property_idle("is_busy", True)

    def _pop_busy(self) -> None:
        """Decrement busy depth; clear is_busy only at depth zero."""
        if self._busy_depth > 0:
            self._busy_depth -= 1
        if self._busy_depth == 0:
            self._set_property_idle("is_busy", False)

    def _emit_idle(self, signal_name: str, *args) -> None:
        """Emit a GObject signal on the GTK main thread (thread-safe).

        Args:
            signal_name: Name of the signal to emit
            *args: Signal arguments
        """
        GLib.idle_add(self._apply_emit_idle, signal_name, *args)

    def _apply_emit_idle(self, signal_name: str, *args) -> bool:
        self.emit(signal_name, *args)
        return False

    def clear_error(self) -> None:
        """Clear error message."""
        self.error_message = None

    def _update_selection_state(self) -> None:
        self.selected_wallpapers = self._selected_wallpapers_list
        self.selected_count = len(self._selected_wallpapers_list)
        self.selection_mode = self.selected_count > 0

    def prune_selection(self, valid_wallpapers: list) -> None:
        """Drop selection entries that are no longer present in a wallpaper
        list so selected_count can never exceed visible items (L10).

        Args:
            valid_wallpapers: The wallpapers that still exist.
        """
        self._selected_wallpapers_list = [
            w for w in self._selected_wallpapers_list if w in valid_wallpapers
        ]
        self._update_selection_state()

    def toggle_selection(self, wallpaper) -> None:
        """Toggle wallpaper selection."""
        if wallpaper in self._selected_wallpapers_list:
            self._selected_wallpapers_list.remove(wallpaper)
        else:
            self._selected_wallpapers_list.append(wallpaper)
        self._update_selection_state()

    def select_all(self) -> None:
        """Select all wallpapers."""
        # Subclasses should override this with their wallpaper list
        pass

    def deselect_all(self) -> None:
        """Deselect all wallpapers."""
        self._selected_wallpapers_list.clear()
        self._update_selection_state()

    def clear_selection(self) -> None:
        """Clear selection and exit selection mode."""
        self.deselect_all()
        self.selection_mode = False

    def get_selected_wallpapers(self) -> list:
        """Get list of selected wallpapers."""
        return self._selected_wallpapers_list.copy()
