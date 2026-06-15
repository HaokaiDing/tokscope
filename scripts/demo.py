"""Generate a sanitized demo card (entirely fake data) for the README.

    uv run python scripts/demo.py

Writes assets/demo.png. Uses no real logs — safe to publish.
"""
from __future__ import annotations
import random
from datetime import date, timedelta
from pathlib import Path
from tokscope import render
from tokscope.cli import html_to_png

ROOT = Path(__file__).resolve().parent.parent


def _heatmap(start: date, end: date):
    rnd = random.Random(7)
    out, d = [], start
    while d <= end:
        weekday = d.weekday()
        n = 0 if rnd.random() < 0.13 else rnd.randint(1, 9 if weekday < 5 else 4)
        if rnd.random() < 0.06:
            n += rnd.randint(10, 38)
        out.append({"date": d.isoformat(), "count": n * 120})
        d += timedelta(days=1)
    return out


def demo_data() -> dict:
    start, end = date(2026, 1, 1), date(2026, 6, 30)
    return {
        "totals": {"tokens": 8_420_000_000, "cost_usd": 1248.0, "sessions": 1204,
                   "messages": 31_500, "active_days": 142,
                   "span": {"start": start.isoformat(), "end": end.isoformat()},
                   "unpriced_sessions": 0},
        "tool_breakdown": [
            {"tool": "claude_code", "tokens": 5_100_000_000, "cost_usd": 758.0},
            {"tool": "codex", "tokens": 2_300_000_000, "cost_usd": 342.0},
            {"tool": "cline", "tokens": 1_020_000_000, "cost_usd": 148.0}],
        "model_leaderboard": [
            {"model": "claude-opus-4-8", "tokens": 4_600_000_000, "cost_usd": 642.0, "priced": True},
            {"model": "gpt-5.5", "tokens": 2_100_000_000, "cost_usd": 408.0, "priced": True},
            {"model": "claude-sonnet-4-6", "tokens": 900_000_000, "cost_usd": 121.0, "priced": True},
            {"model": "gpt-5.4", "tokens": 480_000_000, "cost_usd": 52.0, "priced": True},
            {"model": "claude-haiku-4-5", "tokens": 210_000_000, "cost_usd": 18.0, "priced": True}],
        "heatmap": _heatmap(start, end),
        "rhythm": {"busiest_day": {"date": "2026-03-14", "count": 5200}, "peak_hour": 22,
                   "night_owl_pct": 38.0, "longest_streak": 27, "longest_session_min": 195.0},
        "weekday": [120, 210, 240, 230, 205, 175, 95],
        "projects": [{"project": "my-saas-app", "count": 4200},
                     {"project": "portfolio-site", "count": 1800},
                     {"project": "data-pipeline", "count": 1500},
                     {"project": "cli-tool", "count": 920},
                     {"project": "notes-app", "count": 610}],
        "cache": {"read_tokens": 6_820_000_000, "creation_tokens": 310_000_000},
        "personality": {"title": "夜猫子 · Token 鲸鱼 · 多栖玩家", "icon": "moon"},
    }


def main():
    out_html = ROOT / "out" / "demo.html"
    render.render(demo_data(), out_html)
    png = ROOT / "assets" / "demo.png"
    png.parent.mkdir(parents=True, exist_ok=True)
    result = html_to_png(out_html, png)
    print("demo →", result or "FAILED (need Chrome)")


if __name__ == "__main__":
    main()
