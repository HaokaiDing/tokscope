from __future__ import annotations
from collections import Counter, defaultdict
from datetime import timezone
from .pricing import normalize_model

SESSION_GAP_MIN = 30   # idle gap that splits one session into separate focus runs


def _local(ts, tz):
    return ts.astimezone(tz)


def _toktotal(r):
    return r.input_tokens + r.output_tokens + r.cache_read_tokens + r.cache_creation_tokens


def totals(records, pings, tz):
    days = {(_local(p.timestamp, tz).date()) for p in pings}
    return {
        "tokens": sum(_toktotal(r) for r in records),
        "cost_usd": sum(r.cost_usd for r in records),
        "sessions": len({(r.tool, r.session_id) for r in records}),
        "messages": len(records),
        "active_days": len(days),
        "span": _span(pings, tz),
        "unpriced_sessions": sum(1 for r in records if not r.priced),
    }


def _span(pings, tz):
    if not pings:
        return None
    ds = sorted(_local(p.timestamp, tz).date() for p in pings)
    return {"start": ds[0].isoformat(), "end": ds[-1].isoformat()}


def tool_breakdown(records):
    agg = defaultdict(lambda: {"tokens": 0, "cost_usd": 0.0})
    for r in records:
        a = agg[r.tool]
        a["tokens"] += _toktotal(r)
        a["cost_usd"] += r.cost_usd
    return sorted(({"tool": k, **v} for k, v in agg.items()),
                  key=lambda x: x["tokens"], reverse=True)


def model_leaderboard(records, top=8):
    # group by canonical id so dot/dash/dated variants of one model merge into one row
    agg = defaultdict(lambda: {"tokens": 0, "cost_usd": 0.0, "priced": True})
    for r in records:
        a = agg[normalize_model(r.model)]
        a["tokens"] += _toktotal(r)
        a["cost_usd"] += r.cost_usd
        a["priced"] = a["priced"] and r.priced
    # rank by usage (tokens) so heavily-used but unpriced models (e.g. Fable) still show
    rows = sorted(({"model": k, **v} for k, v in agg.items()),
                  key=lambda x: x["tokens"], reverse=True)
    return rows[:top]


def heatmap(pings, tz):
    c = Counter(_local(p.timestamp, tz).date() for p in pings)
    return [{"date": d.isoformat(), "count": n} for d, n in sorted(c.items())]


def rhythm(records, pings, tz):
    by_day = Counter(_local(p.timestamp, tz).date() for p in pings)
    by_hour = Counter(_local(p.timestamp, tz).hour for p in pings)
    busiest = max(by_day.items(), key=lambda x: x[1]) if by_day else None
    peak_hour = max(by_hour.items(), key=lambda x: x[1])[0] if by_hour else None
    night = sum(n for h, n in by_hour.items() if h < 6 or h >= 22)
    night_pct = (night / sum(by_hour.values()) * 100) if by_hour else 0.0
    longest = _longest_focus_run(pings)
    return {
        "busiest_day": {"date": busiest[0].isoformat(), "count": busiest[1]} if busiest else None,
        "peak_hour": peak_hour,
        "night_owl_pct": night_pct,
        "longest_streak": _longest_streak(set(by_day)),
        "longest_session_min": longest,
    }


def _longest_focus_run(pings) -> float:
    """Longest contiguous activity run (minutes) within one session, splitting on
    idle gaps > SESSION_GAP_MIN so a resumed days-long session_id can't inflate it."""
    by_sess = defaultdict(list)
    for p in pings:
        by_sess[(p.tool, p.session_id)].append(p.timestamp)
    gap = SESSION_GAP_MIN * 60
    longest = 0.0
    for ts_list in by_sess.values():
        ts_list.sort()
        run_start = prev = ts_list[0]
        for t in ts_list[1:]:
            if (t - prev).total_seconds() > gap:
                longest = max(longest, (prev - run_start).total_seconds() / 60)
                run_start = t
            prev = t
        longest = max(longest, (prev - run_start).total_seconds() / 60)
    return longest


def _longest_streak(days: set) -> int:
    if not days:
        return 0
    best = cur = 1
    ds = sorted(days)
    for prev, d in zip(ds, ds[1:]):
        cur = cur + 1 if (d - prev).days == 1 else 1
        best = max(best, cur)
    return best


def project_leaderboard(pings, top=8):
    c = Counter(p.project for p in pings if p.project)
    return [{"project": k, "count": n} for k, n in c.most_common(top)]


def weekday_counts(pings, tz):
    """Activity counts per weekday, Sun..Sat (index 0..6)."""
    c = [0] * 7
    for p in pings:
        d = _local(p.timestamp, tz)
        c[(d.weekday() + 1) % 7] += 1   # Python weekday() Mon=0..Sun=6 -> Sun=0
    return c


def cache_stats(records):
    read = sum(r.cache_read_tokens for r in records)
    created = sum(r.cache_creation_tokens for r in records)
    return {"read_tokens": read, "creation_tokens": created}


def personality(d) -> dict:
    r = d["rhythm"]
    tokens = d["totals"]["tokens"]
    tags = []
    if r.get("night_owl_pct", 0) >= 30:
        tags.append("夜猫子")
    if tokens >= 500_000_000:
        tags.append("Token 鲸鱼")
    if tokens and d["cache"]["read_tokens"] > tokens * 0.3:
        tags.append("缓存抠门大师")
    if len(d["tool_breakdown"]) >= 3:
        tags.append("多栖玩家")
    title = " · ".join(tags) if tags else "稳健玩家"
    icon = "moon" if "夜猫子" in title else "flame"
    return {"title": title, "icon": icon}


def compute_all(records, pings, tz=timezone.utc) -> dict:
    d = {
        "totals": totals(records, pings, tz),
        "tool_breakdown": tool_breakdown(records),
        "model_leaderboard": model_leaderboard(records),
        "heatmap": heatmap(pings, tz),
        "rhythm": rhythm(records, pings, tz),
        "weekday": weekday_counts(pings, tz),
        "projects": project_leaderboard(pings),
        "cache": cache_stats(records),
    }
    d["personality"] = personality(d)
    return d
