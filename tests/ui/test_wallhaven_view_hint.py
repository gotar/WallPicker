"""Tests for the few-results pagination hint in WallhavenView."""

from ui.views.wallhaven_view import few_results_hint


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
