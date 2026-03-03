# ABOUTME: Tests for PDF text batching logic.
# ABOUTME: Verifies page grouping, boundary conditions, and empty page filtering.

import pytest

from agents import PAGE_BREAK, MIN_TEXT_LENGTH, make_batches


def test_batches_single_page():
    result = make_batches(["Page one content here " * 10], batch_size=5)
    assert len(result) == 1
    start, end, text = result[0]
    assert start == 1
    assert end == 1


def test_batches_exact_multiple():
    pages = [f"Content for page {i} " * 10 for i in range(20)]
    result = make_batches(pages, batch_size=10)
    assert len(result) == 2
    assert result[0][:2] == (1, 10)
    assert result[1][:2] == (11, 20)


def test_batches_remainder():
    pages = [f"Content for page {i} " * 10 for i in range(15)]
    result = make_batches(pages, batch_size=10)
    assert len(result) == 2
    assert result[0][:2] == (1, 10)
    assert result[1][:2] == (11, 15)


def test_batches_page_break_delimiter():
    pages = ["Page A content here" * 5, "Page B content here" * 5]
    result = make_batches(pages, batch_size=10)
    _, _, text = result[0]
    assert PAGE_BREAK in text
    parts = text.split(PAGE_BREAK)
    assert len(parts) == 2


def test_batches_skip_empty_pages():
    pages = ["", "  ", "\n\n"]
    result = make_batches(pages, batch_size=10)
    assert len(result) == 0


def test_batches_skip_short_text():
    pages = ["x" * (MIN_TEXT_LENGTH - 1)]
    result = make_batches(pages, batch_size=10)
    assert len(result) == 0


def test_batches_keep_sufficient_text():
    pages = ["x" * MIN_TEXT_LENGTH]
    result = make_batches(pages, batch_size=10)
    assert len(result) == 1


def test_batches_empty_input():
    result = make_batches([], batch_size=10)
    assert result == []


@pytest.mark.parametrize("batch_size", [1, 5, 10, 50])
def test_batches_cover_all_pages(batch_size):
    pages = [f"Content for page {i} " * 10 for i in range(23)]
    result = make_batches(pages, batch_size=batch_size)
    total_pages = sum(end - start + 1 for start, end, _ in result)
    assert total_pages == 23


@pytest.mark.parametrize("batch_size", [1, 3, 7])
def test_batches_pages_are_contiguous(batch_size):
    pages = [f"Content for page {i} " * 10 for i in range(10)]
    result = make_batches(pages, batch_size=batch_size)
    for i in range(1, len(result)):
        prev_end = result[i - 1][1]
        curr_start = result[i][0]
        assert curr_start == prev_end + 1
