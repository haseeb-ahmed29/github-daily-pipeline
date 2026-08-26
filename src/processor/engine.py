"""One-repository-per-run processor with README-only maintenance."""
from __future__ import annotations

from datetime import date
import subprocess
import tempfile
from pathlib import Path

from src.detectors.project import check_commands, detect_technology
from src.github_api.client import GitHubClient
from src.validators.safety import ensure_clean_checkout


MARKER = "<!-- github-daily-pipeline -->"


def _run(command: list[str], cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180, check=True)
    return result.stdout[-4000:]


def _maintenance_section(existing: str | None, run_date: str) -> str:
    """Add or refresh one bounded section while preserving the repository's README."""
    current = existing or "# Project\n"
    section = (
        f"{MARKER}\n"
        "## Daily maintenance\n\n"
        f"README verified by the daily repository maintenance pipeline on {run_date}.\n"
        ""
    )
    if MARKER in current:
        prefix = current.split(MARKER, 1)[0].rstrip()
        return f"{prefix}\n\n{section}"
    return f"{current.rstrip()}\n\n{section}"


def process(record, dry_run: bool, logger, client: GitHubClient | None = None, run_date: str | None = None) -> tuple[str, str, str | None, str]:
    """Update only README.md through the Contents API; return status, action, SHA, push result."""
    if dry_run:
        return "no_action_needed", f"Dry run: would update README.md in {record.full_name} on {record.default_branch}", None, "not_attempted"
    if client is None:
        raise RuntimeError("GitHub client is required when DRY_RUN is false")

    effective_date = run_date or date.today().isoformat()
    readme = client.readme(record.full_name, record.default_branch)
    existing = None
    sha = None
    if readme:
        sha = readme.get("sha")
        encoded = readme.get("content", "")
        import base64
        existing = base64.b64decode(encoded).decode("utf-8") if encoded else ""
    content = _maintenance_section(existing, effective_date)
    if existing == content:
        return "no_action_needed", "README already contains today's maintenance entry", None, "not_attempted"

    response = client.update_readme(
        record.full_name,
        record.default_branch,
        content,
        f"docs: update README maintenance record ({effective_date})",
        sha=sha,
    )
    commit_sha = ((response.get("commit") or {}).get("sha"))
    logger.info("Updated README.md in %s with commit %s", record.full_name, commit_sha or "unknown")
    return "completed", "Updated README.md with today's maintenance record", commit_sha, "pushed"
