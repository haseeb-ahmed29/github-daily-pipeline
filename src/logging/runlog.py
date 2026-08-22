"""File and GitHub Actions summary logging."""
from __future__ import annotations

import logging
import os
from pathlib import Path


def configure(log_dir: str = "logs") -> logging.Logger:
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("github-daily-pipeline")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.FileHandler(Path(log_dir) / "pipeline.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.addHandler(logging.StreamHandler())
    return logger


def actions_summary(title: str, lines: list[str]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with open(summary_path, "a", encoding="utf-8") as stream:
        stream.write(f"## {title}\n\n")
        for line in lines:
            stream.write(f"- {line}\n")
