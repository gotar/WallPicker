# Wallpicker Accessibility Implementation

This document describes the comprehensive accessibility features implemented in Wallpicker to ensure the application is usable by everyone, including users who rely on assistive technologies.

## Implemented Features

### 1. Screen Reader Support

All UI components now have proper accessibility labels for screen readers:

- **Wallpaper Cards**: Announce filename, resolution, file size, and current/favorite status
- **Action Buttons**: All buttons have descriptive names and roles (Set wallpaper, Add/Remove from favorites, Download, Delete, More options)
- **Form Controls**: Search entries, dropdowns, and checkboxes have accessible labels
- **Status Pages**: Loading, empty, and error pages have descriptive labels
- **Preview Dialog**: Metadata rows and action buttons are properly labeled

### 2. Keyboard Navigation

The application supports full keyboard navigation:

- **Tab**: Navigate between tabs (Local, Wallhaven, Favorites)
- **Arrow Keys**: Navigate within wallpaper grids
- **Enter**: Activate focused element
- **Escape**: Deselect all or close dialogs
- **Ctrl+A**: Select all wallpapers
- **Ctrl+R**: Refresh current view
- **Space**: Toggle favorite status (in preview dialog)

All interactive elements are focusable and have visible focus indicators.

### 3. Focus Indicators

Strong, visible focus indicators are implemented via CSS:

- **3px solid outline** for all interactive elements
- **Offset** of 2-4px for clear separation from content
- **Animated focus ring** that pulses gently for visual feedback
- **Enhanced card focus** with shadow effects
- High contrast support for better visibility

### 4. Text Scaling

All text uses relative units that respect system font size settings:

- **Base font size**: `1rem` (respects system setting)
- **Relative sizes**: `0.875rem` for captions, `1rem` for headings
- **Line height**: Minimum 1.4 for readability
- **Minimum touch targets**: 44px height, 44px width for buttons

### 5. High Contrast Theme Support

The application automatically adapts to high contrast themes:

- **Enhanced borders**: 2-3px borders for cards and buttons
- **Improved text contrast**: Ensures minimum WCAG AA 4.5:1 ratio
- **Visible selection indicators**: Bold borders for selected/focused elements
- **No reliance on shadows**: Uses solid borders instead

### 6. Reduced Motion Support

Respects user's motion preference via `prefers-reduced-motion` media query:

- **Disables animations**: All non-essential transitions and animations
- **Instant state changes**: Essential state changes remain but are instant
- **No focus ring animation**: Reduces motion for motion-sensitive users
- **No hover effects**: Disables scale/transform animations

### 7. Color Contrast

All text and interactive elements meet WCAG AA (4.5:1) contrast requirements:

- **Dim labels**: Minimum 70% opacity
- **Error messages**: High contrast with bold font weight
- **Tooltips**: Readable background and foreground colors
- **Icons**: Paired with labels where color alone conveys meaning

### 8. Accessible Roles

All widgets have proper ARIA-like roles:

- `Gtk.AccessibleRole.BUTTON` - Action buttons
- `Gtk.AccessibleRole.CHECK_BOX` - Selection checkboxes
- `Gtk.AccessibleRole.TOGGLE_BUTTON` - Favorite toggle
- `Gtk.AccessibleRole.IMG` - Wallpaper thumbnails
- `Gtk.AccessibleRole.GROUP` - Wallpaper cards
- `Gtk.AccessibleRole.LIST` - Wallpaper grids
- `Gtk.AccessibleRole.COMBO_BOX` - Dropdowns
- `Gtk.AccessibleRole.ENTRY` - Search fields
- `Gtk.AccessibleRole.STATUS` - Status labels
- `Gtk.AccessibleRole.ALERT` - Error messages

### 9. Touch-Friendly Design

All interactive elements meet mobile accessibility standards:

- **Minimum touch target**: 44x44 pixels for buttons
- **Spacing**: Adequate spacing between interactive elements
- **Feedback**: Visual feedback for touch interactions
- **Gesture support**: Long press for additional options

## Component Accessibility Details

### WallpaperCard Component

```python
# Card level
set_accessible_role(Gtk.AccessibleRole.GROUP)
set_accessible_name("Wallpaper: landscape.jpg")
set_accessible_description("Resolution: 1920x1080. Size: 2.4 MB. In favorites")

# Image
set_accessible_name("Wallpaper thumbnail: landscape.jpg")
set_accessible_role(Gtk.AccessibleRole.IMG)

# Action buttons
set_accessible_name("Set wallpaper")
set_accessible_description("Set this image as desktop background")
set_accessible_role(Gtk.AccessibleRole.BUTTON)
```

### StatusPage Component

```python
# Loading state
set_accessible_name("Loading page")
set_accessible_description("Loading wallpapers from server")

# Empty state
set_accessible_name("Empty page")
set_accessible_description("No wallpapers found in collection")

# Error state
set_accessible_name("Error page")
set_accessible_description("Failed to load wallpapers")

# Retry button
set_accessible_name("Retry button")
set_accessible_description("Retry loading wallpapers")
```

### PreviewDialog Component

```python
# Dialog
set_accessible_name("Wallpaper preview dialog")
set_accessible_description("Full preview of wallpaper with metadata and actions")

# Preview image
set_accessible_name("Wallpaper preview: landscape.jpg")
set_accessible_role(Gtk.AccessibleRole.IMG)

# Metadata rows
set_accessible_name("Filename: landscape.jpg")
set_accessible_role(Gtk.AccessibleRole.ROW)

# Action buttons
set_accessible_name("Set wallpaper")
set_accessible_description("Apply this wallpaper to desktop")
set_accessible_role(Gtk.AccessibleRole.BUTTON)
```

### SearchFilterBar Component

```python
# Search entry
set_accessible_name("Search wallpapers")
set_accessible_description("Enter keywords to filter wallpaper collection")

# Sort dropdown
set_accessible_name("Sort by")
set_accessible_description("Choose sorting order for wallpapers")
set_accessible_role(Gtk.AccessibleRole.COMBO_BOX)

# Filter checkboxes
set_accessible_name("General category")
set_accessible_role(Gtk.AccessibleRole.RADIO_BUTTON)
```

## Testing Checklist

### Screen Reader Testing (Orca, NVDA, VoiceOver)

- [ ] All buttons announce their purpose correctly
- [ ] Wallpaper cards announce filename and metadata
- [ ] Form fields have associated labels
- [ ] Status changes are announced
- [ ] Error messages are accessible
- [ ] Dialogs announce their purpose

### Keyboard Navigation Testing

- [ ] Tab navigates through all interactive elements
- [ ] Arrow keys navigate within grids
- [ ] Enter/Space activates focused items
- [ ] Escape closes dialogs/clears selection
- [ ] Ctrl+A selects all items
- [ ] Ctrl+R refreshes current view
- [ ] Focus indicators are visible
- [ ] No keyboard traps exist
- [ ] Tab order is logical

### Visual Testing

- [ ] Focus indicators are visible (3px minimum)
- [ ] Text contrast meets WCAG AA (4.5:1)
- [ ] Color alone doesn't convey information
- [ ] Text scales properly with system settings
- [ ] High contrast mode works correctly
- [ ] Reduced motion preference is respected

### Touch Testing

- [ ] Touch targets are at least 44x44px
- [ ] Spacing between targets is adequate
- [ ] Touch feedback is provided
- [ ] Gestures work correctly
- [ ] No accidental activations

## WCAG 2.1 Compliance

This implementation aims to meet WCAG 2.1 Level AA:

### Perceivable
1.1 Text Alternatives: ✓ All images have accessible names
1.2 Time-based Media: N/A (no video/audio)
1.3 Adaptable: ✓ Works with assistive technologies, structured content
1.4 Distinguishable: ✓ High contrast, reduced motion options

### Operable
2.1 Keyboard Accessible: ✓ Full keyboard navigation
2.2 Enough Time: ✓ No time limits
2.3 Seizures: ✓ No flashing content, respects reduced motion
2.4 Navigable: ✓ Clear focus indicators, logical order
2.5 Input Modalities: ✓ Touch-friendly targets

### Understandable
3.1 Readable: ✓ Clear labels, consistent layout
3.2 Predictable: ✓ Consistent behavior
3.3 Input Assistance: ✓ Helpful error messages

### Robust
4.1 Compatible: ✓ Works with assistive technologies

## Browser/System Settings Supported

- ✓ Font size scaling (system-wide)
- ✓ High contrast theme (automatic detection)
- ✓ Reduced motion preference (`prefers-reduced-motion`)
- ✓ Screen scaling (HiDPI/Retina support)
- ✓ Dark/light mode (automatic adaptation)

## Testing Tools

### Linux (GNOME)
```bash
# Enable ORCA screen reader
orca

# Test with GTK accessibility tools
at-spi-registryd &

# Inspect accessibility tree
accerciser
```

### Screen Reader Commands (Orca)
- **Desktop**: `Ctrl+Alt+D` to focus desktop
- **Review**: `Orca+Up/Down/Left/Right` to review
- **Say All**: `Orca+S` to read entire window
- **Flat Review**: `Orca+KP7/8/9/4/6/1/2/3` for grid navigation

## Known Limitations

1. **Thumbnail Loading**: While thumbnails load, placeholder may not fully describe the image
2. **Dynamic Content**: Real-time updates (e.g., loading states) may not be announced by all screen readers
3. **Complex Grids**: Grid navigation may require multiple tab stops in some screen readers

## Future Improvements

1. **Live Regions**: Add ARIA live regions for dynamic content updates
2. **Skip Links**: Add "Skip to content" links for keyboard users
3. **Focus Management**: Improved focus restoration after dialogs close
4. **Error Reporting**: More detailed error descriptions for screen readers
5. **Help Documentation**: Accessible user manual

## Resources

- [GTK4 Accessibility Documentation](https://docs.gtk.org/gtk4/section-accessibility.html)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [GNOME Accessibility Guide](https://developer.gnome.org/hig/patterns/containers/accessibility.html)
- [ATK Documentation](https://developer.gnome.org/atk/stable/)

## Reporting Accessibility Issues

If you encounter accessibility issues while using Wallpicker, please report them:

1. Describe the task you were trying to accomplish
2. Specify the assistive technology you're using (Orca, NVDA, VoiceOver)
3. Include steps to reproduce the issue
4. Describe the expected vs. actual behavior

Report issues at: https://github.com/gotar/wallpicker/issues

## Credits

Accessibility implementation follows W3C WCAG 2.1 guidelines and GNOME Human Interface Guidelines for accessibility.
