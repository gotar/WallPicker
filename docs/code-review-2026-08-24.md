# WallPicker — Deep Code Review & Fix Plan

**Date:** 2026-01-16+ / reviewed 2026-08-24
**Scope:** full project (`src/` ~9.6k LOC, `tests/`, packaging), reviewed by 5 parallel agents
**Verification baseline:** tests pass in `.venv` (314 passed), coverage **53%** (AGENTS.md claims >95%), `ruff` clean, `mypy src/` vacuous (almost everything excluded)

---

## ROOT CAUSE #1 — asyncio runs on a background thread; GTK is touched from it everywhere

`src/core/asyncio_integration.py:21-38` (`setup_event_loop`) runs the asyncio loop on a
**daemon thread**; `schedule_async()` = `run_coroutine_threadsafe()`. Every coroutine
continuation therefore executes off the GTK main thread, yet large parts of the codebase
directly mutate GObject properties, emit signals, create widgets, and show toasts there.
GTK4 is not thread-safe → intermittent crashes/corruption that "mostly works".

Affected (verified):
- All VM property writes: `is_busy`, `error_message`, `wallpapers`
  (`wallhaven_view_model.py:246-285`, `local_view_model.py:237-243,281`,
  `favorites_view_model.py:86-303`)
- Direct widget building from a notify handler:
  `local_view.py:334-355` `_on_wallpapers_changed` → `_create_wallpaper_card`
- Signal emissions from async context: `local_view_model.py:617` (`_finish_upscale`),
  `:701` (`_finish_tag`) → handlers touch overlays/toasts (`local_view.py:663-800,939,1021`)
- Toasts after `await`: all views + `favorites_view_model.py:327-333`
- Pagination labels: `wallhaven_view.py:392-408`

Note the codebase is *inconsistent*: `search_wallpapers` correctly uses
`GLib.idle_add(self._set_wallpapers, ...)` — the pattern already exists, it just isn't used
everywhere.

## ROOT CAUSE #2 — non-atomic file writes everywhere

Config, favorites, thumbnails, downloads, symlink: plain truncate-and-write.
Crash/power-loss mid-write permanently corrupts user data (all favorites lost) or poisons
caches with files that are then served forever as valid.

---

## CRITICAL

| # | Bug | Location | Fix |
|---|-----|----------|-----|
| C1 | GTK widgets/signals manipulated from asyncio background thread (systemic — see Root Cause #1) | `asyncio_integration.py`, all VMs, all views | Introduce `BaseViewModel._set_property_idle()` / idle-dispatch helper; route ALL property writes, signal emissions and toast calls through `GLib.idle_add`. Make `ToastService.show_*` hop internally. |
| C2 | Upscale failure mid-rename loses original wallpaper: `rename(backup)` succeeds, `temp.rename(path)` fails → backup never restored | `local_view_model.py:556-573` | In except branch: if `backup.exists() and not path.exists(): backup.rename(path)` before reporting failure |
| C3 | clip-cpp subprocess has no timeout → 2 hung processes permanently deadlock the tag queue + zombie leak | `tag_generation.py:286-296` | `await asyncio.wait_for(proc.communicate(), timeout=120)`; on timeout `proc.kill(); await proc.communicate()` |

## HIGH

| # | Bug | Location | Fix |
|---|-----|----------|-----|
| H1 | Partial download left on disk is later returned as a valid wallpaper ("already downloaded" check hits truncated file) | `wallhaven_service.py:207` + `wallhaven_view_model.py:450` | Download to `.part`, `os.replace()` on success, delete `.part` on error |
| H2 | Single-card refresh broken twice: `_refresh_wallpaper_card` grabs Overlay instead of Picture (AttributeError swallowed by GLib); primary success path never reloads image at all → old thumbnail shown after upscale | `local_view.py:806-826`, `828-884` | Store `Gtk.Picture` refs per path alongside `_metadata_labels`; find Picture inside overlay; reload paintable in `_refresh_wallpaper_card_by_path` |
| H3 | PreviewDialog remote images ALWAYS fail for uncached Wallhaven items: `download_and_cache(url, None)` → `session.get` on None → AttributeError → "Failed to load image" | `preview_dialog.py:340-360`, `thumbnail_cache.py:127` | Call `get_or_download_async(url)` instead |
| H4 | Search button & pull-to-refresh reset everything to defaults: set nonexistent `view_model.query` (silently creates dead attr), call `search_wallpapers()` with no args → toplist search ignoring user query/filters | `wallhaven_view.py:339-342, 381-384, 432-449`; VM API at `wallhaven_view_model.py:191-260` | Add VM method `apply_current_filters_and_search()` reading its own properties; call it from both places |
| H5 | Infinite scroll dead code: `EventControllerScroll()` created with default flags NONE → no events ever delivered | `wallhaven_view.py:296-302` | `set_flags(VERTICAL)` + busy/debounce guard in `_on_scroll` |
| H6 | One malformed favorites.json entry kills loading of ALL favorites (enum ValueError / KeyError / isoformat ValueError, no per-item handling) | `wallpaper.py:139-140`, `favorite.py:43-47`, `favorites_service.py:84` | Guarded enum conversion with fallbacks in `from_dict`; per-item try/except skip+log in `_parse_favorites_data` |
| H7 | Blocking PIL decode + JSON reads on UI thread during sort/filter of local library (hundreds of `Image.open` per keystroke) | `local_service.py:44-77`; callers `local_view.py:700,720-727,1141-1147`, `local_view_model.py:277,328-331,364-367` | Pre-resolve resolutions via `asyncio.to_thread` during scan; make resolution/tags eagerly-loaded fields |
| H8 | Shared `_active_count` between upscale & tag queues → combined limit 2 (not 2+2), misleading UI counts | `local_view_model.py:69-70,176-178,594-600,687-703` | Separate `_upscale_active_count` / `_tag_active_count` |
| H9 | Queue state mutated from both GTK thread and asyncio thread without lock (check-then-act on deque/counters) → stuck spinners, lost tasks | `local_view_model.py:583-598,608-620,668-703` | `threading.Lock` around queue ops, or funnel all mutations through the asyncio thread |

## MEDIUM

| # | Bug | Location | Fix |
|---|-----|----------|-----|
| M1 | Non-atomic config/favorites writes destroy data on crash | `favorites_service.py:227`, `config_service.py:41,86` | tmp file + `os.replace()` |
| M2 | Thumbnail disk cache keyed with builtin `hash()` → salted per process, cache NEVER hit after restart, orphans accumulate forever | `thumbnail_loader.py:54-55` | `hashlib.md5(str(path)).hexdigest()` |
| M3 | `ThumbnailCache.cleanup()` TOCTOU races between 4 worker threads (`f.stat()` FileNotFoundError kills whole download); cleanup runs on every download | `thumbnail_cache.py:54,70-71` | try/except around stat; debounce/startup-only cleanup |
| M4 | Corrupt cache entries served forever (in-place write, only existence+mtime checked) | `thumbnail_cache.py:87-96,110-113` | atomic write + invalidate on decode failure |
| M5 | Rate-limiter check-then-act race; no HTTP 429 handling at all | `wallhaven_service.py:41-47,139` | `asyncio.Lock` around sleep+update; backoff on 429 |
| M6 | aiohttp session never closed (`close()` has zero callers); `__del__` cleanup unsafe from GC thread | `wallhaven_service.py:225-235` | wire into `Adw.Application.do_shutdown` / window destroy |
| M7 | `search_favorites` returns `list[Favorite]` OR `list[Wallpaper]` depending on query | `favorites_service.py:203 vs 214` | always return `[f.wallpaper for f in favorites]` |
| M8 | clip-anytorch detection checks wrong module; second import block unreachable → documented fallback is dead code | `tag_generation.py:49-63` | single probe chain incl. `import clip_anytorch` |
| M9 | Category checkboxes radio-grouped → Wallhaven bitmask categories impossible (Anime silently unchecks General) | `search_filter_bar.py:158-159,275-296` | remove `set_group()`, accumulate bits |
| M10 | Filter-chip removal keys mismatch display vs backend names → stale sort filter re-sent forever; chips container never attached to UI (invisible feature) | `search_filter_bar.py:120-126,500-537` | normalize keys; append chips container in views |
| M11 | `do_activate` rebuilds window + ViewModels on every activation (D-Bus relaunch) → leaked windows, duplicated signals/loads | `main_window.py:59-137` | early-return/present existing window |
| M12 | Ctrl+Shift+Tab unreachable — first branch matches Tab regardless of Shift | `main_window.py:383-400` | check SHIFT before generic Tab branch |
| M13 | Upscale/tag-complete fallback hides the WRONG card's overlay ("first wallpaper with a card") → real card spinner stuck forever | `local_view.py:786-801,713-720` | track pending work keyed by path; no first-match fallback |
| M14 | Stale async results overwrite newer state (no generation counter): rapid filter changes race; favorites refresh double-schedules loads | `local_view_model.py:255-302`, `favorites_view_model.py:96-100` | monotonic generation counter, discard stale completions |
| M15 | Transient search error wipes existing grid results | `wallhaven_view_model.py:265-269` | keep old wallpapers, show toast |
| M16 | `FavoritesViewModel._show_toast` calls nonexistent `get_root()` → every favorites toast silently dies (+ MVVM violation) | `favorites_view_model.py:279-295` | inject toast service like LocalViewModel does |
| M17 | Shared `is_busy` toggled from concurrent ops → spinner cleared early / error flags crossed | all VMs, `base.py` | busy depth counter |
| M18 | Favorites keyboard Space removes wrong record (`wallpaper.id` vs `favorite.wallpaper_id`) | `favorites_view.py:160-166 vs 418` | pass the Favorite object |
| M19 | PreviewDialog builds Gdk.Texture in raw worker thread + manual `threading.Thread` (project forbids); mutates widgets after dialog close | `preview_dialog.py:310-388` | decode pixbuf in thread, construct Texture in idle_add; guard with closed flag |
| M20 | Blocking MD5 hash of entire library on UI thread (find-by-hash) | `local_view_model.py:126-155`, called `local_view.py:454,462` | `asyncio.to_thread` + size pre-filter + mtime-keyed cache |
| M21 | Zero-division trap: `Resolution.aspect_ratio` with default `Resolution(0,0)` from `from_dict` | `wallpaper.py:30-32,131-134` | guard height, validate > 0 |
| M22 | `launcher.sh` relaunches app as second instance whenever first exits non-zero (crash looks like restart) | `launcher.sh:3-7` | probe interpreter availability up front; don't fall back on app exit codes |
| M23 | `main.py` secondary entry point never calls `setup_event_loop()` → first `schedule_async` raises RuntimeError | `main.py:16-25` | delete `main.py` or fix init |
| M24 | install.sh desktop-entry sed targets wrong string → installed Exec points to nonexistent `/usr/bin/wallpicker` | `install.sh:88-90` | sed actual `Exec=/usr/bin/wallpicker` line |
| M25 | install.sh pip `--user` fails on PEP 668 systems (Debian 12+, Fedora) | `install.sh:44` | use venv or `--break-system-packages` |
| M26 | Version chaos: pyproject=2.5.3, PKGBUILD/aur=2.5.4, root `.SRCINFO`=2.2.3 | packaging files | bump to one version, regenerate .SRCINFOs |
| M27 | No teardown for event loop / container: SIGINT hard-kills, in-flight JSON write can be truncated (ties into M1); `ServiceContainer` is dead code anyway | `asyncio_integration.py:31-40`, `container.py`, `launcher.py:33` | graceful shutdown hook; delete or properly adopt container |
| M28 | `schedule_async` returns concurrent Future annotated as Task; exceptions never observed anywhere → silent failures + misleading API | `asyncio_integration.py:59-91`, `main_window.py:226-231` | add logging done-callback internally; fix type hints |

## LOW (selected)

| # | Bug | Location |
|---|-----|----------|
| L1 | Unbounded in-memory thumbnail cache (RAM growth) | `thumbnail_loader.py:152,172` |
| L2 | Negative tag-cache result re-reads disk on EVERY property access (missing `_tags_loaded` flag); hit 3×/card/render + per keystroke in search | `local_service.py:62-70,185` |
| L3 | Non-atomic symlink update (`unlink`→`symlink_to` window; FileExistsError if regular file present) | `wallpaper_setter.py:75-78` |
| L4 | `notify-send` without timeout can hang worker forever | `notification_service.py:31-35` |
| L5 | Pillow handle leak in CLIP preprocessing | `tag_generation.py:119` |
| L6 | No explicit aiohttp timeouts (300 s default stall) | `wallhaven_service.py:36-40` |
| L7 | `_clear_grid` doesn't clear `_tags_labels`/`_tag_overlays` → destroyed widgets retained | `local_view.py:238-251` |
| L8 | Double debounce (300+300 ms) + timers never cancelled on destroy | `search_filter_bar.py:333`, views |
| L9 | Flash-animation timeouts touch possibly-disposed cards | `local_view.py:820-822,877-879` |
| L10 | Selection list retains removed wallpapers → select_all operates on dead paths | `base.py:47-56` |
| L11 | Initial load ignores configured purity/order (hardcoded SFW desc) | `wallhaven_view_model.py:170-188` |
| L12 | Queue item leaked if schedule fails after count increment | `local_view_model.py:597,689` |
| L13 | Narrow exception handlers in fire-and-forget coroutines swallow unexpected errors | various VMs |
| L14 | Dead code: `WallpaperCard` component unused + stub loader, `_needs_full_rebuild` flag unread, empty try/finally | `wallpaper_card.py`, `local_view.py:176-185,599-601` |
| L15 | `Favorite.from_dict(wallpaper_class=...)` ignored param; naive/aware datetime subtraction trap | `favorite.py:15-47` |
| L16 | Config validation blocks ALL saves when wallpapers dir missing externally | `config.py:26-37`, `config_service.py:82` |
| L17 | Stray root `test_tagging.py` pseudo-test hitting real model/hardcoded path | repo root |
| L18 | Unused dep `requests` declared everywhere; mypy overrides make `mypy src/` vacuous | `requirements.txt`, `pyproject.toml` |
| L19 | Redundant asyncio markers + deprecated `event_loop` fixture (breaks pytest-asyncio ≥0.26) | `pyproject.toml`, `conftest.py` |
| L20 | `assert True` placeholder tests | `test_wallpaper_setter.py:389`, `test_base_view_model.py:135` |

---

# FIX PLAN (4 phases, ordered by risk ÷ effort)

## Phase 1 — Data integrity & crashes (half day)
*No architecture changes; small, surgical, testable fixes.*
1. **C2** restore-from-backup in upscale replace (`local_view_model.py:556-573`)
2. **H1** atomic `.part` downloads (`wallhaven_service.py`)
3. **M1** atomic config/favorites writes (tmp + `os.replace`)
4. **H6/M6** per-item favorite parsing guards; guarded enum conversion in domain `from_dict`
5. **C3** subprocess timeouts (`tag_generation.py`, plus `notification_service.py` L4)
6. **M2** stable cache key (`hashlib.md5`) + **M3/M4** cache TOCTOU guards & atomic write
7. **M21** zero-guard `Resolution.aspect_ratio`

## Phase 2 — Threading correctness (the big one, ~2 days)
*Root Cause #1. Do after Phase 1 so behavior changes are isolated.*
1. Add to `BaseViewModel`: `_set_property_idle(name, value)`, `_emit_idle(signal, *args)`
   using `GLib.idle_add`; migrate ALL async-context property writes/signal emissions
   (C1, VM findings #1/#2)
2. Make `ToastService.show_*` internally marshal via `idle_add`
3. Fix `views/local_view._on_wallpapers_changed` to run on main thread only
4. **H9/H8**: separate + lock-protect upscale/tag queue counters; enqueue only from asyncio side
5. **M28**: done-callback logging in `schedule_async`; correct type hints
6. **M19**: PreviewDialog — pixbuf decode in thread, Texture on main thread, drop raw Thread
7. **M27**: graceful shutdown (`loop.call_soon_threadsafe(loop.stop)` on app quit; close aiohttp session M6)
8. Regression-test: run app under `G_DEBUG=fatal-warnings`, exercise all tabs/queues

## Phase 3 — Broken user-facing features (1–1.5 days)
1. **H2** card refresh: store Picture refs, reload paintable after upscale
2. **H3** preview dialog: use `get_or_download_async`
3. **H4** search/pull-to-refresh honoring filters (new VM method)
4. **H5** infinite-scroll controller flags + guard
5. **M9/M10** category bitmask + chip key normalization (+ actually attach chips UI)
6. **M11** activate-guard; **M12** Shift+Tab ordering
7. **M13** per-path pending-work map (no wrong-card fallback)
8. **M14** generation counters for search/filter staleness; **M15** keep results on transient error
9. **M16** favorites toast service injection; **M18** Space-remove identity fix
10. **H7/L2/M20** move PIL/JSON/hash work off main thread (scan-time resolution loading,
    `_tags_loaded` flag, async hashing)

## Phase 4 — Tests, packaging, hygiene (1 day)
1. Add missing test coverage (currently 53%): `tests/services/test_tag_generation.py`,
   queue-concurrency tests for upscaler/tagger, wallpaper_setter failure paths, container teardown
2. Replace `assert True` placeholders; remove deprecated `event_loop` fixture; rename stray
   `test_tagging.py` → `scripts/manual_tagging_check.py`
3. Packaging: unify versions (pyproject/PKGBUILD/.SRCINFO), fix install.sh Exec-line sed +
   PEP 668, drop unused `requests`, align clip-anytorch optional dep
4. Delete/reduce dead code: `main.py`, `ServiceContainer` (or wire it in), `WallpaperCard`,
   `_needs_full_rebuild`, unreachable clip-anytorch block (M8 fix covers)
5. Tighten `mypy` overrides gradually (ui last); keep `ruff` green
6. Update AGENTS.md coverage claim or raise coverage toward it

## Suggested verification loop per phase
```bash
.venv/bin/python -m pytest tests/ -q        # must stay green
ruff check .
G_DEBUG=fatal-warnings timeout 60 ./launcher.sh   # manual smoke per phase
```
