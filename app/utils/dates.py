"""Date and timezone utilities (default Asia/Karachi)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.config import get_settings


def get_tz(name: str | None = None) -> ZoneInfo:
    tz_name = name or get_settings().default_timezone
    try:
        return ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001
        return ZoneInfo("Asia/Karachi")


def now_tz(tz_name: str | None = None) -> datetime:
    return datetime.now(get_tz(tz_name))


def today_tz(tz_name: str | None = None) -> date:
    return now_tz(tz_name).date()


def ensure_aware(dt: datetime, tz_name: str | None = None) -> datetime:
    tz = get_tz(tz_name)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)


def parse_datetime(value: Any, tz_name: str | None = None) -> datetime | None:
    """Parse common datetime string formats into an aware datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return ensure_aware(value, tz_name)
    text = str(value).strip()
    formats = (
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%Y.%m.%d %H:%M:%S",
    )
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            return ensure_aware(dt, tz_name)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return ensure_aware(dt, tz_name)
    except ValueError:
        return None


def parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def period_range(
    period: str,
    start: date | None = None,
    end: date | None = None,
    tz_name: str | None = None,
) -> tuple[datetime | None, datetime | None]:
    """
    Resolve a named period into start/end datetimes in the configured timezone.

    Returns (None, None) for all-time.
    """
    tz = get_tz(tz_name)
    now = now_tz(tz_name)
    today = now.date()

    if period == "custom" and start and end:
        start_dt = datetime.combine(start, datetime.min.time(), tzinfo=tz)
        end_dt = datetime.combine(end, datetime.max.time().replace(microsecond=0), tzinfo=tz)
        return start_dt, end_dt

    if period == "today":
        start_dt = datetime.combine(today, datetime.min.time(), tzinfo=tz)
        return start_dt, now

    if period == "7d":
        start_day = today - timedelta(days=6)
        start_dt = datetime.combine(start_day, datetime.min.time(), tzinfo=tz)
        return start_dt, now

    if period == "30d":
        start_day = today - timedelta(days=29)
        start_dt = datetime.combine(start_day, datetime.min.time(), tzinfo=tz)
        return start_dt, now

    if period == "month":
        start_day = today.replace(day=1)
        start_dt = datetime.combine(start_day, datetime.min.time(), tzinfo=tz)
        return start_dt, now

    if period == "prev_month":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        first_prev = last_prev.replace(day=1)
        start_dt = datetime.combine(first_prev, datetime.min.time(), tzinfo=tz)
        end_dt = datetime.combine(last_prev, datetime.max.time().replace(microsecond=0), tzinfo=tz)
        return start_dt, end_dt

    if period == "year":
        start_day = today.replace(month=1, day=1)
        start_dt = datetime.combine(start_day, datetime.min.time(), tzinfo=tz)
        return start_dt, now

    # all / unknown
    return None, None


def previous_equivalent_period(
    start: datetime | None, end: datetime | None
) -> tuple[datetime | None, datetime | None]:
    """Return the period of equal length immediately preceding [start, end]."""
    if start is None or end is None:
        return None, None
    length = end - start
    prev_end = start - timedelta(microseconds=1)
    prev_start = prev_end - length
    return prev_start, prev_end


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "—"
    seconds = abs(int(seconds))
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    if not days and not hours:
        parts.append(f"{secs}s")
    return " ".join(parts)


def month_bounds(year: int, month: int, tz_name: str | None = None) -> tuple[datetime, datetime]:
    tz = get_tz(tz_name)
    start = datetime(year, month, 1, tzinfo=tz)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=tz) - timedelta(seconds=1)
    else:
        end = datetime(year, month + 1, 1, tzinfo=tz) - timedelta(seconds=1)
    return start, end


# UTC helper for storage consistency
UTC = timezone.utc
