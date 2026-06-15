from __future__ import annotations
import argparse
import os
import platform
import re
import shutil
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from . import stats, render
from .filters import parse_window, apply_window
from .pricing import Pricing
from .adapters.claude_code import ClaudeCodeAdapter
from .adapters.codex import CodexAdapter
from .adapters.cline import ClineAdapter, default_task_dirs
from .detect import detect_installed, DISPLAY


def _chrome_candidates() -> list[str]:
    s = platform.system()
    if s == "Darwin":
        return ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    if s == "Windows":
        pf = [os.environ.get("PROGRAMFILES", r"C:\Program Files"),
              os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
              os.environ.get("LOCALAPPDATA", "")]
        return [rf"{b}\Google\Chrome\Application\chrome.exe" for b in pf if b] + \
               [rf"{pf[0]}\Microsoft\Edge\Application\msedge.exe"]
    return ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium"]


def find_chrome() -> str | None:
    for c in _chrome_candidates():
        if Path(c).exists():
            return c
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge"):
        p = shutil.which(name)
        if p:
            return p
    return None


def open_path(p: Path) -> None:
    """Open a file with the OS default app, cross-platform."""
    s = platform.system()
    try:
        if s == "Darwin":
            subprocess.run(["open", str(p)], check=False)
        elif s == "Windows":
            os.startfile(str(p))  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(p)], check=False)
    except (OSError, AttributeError):
        pass


def html_to_png(html_path: Path, png_path: Path, width: int = 1100, scale: int = 2) -> Path | None:
    """Render the HTML to a PNG via headless Chrome at its true content height (2x)."""
    chrome = find_chrome()
    if not chrome:
        print("PNG 导出需要 Chrome/Chromium，未找到——已跳过（HTML 照常生成）。", file=sys.stderr)
        return None
    url = html_path.resolve().as_uri()
    base = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars",
            f"--virtual-time-budget=3000"]
    # 1) measure true content height at the target width (layout depends on width)
    height = 1600
    try:
        dom = subprocess.run(
            base + [f"--window-size={width},3000", "--dump-dom", url],
            capture_output=True, text=True, timeout=60).stdout
        m = re.search(r'data-h="(\d+)"', dom)
        if m:
            height = max(600, min(int(m.group(1)) + 8, 8000))
    except (subprocess.SubprocessError, OSError):
        pass
    # 2) screenshot at the measured height, 2x for a crisp share image
    try:
        subprocess.run(
            base + [f"--window-size={width},{height}", f"--force-device-scale-factor={scale}",
                    f"--screenshot={png_path}", url],
            capture_output=True, timeout=120, check=True)
    except (subprocess.SubprocessError, OSError) as e:
        print(f"PNG 截图失败：{e}", file=sys.stderr)
        return None
    return png_path if png_path.exists() else None


def default_lang() -> str:
    loc = (os.environ.get("LC_ALL") or os.environ.get("LANG") or "").lower()
    return "zh" if loc.startswith("zh") else "en"


def build_adapters(args):
    adapters = []
    if args.claude_root != "skip":
        adapters.append(ClaudeCodeAdapter(root=Path(args.claude_root)) if args.claude_root
                        else ClaudeCodeAdapter())
    if args.codex_root != "skip":
        adapters.append(CodexAdapter(root=Path(args.codex_root)) if args.codex_root
                        else CodexAdapter())
    if args.cline_root != "skip":
        if args.cline_root:
            adapters.append(ClineAdapter(root=Path(args.cline_root)))
        else:
            adapters += [ClineAdapter(root=d) for d in default_task_dirs()]
    return [a for a in adapters if a.available()]


def run(argv=None) -> int:
    p = argparse.ArgumentParser(prog="tokology")
    p.add_argument("--year", type=int)
    p.add_argument("--month")           # YYYY-MM
    p.add_argument("--since")           # YYYY-MM-DD
    p.add_argument("--out")
    p.add_argument("--png", action="store_true", help="also export a shareable PNG (needs Chrome)")
    p.add_argument("--no-open", action="store_true")
    p.add_argument("--no-pricing", action="store_true")
    p.add_argument("--claude-root", default="")   # "" = default home; "skip" disables
    p.add_argument("--codex-root", default="")
    p.add_argument("--cline-root", default="")
    p.add_argument("--lang", choices=["en", "zh"], default=default_lang(),
                   help="card language (default: from system locale)")
    args = p.parse_args(argv)

    adapters = build_adapters(args)
    records, pings = [], []
    for a in adapters:
        r, pg = a.collect()
        records += r
        pings += pg

    installed = detect_installed()
    contributing = sorted({r.tool for r in records})
    print("detected:    " + (", ".join(installed) or "none"))
    print("token data:  " + (", ".join(DISPLAY.get(t, t) for t in contributing) or "none"))

    if not args.no_pricing:
        pricing = Pricing.from_sqlite()
        for r in records:
            pricing.price(r)

    lo, hi = parse_window(args.year, args.month, args.since)
    records, pings = apply_window(records, pings, lo, hi)

    tz = datetime.now().astimezone().tzinfo or timezone.utc
    data = stats.compute_all(records, pings, tz=tz)

    out = Path(args.out) if args.out else (Path(__file__).parent.parent / "out"
          / f"wrapped-{datetime.now():%Y%m%d}.html")
    render.render(data, out, lang=args.lang)
    print(f"wrapped → {out}  ({data['totals']['sessions']} sessions, "
          f"${data['totals']['cost_usd']:.0f})")

    png = None
    if args.png:
        png = html_to_png(out, out.with_suffix(".png"))
        if png:
            print(f"png     → {png}")

    if not args.no_open:
        open_path(png or out)
    return 0


def main():
    sys.exit(run())
