from pathlib import Path
from tokology.adapters.cline import ClineAdapter

FIX = Path(__file__).parent / "fixtures" / "cline"


def test_cline_sums_per_request_tokens():
    a = ClineAdapter(root=FIX)
    records, pings = a.collect()
    assert len(records) == 1
    r = records[0]
    assert r.tool == "cline" and r.model == "gpt-5.4-xhigh"
    assert r.input_tokens == 1500          # 1000 + 500 (summed, per-request)
    assert r.output_tokens == 300          # 200 + 100
    assert r.cache_read_tokens == 400      # 300 + 100
    assert r.cache_creation_tokens == 50   # 50 + 0
    assert len(pings) == 3                 # every ts'd message
