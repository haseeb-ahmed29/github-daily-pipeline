"""Safety gates for repository processing."""
from __future__ import annotations

import subprocess
from pathlib import Path


class SafetyViolation(RuntimeError):
    pass


def ensure_clean_checkout(root: Path) -> None:
    result = subprocess.run(["git", "status", "--porcelain"], cwd=root, text=True, stdout=subprocess.PIPE, check=True)
    if result.stdout.strip():
        raise SafetyViolation("Repository has uncommitted changes; refusing to overwrite user work")


def validate_push_command(command: list[str]) -> None:
    forbidden = {"--force", "--force-with-lease", "-f"}
    if any(part in forbidden for part in command):
        raise SafetyViolation("Force push is prohibited")


def validate_change_paths(paths: list[str]) -> None:
    if any(path == ".env" or path.endswith("/.env") or path.startswith(".git/") for path in paths):
        raise SafetyViolation("Credential and history paths cannot be changed")
