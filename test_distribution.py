"""
Tests for the imposition maths. Run with `pytest`, or directly:

    python test_distribution.py
"""

import pytest

from distribution import BLANK, distribution_booklets, distribution_booklets_pages, distribution_pages


def test_full_booklet_order():
    # 8 pages on 2 sheets: outer sheet carries the first and last pages.
    assert distribution_pages(0, 7) == [(7, 0), (1, 6), (5, 2), (3, 4)]


def test_blanks_land_after_the_last_page():
    # 5 pages padded to 8: the 3 blanks must occupy the last reading slots.
    assert distribution_pages(0, 4) == [(BLANK, 0), (1, BLANK), (BLANK, 2), (3, 4)]


def test_pages_must_be_ordered():
    with pytest.raises(ValueError):
        distribution_pages(5, 2)
    with pytest.raises(TypeError):
        distribution_pages(0.0, 3)


@pytest.mark.parametrize("n_pages", [1, 2, 3, 4, 5, 7, 8, 27, 28, 29, 100, 313])
def test_every_page_appears_exactly_once(n_pages):
    booklets = distribution_booklets_pages(n_pages)
    used = [page for booklet in booklets for pair in booklet for page in pair if page != BLANK]
    assert sorted(used) == list(range(n_pages))


@pytest.mark.parametrize("n_pages", [1, 5, 27, 28, 100])
def test_short_documents_still_produce_one_booklet(n_pages):
    # Regression: anything under 4 * 7 pages used to raise "Too many sheets".
    assert len(distribution_booklets_pages(n_pages)) >= 1


def test_booklets_cover_the_document_without_overlap():
    ranges = distribution_booklets(100, n_booklets=4)
    assert ranges[0][0] == 0
    assert ranges[-1][1] == 99
    for (_, end), (begin, _) in zip(ranges, ranges[1:]):
        assert begin == end + 1


def test_auto_targets_the_requested_sheets_per_booklet():
    # 100 pages = 25 sheets; aiming for 7 sheets per booklet gives 4 booklets.
    assert len(distribution_booklets(100, n_sheets=7)) == 4


def test_explicit_booklet_count_is_honoured():
    assert len(distribution_booklets(100, n_booklets=5)) == 5


def test_rejects_impossible_requests():
    with pytest.raises(ValueError):
        distribution_booklets(8, n_booklets=5)  # 8 pages = 2 sheets only
    with pytest.raises(ValueError):
        distribution_booklets(0)
    with pytest.raises(ValueError):
        distribution_booklets(10, n_booklets=0)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
