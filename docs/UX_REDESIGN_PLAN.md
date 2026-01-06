# Wallpicker UI/UX Redesign Implementation Plan

## Overview
Comprehensive UI/UX redesign to transform Wallpicker into a modern GTK4/Libadwaita application with adaptive layouts, smooth transitions, and polished components.

**Start Date:** 2026-01-06  
**Current Phase:** Phase 2 (Component Redesign)

---

## Progress Tracking

### ✅ Phase 1: Foundation (Completed)
- [x] Refactor main_window.py to use Adw.ToolbarView
- [x] Create Toast Service (toast_service.py) with Adw.ToastOverlay
- [x] Create reusable Status Page component (status_page.py)
- [x] Update CSS system with variables and theming
- [x] Update documentation (AGENTS.md)

**Test Results:** 237/237 tests passing ✅

---

### 🔄 Phase 2: Component Redesign (In Progress)
- [x] Redesign Wallpaper Cards (wallpaper_card.py) - DONE
- [ ] Modernize Search/Filter Bar with modern widgets

**Next:** Create modern search/filter bar component

---

### ⏳ Phase 3: Advanced Features (Pending)
- [ ] Implement Adw.Banner Service (banner_service.py)
- [ ] Add Multi-Selection Support
- [ ] Create Preview Dialog
- [ ] Add Current Wallpaper Indicator

### ⏳ Phase 4: Responsive & Adaptive (Pending)
- [ ] Implement Adaptive Layouts with Adw.Breakpoint
- [ ] Integrate Adw.Clamp
- [ ] Add Touch Gestures

### ⏳ Phase 5: Animations & Polish (Pending)
- [ ] Add Transitions
- [ ] Implement Keyboard Navigation
- [ ] Improve Accessibility

### ⏳ Phase 6: Testing & Refinement (Pending)
- [ ] Update Unit Tests
- [ ] Cross-Theme Testing
- [ ] Performance Optimization

### ⏳ Phase 7: Documentation & Release (Pending)
- [ ] Create Release Notes

---

## Files Created/Modified

### New Files
```
src/services/toast_service.py          - Native Adw.Toast notifications
src/ui/components/status_page.py       - Reusable loading/empty/error states
src/ui/components/wallpaper_card.py     - Modern card with animations
```

### Modified Files
```
src/ui/main_window.py              - Refactored to Adw.ToolbarView
data/style.css                    - Modern CSS with variables
AGENTS.md                          - Updated architecture documentation
docs/UX_REDESIGN_PLAN.md          - This file (NEW)
```

---

## Implementation Notes

### Component Design Patterns

**Wallpaper Card:**
- Size: 280x200px (minimum)
- Image: 260x140px with ContentFit.COVER
- Double-click: Set wallpaper
- States: default, hover, selected, current (with pulse animation)
- Actions: Set wallpaper, favorite, download (Wallhaven), info, delete (Local)

**Status Page:**
- Stack-based with 4 states: loading, empty, error, content
- Crossfade transitions (300ms)
- Retry button on error state
- Configurable titles/descriptions

**Toast Service:**
- Window-level Adw.ToastOverlay
- Methods: success (4s timeout), error (6s, high priority), info (3s), warning (5s)
- Optional undo/callback buttons
- FIFO queue for multiple toasts

---

## Testing Strategy

### Current Test Coverage
- Unit tests: 237 passing
- Coverage: 93%
- All service, domain, and view model tests passing

### Tests to Add (Phase 6)
- [ ] ToastService unit tests
- [ ] WallpaperCard component tests
- [ ] StatusPage component tests
- [ ] BannerService tests (when created)
- [ ] Integration tests for new UI components
- [ ] Cross-theme visual regression tests

---

## Next Steps

### Immediate (Phase 2)
1. Create modern Search/Filter Bar component
   - Use Gtk.DropDown for sorting
   - Adw.Revealer for filter panel
   - Active filter chips (removable)
   - Debounced search entry (300ms)

2. Integrate new components into views
   - Replace old wallpaper cards in all 3 views
   - Replace old status/error displays
   - Connect toast service

### Short-term (Phase 3-4)
3. Implement BannerService and multi-selection
4. Create Preview Dialog component
5. Add current wallpaper indicator to header
6. Implement adaptive layouts with breakpoints

### Long-term (Phase 5-7)
7. Add animations and transitions
8. Implement keyboard navigation
9. Accessibility improvements
10. Performance optimization
11. Final testing and documentation

---

## Configuration Required

### No Configuration Changes Needed
All existing functionality preserved. No breaking changes to config file format.

### Future Configuration Options
- `adaptive_ui_enabled`: Enable/disable responsive layouts (default: true)
- `animations_enabled`: Enable/disable animations (default: true)
- `card_size`: Preferred card size (default: 280x200)

---

## Dependencies (Current)
```
requests>=2.31.0
Pillow>=10.0.0
PyGObject>=3.46.0
send2trash>=1.8.2
aiohttp>=3.9.0
rapidfuzz>=3.0.0
```

**No new dependencies required** - using only GTK4 and Libadwaita 1.4+ features.

---

## Migration Notes

### For Developers
- All ViewModels unchanged (backward compatible)
- New UI components optional initially
- Can incrementally replace old components

### For Users
- No migration needed (seamless upgrade)
- All existing features preserved
- UI improvements only (no data changes)

---

## Rollback Plan

If issues arise:
1. Git revert to pre-redesign commit
2. Restore old main_window.py from backup
3. Disable new components via feature flags
4. Fix issues and re-deploy

---

## Contact & Support

For questions about this redesign, reference:
- Original design plan from frontend-ui-ux-engineer
- GTK4/Libadwaita documentation: https://docs.gtk.org/gtk4/
- Libadwaita documentation: https://gnome.pages.gitlab.gnome.org/libadwaita/

---

**Last Updated:** 2026-01-06  
**Status:** Phase 1 Complete, Phase 2 In Progress
