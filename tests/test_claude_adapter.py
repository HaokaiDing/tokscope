from datetime import datetime, timezone
from pathlib import Path
from tokscope.adapters.base import UsageRecord, ActivityPing, parse_iso, project_name
from tokscope.adapters.claude_code import ClaudeCodeAdapter

FIX = Path(__file__).parent / "fixtures" / "claude"


def test_usage_record_defaults():
    r = UsageRecord(tool="cc", session_id="s", timestamp=datetime.now(timezone.utc),
                    model="m", project="p")
    assert r.input_tokens == 0 and r.cost_usd == 0.0 and r.priced is False


def test_parse_iso_handles_z():
    dt = parse_iso("2026-06-01T05:45:06.294Z")
    assert dt.tzinfo is not None and dt.year == 2026 and dt.hour == 5


def test_project_name_drops_home():
    from pathlib import Path
    assert project_name(str(Path.home())) is None
    assert project_name("/Users/x/myproj") == "myproj"
    assert project_name(None) is None


def test_claude_collect_skips_synthetic_and_nonassistant():
    a = ClaudeCodeAdapter(root=FIX)
    records, pings = a.collect()
    assert len(records) == 1
    r = records[0]
    assert r.tool == "claude_code" and r.model == "claude-opus-4-8"
    assert r.input_tokens == 100 and r.output_tokens == 50
    assert r.cache_creation_tokens == 10 and r.cache_read_tokens == 200
    assert r.project == "proj-alpha" and r.session_id == "cc-sess-1"
    assert len(pings) == 1 and pings[0].timestamp == r.timestamp
