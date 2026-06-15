from pathlib import Path
from tokology import cli

FIX = Path(__file__).parent / "fixtures"


def test_html_to_png_without_chrome_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "find_chrome", lambda: None)
    assert cli.html_to_png(tmp_path / "x.html", tmp_path / "x.png") is None


def test_cli_run_on_fixtures(tmp_path):
    out = tmp_path / "w.html"
    code = cli.run(argv=[
        "--no-open", "--out", str(out),
        "--claude-root", str(FIX / "claude"),
        "--codex-root", str(FIX / "codex"),
        "--no-pricing",
    ])
    assert code == 0
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "tokology" in html.lower()
