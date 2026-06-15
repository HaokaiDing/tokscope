import sqlite3
import pytest
from datetime import datetime, timezone
from tokology.adapters.base import UsageRecord
from tokology.pricing import Pricing, normalize_model


@pytest.fixture
def pricing_db(tmp_path):
    db = tmp_path / "pricing.sqlite"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE model_pricing (model_id TEXT PRIMARY KEY, display_name TEXT, "
        "input_cost_per_million TEXT, output_cost_per_million TEXT, "
        "cache_read_cost_per_million TEXT, cache_creation_cost_per_million TEXT)"
    )
    con.executemany(
        "INSERT INTO model_pricing VALUES (?,?,?,?,?,?)",
        [
            ("claude-opus-4-8", "Opus 4.8", "5", "25", "0.50", "6.25"),
            ("mimo-v2.5-pro", "MiMo V2.5 Pro", "1", "3", "0.20", "0"),
        ],
    )
    con.commit(); con.close()
    return db


def _rec(model, **kw):
    return UsageRecord(tool="t", session_id="s", timestamp=datetime.now(timezone.utc),
                       model=model, project=None, **kw)


def test_exact_match_cost(pricing_db):
    p = Pricing.from_sqlite(pricing_db)
    r = _rec("claude-opus-4-8", input_tokens=1_000_000, output_tokens=1_000_000,
             cache_read_tokens=1_000_000, cache_creation_tokens=1_000_000)
    p.price(r)
    assert r.priced is True
    assert round(r.cost_usd, 2) == round(5 + 25 + 0.50 + 6.25, 2)


def test_unpriced_model_marked(pricing_db):
    p = Pricing.from_sqlite(pricing_db)
    r = _rec("totally-unknown-model", input_tokens=1_000_000)
    p.price(r)
    assert r.priced is False and r.cost_usd == 0.0


def test_normalized_alias_match(pricing_db):
    p = Pricing.from_sqlite(pricing_db)
    r = _rec("claude-opus-4-8-20260101", input_tokens=1_000_000)
    p.price(r)
    assert r.priced is True and round(r.cost_usd, 4) == 5.0


def test_normalize_strips_date_suffix():
    assert normalize_model("claude-opus-4-8-20260101") == "claude-opus-4-8"


def test_dot_notation_matches_dash(pricing_db):
    p = Pricing.from_sqlite(pricing_db)
    r = _rec("claude-opus-4.8", output_tokens=1_000_000)   # dot, table has dash
    p.price(r)
    assert r.priced is True and round(r.cost_usd, 2) == 25.0


def test_builtin_fills_fable_when_ccswitch_lacks_it(pricing_db):
    # pricing_db has no Fable row; the builtin supplement should price it
    p = Pricing.from_sqlite(pricing_db)
    r = _rec("claude-fable-5", input_tokens=1_000_000, output_tokens=1_000_000)
    p.price(r)
    assert r.priced is True
    assert round(r.cost_usd, 2) == 60.0   # 10 input + 50 output


def test_normalize_strips_effort_suffix():
    assert normalize_model("gpt-5.4-xhigh") == "gpt-5.4"
    assert normalize_model("gpt-5.4-low") == "gpt-5.4"
