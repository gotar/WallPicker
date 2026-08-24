# WALLPICKER

**Refactored:** 2026-01-05 (Updated: 2026-01-16 with v2.1 AI upscaling and resolution sorting)
**Type:** Python GTK4 + Libadwaita Desktop App (MVVM Architecture)

## OVERVIEW
Wallpaper picker with multi-source support (Wallhaven API + local files). Features a modern MVVM architecture, async operations, constructor-injected services, and comprehensive testing.

**Phase 2 Complete:** AI upscaling with waifu2x, AI tagging with CLIP models, concurrent queue processing, resolution sorting, and single-card refresh.

## STRUCTURE
```
./
├── src/
│   ├── core/         # Core infrastructure (asyncio/GTK integration, logging)
│   ├── domain/       # Domain entities and value objects
│   ├── services/     # Business logic services (Async)
│   └── ui/           # UI Layer (MVVM)
│       ├── components/    # Reusable UI components
│       ├── view_models/  # Presentation logic
│       └── views/        # GTK Widgets
├── tests/            # Pytest test suite
└── data/             # Assets
```

## KEY COMPONENTS

| Component | Location | Description |
|-----------|----------|-------------|
| **Entry Point** | `src/ui/main_window.py` | Orchestrates ViewModels and services with Adw.ToolbarView |
| **Domain Models** | `src/domain/` | Rich entities (Wallpaper, Config) |
| **Wallhaven** | `src/services/wallhaven_service.py` | Async API client (aiohttp) |
| **Local Files** | `src/services/local_service.py` | Local file management |
| **ViewModels** | `src/ui/view_models/` | Observable state for UI binding |
| **Toast Service** | `src/services/toast_service.py` | Native Adw.ToastOverlay for notifications |
| **Status Page** | `src/ui/components/status_page.py` | Reusable loading/empty/error states |
| **Views** | `src/ui/views/` | GTK widgets that bind to ViewModels |
| **AI Upscaler** | `src/ui/view_models/local_view_model.py` | waifu2x-ncnn-vulkan integration with queue |
| **AI Tagger** | `src/services/tag_generation.py` | CLIP-based image tagging with clip-anytorch/clip-cpp |

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

### AI Upscaling (v2.1)
- Config option `upscaler_enabled` in `~/.config/wallpicker/config.json`
- Uses waifu2x-ncnn-vulkan with CPU mode (avoids RADV driver bugs)
- Queue system with 2 concurrent operations
- Visual feedback: blocking overlay with spinner, flash animation on complete
- Auto-refresh of thumbnail and metadata (resolution/size)
- Image verification before replacement, backup on failure

### AI Tagging (v2.5.3)
- Config option `tagger_enabled` in `~/.config/wallpicker/config.json`
- Uses CLIP models via clip-anytorch (Python) or clip-cpp (C++ binary)
- Supports concurrent tagging with queue system
- Tags are cached persistently and displayed on wallpaper cards
- Fallback detection: prefers clip-anytorch, falls back to clip-cpp if available

### Async Operations
- Network and file I/O use `async`/`await`.
- UI invokes async methods via `GLib` integration or `asyncio`.
- No `threading.Thread` for IO-bound tasks (replaced by asyncio).

### Testing
- **Framework**: `pytest`
- **Coverage**: ~60% (target: >95%; see docs/code-review-2026-08-24.md Phase 4)
- **Fixtures**: `tests/conftest.py` handles mock services and async loops.
- **Structure**: Tests mirror source directory structure.

## CONFIGURATION
- **Config**: `~/.config/wallpicker/config.json`
- **Cache**: `~/.cache/wallpicker/` (Thumbnails, Logs)
- **Wallpaper Setting**: canonical omarchy state symlink
`~/.local/state/omarchy/current/background` via `omarchy-theme-bg-set`
(awww fallback; legacy `~/.config/omarchy/current/background` kept in sync)

## GENERAL TASK WORKFLOW

Every non-trivial task follows this loop, in order:

1. **General idea** — one-paragraph statement of the task: what changes for the
   user, which areas of the repo are touched.
2. **Grill me (automatic)** — run the `grill-me` skill: self-interrogate scope,
   edge cases, acceptance criteria, compatibility and rollout. Produce a frozen
   Q&A ledger; every answer tagged `[repo]` (cite file:line) or `[default]`
   (safest reversible assumption). No user round-trip.
3. **TDD implementation** — per bug/feature:
   - write the failing test first (see red),
   - minimal implementation to green,
   - test + fix in ONE atomic commit:
     `fix(<scope>): <what+why> (review <ID>)` / `feat(<scope>): ...` /
     `test(<scope>): ...`.
   Suite (`pytest`) and `ruff` must be green before every commit. Never run
   potentially-hanging commands without a `timeout` prefix.
4. **Worktrees & subagents** — parallel work uses managed git worktree lanes
   (one writer per worktree), each lane with DISJOINT file claims recorded in a
   lane board before launch, gated on pytest+ruff, reporting its branch/commits.
   Shared seams (same file touched by two concerns) stay in ONE sequential lane.
   A fresh-context read-only reviewer verifies merged results afterwards.
5. **Review loop** — after implementation, an independent review pass verifies
   every item semantically (not superficially) and hunts for regressions the
   diff introduced. Findings loop back to step 3 until zero remain.
6. **Commit, push, publish** — when the loop is done:
   - sync version across `pyproject.toml`, `PKGBUILD`, `.SRCINFO`,
     `aur/PKGBUILD`, `aur/.SRCINFO` (ALL five must agree, including the
     `#tag=vX.Y.Z` source lines) and add a CHANGELOG entry,
   - commit `chore(release): bump version to X.Y.Z`, tag `vX.Y.Z`,
   - `git push origin master --tags` (AUR PKGBUILD builds from that GitHub tag),
   - publish to AUR with `./aur-push.sh` (clones
     `aur@aur.archlinux.org:wallpicker.git`, copies `aur/PKGBUILD` +
     `aur/.SRCINFO`, commits "Update to vX.Y.Z", pushes).

## WALLPAPER SETTING (omarchy integration)

The omarchy shell renders the desktop background from the canonical symlink
`~/.local/state/omarchy/current/background`; it does NOT need a compositor
wallpaper drawn underneath. WallPicker integrates via `omarchy-theme-bg-set`
(which updates that link and notifies the shell over IPC) — see
`src/services/wallpaper_setter.py`. Direct `awww img` calls are only a
fallback for non-omarchy systems; calling them on top of the shell path draws
a second wallpaper layered over the theme's. Legacy link
`~/.config/omarchy/current/background` is kept in sync for old consumers only.

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
- **Runtime**: `PyGObject`, `aiohttp`, `Pillow`, `rapidfuzz`, `send2trash`
- **Dev**: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`
- **Optional**: `awww` (animated transitions), `waifu2x-ncnn-vulkan` (AI upscaling), `clip-anytorch` (AI tagging)
