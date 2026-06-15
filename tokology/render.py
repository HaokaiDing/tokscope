from __future__ import annotations
import base64
import json
from pathlib import Path

TEMPLATES = Path(__file__).parent / "templates"
FONTS = TEMPLATES / "fonts"
TEMPLATE = TEMPLATES / "wrapped.html.tmpl"


def _font_b64(name: str) -> str:
    f = FONTS / name
    return base64.b64encode(f.read_bytes()).decode() if f.exists() else ""


def render(data: dict, out_path: Path, lang: str = "en") -> Path:
    # Plain string substitution — no template engine, zero runtime dependencies.
    # All view logic lives in the card's inline JS; we only inject these values.
    html = TEMPLATE.read_text(encoding="utf-8")
    subs = {
        "__TOKOLOGY_LANG__": "zh" if lang == "zh" else "en",
        "__TOKOLOGY_FONT_400__": _font_b64("ibm-plex-mono-400.woff2"),
        "__TOKOLOGY_FONT_600__": _font_b64("ibm-plex-mono-600.woff2"),
        "__TOKOLOGY_FONT_700__": _font_b64("ibm-plex-mono-700.woff2"),
        "__TOKOLOGY_DATA__": json.dumps(data, ensure_ascii=False),
    }
    for key, value in subs.items():
        html = html.replace(key, value)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
