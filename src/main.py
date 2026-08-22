"""GitHub Actions entry point for one-repository-per-day rotation."""
from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from src.github_api.client import GitHubClient
from src.logging.runlog import actions_summary, configure
from src.processor.engine import process
from src.queue.store import QueueStore


def main() -> int:
    logger = configure(os.environ.get("LOG_DIR", "logs"))
    token = os.environ.get("GITHUB_TOKEN")
    username = os.environ.get("GITHUB_USERNAME")
    if not token or not username:
        raise SystemExit("GITHUB_TOKEN and GITHUB_USERNAME are required")
    timezone_name = os.environ.get("TIMEZONE", "Asia/Karachi")
    run_date = datetime.now(ZoneInfo(timezone_name)).date().isoformat()
    client = GitHubClient(token, username)
    store = QueueStore(os.environ.get("QUEUE_STATE_PATH", "state/repos.json"))
    automation_repo = os.environ.get("AUTOMATION_REPOSITORY", f"{username}/github-daily-pipeline")
    records = store.sync(client.repositories(), automation_repo)
    target = store.select_for_day(run_date)
    if target is None:
        message = f"No repository selected: the daily rotation for {run_date} is already complete or the queue is empty"
        logger.info(message)
        actions_summary("Daily repository rotation", [message, f"Total repositories: {len(records)}"])
        return 0

    store.begin_run(target, run_date)
    dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
    logger.info("Date=%s selected=%s position=%s/%s new=%s dry_run=%s", run_date, target.full_name, target.queue_position, len(records), target.is_new, dry_run)
    try:
        status, action = process(target, dry_run, logger)
        target.status = status
        next_position = next((r.queue_position for r in records if r.enabled and not r.manual_review and r.queue_position > target.queue_position), None)
        if next_position is None:
            next_position = min((r.queue_position for r in records if r.enabled and not r.manual_review), default=1)
        store.finish_run(target, status, action, run_date, push_result="not_attempted" if dry_run else "adapter_not_configured")
        logger.info("Result=%s action=%s next_position=%s", status, action, next_position)
        actions_summary("Daily repository rotation", [
            f"Date: `{run_date}`", f"Selected: `{target.full_name}` ({target.queue_position}/{len(records)})",
            f"New repository: `{target.is_new}`", f"Result: `{status}`", f"Action: {action}",
            f"Dry run: `{dry_run}`", f"Next rotation position: `{next_position}`",
        ])
    except Exception as error:
        store.record_failure(target, run_date, "Processing failed", str(error))
        logger.exception("Processing failed for %s", target.full_name)
        actions_summary("Daily repository rotation failure", [f"Date: `{run_date}`", f"Selected: `{target.full_name}`", f"Failure count: `{target.failure_count}`", f"Manual review: `{target.manual_review}`", f"Error: {error}"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
