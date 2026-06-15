from __future__ import annotations
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path
from .adapters.base import UsageRecord

DEFAULT_DB = Path.home() / ".cc-switch" / "cc-switch.db"

# Explicit aliases for ids that don't normalize cleanly.
ALIASES: dict[str, str] = {
    "claude-opus-4.8": "claude-opus-4-8",   # dot vs dash notation for the same model
}

# Supplemental prices ($/1M) for models cc-switch's table doesn't carry yet.
# cc-switch entries take precedence; these only fill gaps. cache_read = 0.1x input,
# cache_creation = 1.25x input (same convention cc-switch uses for Claude models).
# Source: Claude API model pricing (claude-api skill), 2026-06.
BUILTIN_PRICES: dict[str, dict[str, float]] = {
    "claude-fable-5": {"input": 10.0, "output": 50.0, "cache_read": 1.0, "cache_creation": 12.5},
}

_DATE_SUFFIX = re.compile(r"-\d{6,8}$")
_EFFORT_SUFFIX = re.compile(r"-(x?high|medium|low|minimal)$")


def normalize_model(model: str) -> str:
    m = model.strip().lower()
    m = _DATE_SUFFIX.sub("", m)            # drop trailing -YYYYMMDD / -YYYYMM
    m = _EFFORT_SUFFIX.sub("", m)          # drop effort suffix (Cline: gpt-5.4-xhigh)
    return ALIASES.get(m, m)


def _to_float(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


class Pricing:
    def __init__(self, table: dict[str, dict[str, float]]):
        self.table = table

    @classmethod
    def from_sqlite(cls, db_path: Path = DEFAULT_DB) -> "Pricing":
        db_path = Path(db_path)
        table: dict[str, dict[str, float]] = {}
        if db_path.exists():
            with tempfile.TemporaryDirectory() as td:
                copy = Path(td) / "p.sqlite"
                shutil.copy2(db_path, copy)
                con = sqlite3.connect(copy)
                try:
                    rows = con.execute(
                        "SELECT model_id, input_cost_per_million, output_cost_per_million, "
                        "cache_read_cost_per_million, cache_creation_cost_per_million "
                        "FROM model_pricing"
                    ).fetchall()
                finally:
                    con.close()
            for mid, i, o, cr, cc in rows:
                table[normalize_model(mid)] = {
                    "input": _to_float(i), "output": _to_float(o),
                    "cache_read": _to_float(cr), "cache_creation": _to_float(cc),
                }
        # cc-switch wins; builtins fill any model it doesn't carry (e.g. Fable 5)
        for k, v in BUILTIN_PRICES.items():
            table.setdefault(k, v)
        return cls(table)

    def rate_for(self, model: str) -> dict[str, float] | None:
        key = normalize_model(model)
        rate = self.table.get(key)
        if rate is None and "." in key:        # fallback: X.Y -> X-Y (claude dash style)
            rate = self.table.get(key.replace(".", "-"))
        return rate

    def price(self, rec: UsageRecord) -> None:
        rate = self.rate_for(rec.model)
        if rate is None:
            rec.priced = False
            rec.cost_usd = 0.0
            return
        rec.cost_usd = (
            rec.input_tokens / 1e6 * rate["input"]
            + rec.output_tokens / 1e6 * rate["output"]
            + rec.cache_read_tokens / 1e6 * rate["cache_read"]
            + rec.cache_creation_tokens / 1e6 * rate["cache_creation"]
        )
        rec.priced = True
