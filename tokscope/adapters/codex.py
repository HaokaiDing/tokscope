from __future__ import annotations
import json
from collections import Counter
from pathlib import Path
from .base import UsageRecord, ActivityPing, parse_iso, project_name

DEFAULT_ROOT = Path.home() / ".codex" / "sessions"


class CodexAdapter:
    name = "codex"

    def __init__(self, root: Path = DEFAULT_ROOT):
        self.root = Path(root)

    def available(self) -> bool:
        return self.root.exists()

    def collect(self) -> tuple[list[UsageRecord], list[ActivityPing]]:
        records: list[UsageRecord] = []
        pings: list[ActivityPing] = []
        for f in self.root.rglob("rollout-*.jsonl"):
            rec, file_pings = self._parse_file(f)
            if rec is not None:
                records.append(rec)
            pings.extend(file_pings)
        return records, pings

    def _parse_file(self, f: Path):
        session_id = f.stem
        project = None
        models: Counter[str] = Counter()
        last_usage = None
        last_ts = None
        file_pings: list[ActivityPing] = []
        for line in self._lines(f):
            obj = self._loads(line)
            if obj is None:
                continue
            ts = None
            if obj.get("timestamp"):
                try:
                    ts = parse_iso(obj["timestamp"])
                except (ValueError, TypeError):
                    ts = None
            t = obj.get("type")
            p = obj.get("payload") or {}
            if t == "session_meta":
                session_id = p.get("id", session_id)
                if p.get("cwd"):
                    project = project_name(p["cwd"])
            elif t == "turn_context":
                if p.get("model"):
                    models[p["model"]] += 1
                if project is None and p.get("cwd"):
                    project = project_name(p["cwd"])
            elif t == "event_msg" and p.get("type") == "token_count":
                info = p.get("info")
                if info and info.get("total_token_usage"):
                    last_usage = info["total_token_usage"]   # cumulative -> keep last
                    last_ts = ts or last_ts
            if ts is not None:
                file_pings.append(ActivityPing(self.name, session_id, ts, project))
        rec = None
        if last_usage is not None:
            model = models.most_common(1)[0][0] if models else "unknown"
            cached = last_usage.get("cached_input_tokens", 0)
            inp = last_usage.get("input_tokens", 0)
            ts = last_ts or (file_pings[-1].timestamp if file_pings else None)
            rec = UsageRecord(
                tool=self.name, session_id=session_id,
                timestamp=ts, model=model, project=project,
                input_tokens=max(inp - cached, 0),
                output_tokens=last_usage.get("output_tokens", 0),
                cache_read_tokens=cached,
                cache_creation_tokens=0,
            )
        for ping in file_pings:
            ping.session_id = session_id
            if ping.project is None:
                ping.project = project
        return rec, file_pings

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
