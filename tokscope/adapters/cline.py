from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .base import UsageRecord, ActivityPing

# Cline is a VS Code extension; tasks live under each editor's globalStorage.
_REL = "Library/Application Support/{app}/User/globalStorage/saoudrizwan.claude-dev/tasks"
_APPS = ["Code", "Cursor", "Code - Insiders", "Windsurf", "VSCodium"]


def default_task_dirs() -> list[Path]:
    home = Path.home()
    return [home / _REL.format(app=a) for a in _APPS
            if (home / _REL.format(app=a)).exists()]


class ClineAdapter:
    name = "cline"

    def __init__(self, root: Path):
        self.root = Path(root)

    def available(self) -> bool:
        return self.root.exists()

    def collect(self) -> tuple[list[UsageRecord], list[ActivityPing]]:
        records: list[UsageRecord] = []
        pings: list[ActivityPing] = []
        for task in sorted(p for p in self.root.iterdir() if p.is_dir()):
            rec, tp = self._task(task)
            if rec is not None:
                records.append(rec)
            pings.extend(tp)
        return records, pings

    def _task(self, task: Path):
        ui = self._load(task / "ui_messages.json")
        if not isinstance(ui, list):
            return None, []
        ti = to = cr = cw = 0
        found = False
        pings: list[ActivityPing] = []
        sid = task.name
        for m in ui:
            ts = m.get("ts")
            if isinstance(ts, (int, float)):
                pings.append(ActivityPing(self.name, sid,
                                          datetime.fromtimestamp(ts / 1000, tz=timezone.utc), None))
            if m.get("say") == "api_req_started":
                try:
                    info = json.loads(m.get("text") or "{}")
                except json.JSONDecodeError:
                    continue
                ti += info.get("tokensIn", 0)        # new (non-cache) input
                to += info.get("tokensOut", 0)
                cr += info.get("cacheReads", 0)
                cw += info.get("cacheWrites", 0)
                found = True
        if not found:
            return None, pings
        model = self._model(self._load(task / "task_metadata.json"))
        try:
            ts0 = datetime.fromtimestamp(int(task.name) / 1000, tz=timezone.utc)
        except ValueError:
            ts0 = pings[0].timestamp if pings else datetime.now(timezone.utc)
        rec = UsageRecord(
            tool=self.name, session_id=sid, timestamp=ts0, model=model, project=None,
            input_tokens=ti, output_tokens=to, cache_read_tokens=cr, cache_creation_tokens=cw,
        )
        return rec, pings

    @staticmethod
    def _model(meta) -> str:
        if isinstance(meta, dict):
            mu = meta.get("model_usage")
            if isinstance(mu, list):
                ids = [e.get("model_id") for e in mu if isinstance(e, dict) and e.get("model_id")]
                if ids:
                    return Counter(ids).most_common(1)[0][0]
        return "unknown"

    @staticmethod
    def _load(p: Path):
        try:
            return json.loads(p.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, json.JSONDecodeError):
            return None
