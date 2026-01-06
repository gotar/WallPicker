# Adw.Clamp Integration Summary

## Overview
Integrated Adw.Clamp into Wallpicker's main layout to constrain maximum width and provide optimal readability across different screen sizes.

## Implementation Details

### 1. Main Window Layout Changes

**File:** `src/ui/main_window.py`

**Changes:**
- Replaced `stack_with_banner` Gtk.Box with Adw.Clamp wrapping the ViewStack
- Added banner widget as a separate bottom bar element (between Clamp and ViewSwitcherBar)
- Configured clamp with optimal settings for wallpaper grid display

**Configuration:**
```python
clamp = Adw.Clamp()
clamp.set_maximum_size(1400)      # Max width: 1400px
clamp.set_tightening_threshold(1000)  # Start tightening at 1000px
clamp.set_child(self.stack)       # Wrap ViewStack
```

**Content Hierarchy:**
```
WallPickerWindow (ApplicationWindow)
 └─ Adw.ToolbarView
     ├─ Adw.HeaderBar
     ├─ Adw.Clamp (NEW)
     │   └─ Adw.ViewStack
     │       ├─ LocalView
     │       ├─ WallhavenView
     │       └─ FavoritesView
     ├─ Adw.Banner (below Clamp, above ViewSwitcherBar)
     └─ Adw.ViewSwitcherBar
```

### 2. CSS Styling

**File:** `data/style.css`

**Added Styles:**
```css
/* Adw.Clamp Styling */
clamp {
    halign: center;
}

/* Clamp automatically centers content and handles width constraints
 * No additional CSS needed for the tightening effect - it's native
 * to Adw.Clamp behavior */
```

**Note:** Most behavior is native to Adw.Clamp through API properties, so minimal CSS is required.

### 3. Verification Script

**File:** `verify_clamp_layout.py`

**Features:**
- Interactive GUI test to visualize clamp behavior across different window sizes
- Property verification mode (`--test` flag) to verify configuration values
- Quick resize buttons to test specific window widths (800, 1000, 1200, 1400, 1600, 1920)
- Real-time width display showing window vs content width
- Visual grid of placeholder cards to demonstrate centering behavior

**Usage:**
```bash
# Run interactive verification
python verify_clamp_layout.py

# Run property verification only
python verify_clamp_layout.py --test
```

## Clamp Behavior

### Width Ranges and Behavior

| Window Width | Content Width | Behavior |
|--------------|---------------|----------|
| < 1000px | Full width | No margins, content spans full width |
| 1000-1400px | Full width | Decreasing margins (tightening effect) |
| > 1400px | Fixed 1400px | Content constrained to max width, centered |

### Visual Examples

**Narrow Window (800px):**
```
┌────────────────────────────────────┐
│        Header Bar (800px)          │
├────────────────────────────────────┤
│  Full width content (800px)        │
│  No margins                        │
│  2-3 columns visible              │
└────────────────────────────────────┘
```

**Medium Window (1200px):**
```
┌────────────────────────────────────────────────────┐
│           Header Bar (1200px)                      │
├──────────┬─────────────────────────────────────────┤
│          │                                         │
│ Margins  │  Full width content (1200px)           │
│ ~100px   │  4 columns visible                     │
│          │                                         │
└──────────┴─────────────────────────────────────────┘
```

**Wide Window (2000px):**
```
┌────────────────────────────────────────────────────────────────────────────┐
│                      Header Bar (2000px)                                │
├──────────────────────────┬───────────────────────────────────────────────┤
│                         │                                               │
│   Side margins (300px)  │  Clamped content (1400px max)                 │
│                         │  Centered content                              │
│                         │  6 columns visible                             │
│                         │                                               │
└──────────────────────────┴───────────────────────────────────────────────┘
```

## Interaction with Adaptive Breakpoints

Adw.Clamp and adaptive breakpoints work together:

- **Adaptive Breakpoints:** Control grid column count (2-6 columns based on available space)
- **Adw.Clamp:** Controls maximum content width (1400px)
- **Combined Effect:** Responsive columns within constrained maximum width

**Example scenarios:**
- 2000px window: Clamp to 1400px, 6 columns (max)
- 1000px window: Full width (1000px), 4 columns
- 700px window: Full width (700px), 3 columns

## Integration with Existing Components

Adw.Clamp does not conflict with:

- ✓ Adw.Banner (positioned below Clamp as bottom bar)
- ✓ Adw.ToastOverlay (wraps entire ToolbarView externally)
- ✓ Adw.HeaderBar (top bar, unaffected by clamp)
- ✓ Adw.ViewSwitcherBar (bottom bar, unaffected by clamp)
- ✓ Adaptive layout breakpoints (work together)

## Edge Cases Handled

### Narrow Windows (< 600px)
- Clamp does not interfere with minimum width
- Full width (no tightening yet)
- Content remains usable with reduced columns

### Ultra-Wide Windows (> 2000px)
- Clamp constrains content to 1400px maximum
- Content perfectly centered
- Side margins provide aesthetic balance

### Window Title Bar
- Spans full window width
- Not affected by clamp
- Positioned outside Adw.ToolbarView

## Testing Recommendations

1. **Verification Script:**
   ```bash
   python verify_clamp_layout.py
   ```

2. **Manual Testing:**
   - Resize window gradually from 600px to 2000px
   - Observe centering at different widths
   - Check grid column counts adapt correctly
   - Verify banner position remains consistent

3. **Edge Cases:**
   - Test at exactly 1000px and 1400px boundaries
   - Test with very narrow windows (< 600px)
   - Test with very wide windows (> 2000px)
   - Verify no overlap with banner or view switcher bar

## Benefits

1. **Improved Readability:** Constrained width prevents line readability issues on ultra-wide monitors
2. **Better Centering:** Content automatically centered on wide screens
3. **Responsive Margins:** Smooth tightening effect provides visual hierarchy
4. **Optimal for Wallpapers:** 1400px width allows comfortable 6-column grid for wallpaper thumbnails
5. **Native Implementation:** Uses GTK4/Libadwaita's built-in Adw.Clamp widget
6. **Minimal Code:** Clean integration with no custom layout logic needed

## Files Modified

1. `src/ui/main_window.py` - Added Adw.Clamp wrapping ViewStack
2. `data/style.css` - Added minimal clamp styling
3. `verify_clamp_layout.py` - Created verification script (new file)

## Verification

Run the verification script to confirm:
```bash
# Property verification
python verify_clamp_layout.py --test

# Interactive test
python verify_clamp_layout.py
```

Expected output from `--test` mode:
```
Verifying Adw.Clamp properties...

Default values:
  maximum_size: 600
  tightening_threshold: 400

Configured values:
  maximum_size: 1400
  tightening_threshold: 1000

✓ Clamp properties verified successfully
✓ max-width: 1400px
✓ tightening_threshold: 1000px
```
