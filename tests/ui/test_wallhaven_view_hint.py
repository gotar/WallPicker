"""Tests for the few-results pagination hint in WallhavenView."""

import pytest

from ui.views.wallhaven_view import few_results_hint


def _gtk_display_available() -> bool:
    """Widget instantiation needs a live display; skip headless CI."""
    try:
        from gi.repository import Gdk

        return Gdk.Display.get_default() is not None
    except Exception:  # pragma: no cover - import failure counts as no display
        return False


needs_display = pytest.mark.skipif(
    not _gtk_display_available(), reason="no GTK display available"
)


class TestFewResultsHint:
    """Test the pure hint helper (no GTK widgets needed)."""

    def test_no_hint_for_large_result_sets(self):
        assert few_results_hint("toplist", 1000) == ""
        assert few_results_hint("toplist", 100) == ""

    def test_hint_for_few_results_with_toplist(self):
        hint = few_results_hint("toplist", 35)
        assert hint != ""
        assert "sorting" in hint.lower()

    def test_no_hint_for_few_results_with_other_sorting(self):
        assert few_results_hint("date_added", 35) == ""
        assert few_results_hint("views", 10) == ""

    def test_no_hint_for_zero_total(self):
        # Zero total means an empty/error result, not a narrow filter.
        assert few_results_hint("toplist", 0) == ""


class TestUpdatePaginationHintWiring:
    """Test that update_pagination actually wires the hint into the label."""

    @needs_display
    def test_pagination_label_includes_hint_for_sparse_toplist(
        self, wallhaven_view_model, mock_idle_add
    ):
        from ui.views.wallhaven_view import WallhavenView

        view = WallhavenView(view_model=wallhaven_view_model)
        wallhaven_view_model.sorting = "toplist"
        wallhaven_view_model.total_wallpapers = 35

        view.update_pagination(1, 2)

        text = view.page_label.get_text()
        assert "Page 1 / 2" in text
        assert "Tip: toplist found only 35 wallpapers" in text

    @needs_display
    def test_pagination_label_omits_hint_for_other_sorting(
        self, wallhaven_view_model, mock_idle_add
    ):
        from ui.views.wallhaven_view import WallhavenView

        view = WallhavenView(view_model=wallhaven_view_model)
        wallhaven_view_model.sorting = "date_added"
        wallhaven_view_model.total_wallpapers = 35

        view.update_pagination(1, 2)

        assert "Tip:" not in view.page_label.get_text()
