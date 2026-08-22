"""Persistent deterministic queue state for GitHub repositories."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUSES = {"pending", "processing", "completed", "failed", "skipped", "no_action_needed"}


@dataclass
class RepositoryRecord:
    name: str
    id: int
    full_name: str
    default_branch: str
    status: str = "pending"
    last_processed_date: str | None = None
    last_action: str = "Discovered"
    failure_count: int = 0
    enabled: bool = True
    queue_position: int = 0
    manual_review: bool = False
    last_error: str | None = None


class QueueStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"repositories": [], "runs": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, state: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def sync(self, discovered: list[dict[str, Any]], automation_repo: str) -> list[RepositoryRecord]:
        state = self.load()
        records = {item["id"]: RepositoryRecord(**item) for item in state.get("repositories", [])}
        for repo in discovered:
            if repo.get("archived") or repo["full_name"] == automation_repo:
                continue
            if repo["id"] not in records:
                records[repo["id"]] = RepositoryRecord(repo["name"], repo["id"], repo["full_name"], repo.get("default_branch") or "main")
            else:
                records[repo["id"]].default_branch = repo.get("default_branch") or records[repo["id"]].default_branch
        ordered = sorted(records.values(), key=lambda r: (r.last_processed_date is not None, r.last_processed_date or "", r.id))
        for position, record in enumerate(ordered, 1):
            record.queue_position = position
        state["repositories"] = [asdict(record) for record in ordered]
        self.save(state)
        return ordered

    def next_eligible(self) -> RepositoryRecord | None:
        records = [RepositoryRecord(**item) for item in self.load().get("repositories", [])]
        eligible = [r for r in records if r.enabled and not r.manual_review and r.status in {"pending", "skipped", "no_action_needed"}]
        return sorted(eligible, key=lambda r: r.queue_position)[0] if eligible else None

    def record(self, record: RepositoryRecord, status: str, action: str, error: str | None = None) -> None:
        if status not in STATUSES:
            raise ValueError(f"Unknown status: {status}")
        state = self.load()
        date = datetime.now(timezone.utc).date().isoformat()
        for item in state.get("repositories", []):
            if item["id"] == record.id:
                item.update(asdict(record), status=status, last_action=action, last_processed_date=date, last_error=error)
        state.setdefault("runs", []).append({"timestamp": datetime.now(timezone.utc).isoformat(), "repository": record.full_name, "status": status, "action": action, "error": error})
        state["runs"] = state["runs"][-100:]
        self.save(state)
