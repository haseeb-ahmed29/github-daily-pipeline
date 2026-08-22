"""Persistent daily repository rotation state."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
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
    is_new: bool = True


class QueueStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"repositories": [], "runs": [], "rotation": {"last_run_date": None, "last_repository_id": None, "next_position": 1}}
        state = json.loads(self.path.read_text(encoding="utf-8"))
        state.setdefault("runs", [])
        state.setdefault("rotation", {"last_run_date": None, "last_repository_id": None, "next_position": 1})
        state["rotation"].setdefault("next_position", 1)
        for item in state.get("repositories", []):
            item.setdefault("last_error", None)
            item.setdefault("is_new", False)
            item.setdefault("queue_position", 0)
            item.setdefault("manual_review", False)
        return state

    def save(self, state: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.path)

    def sync(self, discovered: list[dict[str, Any]], automation_repo: str) -> list[RepositoryRecord]:
        state = self.load()
        current = {item["id"]: RepositoryRecord(**item) for item in state.get("repositories", [])}
        max_position = max((record.queue_position for record in current.values()), default=0)
        for repo in discovered:
            if repo.get("archived") or repo["full_name"] == automation_repo:
                continue
            if repo["id"] not in current:
                max_position += 1
                current[repo["id"]] = RepositoryRecord(
                    name=repo["name"], id=repo["id"], full_name=repo["full_name"],
                    default_branch=repo.get("default_branch") or "main", queue_position=max_position,
                )
            else:
                record = current[repo["id"]]
                record.default_branch = repo.get("default_branch") or record.default_branch
                record.is_new = False
        records = sorted(current.values(), key=lambda record: record.queue_position)
        state["repositories"] = [asdict(record) for record in records]
        state["rotation"]["next_position"] = self._next_position(records, state["rotation"].get("next_position", 1))
        self.save(state)
        return records

    @staticmethod
    def _next_position(records: list[RepositoryRecord], position: int) -> int:
        if not records:
            return 1
        positions = {record.queue_position for record in records}
        if position in positions:
            return position
        return min(positions)

    def next_eligible(self) -> RepositoryRecord | None:
        """Return the next eligible record without changing daily state."""
        records = [RepositoryRecord(**item) for item in self.load().get("repositories", [])]
        eligible = [record for record in records if record.enabled and not record.manual_review]
        return sorted(eligible, key=lambda record: record.queue_position)[0] if eligible else None

    def select_for_day(self, run_date: str) -> RepositoryRecord | None:
        state = self.load()
        if state["rotation"].get("last_run_date") == run_date:
            return None
        records = [RepositoryRecord(**item) for item in state.get("repositories", [])]
        eligible = [record for record in records if record.enabled and not record.manual_review]
        if not eligible:
            return None
        next_position = state["rotation"].get("next_position", 1)
        ordered = sorted(eligible, key=lambda record: record.queue_position)
        at_or_after = [record for record in ordered if record.queue_position >= next_position]
        return (at_or_after or ordered)[0]

    def begin_run(self, record: RepositoryRecord, run_date: str) -> None:
        state = self.load()
        state["rotation"]["last_run_date"] = run_date
        state["rotation"]["last_repository_id"] = record.id
        for item in state.get("repositories", []):
            if item["id"] == record.id:
                item.update(status="processing", last_action="Selected for daily rotation", is_new=False)
        self.save(state)

    def finish_run(self, record: RepositoryRecord, status: str, action: str, run_date: str, error: str | None = None, commit_sha: str | None = None, push_result: str = "not_attempted") -> None:
        if status not in STATUSES:
            raise ValueError(f"Unknown status: {status}")
        state = self.load()
        records = [RepositoryRecord(**item) for item in state.get("repositories", [])]
        was_new = record.is_new
        record.status = status
        record.last_processed_date = run_date
        record.last_action = action
        record.last_error = error
        record.is_new = False
        for item in records:
            if item.id == record.id:
                item.__dict__.update(record.__dict__)
        positions = sorted(item.queue_position for item in records if item.enabled and not item.manual_review)
        next_position = next((position for position in positions if position > record.queue_position), positions[0] if positions else 1)
        state["repositories"] = [asdict(item) for item in records]
        state["rotation"].update(last_run_date=run_date, last_repository_id=record.id, next_position=next_position)
        state.setdefault("runs", []).append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "date": run_date,
            "repository": record.full_name,
            "rotation_position": record.queue_position,
            "total_repositories": len(records),
            "is_new": was_new,
            "status": status,
            "action": action,
            "commit_sha": commit_sha,
            "push_result": push_result,
            "next_position": next_position,
            "error": error,
        })
        state["runs"] = state["runs"][-100:]
        self.save(state)

    def record_failure(self, record: RepositoryRecord, run_date: str, action: str, error: str) -> None:
        record.failure_count += 1
        record.manual_review = record.failure_count >= 3
        self.finish_run(record, "failed", action, run_date, error=error, push_result="not_attempted")
