from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Protocol, runtime_checkable


@dataclass
class UsageRecord:
    tool: str
    session_id: str
    timestamp: datetime
    model: str
    project: str | None
    input_tokens: int = 0          # non-cached input
    output_tokens: int = 0         # includes reasoning
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cost_usd: float = 0.0          # filled by pricing
    priced: bool = False           # filled by pricing


@dataclass
class ActivityPing:
    tool: str
    session_id: str
    timestamp: datetime
    project: str | None = None


@runtime_checkable
class Adapter(Protocol):
    name: str

    def available(self) -> bool: ...

    def collect(self) -> tuple[list[UsageRecord], list[ActivityPing]]: ...


def parse_iso(ts: str) -> datetime:
    """Parse ISO-8601 (with trailing Z) into a tz-aware datetime."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def project_name(cwd: str | None) -> str | None:
    """Basename of cwd as the project; None for the home dir (not a project)."""
    if not cwd:
        return None
    p = Path(cwd)
    if p == Path.home():
        return None
    return p.name
