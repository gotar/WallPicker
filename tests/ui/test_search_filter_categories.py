"""Tests for M9: Wallhaven category checkboxes must support bitmask multi-select."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def bar():
    from ui.components.search_filter_bar import SearchFilterBar

    return SearchFilterBar(tab_type="wallhaven")


class TestCategoryBitmask:
    def test_multiple_categories_can_be_active(self, bar):
        """Radio-grouping made multi-select impossible (Anime unchecked
        General). Checkboxes must be independent."""
        bar.category_sfw.set_active(True)
        bar.category_anime.set_active(True)

        assert bar.category_sfw.get_active()
        assert bar.category_anime.get_active()

    def test_bitmask_accumulates_across_checkboxes(self, bar):
        bar.category_sfw.set_active(True)
        bar.category_anime.set_active(True)

        assert bar._active_filters["category"] == "110"

    def test_all_three_categories(self, bar):
        for cb in (bar.category_sfw, bar.category_anime, bar.category_people):
            cb.set_active(True)
        assert bar._active_filters["category"] == "111"

    def test_unchecking_all_removes_category_filter(self, bar):
        bar.category_sfw.set_active(True)
        bar.category_sfw.set_active(False)
        bar.category_anime.set_active(False)
        bar.category_people.set_active(False)

        assert "category" not in bar._active_filters

    def test_filter_change_callback_receives_bitmask(self, bar):
        received = []
        bar._on_filter_changed_callback = lambda filters: received.append(
            dict(filters)
        )

        # Start from an empty selection, then pick Anime only
        bar.category_sfw.set_active(False)
        received.clear()
        bar.category_anime.set_active(True)
        assert received and received[-1].get("category") == "010"

    def test_chip_removal_clears_all_category_checkboxes(self, bar):
        bar.category_sfw.set_active(True)
        bar.category_anime.set_active(True)

        # Simulate clicking the remove button on the Category chip
        remove_btn = None
        child = bar._chips_container.get_first_child()
        while child:
            if getattr(child, "_filter_type", None) == "category":
                remove_btn = child.get_last_child()
                break
            child = child.get_next_sibling()

        assert remove_btn is not None
        bar._on_chip_remove_clicked(remove_btn)

        assert not bar.category_sfw.get_active()
        assert not bar.category_anime.get_active()
        assert not bar.category_people.get_active()
        assert "category" not in bar._active_filters
