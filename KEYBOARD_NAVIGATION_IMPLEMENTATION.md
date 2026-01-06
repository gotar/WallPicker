# Keyboard Navigation Implementation Summary

## Overview
Implemented full keyboard navigation support for Wallpicker following GTK4/Libadwaita best practices.

## Features Implemented

### 1. Tab Navigation (main_window.py)
- **Ctrl/Cmd + 1/2/3**: Direct tab selection (Local/Wallhaven/Favorites)
- **Alt + 1/2/3**: Alternative direct tab selection
- **Ctrl/Cmd + Tab**: Switch to next tab
- **Ctrl/Cmd + Shift + Tab**: Switch to previous tab
- **Ctrl/Cmd + [ / ]**: Alternative previous/next tab navigation

### 2. Search Focus (main_window.py)
- **Ctrl/Cmd + F**: Focus search entry in current view
- **Ctrl/Cmd + N**: New search (clears and focuses search entry)
- **Escape**: Clear search text and lose focus

### 3. Grid Navigation (local_view.py, favorites_view.py, wallhaven_view.py)
- **Arrow Keys (↑/↓/←/→)**: Navigate between wallpaper cards
- **Enter/Return**: Set wallpaper on focused card
- **Space**: Toggle favorite on focused card
- **Escape**: Clear selection and remove focus

Grid navigation features:
- Cards are made focusable with `set_can_focus(True)` and `set_focusable(True)`
- Card-to-wallpaper mapping for keyboard activation
- Smooth focus navigation wrapping (circular navigation)

### 4. Action Shortcuts (main_window.py)
- **Ctrl/Cmd + R**: Refresh current view
- **Ctrl/Cmd + N**: New search (clears search text)

### 5. Preview Dialog (preview_dialog.py)
- **Escape**: Close dialog
- **Ctrl/Cmd + W**: Close dialog
- **Enter/Return**: Set wallpaper
- **Space**: Toggle favorite

### 6. Menu Integration (main_window.py)
- Added menu button with PopoverMenu
- **Keyboard Shortcuts** menu item to display shortcuts dialog
- **About** menu item for application info

### 7. Focus Management (main_window.py)
- `_setup_focus_chain()` method to manage focus on tab changes
- Automatic focus on appropriate widgets when switching tabs
- Focus on search entry or grid as appropriate

### 8. Shortcuts Dialog (src/ui/components/shortcuts_dialog.py)
- Complete `ShortcutsDialog` component with Adw.Dialog
- Organized shortcut groups:
  - Tab Navigation
  - Search
  - Grid Navigation
  - Actions
  - Preview Dialog
  - Multi-Selection
  - Tips
- Accessible from menu or keyboard shortcuts

### 9. CSS Focus Styling (data/style.css)
- Global focus indicators with smooth animations
- Card focus styling with scale transformation
- Focus ring animations (`@keyframes focus-pulse`, `@keyframes focus-appear`)
- Button focus indicators
- Shortcuts dialog styling
- Reduced motion support (`prefers-reduced-motion`)
- High contrast theme support

## Technical Implementation Details

### EventControllerKey Pattern
All keyboard shortcuts use GTK4's `EventControllerKey`:
```python
key_controller = Gtk.EventControllerKey()
key_controller.connect("key-pressed", self._on_key_pressed)
widget.add_controller(key_controller)
```

### Key Handler Pattern
Keyboard handlers return `True` for handled keys, `False` to pass through:
```python
def _on_key_pressed(self, controller, keyval, keycode, state):
    if state & Gdk.ModifierType.CONTROL_MASK and keyval == Gdk.KEY_f:
        self._focus_search_entry()
        return True  # Handled
    return False  # Pass to default handler
```

### Modifier Key Detection
Uses GTK4 modifier masks:
- `Gdk.ModifierType.CONTROL_MASK`: Ctrl key
- `Gdk.ModifierType.SUPER_MASK`: Cmd/Meta key (macOS)
- `Gdk.ModifierType.SHIFT_MASK`: Shift key
- `Gdk.ModifierType.MOD1_MASK`: Alt key

### Card Focus Navigation
Grid navigation uses FlowBox focus system:
```python
def _focus_next_card(self):
    current = self.wallpaper_grid.get_focus_child()
    children = list(self.wallpaper_grid)
    if current:
        idx = children.index(current)
        next_idx = (idx + 1) % len(children)
        children[next_idx].grab_focus()
    else:
        children[0].grab_focus()  # Focus first if none focused
```

### Card-to-Wallpaper Mapping
For keyboard activation, track card→wallpaper mapping:
```python
# In _create_wallpaper_card:
card.set_can_focus(True)
card.set_focusable(True)
self.card_wallpaper_map[card] = wallpaper

# In _on_grid_key_pressed:
focused = self.wallpaper_grid.get_focus_child()
if focused and focused in self.card_wallpaper_map:
    wallpaper = self.card_wallpaper_map[focused]
    self._on_set_wallpaper(None, wallpaper)
```

## Files Modified

### Created:
- `src/ui/components/shortcuts_dialog.py` - Shortcuts dialog component
- `tests/ui/test_keyboard_navigation.py` - Keyboard navigation tests

### Modified:
- `src/ui/main_window.py` - Tab navigation, search focus, menu integration
- `src/ui/views/local_view.py` - Grid navigation, card focusability
- `src/ui/views/favorites_view.py` - Grid navigation, card focusability
- `src/ui/views/wallhaven_view.py` - Grid navigation, card focusability
- `src/ui/components/preview_dialog.py` - Ctrl+W shortcut
- `data/style.css` - Focus indicators, animations

## Testing

### Unit Tests (`tests/ui/test_keyboard_navigation.py`)
- Tab navigation tests
- Grid navigation tests for all views
- Preview dialog shortcut tests
- Shortcuts dialog tests
- CSS style tests
- Method existence checks

### Manual Testing Checklist
- [ ] Tab shortcuts (Ctrl+1/2/3) work
- [ ] Arrow keys navigate grid
- [ ] Enter sets wallpaper
- [ ] Space toggles favorite
- [ ] Ctrl+F focuses search
- [ ] Ctrl+R refreshes
- [ ] Escape clears selection
- [ ] Preview dialog shortcuts work
- [ ] Shortcuts dialog displays correctly
- [ ] Focus indicators visible
- [ ] Reduced motion respected
- [ ] High contrast theme works

## Accessibility Features

### Focus Indicators
- Strong, visible 3px focus outlines
- Smooth focus animations
- Color-coded with accent color

### Reduced Motion
- CSS media query `@media (prefers-reduced-motion: reduce)`
- Disables non-essential animations
- Instant transitions when reduced motion enabled

### High Contrast Theme
- `.high-contrast` class support
- Enhanced borders and indicators
- Improved text readability

### Keyboard-First Navigation
- All features accessible via keyboard
- No mouse required for core functionality
- Logical tab order and focus chain

## Shortcuts Summary

| Category | Shortcuts | Action |
|----------|-----------|--------|
| Tab Nav | Ctrl+1/2/3 | Go to Local/Wallhaven/Favorites tab |
| Tab Nav | Alt+1/2/3 | Alternative tab selection |
| Tab Nav | Ctrl+Tab | Next tab |
| Tab Nav | Ctrl+Shift+Tab | Previous tab |
| Tab Nav | Ctrl+[ / Ctrl+] | Previous/Next tab (alternative) |
| Search | Ctrl+F | Focus search entry |
| Search | Ctrl+N | New search (clears text) |
| Search | Escape | Clear search, lose focus |
| Grid | ↑/↓/←/→ | Navigate between cards |
| Grid | Enter/Return | Set wallpaper |
| Grid | Space | Toggle favorite |
| Grid | Escape | Clear selection, lose focus |
| Actions | Ctrl+R | Refresh current view |
| Actions | Ctrl+A | Select all |
| Actions | Ctrl+Shift+Click | Range selection |
| Actions | Ctrl+Click | Toggle selection |
| Preview | Escape | Close dialog |
| Preview | Ctrl+W | Close dialog |
| Preview | Enter | Set wallpaper |
| Preview | Space | Toggle favorite |

## Future Enhancements

Potential improvements:
1. **Ctrl+?** shortcut to show shortcuts dialog globally
2. **Custom shortcuts** configuration in settings
3. **Vi-style navigation** (hjkl) option
4. **Multi-row navigation** for grid (PageUp/PageDown)
5. **Quick filters** via keyboard (1-9 for categories)
6. **Context-sensitive shortcuts** (different shortcuts based on focused widget)

## References

Based on GTK4 and Libadwaita best practices:
- [GTK4 Documentation](https://docs.gtk.org/gtk4/)
- [GNOME HIG - Keyboard Navigation](https://developer.gnome.org/hig/patterns/keyboard.html)
- [GNOME Music](https://github.com/GNOME/gnome-music) - Reference implementation
- [Libadwaita 1.8 ShortcutsDialog](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/class.ShortcutsDialog.html)

## Conclusion

Comprehensive keyboard navigation has been successfully implemented following GTK4/Libadwaita best practices. All core functionality is now accessible via keyboard, with smooth focus indicators, proper accessibility support, and a discoverable shortcuts dialog.
