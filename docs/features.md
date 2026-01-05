# Wallpicker Features Specification

This document outlines the required features and expected behavior for the Wallpicker application. Use this as a reference to verify correct implementation.

## App-Wide Features

### Configuration
- Loads settings from `~/.config/wallpicker/config.json`
- Supports custom local wallpapers directory (`local_wallpapers_dir`)
- Falls back to `~/Pictures` if configured directory doesn't exist
- Persists user preferences
- System notifications toggle (`notifications_enabled`)

### Caching System
- ThumbnailCache for Wallhaven images (7-day expiry, 500MB limit)
- Automatic cleanup of expired/old thumbnails
- Disk-based persistent caching

### UI Framework
- GTK4 + Libadwaita for modern native interface
- MVVM architecture with ViewModels and Services
- Responsive layout with proper theming
- Async operations to prevent UI blocking

### Wallpaper Setting
- Sets desktop wallpaper using `awww` utility
- Supports animated transitions
- Symlink-based wallpaper management (`~/.cache/current_wallpaper`)

### Notifications
- System notifications for successful actions (add to favorites, delete wallpaper)
- Configurable via `notifications_enabled` setting (default: true)
- Uses `notify-send` for desktop notifications
- Graceful fallback when notifications are unavailable

## Local Tab

### Core Functionality
- Browses wallpapers from configured directory (default: `~/Pictures`)
- Displays thumbnail previews (180x180)
- Shows filename as tooltip on hover
- Counts total wallpapers in status bar

### Actions Per Wallpaper
- **Set as Wallpaper**: Sets the image as desktop background
- **Add to Favorites**: Adds wallpaper to favorites collection with notification
- **Delete**: Moves file to trash with confirmation dialog and notification

### Features
- Recursive directory scanning
- Supports common image formats (jpg, png, webp, bmp, gif)
- Real-time directory changes (refresh button)
- Custom directory selection via folder button or config
- System notifications for successful actions

## Wallhaven Tab

### Core Functionality
- Searches Wallhaven.cc API for wallpapers
- Displays thumbnail grid with pagination
- Filters by category, purity, sorting, resolution

### Search & Filters
- Text search with fuzzy matching
- Category: General, Anime, People
- Purity: SFW, Sketchy, NSFW
- Sorting: Date Added, Relevance, Random, Views, Favorites, Toplist
- Resolution filters

### Actions Per Wallpaper
- **Set as Wallpaper**: Downloads and sets as background
- **Add to Favorites**: Saves to local favorites collection

### Features
- Rate limiting (45 requests/minute)
- Thumbnail caching for performance
- Pagination with prev/next buttons
- Status updates during search

## Favorites Tab

### Core Functionality
- Displays user's saved favorite wallpapers
- Thumbnail grid with filename tooltips
- Counts total favorites in status bar

### Actions Per Wallpaper
- **Set as Wallpaper**: Sets favorite as desktop background
- **Remove from Favorites**: Deletes from collection with confirmation

### Features
- Persistent storage in `~/.config/wallpicker/favorites.json`
- Search within favorites
- Automatic refresh after additions/removals
- Auto-refresh when switching to tab
- Backwards compatibility with old favorites format

## Expected Behavior

### Startup
- App loads config and initializes services
- Local and Favorites tabs populate immediately
- Thumbnails load asynchronously in background
- No UI blocking during thumbnail loading

### Performance
- Smooth scrolling through large collections
- Fast search and filtering
- Efficient memory usage
- Background thumbnail loading

### Error Handling
- Graceful fallback for missing images
- User-friendly error messages
- Confirmation dialogs for destructive actions
- Config validation with sensible defaults

### User Experience
- Intuitive navigation between tabs
- Consistent action buttons across tabs
- Visual feedback for operations
- Keyboard and mouse support

## Testing Notes

Tests currently cover backend services and models:
- LocalWallpaperService directory scanning
- FavoritesService persistence
- ConfigService validation
- WallpaperSetter functionality

UI integration tests are missing, which allowed simplified UI to pass tests. Future tests should include:
- UI widget creation and interaction
- ViewModel data binding
- End-to-end user workflows

## Implementation Checklist

Use this to verify complete implementation:

- [x] Config loading and custom directory support
- [x] Thumbnail caching system
- [x] Local tab with full-size previews and actions
- [x] Wallhaven search and filtering
- [x] Favorites management
- [x] Async thumbnail loading
- [x] Error handling and confirmations
- [x] Responsive UI layout
- [x] Wallpaper setting with transitions
- [x] System notifications for actions
- [x] Folder button for directory selection
- [x] Auto-refresh favorites tab
- [x] Backwards compatibility for old favorites format
