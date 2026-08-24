"""Regression tests for upscale/tag completion handling in LocalView.

These tests exercise the completion handlers without instantiating GTK
widgets: LocalView is created via ``__new__`` and only the state the
handlers touch is provided.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _make_local_view():
    from ui.views.local_view import LocalView

    view = LocalView.__new__(LocalView)
    view._path_card_map = {}
    view._upscale_overlays = {}
    view._tag_overlays = {}
    view.toast_service = None
    return view


class TestUpscaleCompletionRouting:
    """Completion events must touch only the card that queued the work."""

    def test_no_pending_path_state_remains(self):
        """The write-only pending path sets are dead state and must be gone."""
        import inspect

        from ui.views.local_view import LocalView

        source = inspect.getsource(LocalView)
        assert "_pending_upscale_paths" not in source
        assert "_pending_tag_paths" not in source

    def test_upscale_completion_for_evicted_card_touches_nothing(
        self, tmp_path, mocker
    ):
        """A completion event for an evicted/unknown card must not affect
        unrelated cards (no first-match fallback, M13)."""
        view = _make_local_view()

        card_a = object()
        path_a = str(tmp_path / "a.jpg")
        view._path_card_map[path_a] = card_a

        hidden = []
        refreshed = []
        mocker.patch.object(view, "_hide_upscale_overlay", side_effect=hidden.append)
        mocker.patch.object(
            view, "_refresh_wallpaper_card_by_path", side_effect=refreshed.append
        )

        # Completion for an unknown (evicted) path: unrelated card untouched.
        view._on_upscale_complete(None, True, "done", str(tmp_path / "evicted.jpg"))
        assert hidden == []
        assert refreshed == []

        # Completion for the known path still routes to the right card.
        view._on_upscale_complete(None, True, "done", path_a)
        assert hidden == [card_a]
        assert refreshed == [path_a]

    def test_tag_completion_for_evicted_card_touches_nothing(self, tmp_path, mocker):
        """Same guarantee for tagging completions."""
        view = _make_local_view()

        card_b = object()
        path_b = str(tmp_path / "b.jpg")
        view._path_card_map[path_b] = card_b

        hidden = []
        refreshed = []
        mocker.patch.object(view, "_hide_tag_overlay", side_effect=hidden.append)
        mocker.patch.object(
            view, "_refresh_wallpaper_card_by_path", side_effect=refreshed.append
        )

        view._on_tagging_complete(None, False, "failed", str(tmp_path / "evicted.jpg"))
        assert hidden == []
        assert refreshed == []

        view._on_tagging_complete(None, True, "done", path_b)
        assert hidden == [card_b]
        assert refreshed == [path_b]
