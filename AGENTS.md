# WALLPICKER

**Refactored:** 2026-01-05 (Updated: 2026-01-06 with Phase 1 UI/UX improvements)
**Type:** Python GTK4 + Libadwaita Desktop App (MVVM Architecture)

## OVERVIEW
Wallpaper picker with multi-source support (Wallhaven API + local files). Features a modern MVVM architecture, async operations, dependency injection, and comprehensive testing. 

**Phase 1 Complete:** Refactored to modern Adw.ToolbarView layout with native Toast notifications and reusable Status Page components.

## STRUCTURE
```
./
├── src/
│   ├── core/         # Core infrastructure (DI container, logging)
│   ├── domain/       # Domain entities and value objects
│   ├── services/     # Business logic services (Async)
│   └── ui/           # UI Layer (MVVM)
│       ├── components/    # Reusable UI components (NEW)
│       ├── view_models/  # Presentation logic
│       └── views/        # GTK Widgets
├── tests/            # Pytest test suite
└── data/             # Assets
```

## KEY COMPONENTS

| Component | Location | Description |
|-----------|----------|-------------|
| **Entry Point** | `src/ui/main_window.py` | Orchestrates DI container and ViewModels with Adw.ToolbarView |
| **DI Container** | `src/core/container.py` | Manages service lifecycles and dependencies |
| **Domain Models** | `src/domain/` | Rich entities (Wallpaper, Config) |
| **Wallhaven** | `src/services/wallhaven_service.py` | Async API client (aiohttp) |
| **Local Files** | `src/services/local_service.py` | Local file management |
| **ViewModels** | `src/ui/view_models/` | Observable state for UI binding |
| **Toast Service** | `src/services/toast_service.py` (NEW) | Native Adw.ToastOverlay for notifications |
| **Status Page** | `src/ui/components/status_page.py` (NEW) | Reusable loading/empty/error states |
| **Views** | `src/ui/views/` | GTK widgets that bind to ViewModels |

## ARCHITECTURE CONVENTIONS

### MVVM Pattern
- **Models**: Domain entities (`src/domain`) and Services (`src/services`)
- **ViewModels**: Expose observable properties (`GObject.Property`) and command methods. No GTK widget references.
- **Views**: GTK widgets that bind to ViewModels. No business logic.
- **Components**: Reusable UI elements (`src/ui/components/`).

### Modern UI Layout (Phase 1)
- **Adw.ToolbarView**: Proper header/content separation with flat styling
- **Adw.HeaderBar**: Window title, refresh button, menu button
- **Adw.ViewSwitcherBar**: Tab navigation at bottom
- **Adw.ToastOverlay**: Window-level native notifications (replaces inline errors)
- **Adw.StatusPage**: Empty/loading/error states with Adw.Stack

### Dependency Injection
- Services are registered in `ServiceContainer`.
- Dependencies are injected via constructor.
- `main_window.py` bootstraps the container.

### Async Operations
- Network and file I/O use `async`/`await`.
- UI invokes async methods via `GLib` integration or `asyncio`.
- No `threading.Thread` for IO-bound tasks (replaced by asyncio).

### Testing
- **Framework**: `pytest`
- **Coverage**: >95%
- **Fixtures**: `tests/conftest.py` handles mock services and async loops.
- **Structure**: Tests mirror source directory structure.

## CONFIGURATION
- **Config**: `~/.config/wallpicker/config.json`
- **Cache**: `~/.cache/wallpicker/` (Thumbnails, Logs)
- **Wallpaper Setting**: Symlink at `~/.cache/current_wallpaper` + `awww`

## COMMANDS
```bash
# Run Application
./launcher.sh

# Run Tests
python -m pytest tests/

# Code Quality
ruff check .
black .
mypy src/
```

## DEPENDENCIES
- **Runtime**: `PyGObject`, `aiohttp`, `requests`, `Pillow`, `rapidfuzz`, `send2trash`
- **Dev**: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `black`, `mypy`
