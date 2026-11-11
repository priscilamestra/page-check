import pytest

from pagecheck.acquisition.browser.visual_probe import image_status, scroll_positions


def test_scroll_short_page():
    assert scroll_positions(500, 600, 200) == [0]


def test_scroll_long_page_reaches_bottom():
    assert scroll_positions(1600, 600, 450) == [0, 450, 900, 1000]


def test_scroll_invalid_dimensions():
    with pytest.raises(ValueError):
        scroll_positions(100, 0, 20)


def test_image_loaded():
    assert image_status(has_source=True, complete=True, natural_width=100) == "loaded"


def test_image_broken():
    assert image_status(has_source=True, complete=True, natural_width=0) == "broken"


def test_image_still_pending_is_not_called_broken():
    assert image_status(has_source=True, complete=False, natural_width=0) == "not_verified"


def test_image_without_src_not_verified():
    assert image_status(has_source=False, complete=True, natural_width=0) == "not_verified"
