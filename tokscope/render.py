from __future__ import annotations
import base64
import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES = Path(__file__).parent / "templates"
FONTS = TEMPLATES / "fonts"


def _font_b64(name: str) -> str:
    f = FONTS / name
    return base64.b64encode(f.read_bytes()).decode() if f.exists() else ""


def render(data: dict, out_path: Path, lang: str = "en") -> Path:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )
    tmpl = env.get_template("wrapped.html.j2")
    html = tmpl.render(
        data_json=json.dumps(data, ensure_ascii=False),
        lang="zh" if lang == "zh" else "en",
        font_400=_font_b64("ibm-plex-mono-400.woff2"),
        font_600=_font_b64("ibm-plex-mono-600.woff2"),
        font_700=_font_b64("ibm-plex-mono-700.woff2"),
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
