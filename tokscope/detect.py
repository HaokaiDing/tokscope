from __future__ import annotations
from pathlib import Path
from .adapters.cline import default_task_dirs

# Borrowed from tokenarena's idea: show which AI coding tools are installed,
# so the user can see coverage at a glance. Detection != token data available —
# only tools that persist token usage locally actually contribute records.
_PATHS = [
    ("Claude Code", Path.home() / ".claude" / "projects"),
    ("Codex", Path.home() / ".codex" / "sessions"),
    ("Gemini CLI", Path.home() / ".gemini"),
    ("OpenCode", Path.home() / ".local" / "share" / "opencode"),
    ("Copilot CLI", Path.home() / ".copilot"),
    ("Hermes", Path.home() / ".hermes"),
]

DISPLAY = {
    "claude_code": "Claude Code", "codex": "Codex", "cline": "Cline",
    "gemini": "Gemini CLI", "opencode": "OpenCode", "copilot": "Copilot CLI",
}


def detect_installed() -> list[str]:
    """Names of AI coding tools that appear installed on this machine."""
    found = [name for name, path in _PATHS if path.exists()]
    if default_task_dirs():
        found.append("Cline")
    return found
