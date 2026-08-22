"""One-repository-per-run processor with conservative maintenance behavior."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from src.detectors.project import check_commands, detect_technology
from src.validators.safety import ensure_clean_checkout


def _run(command: list[str], cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180, check=True)
    return result.stdout[-4000:]


def process(record, dry_run: bool, logger) -> tuple[str, str]:
    if dry_run:
        return "no_action_needed", f"Dry run: would inspect {record.full_name} on {record.default_branch}"
    with tempfile.TemporaryDirectory(prefix="github-daily-pipeline-") as workspace:
        root = Path(workspace) / record.name
        _run(["git", "clone", "--depth", "1", "--branch", record.default_branch, f"https://github.com/{record.full_name}.git", str(root)], Path(workspace))
        ensure_clean_checkout(root)
        technologies = detect_technology(root)
        for command in check_commands(root, technologies):
            try:
                logger.info("Running %s for %s", " ".join(command), record.full_name)
                _run(command, root)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                raise RuntimeError(f"Validation command failed: {' '.join(command)} ({error})") from error
        # No generic edit is permitted. An adapter must identify a real task and
        # validate its change paths before this function can commit or push.
        return "no_action_needed", f"Inspected {', '.join(technologies)} and ran available checks; no approved meaningful update found"
