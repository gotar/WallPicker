"""Modern Search/Filter Bar component with dropdown, chips, and filter panel."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from collections.abc import Callable
from typing import Any

from gi.repository import Adw, GLib, GObject, Gtk


class SearchFilterBar(Gtk.Box):
    """Modern search and filter bar with dropdown, chips, and panel.

    This component provides a unified search and filter interface that works across
    different tabs (wallhaven, local, favorites) with appropriate controls for each.

    Features:
    - Debounced search entry (300ms)
    - Modern Gtk.DropDown for sorting
    - Collapsible filter popover with Wallhaven-specific options
    - Active filter chips with remove functionality
    - Responsive layout behavior
    """

    __gtype_name__ = "SearchFilterBar"

    def __init__(
        self,
        tab_type: str = "wallhaven",
        on_search_changed: Callable[[str], None] | None = None,
        on_sort_changed: Callable[[str], None] | None = None,
        on_filter_changed: Callable[[dict[str, Any]], None] | None = None,
    ):
        """Initialize the Search/Filter Bar.

        Args:
            tab_type: One of "wallhaven", "local", "favorites"
            on_search_changed: Callback when search text changes (after debounce)
            on_sort_changed: Callback when sort option changes
            on_filter_changed: Callback when any filter changes
        """
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.tab_type = tab_type
        self._search_timer: int | None = None

        self._on_search_changed_callback = on_search_changed
        self._on_sort_changed_callback = on_sort_changed
        self._on_filter_changed_callback = on_filter_changed

        self._active_filters: dict[str, Any] = {}

        self._create_ui()
        self._setup_callbacks()

    def _create_ui(self):
        """Create the UI components."""
        self.add_css_class("search-filter-bar")

        # Search entry
        self.search_entry = Gtk.SearchEntry(placeholder_text=self._get_search_placeholder())
        self.search_entry.set_hexpand(True)
        self.search_entry.set_size_request(300, -1)
        self.append(self.search_entry)

        # Sort dropdown (always visible)
        self.sort_dropdown = Gtk.DropDown()
        self._populate_sort_options()
        self.append(self.sort_dropdown)

        # Filter toggle button (Wallhaven only)
        if self.tab_type == "wallhaven":
            self.filter_btn = Gtk.MenuButton()
            self.filter_btn.set_icon_name("preferences-other-symbolic")
            self.filter_btn.set_tooltip_text("Filters")
            self.filter_btn.add_css_class("flat")
            self.append(self.filter_btn)

            # Create filter popover
            self._create_filter_popover()

        # Active filter chips (initially hidden)
        self._chips_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._chips_container.add_css_class("filter-chips")
        self._chips_container.set_visible(False)

    def _get_search_placeholder(self) -> str:
        """Get search placeholder text based on tab type."""
        placeholders = {
            "wallhaven": "Search wallpapers...",
            "local": "Search local wallpapers...",
            "favorites": "Search favorites...",
        }
        return placeholders.get(self.tab_type, "Search...")

    def _populate_sort_options(self):
        """Populate sort dropdown based on tab type."""
        self._sort_options_list = self._get_sort_options()
        string_list = Gtk.StringList()
        for display_name, _ in self._sort_options_list:
            string_list.append(display_name)
        self.sort_dropdown.set_model(string_list)

        # Store sort mapping for value lookup
        self._sort_mapping = {idx: value for idx, (_, value) in enumerate(self._sort_options_list)}

    def _get_sort_options(self) -> list[tuple[str, str]]:
        """Get sort options for current tab type.

        Returns:
            List of (display_name, backend_value) tuples
        """
        if self.tab_type == "wallhaven":
            return [
                ("Newest", "date_added"),
                ("Relevance", "relevance"),
                ("Random", "random"),
                ("Views", "views"),
                ("Favorites", "favorites"),
                ("Toplist", "toplist"),
            ]
        elif self.tab_type in ("local", "favorites"):
            return [
                ("Name", "name"),
                ("Date Added", "date"),
            ]
        return []

    def _create_filter_popover(self):
        """Create filter popover with collapsible panel (Wallhaven only)."""
        self.filter_popover = Gtk.Popover()
        self.filter_popover.set_position(Gtk.PositionType.BOTTOM)

        # Create popover content
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)

        # Category section
        category_label = Gtk.Label(label="Category")
        category_label.add_css_class("heading")
        category_label.set_halign(Gtk.Align.START)
        content_box.append(category_label)

        category_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.category_sfw = Gtk.CheckButton(label="General")
        self.category_anime = Gtk.CheckButton(label="Anime")
        self.category_people = Gtk.CheckButton(label="People")

        # Group checkboxes together (group second and third with first)
        self.category_anime.set_group(self.category_sfw)
        self.category_people.set_group(self.category_sfw)

        category_box.append(self.category_sfw)
        category_box.append(self.category_anime)
        category_box.append(self.category_people)
        content_box.append(category_box)

        # Purity section
        purity_label = Gtk.Label(label="Purity")
        purity_label.add_css_class("heading")
        purity_label.set_halign(Gtk.Align.START)
        content_box.append(purity_label)

        purity_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.purity_sfw = Gtk.CheckButton(label="SFW")
        self.purity_sketchy = Gtk.CheckButton(label="Sketchy")
        self.purity_nsfw = Gtk.CheckButton(label="NSFW")

        purity_box.append(self.purity_sfw)
        purity_box.append(self.purity_sketchy)
        purity_box.append(self.purity_nsfw)
        content_box.append(purity_box)

        # Resolution section (all tabs)
        resolution_label = Gtk.Label(label="Resolution")
        resolution_label.add_css_class("heading")
        resolution_label.set_halign(Gtk.Align.START)
        content_box.append(resolution_label)

        self.resolution_dropdown = Gtk.DropDown()
        resolution_list = Gtk.StringList()
        resolution_list.append("All")
        resolution_list.append("1920x1080")
        resolution_list.append("2560x1440")
        resolution_list.append("3840x2160 (4K)")
        self.resolution_dropdown.set_model(resolution_list)
        content_box.append(self.resolution_dropdown)

        # Apply button
        apply_btn = Gtk.Button(label="Apply Filters")
        apply_btn.add_css_class("suggested-action")
        apply_btn.set_halign(Gtk.Align.END)
        content_box.append(apply_btn)

        self.filter_popover.set_child(content_box)
        self.filter_btn.set_popover(self.filter_popover)

        # Connect apply button
        apply_btn.connect("clicked", self._on_apply_filters)

    def _setup_callbacks(self):
        """Setup signal callbacks."""
        # Search entry with debouncing
        self.search_entry.connect("search-changed", self._on_search_entry_changed)

        # Sort dropdown
        self.sort_dropdown.connect("notify::selected", self._on_sort_changed)

        # Filter checkboxes (Wallhaven only)
        if self.tab_type == "wallhaven":
            self.category_sfw.connect("toggled", self._on_category_toggled)
            self.category_anime.connect("toggled", self._on_category_toggled)
            self.category_people.connect("toggled", self._on_category_toggled)
            self.purity_sfw.connect("toggled", self._on_purity_toggled)
            self.purity_sketchy.connect("toggled", self._on_purity_toggled)
            self.purity_nsfw.connect("toggled", self._on_purity_toggled)

            # Resolution dropdown
            self.resolution_dropdown.connect("notify::selected", self._on_resolution_changed)

    def _on_search_entry_changed(self, entry: Gtk.SearchEntry):
        """Handle search entry text change with debouncing."""
        # Cancel existing timer
        if self._search_timer:
            GObject.source_remove(self._search_timer)

        # Set new timer (300ms debounce)
        self._search_timer = GObject.timeout_add(300, self._perform_search)

    def _perform_search(self) -> bool:
        """Perform the actual search (called after debounce)."""
        search_text = self.search_entry.get_text()
        self._search_timer = None

        if self._on_search_changed_callback:
            self._on_search_changed_callback(search_text)

        return False  # Don't repeat

    def _on_sort_changed(self, dropdown: Gtk.DropDown, pspec: GObject.ParamSpec):
        """Handle sort dropdown selection change."""
        selected = dropdown.get_selected()
        if selected != Gtk.INVALID_LIST_POSITION and selected in self._sort_mapping:
            sort_value = self._sort_mapping[selected]
            self._add_filter_chip("Sort", self._get_sort_display_name(sort_value))
            self._active_filters["sort"] = sort_value

            if self._on_sort_changed_callback:
                self._on_sort_changed_callback(sort_value)

            if self._on_filter_changed_callback:
                self._on_filter_changed_callback(self._active_filters)

    def _get_sort_display_name(self, value: str) -> str:
        """Get display name for sort value."""
        for display, backend in self._sort_options_list:
            if backend == value:
                return display
        return value

    def _on_category_toggled(self, button: Gtk.CheckButton):
        """Handle category checkbox toggle (Wallhaven only)."""
        if button.get_active():
            # Remove old category chip if exists
            self._remove_filter_chip_by_type("category")

            # Determine category code
            if button == self.category_sfw:
                code = "100"
                name = "General"
            elif button == self.category_anime:
                code = "010"
                name = "Anime"
            elif button == self.category_people:
                code = "001"
                name = "People"
            else:
                code = "111"
                name = "All"

            self._active_filters["category"] = code
            self._add_filter_chip("Category", name)

            if self._on_filter_changed_callback:
                self._on_filter_changed_callback(self._active_filters)

    def _on_purity_toggled(self, button: Gtk.CheckButton):
        """Handle purity checkbox toggle (Wallhaven only)."""
        purity_bits = ""

        if self.purity_sfw.get_active():
            purity_bits += "1"
        else:
            purity_bits += "0"

        if self.purity_sketchy.get_active():
            purity_bits += "1"
        else:
            purity_bits += "0"

        if self.purity_nsfw.get_active():
            purity_bits += "1"
        else:
            purity_bits += "0"

        # Remove old purity chip if exists
        self._remove_filter_chip_by_type("purity")

        # Determine purity display name
        active_count = purity_bits.count("1")
        if active_count == 1:
            if self.purity_sfw.get_active():
                name = "SFW"
            elif self.purity_sketchy.get_active():
                name = "Sketchy"
            elif self.purity_nsfw.get_active():
                name = "NSFW"
            else:
                name = "Custom"
        elif active_count == 3:
            name = "All"
        else:
            name = "Custom"

        self._active_filters["purity"] = purity_bits
        self._add_filter_chip("Purity", name)

        if self._on_filter_changed_callback:
            self._on_filter_changed_callback(self._active_filters)

    def _on_resolution_changed(self, dropdown: Gtk.DropDown, pspec: GObject.ParamSpec):
        """Handle resolution dropdown change."""
        selected = dropdown.get_selected()
        if selected == 0:
            # "All" selected
            self._remove_filter_chip_by_type("resolution")
            if "resolution" in self._active_filters:
                del self._active_filters["resolution"]
        else:
            resolutions = ["", "1920x1080", "2560x1440", "3840x2160"]
            if selected < len(resolutions):
                value = resolutions[selected]
                name = dropdown.get_model().get_string(selected)
                self._active_filters["resolution"] = value
                self._add_filter_chip("Resolution", name)

        if self._on_filter_changed_callback:
            self._on_filter_changed_callback(self._active_filters)

    def _on_apply_filters(self, button: Gtk.Button):
        """Handle apply filters button click (Wallhaven only)."""
        self.filter_popover.popdown()

    def _add_filter_chip(self, filter_type: str, value: str):
        """Add a filter chip to the chips container.

        Args:
            filter_type: Type of filter (e.g., "Sort", "Category")
            value: Filter value to display
        """
        # Remove existing chip of same type
        self._remove_filter_chip_by_type(filter_type)

        # Show chips container if not visible
        if not self._chips_container.get_visible():
            self._chips_container.set_visible(True)

        # Create chip
        chip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        chip.add_css_class("filter-chip")

        # Chip label
        label = Gtk.Label(label=f"{filter_type}: {value}")
        chip.append(label)

        # Remove button
        remove_btn = Gtk.Button(icon_name="window-close-symbolic")
        remove_btn.add_css_class("filter-chip-remove")
        remove_btn.add_css_class("flat")
        remove_btn.set_size_request(24, 24)

        # Store filter type on button for removal
        remove_btn._filter_type = filter_type

        remove_btn.connect("clicked", self._on_chip_remove_clicked)
        chip.append(remove_btn)

        # Store chip reference
        chip._filter_type = filter_type

        self._chips_container.append(chip)
        chip.add_css_class("chip-appeared")

    def _remove_filter_chip_by_type(self, filter_type: str):
        """Remove filter chip of specific type."""
        child = self._chips_container.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            if hasattr(child, "_filter_type") and child._filter_type == filter_type:
                child.add_css_class("chip-removing")
                GLib.timeout_add(200, lambda: self._chips_container.remove(child) or False)
                break
            child = next_child

        # Hide chips container if empty
        if not self._chips_container.get_first_child():
            self._chips_container.set_visible(False)

    def _on_chip_remove_clicked(self, button: Gtk.Button):
        """Handle chip remove button click."""
        filter_type = getattr(button, "_filter_type", None)
        if filter_type:
            self._remove_filter_chip_by_type(filter_type)

            # Reset filter state
            if filter_type in self._active_filters:
                del self._active_filters[filter_type]

            # Reset UI controls
            if filter_type == "Sort":
                self.sort_dropdown.set_selected(Gtk.INVALID_LIST_POSITION)
            elif filter_type == "Category" and self.tab_type == "wallhaven":
                # Reset to General (default)
                self.category_sfw.set_active(True)
                self.category_anime.set_active(False)
                self.category_people.set_active(False)
            elif filter_type == "Purity" and self.tab_type == "wallhaven":
                # Reset to SFW only (default)
                self.purity_sfw.set_active(True)
                self.purity_sketchy.set_active(False)
                self.purity_nsfw.set_active(False)
            elif filter_type == "Resolution":
                self.resolution_dropdown.set_selected(0)

            # Notify filter changed
            if self._on_filter_changed_callback:
                self._on_filter_changed_callback(self._active_filters)

    def get_search_text(self) -> str:
        """Get current search text."""
        return self.search_entry.get_text()

    def get_active_sort(self) -> str | None:
        """Get selected sort value."""
        selected = self.sort_dropdown.get_selected()
        if selected != Gtk.INVALID_LIST_POSITION and selected in self._sort_mapping:
            return self._sort_mapping[selected]
        return None

    def get_active_filters(self) -> dict[str, Any]:
        """Get all active filters.

        Returns:
            Dictionary of filter_type -> filter_value pairs
        """
        return self._active_filters.copy()

    def set_sort_options(self, options: list[tuple[str, str]]):
        """Update sort dropdown options.

        Args:
            options: List of (display_name, backend_value) tuples
        """
        self._sort_options_list = options
        string_list = Gtk.StringList()
        for display_name, _ in options:
            string_list.append(display_name)
        self.sort_dropdown.set_model(string_list)
        self._sort_mapping = {idx: value for idx, (_, value) in enumerate(options)}

    def clear_filters(self):
        """Clear all active filters."""
        # Clear active filters dict
        self._active_filters.clear()

        # Remove all chips
        while chip := self._chips_container.get_first_child():
            self._chips_container.remove(chip)
        self._chips_container.set_visible(False)

        # Reset UI controls
        self.sort_dropdown.set_selected(Gtk.INVALID_LIST_POSITION)
        self.search_entry.set_text("")

        if self.tab_type == "wallhaven":
            # Reset category to General
            self.category_sfw.set_active(True)
            self.category_anime.set_active(False)
            self.category_people.set_active(False)

            # Reset purity to SFW
            self.purity_sfw.set_active(True)
            self.purity_sketchy.set_active(False)
            self.purity_nsfw.set_active(False)

            # Reset resolution to All
            self.resolution_dropdown.set_selected(0)

        # Notify filter changed
        if self._on_filter_changed_callback:
            self._on_filter_changed_callback(self._active_filters)

    def set_search_text(self, text: str):
        """Set the search text programmatically."""
        self.search_entry.set_text(text)

    def set_sort(self, sort_value: str):
        """Set the sort dropdown to a specific value.

        Args:
            sort_value: Backend sort value to select
        """
        for idx, value in self._sort_mapping.items():
            if value == sort_value:
                self.sort_dropdown.set_selected(idx)
                break

    def get_chips_container(self) -> Gtk.Box:
        """Get the chips container for adding to the parent layout.

        Returns:
            The chips container widget
        """
        return self._chips_container
