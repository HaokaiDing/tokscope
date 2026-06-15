from datetime import datetime, timedelta, timezone
from tokscope.adapters.base import UsageRecord, ActivityPing
from tokscope import stats


def _rec(tool, model, day, hour, cost, sid, proj="p", out=10, cr=0):
    ts = datetime(2026, 6, day, hour, tzinfo=timezone.utc)
    r = UsageRecord(tool=tool, session_id=sid, timestamp=ts, model=model, project=proj,
                    input_tokens=100, output_tokens=out, cache_read_tokens=cr)
    r.cost_usd = cost; r.priced = True
    return r


def _ping(tool, day, hour, sid, proj="p"):
    return ActivityPing(tool, sid, datetime(2026, 6, day, hour, tzinfo=timezone.utc), proj)


def test_totals_and_tool_breakdown():
    recs = [_rec("claude_code", "opus", 1, 2, 3.0, "a"),
            _rec("codex", "gpt", 1, 3, 1.0, "b")]
    pings = [_ping("claude_code", 1, 2, "a"), _ping("codex", 1, 3, "b")]
    d = stats.compute_all(recs, pings, tz=timezone.utc)
    assert d["totals"]["sessions"] == 2
    assert round(d["totals"]["cost_usd"], 2) == 4.0
    tools = {t["tool"]: t for t in d["tool_breakdown"]}
    assert round(tools["claude_code"]["cost_usd"], 2) == 3.0


def test_rhythm_busiest_day_and_streak():
    pings = [_ping("cc", 1, 2, "a"), _ping("cc", 1, 2, "a"), _ping("cc", 1, 3, "a"),
             _ping("cc", 2, 1, "b"), _ping("cc", 3, 1, "c")]
    recs = [_rec("cc", "m", 1, 2, 1.0, "a")]
    d = stats.compute_all(recs, pings, tz=timezone.utc)
    assert d["rhythm"]["busiest_day"]["count"] == 3
    assert d["rhythm"]["longest_streak"] == 3


def test_cache_savings_nonnegative():
    recs = [_rec("cc", "opus", 1, 2, 1.0, "a", cr=1_000_000)]
    d = stats.compute_all(recs, pings=[_ping("cc", 1, 2, "a")], tz=timezone.utc)
    assert d["cache"]["read_tokens"] == 1_000_000


def test_leaderboard_merges_model_notations():
    recs = [_rec("cc", "claude-opus-4.8", 1, 2, 3.0, "a"),
            _rec("cc", "claude-opus-4-8", 1, 2, 2.0, "b")]
    d = stats.compute_all(recs, [_ping("cc", 1, 2, "a")], tz=timezone.utc)
    keys = [m["model"] for m in d["model_leaderboard"]]
    assert keys.count("claude-opus-4-8") == 1            # merged into one row
    row = next(m for m in d["model_leaderboard"] if m["model"] == "claude-opus-4-8")
    assert round(row["cost_usd"], 2) == 5.0


def test_leaderboard_keeps_unpriced_high_usage_model():
    # a cheap priced model (few tokens) vs an unpriced model with lots of tokens
    cheap = _rec("cc", "haiku", 1, 2, 0.5, "a", out=10)        # ~110 tokens, priced
    fable = UsageRecord("cc", "b", cheap.timestamp, "fable-5", "p",
                        input_tokens=1_000_000, output_tokens=1_000)
    fable.priced = False                                       # unpriced -> cost 0
    d = stats.compute_all([cheap, fable], [_ping("cc", 1, 2, "a")], tz=timezone.utc)
    models = [m["model"] for m in d["model_leaderboard"]]
    assert "fable-5" in models                                 # not dropped despite $0
    assert models[0] == "fable-5"                              # ranked first by tokens
    assert d["model_leaderboard"][0]["priced"] is False


def test_weekday_counts_sun_first():
    # 2026-06-01 is a Monday -> Sun-first index 1
    base = datetime(2026, 6, 1, 12, tzinfo=timezone.utc)
    pings = [ActivityPing("cc", "s", base), ActivityPing("cc", "s", base)]
    d = stats.compute_all([_rec("cc", "m", 1, 12, 1.0, "s")], pings, tz=timezone.utc)
    assert len(d["weekday"]) == 7
    assert sum(d["weekday"]) == 2
    assert d["weekday"][1] == 2          # Monday bucket (Sun=0)


def test_longest_focus_run_splits_on_gap():
    base = datetime(2026, 6, 1, 1, tzinfo=timezone.utc)
    pings = [ActivityPing("cc", "s", base),
             ActivityPing("cc", "s", base + timedelta(minutes=10)),
             ActivityPing("cc", "s", base + timedelta(minutes=15)),   # run A = 15 min
             ActivityPing("cc", "s", base + timedelta(minutes=75))]   # gap > 30 -> new run
    recs = [_rec("cc", "m", 1, 1, 1.0, "s")]
    d = stats.compute_all(recs, pings, tz=timezone.utc)
    assert round(d["rhythm"]["longest_session_min"]) == 15
