"""Banner Service for managing Adw.Banner notifications."""

from enum import IntEnum, auto
from typing import Callable, Optional
from gi.repository import Adw, GObject, GLib


class BannerPriority(IntEnum):
    """Priority levels for banner queue management."""

    LOW = auto()  # Info banners
    MEDIUM = auto()  # API warnings, selection banners
    HIGH = auto()  # Storage warnings


class BannerType(str):
    """Banner type identifiers."""

    SELECTION = "selection"
    STORAGE = "storage"
    API = "api"
    INFO = "info"


class BannerService(GObject.Object):
    """Service for managing Adw.Banner notifications.

    Supports priority-based banner queue management with automatic
    dismissal and integration with Adw.ToolbarView layout.
    """

    # GObject properties
    current_banner_type = GObject.Property(type=str, default="")
    is_visible = GObject.Property(type=bool, default=False)

    def __init__(self, window: Adw.ApplicationWindow):
        """Initialize BannerService with window reference.

        Args:
            window: The main application window for banner attachment
        """
        super().__init__()
        self.window = window

        # Banner container (will be inserted into ToolbarView)
        self.banner_container = Adw.Banner()
        self.banner_container.set_revealed(False)
        self.banner_container.set_button_label(None)
        self._current_callback = None
        self._current_banner = None
        self.current_banner_type = None
        self.is_visible = False

    def _apply_css_class(self, css_class: Optional[str]) -> None:
        """Apply CSS class to banner.

        Args:
            css_class: CSS class name or None
        """
        # Clear existing custom classes
        context = self.banner_container.get_style_context()
        context.remove_class("warning-banner")
        context.remove_class("info-banner")
        context.remove_class("selection-banner")

        # Apply new class
        if css_class:
            context.add_class(css_class)

    def _schedule_auto_dismiss(self, seconds: int) -> None:
        """Schedule automatic banner dismissal.

        Args:
            seconds: Seconds before dismissal
        """
        self._dismiss_timeout = GLib.timeout_add_seconds(seconds, self._on_auto_dismiss_timeout)

    def _cancel_auto_dismiss(self) -> None:
        """Cancel scheduled auto-dismiss."""
        if self._dismiss_timeout:
            GLib.source_remove(self._dismiss_timeout)
            self._dismiss_timeout = None

    def _on_auto_dismiss_timeout(self) -> bool:
        """Handle auto-dismiss timeout.

        Returns:
            False to indicate timeout should not repeat
        """
        self.clear_banner()
        return False

    def show_selection_banner(self, count: int, on_set_all: Callable) -> None:
        """Show multi-selection banner.

        Args:
            count: Number of selected wallpapers
            on_set_all: Callback for "Set All" button
        """
        if count <= 0:
            self.hide_selection_banner()
            return

        title = f"{count} wallpaper{'s' if count > 1 else ''} selected"

        self._show_banner(
            title=title,
            button_text="Set All",
            callback=on_set_all,
            priority=BannerPriority.MEDIUM,
            banner_type=BannerType.SELECTION,
            css_class="selection-banner",
        )

    def show_storage_warning(self, used_mb: int, limit_mb: int, on_clear_cache: Callable) -> None:
        """Show storage warning banner.

        Args:
            used_mb: Current cache usage in MB
            limit_mb: Cache limit in MB (typically 500)
            on_clear_cache: Callback for "Clear Cache" button
        """
        title = f"Storage space low ({used_mb} MB / {limit_mb} MB)"

        self._show_banner(
            title=title,
            button_text="Clear Cache",
            callback=on_clear_cache,
            priority=BannerPriority.HIGH,
            banner_type=BannerType.STORAGE,
            css_class="warning-banner",
        )

    def show_api_warning(
        self,
        message: str,
        button_text: Optional[str] = None,
        on_button_click: Optional[Callable] = None,
    ) -> None:
        """Show API quota warning.

        Args:
            message: Warning message
            button_text: Optional button label
            on_button_click: Optional button callback
        """
        self._show_banner(
            title=message,
            button_text=button_text,
            callback=on_button_click,
            priority=BannerPriority.MEDIUM,
            banner_type=BannerType.API,
            css_class="warning-banner",
        )

    def show_info_banner(
        self,
        message: str,
        button_text: Optional[str] = None,
        on_button_click: Optional[Callable] = None,
    ) -> None:
        """Show informational banner.

        Args:
            message: Informational message
            button_text: Optional button label
            on_button_click: Optional button callback
        """
        self._show_banner(
            title=message,
            button_text=button_text,
            callback=on_button_click,
            priority=BannerPriority.LOW,
            banner_type=BannerType.INFO,
            css_class="info-banner",
        )

    def clear_banner(self) -> None:
        """Hide/dismiss current banner."""
        if not self.is_visible:
            return

        self._clear_current_banner()
        self._process_next_banner()

    def hide_selection_banner(self) -> None:
        """Hide multi-selection banner specifically."""
        # Remove from queue if pending
        self._remove_from_queue_by_type(BannerType.SELECTION)

        # Clear if currently visible
        if self.current_banner_type == BannerType.SELECTION:
            self.clear_banner()

    def get_banner_widget(self) -> Adw.Banner:
        """Get the Adw.Banner widget for window layout integration.

        Returns:
            The Adw.Banner widget to be inserted into ToolbarView
        """
        return self.banner_container

    def cleanup(self) -> None:
        """Clean up banner resources on window close."""
        self._cancel_auto_dismiss()
        self._clear_current_banner()
        self._banner_queue.clear()

    @property
    def logger(self):
        """Get logger instance (compatibility with BaseService)."""
        import logging

        return logging.getLogger(self.__class__.__name__)
