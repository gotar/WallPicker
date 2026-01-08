"""Base ViewModel for UI state management."""

import sys
from pathlib import Path

import gi

gi.require_version("GObject", "2.0")
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gi.repository import GObject  # noqa: E402


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

    def clear_error(self) -> None:
        """Clear error message."""
        self.error_message = None

    def _update_selection_state(self) -> None:
        self.selected_wallpapers = self._selected_wallpapers_list
        self.selected_count = len(self._selected_wallpapers_list)
        self.selection_mode = self.selected_count > 0

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
