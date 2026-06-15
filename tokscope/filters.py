from __future__ import annotations
from datetime import datetime, timezone


def parse_window(year: int | None, month: str | None, since: str | None):
    """Return (lo, hi) tz-aware bounds; (None, None) means all-time."""
    if month:
        y, m = map(int, month.split("-"))
        lo = datetime(y, m, 1, tzinfo=timezone.utc)
        hi = datetime(y + (m == 12), (m % 12) + 1, 1, tzinfo=timezone.utc)
        return lo, hi
    if year:
        return (datetime(year, 1, 1, tzinfo=timezone.utc),
                datetime(year + 1, 1, 1, tzinfo=timezone.utc))
    if since:
        lo = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
        return lo, None
    return None, None


def in_window(item, lo, hi) -> bool:
    ts = item.timestamp
    if ts is None:
        return False
    if lo is not None and ts < lo:
        return False
    if hi is not None and ts >= hi:
        return False
    return True


def apply_window(records, pings, lo, hi):
    if lo is None and hi is None:
        return records, pings
    return ([r for r in records if in_window(r, lo, hi)],
            [p for p in pings if in_window(p, lo, hi)])
