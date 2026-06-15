from pathlib import Path
from tokscope.adapters.codex import CodexAdapter

FIX = Path(__file__).parent / "fixtures" / "codex"


def test_codex_takes_last_cumulative_not_sum():
    a = CodexAdapter(root=FIX)
    records, pings = a.collect()
    assert len(records) == 1
    r = records[0]
    assert r.tool == "codex" and r.model == "gpt-5.4"
    assert r.input_tokens == 3000 - 1200     # non-cached input, last cumulative
    assert r.cache_read_tokens == 1200
    assert r.output_tokens == 300
    assert r.cache_creation_tokens == 0
    assert r.project == "proj-beta" and r.session_id == "cx-sess-1"
    assert len(pings) == 5
