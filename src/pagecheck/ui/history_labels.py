"""Present UTC history timestamps in the *browser's* local timezone.

History IDs and stored timestamps remain unchanged. A browser and the API
server may be in completely different countries; only rendering is localized.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def browser_zone(name: str | None, offset_minutes: int | None = None) -> tzinfo:
    """IANA zone first (DST-aware), then browser UTC offset, then explicit UTC.

    Streamlit reports offsets in JavaScript Date.getTimezoneOffset() units:
    minutes west of UTC (Sao Paulo is +180, New York in winter +300).
    """
    if isinstance(name, str) and name.strip():
        try:
            return ZoneInfo(name.strip())
        except (ZoneInfoNotFoundError, ValueError, KeyError):
            # On some Windows machines the standard-library IANA database is
            # unavailable, but pandas brings pytz as a required dependency.
            try:
                import pytz
            except ImportError:
                pass
            else:
                try:
                    return pytz.timezone(name.strip())
                except pytz.UnknownTimeZoneError:
                    pass
    if isinstance(offset_minutes, int) and not isinstance(offset_minutes, bool):
        if -14 * 60 <= offset_minutes <= 14 * 60:
            return timezone(-timedelta(minutes=offset_minutes))
    return timezone.utc


def format_history_time(value: str, *, browser_timezone: str | None = None,
                        browser_offset_minutes: int | None = None) -> str:
    """MM/DD/YYYY, local 12h clock + timezone; no server-timezone guesses."""
    if not isinstance(value, str):
        return "Unknown date"
    try:
        instant = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return "Unknown date"
    # Naive timestamps from older saved records are interpreted as UTC,
    # never as the server's (possibly remote) local time.
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    local = instant.astimezone(browser_zone(browser_timezone, browser_offset_minutes))
    hour = local.hour % 12 or 12
    meridiem = "AM" if local.hour < 12 else "PM"
    zone = local.tzname() or "UTC"
    if zone.startswith(('+', '-')):
        zone = f"UTC{zone}"
    return f"{local:%m/%d/%Y} · {hour}:{local.minute:02d} {meridiem} ({zone})"


def history_option_label(item: dict, *, browser_timezone: str | None = None,
                         browser_offset_minutes: int | None = None) -> str:
    time = format_history_time(item.get("created_at", ""),
                               browser_timezone=browser_timezone,
                               browser_offset_minutes=browser_offset_minutes)
    return f"{time} · {item.get('requested_url', 'Unknown URL')} · {item.get('status', 'unknown')}"
