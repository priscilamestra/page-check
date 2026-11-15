"""UI table behavior: one-row results should not produce an empty long table."""
import pytest
from pagecheck.ui.components.table_sizing import compact_table_height


def test_one_row_is_compact():
    assert compact_table_height(1) < 120


def test_one_row_is_taller_than_header():
    assert compact_table_height(1) >= 80


def test_zero_rows_is_safe():
    assert compact_table_height(0) >= 80


def test_multiple_rows_expand():
    assert compact_table_height(7) > compact_table_height(1)


def test_large_result_is_bounded():
    assert compact_table_height(251) == 380


def test_custom_maximum_is_respected():
    assert compact_table_height(251, max_height=320) == 320


@pytest.mark.parametrize("value", [-1, 2.5, True, "3", None])
def test_invalid_row_count_is_rejected(value):
    with pytest.raises(ValueError):
        compact_table_height(value)


def test_bad_bounds_are_rejected():
    with pytest.raises(ValueError):
        compact_table_height(2, max_height=10, min_height=90)
