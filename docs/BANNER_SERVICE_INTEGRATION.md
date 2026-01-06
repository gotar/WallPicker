"""BannerService Integration Example

This document shows how to integrate BannerService into the Wallpicker
application's main window.
"""

# 1. IMPORT BannerService in main_window.py
# --------------------------------------------------
from services.banner_service import BannerService


# 2. INITIALIZE BannerService in WallPickerWindow.__init__
# --------------------------------------------------
class WallPickerWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        application,
        local_view_model,
        favorites_view_model,
        wallhaven_view_model,
    ):
        super().__init__(application=application)
        self.set_default_size(1200, 800)

        # ... existing initialization ...

        # Create BannerService
        self.banner_service = BannerService(self)

        self._create_ui()


# 3. INSERT banner widget into ToolbarView in _create_ui()
# --------------------------------------------------
def _create_ui(self):
    """Create main UI with Adw.ToolbarView layout."""
    # Create Toast Service
    self.toast_service = ToastService(self)

    # Create ToolbarView
    self.toolbar_view = Adw.ToolbarView()

    # Create HeaderBar
    self.header = Adw.HeaderBar()
    self.toolbar_view.add_top_bar(self.header)

    # ... header setup ...

    # ADD BANNER HERE - below header bar, above content
    banner_widget = self.banner_service.get_banner_widget()
    self.toolbar_view.add_top_bar(banner_widget)

    # View stack for tabs
    self.stack = Adw.ViewStack()
    self.stack.set_hexpand(True)
    self.stack.set_vexpand(True)

    # ... view setup ...

    # View switcher bar
    self.view_switcher_bar = Adw.ViewSwitcherBar()
    self.view_switcher_bar.set_stack(self.stack)
    self.toolbar_view.add_bottom_bar(self.view_switcher_bar)

    # Add stack to toolbar view content
    self.toolbar_view.set_content(self.stack)

    # ... rest of setup ...


# 4. CLEANUP on window close
# --------------------------------------------------
def do_close_request(self):
    """Handle window close request."""
    self.banner_service.cleanup()
    return False


# USAGE EXAMPLES
# --------------------------------------------------

# Example 1: Multi-selection banner
def on_selection_changed(self, selected_count):
    """Handle selection changes."""
    if selected_count > 0:
        self.banner_service.show_selection_banner(
            count=selected_count,
            on_set_all=self._on_set_all_selected,
        )
    else:
        self.banner_service.hide_selection_banner()


def _on_set_all_selected(self):
    """Handle 'Set All' button click."""
    # Set all selected wallpapers
    self.toast_service.show_info("Set all selected wallpapers")
    self.banner_service.clear_banner()


# Example 2: Storage warning
def check_cache_usage(self):
    """Check cache usage and show warning if needed."""
    used_mb = self.thumbnail_cache.get_usage_mb()
    limit_mb = 500

    if used_mb > 450:  # Warning threshold
        self.banner_service.show_storage_warning(
            used_mb=used_mb,
            limit_mb=limit_mb,
            on_clear_cache=self._on_clear_cache,
        )


def _on_clear_cache(self):
    """Handle 'Clear Cache' button click."""
    self.thumbnail_cache.clear_expired()
    self.toast_service.show_info("Cache cleared")
    self.banner_service.clear_banner()


# Example 3: API quota warning
async def check_api_quota(self):
    """Check API quota and show warning if needed."""
    quota_status = await self.wallhaven_service.get_quota_status()

    if quota_status.remaining < 100:  # Low quota
        self.banner_service.show_api_warning(
            message=f"API quota low: {quota_status.remaining} requests remaining",
            button_text="Upgrade Account",
            on_button_click=lambda: self._on_upgrade_account(),
        )


# Example 4: Info banner
def show_update_available(self):
    """Show update available info banner."""
    self.banner_service.show_info_banner(
        message="A new version of Wallpicker is available!",
        button_text="View Release",
        on_button_click=lambda: self._on_view_release(),
    )


# Example 5: Clear all banners
def on_tab_changed(self, stack, pspec):
    """Handle tab change - clear banners when switching."""
    self.banner_service.clear_banner()


# BINDING TO VIEW MODEL PROPERTIES
# --------------------------------------------------
# The banner_service.is_visible property can be observed:
def _setup_banner_bindings(self):
    """Setup bindings between view models and banner service."""
    # Observe selection count from local view model
    self.local_view_model.connect(
        "notify::selected-count",
        lambda obj, pspec: self._on_selection_changed(obj.selected_count)
    )

    # Observe cache usage
    self.thumbnail_cache.connect(
        "notify::usage-mb",
        lambda obj, pspec: self.check_cache_usage()
    )
