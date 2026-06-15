from datetime import datetime, timezone
from tokscope.adapters.base import UsageRecord
from tokscope.filters import parse_window, in_window


def _r(month):
    ts = datetime(2026, month, 15, tzinfo=timezone.utc)
    return UsageRecord(tool="t", session_id="s", timestamp=ts, model="m", project=None)


def test_parse_window_year():
    lo, hi = parse_window(year=2026, month=None, since=None)
    assert lo.year == 2026 and hi.year == 2027


def test_parse_window_month():
    lo, hi = parse_window(year=None, month="2026-06", since=None)
    assert lo.month == 6 and hi.month == 7


def test_in_window_filters():
    lo, hi = parse_window(year=None, month="2026-06", since=None)
    assert in_window(_r(6), lo, hi) is True
    assert in_window(_r(5), lo, hi) is False
