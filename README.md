# GitHub Daily Repository Automation Pipeline

A conservative, queue-based GitHub maintenance system whose **primary product is the repository and its GitHub Actions workflow**. It discovers repositories through the official GitHub REST API and processes **exactly one eligible repository per day**. The optional dashboard is monitoring-only and is never required for automation execution. It is designed to improve repositories only when a legitimate, safe maintenance task is available; otherwise it records `no_action_needed` and moves on at the next scheduled run.

> This project does not create fake commits, contribution farming, or meaningless file changes.

## What it does

Every run synchronizes the repository list, ignores archived repositories and this automation repository, adds newly discovered repositories to persistent state, selects one eligible item, and records the outcome. The Python engine detects common project technologies including PHP, Laravel, Python, Django, C#, ASP.NET Core, Node.js, JavaScript, TypeScript, React, Next.js, and HTML/CSS.

The current safe default is inspection-only. A project-specific maintenance adapter must be added before a repository is modified. This keeps the system from inventing work and ensures every future commit has an explicit, reviewable purpose.

## Project structure

```text
github-daily-pipeline/
├── .github/workflows/daily-pipeline.yml
├── src/
│   ├── github_api/            # GitHub REST API client
│   ├── queue/                 # persistent deterministic queue
│   ├── processor/             # one-repository processor
│   ├── detectors/             # technology and check detection
│   ├── validators/            # safety gates
│   └── logging/               # file and Actions summary logging
├── dashboard/                 # optional monitoring interface only
├── state/repos.json           # persistent queue and run history
├── logs/                      # committed execution logs
├── tests/test_pipeline.py
├── env.example.template       # copy to .env locally
├── .gitignore
└── README.md
```

## Local installation

The engine uses only Python’s standard library. Python 3.11+ is recommended.

```bash
cp env.example.template .env
# Fill in .env locally; never commit it.
export $(grep -v '^#' .env | xargs)
python -m unittest discover -s tests -v
python src/pipeline.py
```

The dashboard is optional and contains no execution path, privileged token, or API dependency. The automation continues to operate through GitHub Actions even if the dashboard is offline.

## GitHub token setup

Create a fine-grained personal access token with access limited to the repositories this pipeline is allowed to inspect and maintain. Add the following GitHub Actions secrets:

| Secret | Purpose |
| --- | --- |
| `PIPELINE_GITHUB_TOKEN` | Token used for API access and safe pushes. The built-in Actions token is used as a fallback. |
| `PIPELINE_GITHUB_USERNAME` | GitHub username whose repositories should be discovered. |

The token is read only from the environment. It is never hardcoded, written to queue state, printed to logs, or committed.

## GitHub Actions schedule

The workflow runs at **10:00 AM Pakistan Standard Time (Asia/Karachi)** every day. Pakistan Standard Time is UTC+5, so the workflow uses `0 5 * * *`. `workflow_dispatch` is also available for a manual run.

The default configuration is deliberately dry-run. Set the repository variable `PIPELINE_DRY_RUN` to `false` only after adding and reviewing a legitimate maintenance adapter. A manual dispatch includes a `dry_run` input so inspection can be tested safely.

## Queue system

`state/queue.json` is updated atomically and stores repository name, numeric ID, full name, default branch, status, last processed date, last action, failure count, enabled state, and manual-review state. Valid statuses are `pending`, `processing`, `completed`, `failed`, `skipped`, and `no_action_needed`.

New repositories are detected automatically on every run. After three consecutive failures, a repository is marked for manual review. A failed repository does not stop the workflow or prevent the next scheduled run.

## Safety boundaries

The system refuses to force-push, rewrite history, delete repositories, commit `.env` files, overwrite uncommitted user changes, expose credentials, or manufacture activity. It clones the selected repository with its default branch and checks for a clean working tree before any adapter is allowed to edit it. If the checkout is not clean, processing stops for that repository and the error is recorded.

## Dashboard

The dashboard shows total repositories, pending work, completed work, manual-review items, the repository queue, last processed date, status, failure count, latest action, and today’s selected repository. It includes a responsive mobile layout and dark/light mode. The visual language uses a warm editorial workspace with ink-blue navigation and signal orange for active attention.

## Troubleshooting

If the workflow reports that `GITHUB_TOKEN` or `GITHUB_USERNAME` is missing, verify the two Actions secrets and the repository variable name. If no repository is selected, check whether every repository is archived, disabled, already in manual review, or excluded as the automation repository. If a run fails three times, inspect the recorded `last_error` in `state/queue.json`, resolve the repository issue manually, and clear `manual_review` only after review.

If the scheduled run appears late, remember that GitHub Actions schedules are best-effort and may be delayed during periods of high load. The configured time remains 05:00 UTC / 10:00 PKT.

## Preparing for GitHub

Create the private repository `github-daily-pipeline`, push this project, add the two secrets, and enable Actions. The workflow at `.github/workflows/daily-pipeline.yml` is the execution entry point; no Manus URL is involved. Do not publish the token or local `.env` file. After the first dry run confirms discovery and queue synchronization, review and add maintenance adapters one technology at a time.
