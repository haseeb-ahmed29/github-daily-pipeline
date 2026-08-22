"""GitHub Actions entry point; independent of the dashboard."""
from __future__ import annotations

import os

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
    client = GitHubClient(token, username)
    store = QueueStore(os.environ.get("QUEUE_STATE_PATH", "state/repos.json"))
    automation_repo = os.environ.get("AUTOMATION_REPOSITORY", "")
    records = store.sync(client.repositories(), automation_repo)
    target = store.next_eligible()
    if target is None:
        logger.info("No eligible repository in queue")
        actions_summary("Daily pipeline", [f"Discovered {len(records)} eligible repositories", "No eligible repository was selected"])
        return 0
    store.record(target, "processing", "Selected for daily processing")
    dry_run = os.environ.get("DRY_RUN", "true").lower() == "true"
    try:
        status, action = process(target, dry_run, logger)
        target.status = status
        store.record(target, status, action)
        actions_summary("Daily pipeline", [f"Repository: `{target.full_name}`", f"Status: `{status}`", f"Action: {action}", f"Dry run: `{dry_run}`"])
    except Exception as error:  # keep the schedule alive for the next repository
        target.failure_count += 1
        target.manual_review = target.failure_count >= 3
        target.status = "failed"
        store.record(target, "failed", "Processing failed", str(error))
        logger.exception("Processing failed for %s", target.full_name)
        actions_summary("Daily pipeline failure", [f"Repository: `{target.full_name}`", f"Failure count: `{target.failure_count}`", f"Manual review: `{target.manual_review}`", f"Error: {error}"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
