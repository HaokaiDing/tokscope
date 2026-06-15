from __future__ import annotations
import json
from pathlib import Path
from .base import UsageRecord, ActivityPing, parse_iso, project_name

DEFAULT_ROOT = Path.home() / ".claude" / "projects"


class ClaudeCodeAdapter:
    name = "claude_code"

    def __init__(self, root: Path = DEFAULT_ROOT):
        self.root = Path(root)

    def available(self) -> bool:
        return self.root.exists()

    def collect(self) -> tuple[list[UsageRecord], list[ActivityPing]]:
        records: list[UsageRecord] = []
        pings: list[ActivityPing] = []
        for f in self.root.rglob("*.jsonl"):
            for line in self._lines(f):
                obj = self._loads(line)
                if obj is None or obj.get("type") != "assistant":
                    continue
                msg = obj.get("message") or {}
                usage = msg.get("usage") or {}
                model = msg.get("model")
                if not model or model == "<synthetic>" or "input_tokens" not in usage:
                    continue
                try:
                    ts = parse_iso(obj["timestamp"])
                except (KeyError, ValueError):
                    continue
                project = project_name(obj.get("cwd"))
                sid = obj.get("sessionId", f.stem)
                records.append(UsageRecord(
                    tool=self.name, session_id=sid, timestamp=ts, model=model,
                    project=project,
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    cache_read_tokens=usage.get("cache_read_input_tokens", 0),
                    cache_creation_tokens=usage.get("cache_creation_input_tokens", 0),
                ))
                pings.append(ActivityPing(self.name, sid, ts, project))
        return records, pings

    @staticmethod
    def _lines(path: Path):
        with path.open(encoding="utf-8", errors="ignore") as fh:
            yield from fh

    @staticmethod
    def _loads(line: str):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            return None
