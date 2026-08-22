"""GitHub Daily Repository Automation Pipeline.

Style note: operational code mirrors the editorial console—explicit, auditable,
and conservative. Every external side effect is isolated behind a small method.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

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
    manual_review: bool = False


class GitHubClient:
    def __init__(self, token: str, username: str | None = None) -> None:
        self.token = token
        self.username = username
        self.base_url = "https://api.github.com"

    def request(self, path: str) -> Any:
        req = Request(
            self.base_url + path,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "github-daily-pipeline",
            },
        )
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def repositories(self) -> list[dict[str, Any]]:
        page = 1
        repositories: list[dict[str, Any]] = []
        while True:
            batch = self.request(f"/user/repos?per_page=100&page={page}&sort=created")
            if not batch:
                return repositories
            repositories.extend(batch)
            if len(batch) < 100:
                return repositories
            page += 1


class QueueStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"repositories": [], "runs": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, state: dict[str, Any]) -> None:
        temp_path = self.path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temp_path.replace(self.path)

    def sync_repositories(self, discovered: list[dict[str, Any]], automation_repo: str) -> list[RepositoryRecord]:
        state = self.load()
        current = {item["id"]: RepositoryRecord(**item) for item in state.get("repositories", [])}
        for repo in discovered:
            full_name = repo["full_name"]
            if repo.get("archived") or full_name == automation_repo:
                continue
            if repo["id"] not in current:
                current[repo["id"]] = RepositoryRecord(
                    name=repo["name"], id=repo["id"], full_name=full_name,
                    default_branch=repo.get("default_branch") or "main",
                )
            else:
                current[repo["id"]].default_branch = repo.get("default_branch") or current[repo["id"]].default_branch
        records = sorted(current.values(), key=lambda item: (item.status != "pending", item.name.lower()))
        state["repositories"] = [asdict(record) for record in records]
        self.save(state)
        return records

    def next_eligible(self) -> RepositoryRecord | None:
        records = [RepositoryRecord(**item) for item in self.load().get("repositories", [])]
        eligible = [r for r in records if r.enabled and not r.manual_review and r.status in {"pending", "skipped", "no_action_needed"}]
        return sorted(eligible, key=lambda r: (r.last_processed_date is not None, r.last_processed_date or "", r.name.lower()))[0] if eligible else None

    def update(self, record: RepositoryRecord, action: str, status: str, error: str | None = None) -> None:
        if status not in STATUSES:
            raise ValueError(f"Unknown status: {status}")
        state = self.load()
        for item in state.get("repositories", []):
            if item["id"] == record.id:
                item.update(asdict(record), status=status, last_processed_date=datetime.now(timezone.utc).date().isoformat(), last_action=action)
                if error:
                    item["last_error"] = error
                break
        state.setdefault("runs", []).append({
            "timestamp": datetime.now(timezone.utc).isoformat(), "repository": record.full_name,
            "status": status, "action": action, "error": error,
        })
        state["runs"] = state["runs"][-100:]
        self.save(state)


def detect_technology(repo_dir: Path) -> list[str]:
    markers = {
        "Python": ["pyproject.toml", "requirements.txt", "setup.py"],
        "Django": ["manage.py"], "Node.js": ["package.json"], "TypeScript": ["tsconfig.json"],
        "Laravel": ["artisan"], "PHP": ["composer.json"], "C# / ASP.NET Core": ["*.csproj", "*.sln"],
        "React": ["src/App.tsx", "src/App.jsx"],
    }
    found = []
    for name, files in markers.items():
        matches = []
        for pattern in files:
            matches.extend(repo_dir.glob(pattern) if "*" in pattern else [repo_dir / pattern])
        if any(path.exists() for path in matches):
            found.append(name)
    return found or ["HTML/CSS or unknown"]


def run_command(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)


def process_repository(record: RepositoryRecord, client: GitHubClient, dry_run: bool, logger: logging.Logger) -> tuple[str, str]:
    """Process one repository conservatively.

    The engine only commits when a legitimate maintenance task is discovered by
    a configured project-specific adapter. It never fabricates a change.
    """
    if dry_run:
        return "no_action_needed", f"Dry run: would inspect {record.full_name} on {record.default_branch}"
    with tempfile.TemporaryDirectory(prefix="github-pipeline-") as workspace:
        repo_dir = Path(workspace) / record.name
        run_command(["git", "clone", "--depth", "1", "--branch", record.default_branch, f"https://github.com/{record.full_name}.git", str(repo_dir)], Path(workspace))
        clean = subprocess.run(["git", "status", "--porcelain"], cwd=repo_dir, text=True, stdout=subprocess.PIPE, check=True).stdout.strip()
        if clean:
            raise RuntimeError("Repository has uncommitted changes after checkout; refusing to overwrite user work")
        technologies = detect_technology(repo_dir)
        logger.info("Inspected %s: %s", record.full_name, ", ".join(technologies))
        # Deliberately no generic edit: meaningful changes require an adapter or human review.
        return "no_action_needed", f"Inspected {', '.join(technologies)}; no safe, meaningful update identified"


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger("github-daily-pipeline")
    token = os.environ.get("GITHUB_TOKEN")
    username = os.environ.get("GITHUB_USERNAME")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    if not username:
        raise SystemExit("GITHUB_USERNAME is required")
    store = QueueStore(os.environ.get("QUEUE_STATE_PATH", "state/queue.json"))
    client = GitHubClient(token, username)
    automation_repo = os.environ.get("AUTOMATION_REPOSITORY", f"{username}/github-daily-pipeline")
    records = store.sync_repositories(client.repositories(), automation_repo)
    target = store.next_eligible()
    if not target:
        logger.info("No eligible repositories in queue")
        return 0
    target.status = "processing"
    store.update(target, "Selected for daily run", "processing")
    dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
    try:
        status, action = process_repository(target, client, dry_run, logger)
        target.status = status
        store.update(target, action, status)
    except Exception as exc:  # one failure must not stop future scheduled runs
        target.failure_count += 1
        target.status = "failed"
        target.manual_review = target.failure_count >= 3
        logger.exception("Failed processing %s", target.full_name)
        store.update(target, str(exc), "failed", str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
