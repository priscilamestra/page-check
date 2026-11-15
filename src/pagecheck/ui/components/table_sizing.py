"""Shared, bounded Streamlit table heights (no long blank grids)."""
from __future__ import annotations


def compact_table_height(
    row_count: int, *, max_height: int = 380, min_height: int = 92,
    row_height: int = 35, header_height: int = 45,
) -> int:
    """Fit short results closely; scroll internally for long results.

    A one-record report must not render an empty 350 px table.
    """
    if isinstance(row_count, bool) or not isinstance(row_count, int) or row_count < 0:
        raise ValueError("Row count must be a nonnegative integer.")
    if min_height < 1 or max_height < min_height or row_height < 1 or header_height < 0:
        raise ValueError("Invalid table sizing settings.")
    return min(max_height, max(min_height, header_height + row_height * row_count))
