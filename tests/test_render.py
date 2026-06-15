from pathlib import Path
from datetime import datetime, timezone
from tokscope.adapters.base import UsageRecord, ActivityPing
from tokscope import stats, render


def test_render_self_contained(tmp_path):
    ts = datetime(2026, 6, 1, 2, tzinfo=timezone.utc)
    recs = [UsageRecord("claude_code", "s", ts, "claude-opus-4-8", "proj", 100, 50, 0, 0)]
    recs[0].cost_usd = 1.23; recs[0].priced = True
    pings = [ActivityPing("claude_code", "s", ts, "proj")]
    data = stats.compute_all(recs, pings, tz=timezone.utc)
    out = render.render(data, tmp_path / "w.html")
    html = Path(out).read_text(encoding="utf-8")
    assert out.exists()
    assert "http://" not in html and "https://" not in html
    assert "tokscope" in html.lower()
    assert "__WRAPPED_DATA__" not in html
