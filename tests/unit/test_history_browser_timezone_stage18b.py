"""Stored UTC stays UTC; labels follow each user's browser timezone."""
from pagecheck.ui.history_labels import browser_zone, format_history_time, history_option_label


def test_brazil_browser_local_time_and_us_date():
    label = format_history_time("2026-11-14T21:56:06+00:00", browser_timezone="America/Sao_Paulo")
    assert label.startswith("11/14/2026 · 6:56 PM")
    assert any(label.endswith(zone) for zone in ("(BRT)", "(-03)", "(UTC-03)"))


def test_us_new_york_dst_is_per_saved_record():
    summer = format_history_time("2026-07-14T21:56:06+00:00", browser_timezone="America/New_York")
    winter = format_history_time("2026-11-14T21:56:06+00:00", browser_timezone="America/New_York")
    assert "5:56 PM" in summer
    assert "4:56 PM" in winter


def test_browser_timezone_not_server_locale(monkeypatch):
    monkeypatch.setenv("TZ", "Asia/Tokyo")
    label = format_history_time("2026-11-14T21:56:06+00:00", browser_timezone="America/Sao_Paulo")
    assert "6:56 PM" in label


def test_browser_offset_fallback_when_timezone_missing():
    label = format_history_time("2026-11-14T21:56:06Z", browser_offset_minutes=180)
    assert "6:56 PM" in label
    assert "UTC-03:00" in label


def test_utc_explicit_if_browser_did_not_supply_timezone():
    label = format_history_time("2026-11-14T21:56:06Z")
    assert "9:56 PM" in label
    assert "UTC" in label


def test_invalid_timezone_name_uses_offset_without_crashing():
    label = format_history_time("2026-11-14T21:56:06Z", browser_timezone="Mars/Unknown", browser_offset_minutes=180)
    assert "6:56 PM" in label


def test_bad_dates_are_clear_and_safe():
    assert format_history_time("not-a-time") == "Unknown date"
    assert format_history_time(None) == "Unknown date"


def test_label_retains_url_status_and_utc_source():
    item = {"created_at": "2026-11-14T21:56:06+00:00", "requested_url": "https://example.com",
            "status": "partial"}
    out = history_option_label(item, browser_timezone="America/Sao_Paulo")
    assert "11/14/2026" in out and "https://example.com · partial" in out
    assert item["created_at"].endswith("+00:00")


def test_invalid_offset_falls_back_utc():
    label = format_history_time("2026-11-14T21:56:06Z", browser_offset_minutes=100000)
    assert "9:56 PM" in label and "UTC" in label
