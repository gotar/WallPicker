# Preview Dialog Component

Modern `Adw.Dialog`-based wallpaper preview dialog with split-view layout, metadata display, and keyboard shortcuts.

## Features

- **Split-view layout**: Full-size image preview on left, metadata sidebar on right
- **Responsive design**: Side-by-side on wide screens, bottom sheet on narrow screens
- **Metadata display**: Filename, resolution, file size, source, category
- **Action buttons**: Set wallpaper, favorite toggle, open externally, copy path, delete
- **Keyboard shortcuts**: Escape (close), Enter (set wallpaper), Space (toggle favorite)
- **Async image loading**: Smooth loading with spinner and error handling
- **Dark background**: Optimized for image contrast

## Usage

### Basic Integration

```python
from ui.components.preview_dialog import PreviewDialog
from domain.wallpaper import Wallpaper, WallpaperSource, WallpaperPurity, Resolution

# Create a wallpaper object
wallpaper = Wallpaper(
    id="example-123",
    url="https://example.com/wallpaper.jpg",
    path="/path/to/wallpaper.jpg",
    resolution=Resolution(1920, 1080),
    source=WallpaperSource.LOCAL,
    category="nature",
    purity=WallpaperPurity.SFW,
    file_size=2400000,  # 2.4 MB in bytes
)

# Create and present dialog
dialog = PreviewDialog(
    window=self.get_root(),  # Get from GTK widget
    wallpaper=wallpaper,
    on_set_wallpaper=self._on_set_wallpaper,
    on_toggle_favorite=self._on_toggle_favorite,
    on_open_externally=self._on_open_externally,
    on_delete=self._on_delete,  # Only for local wallpapers
    on_copy_path=self._on_copy_path,
    is_favorite=False,
    thumbnail_cache=self.thumbnail_cache,  # Optional, for async loading
)
dialog.present()
```

### Callback Implementation

```python
def _on_set_wallpaper(self):
    """Handle set wallpaper action."""
    self.view_model.set_wallpaper(self.wallpaper)
    self.toast_service.show_success("Wallpaper set successfully")

def _on_toggle_favorite(self, is_favorite: bool):
    """Handle favorite toggle."""
    if is_favorite:
        self.view_model.add_to_favorites(self.wallpaper)
        self.toast_service.show_success("Added to favorites")
    else:
        self.view_model.remove_from_favorites(self.wallpaper.id)
        self.toast_service.show_info("Removed from favorites")

def _on_open_externally(self):
    """Handle open externally action."""
    import subprocess
    subprocess.run(["xdg-open", self.wallpaper.path])

def _on_copy_path(self):
    """Handle copy path action."""
    clipboard = Gdk.Display.get_default().get_clipboard()
    clipboard.set_text(self.wallpaper.path)
    self.toast_service.show_info("Path copied to clipboard")

def _on_delete(self):
    """Handle delete action."""
    self.view_model.delete_wallpaper(self.wallpaper)
    self.toast_service.show_success("Wallpaper deleted")
```

### Updating Dialog State

```python
# Update favorite state from external source
dialog.update_favorite_state(True)

# Show/hide delete button (for local wallpapers)
dialog.set_delete_visible(True)
```

## Integration with Existing Views

### Local View Integration

Add an "info" button to each wallpaper card:

```python
def _create_wallpaper_card(self, wallpaper):
    # ... existing card creation ...

    # Add info/preview button
    info_btn = Gtk.Button(icon_name="info-symbolic", tooltip_text="Preview")
    info_btn.add_css_class("action-button")
    info_btn.connect("clicked", self._on_show_preview, wallpaper)
    actions_box.append(info_btn)

    return card

def _on_show_preview(self, button, wallpaper):
    """Show preview dialog."""
    dialog = PreviewDialog(
        window=self.get_root(),
        wallpaper=wallpaper,
        on_set_wallpaper=lambda: self._on_set_wallpaper(None, wallpaper),
        on_toggle_favorite=lambda is_favorite: self._on_toggle_favorite(wallpaper, is_favorite),
        on_open_externally=lambda: self._on_open_externally(wallpaper),
        on_delete=lambda: self._on_delete_wallpaper_with_dialog(wallpaper),
        on_copy_path=lambda: self._on_copy_path(wallpaper),
        is_favorite=self.view_model.is_favorite(wallpaper.id),
        thumbnail_cache=self.view_model.thumbnail_cache,
    )
    dialog.present()
```

### Wallhaven View Integration

```python
def _on_show_preview(self, button, wallpaper):
    """Show preview dialog for Wallhaven wallpaper."""
    dialog = PreviewDialog(
        window=self.get_root(),
        wallpaper=wallpaper,
        on_set_wallpaper=lambda: self._on_set_wallpaper(wallpaper),
        on_toggle_favorite=lambda is_favorite: self._on_toggle_favorite(wallpaper, is_favorite),
        on_copy_path=lambda: self._on_copy_url(wallpaper.url),
        is_favorite=self.view_model.is_favorite(wallpaper.id),
        thumbnail_cache=self.view_model.thumbnail_cache,
    )
    dialog.present()
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Escape | Close dialog |
| Enter | Set wallpaper (primary action) |
| Space | Toggle favorite |

## Responsive Behavior

- **Wide screens (>900px)**: Side-by-side split view (60% image, 40% sidebar)
- **Narrow screens (<900px)**: Bottom sheet with image on top, actions in sheet

## CSS Styling

The dialog uses these CSS classes:

- `.preview-dialog`: Main dialog container
- `.preview-image-container`: Image preview area (black background)
- `.preview-image`: The image itself
- `.preview-sidebar`: Metadata sidebar
- `.pill`: Large pill-shaped action buttons

Customize in `data/style.css`:

```css
.preview-dialog {
    min-width: 800px;
    min-height: 600px;
}

.preview-image-container {
    background: #000;
    padding: 24px;
}

.pill {
    padding: 12px 24px;
    border-radius: 24px;
    font-weight: 600;
}
```

## Advanced Features

### Async Image Loading

The dialog supports async image loading via ThumbnailCache for remote wallpapers:

```python
thumbnail_cache = ThumbnailCache()
dialog = PreviewDialog(
    window=window,
    wallpaper=wallpaper,
    thumbnail_cache=thumbnail_cache,  # Enables async loading
    # ... other callbacks
)
```

Without thumbnail_cache, local files load synchronously.

### Double-Click to Close

Double-clicking the image closes the dialog (convenient for quick previews).

### Clickable Filename

Clicking the filename row in metadata automatically copies the path to clipboard.

## Error Handling

The dialog handles image load failures gracefully:

1. Shows loading spinner while loading
2. Displays error icon and message on failure
3. Allows dialog to remain open for other actions

## Integration Checklist

- [ ] Import `PreviewDialog` component
- [ ] Create callback functions for all actions
- [ ] Pass `window` (get via `get_root()`)
- [ ] Pass `thumbnail_cache` for async loading (optional)
- [ ] Set initial `is_favorite` state
- [ ] Call `dialog.present()` to show
- [ ] Implement update methods for external state changes
