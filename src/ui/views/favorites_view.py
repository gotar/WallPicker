"""View for favorites management."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

"""View for local wallpaper browsing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GObject, Gtk

from ui.view_models.favorites_view_model import FavoritesViewModel


class FavoritesView(Gtk.Box):
    """View for favorites wallpaper browsing"""

    def __init__(self, view_model: FavoritesViewModel):
        print(f"DEBUG: FavoritesView.__init__ called with view_model: {view_model}")
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.view_model = view_model

        # Debug: Check view properties
        print(
            f"DEBUG: FavoritesView created - visible: {self.get_visible()}, sensitive: {self.get_sensitive()}, can_focus: {self.get_can_focus()}"
        )

        # Ensure view can receive events
        self.set_sensitive(True)
        self.set_can_focus(True)
        self.set_focusable(True)

        # Create UI components
        self._create_toolbar()
        self._create_wallpapers_grid()
        self._create_status_bar()

        # Bind to ViewModel state
        self._bind_to_view_model()

        print(
            f"DEBUG: FavoritesView setup complete - visible: {self.get_visible()}, sensitive: {self.get_sensitive()}"
        )

    def _create_toolbar(self):
        """Create toolbar with actions"""
        toolbar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=12,
        )
        toolbar.add_css_class("filter-bar")

        # Refresh button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Refresh")
        refresh_btn.connect("clicked", self._on_refresh_clicked)
        toolbar.append(refresh_btn)

        # Loading spinner
        self.loading_spinner = Gtk.Spinner(spinning=False)
        toolbar.append(self.loading_spinner)

        # Spacer
        spacer = Gtk.Label()
        spacer.set_hexpand(True)
        toolbar.append(spacer)

        # Search entry
        self.search_entry = Gtk.SearchEntry(placeholder_text="Search favorites...")
        self.search_entry.connect("search-changed", self._on_search_changed)
        toolbar.append(self.search_entry)

        self.append(toolbar)

    def _create_wallpapers_grid(self):
        """Create wallpapers grid display"""
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)

        # Create flow box for wallpapers grid
        self.wallpapers_grid = Gtk.FlowBox()
        self.wallpapers_grid.set_homogeneous(True)
        self.wallpapers_grid.set_min_children_per_line(2)
        self.wallpapers_grid.set_max_children_per_line(6)
        self.wallpapers_grid.set_column_spacing(12)
        self.wallpapers_grid.set_row_spacing(12)
        self.wallpapers_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self.scroll.set_child(self.wallpapers_grid)

        self.append(self.scroll)

    def _create_status_bar(self):
        """Create status bar"""
        self.status_label = Gtk.Label(label="")
        self.append(self.status_label)

    def _bind_to_view_model(self):
        """Bind to ViewModel state changes"""
        self.view_model.connect("notify::favorites", self._on_favorites_changed)
        self.view_model.connect("notify::is-busy", self._on_busy_changed)
        self.view_model.connect("notify::error-message", self._on_error_changed)

        # Initial data load
        self._on_favorites_changed()

    def _on_refresh_clicked(self, button):
        """Handle refresh button click"""
        self.view_model.load_favorites()

    def _on_search_changed(self, entry):
        """Handle search entry changes"""
        # Debounce search to avoid excessive filtering
        if self._search_timer:
            GObject.source_remove(self._search_timer)

        self._search_timer = GObject.timeout_add(300, self._perform_search)

    def _perform_search(self):
        """Perform search with debouncing"""
        self.view_model.search_query = self.search_entry.get_text()
        self._search_timer = None
        return False

    def _on_favorites_changed(self, *args):
        """Handle favorites list changes"""
        self.update_wallpapers_grid()
        self.update_status()

    def _on_busy_changed(self, *args):
        """Handle busy state changes"""
        self.loading_spinner.set_spinning(self.view_model.is_busy)

    def _on_error_changed(self, *args):
        """Handle error message changes"""
        # Error handling can be added here if needed

    def update_wallpapers_grid(self):
        """Update the wallpapers grid display"""
        # Clear existing cards
        while self.wallpapers_grid.get_first_child():
            self.wallpapers_grid.remove(self.wallpapers_grid.get_first_child())

        # Add new cards
        for favorite in self.view_model.favorites:
            card = self._create_wallpaper_card(favorite)
            self.wallpapers_grid.append(card)

        # Debug: Check if cards are created and focusable
        print(f"DEBUG: Created {len(self.view_model.favorites)} favorite cards")
        if self.wallpapers_grid.get_first_child():
            first_card = self.wallpapers_grid.get_first_child()
            print(
                f"DEBUG: First card - visible: {first_card.get_visible()}, sensitive: {first_card.get_sensitive()}, can_focus: {first_card.get_can_focus()}"
            )

    def update_status(self):
        """Update status bar"""
        count = len(self.view_model.favorites)
        self.status_label.set_text(f"{count} favorites")

    def _create_wallpaper_card(self, favorite):
        """Create wallpaper card with image and actions"""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.set_size_request(220, 200)
        card.add_css_class("wallpaper-card")

        # Add double-click gesture (same as LocalView)
        gesture = Gtk.GestureClick()
        gesture.set_button(1)  # Left button only
        gesture.connect("pressed", self._on_card_double_clicked, favorite)
        card.add_controller(gesture)

        image = Gtk.Picture()
        image.set_size_request(200, 160)
        image.set_content_fit(Gtk.ContentFit.CONTAIN)
        image.add_css_class("wallpaper-thumb")
        image.set_tooltip_text(
            Path(favorite.wallpaper.path).name if hasattr(favorite, "wallpaper") else "Favorite"
        )

        def on_thumbnail_loaded(texture):
            if texture:
                image.set_paintable(texture)

        self.view_model.load_thumbnail_async(str(favorite.wallpaper.path), on_thumbnail_loaded)

        overlay = Gtk.Overlay()
        overlay.set_child(image)
        card.append(overlay)

        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions_box.set_halign(Gtk.Align.CENTER)
        actions_box.set_homogeneous(True)

        set_btn = Gtk.Button(icon_name="image-x-generic-symbolic", tooltip_text="Set as wallpaper")
        set_btn.add_css_class("action-button")
        set_btn.connect("clicked", self._on_set_wallpaper, favorite)
        actions_box.append(set_btn)

        remove_btn = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Remove")
        remove_btn.add_css_class("destructive-action")
        remove_btn.connect("clicked", self._on_remove_favorite, favorite)
        actions_box.append(remove_btn)

        card.append(actions_box)
        return card

    def _on_set_wallpaper(self, button, favorite):
        """Handle set wallpaper button click"""
        self.view_model.set_wallpaper(favorite)

    def _on_card_double_clicked(self, gesture, n_press, x, y, favorite):
        if n_press >= 2:  # Only trigger on double-click
            self._on_set_wallpaper(None, favorite)

    def _on_remove_favorite(self, button, favorite):
        """Handle remove button click"""
        window = self.get_root()

        dialog = Adw.MessageDialog(
            transient_for=window,
            heading="Remove from favorites?",
            body=f"Are you sure you want to remove '{Path(favorite.wallpaper.path).name}' from favorites?",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove")
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(dialog, response):
            if response == "remove":
                self.view_model.remove_favorite(favorite.wallpaper_id)

        dialog.connect("response", on_response)
        dialog.present()
