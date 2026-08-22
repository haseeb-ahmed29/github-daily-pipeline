# GitHub Daily Repository Pipeline

This repository is the **primary automation product**. GitHub Actions discovers the current repositories for `haseeb-ahmed29`, selects exactly one repository in deterministic rotation order per Pakistan calendar day, performs approved maintenance checks, records the result, and advances the rotation. The optional Manus dashboard is monitoring-only; the workflow does not require it or any Manus URL.

> The system never creates fake commits. If no approved meaningful maintenance task is available, it records `no_action_needed` and advances normally.

## Daily rotation

The workflow runs at **10:00 AM Asia/Karachi**, configured as `0 5 * * *` UTC. It also supports `workflow_dispatch` for manual testing. Each run fetches the current GitHub repository list, ignores archived repositories and the automation repository, appends new repositories to the queue, and selects the next enabled repository by persistent `queue_position`.

After the last eligible repository, the next run wraps to position 1. A second trigger on the same Pakistan calendar date returns without selecting another repository. Failed repositories also advance the pointer; after three failures they are marked for manual review so the rotation cannot remain blocked forever.

## Structure

```text
github-daily-pipeline/
├── .github/workflows/daily-pipeline.yml
├── src/
│   ├── github_api/            # GitHub REST API access
│   ├── queue/                 # persistent rotation state and index
│   ├── processor/             # one-repository processing flow
│   ├── detectors/             # technology and validation command detection
│   ├── validators/            # clean-tree and credential safety gates
│   ├── logging/               # file logs and Actions summaries
│   └── main.py                # Actions entry point
├── state/repos.json           # durable queue, rotation pointer, and run records
├── logs/                      # committed execution logs
├── tests/test_rotation.py
├── tests/test_pipeline.py
├── .env.example
├── .gitignore
└── README.md
```

## Secrets and variables

Configure these GitHub Actions Secrets:

| Name | Required value | Purpose |
| --- | --- | --- |
| `PIPELINE_GITHUB_TOKEN` | A token with access to the repositories the pipeline may maintain | API discovery and pushes to target repositories. |
| `PIPELINE_GITHUB_USERNAME` | `haseeb-ahmed29` | Account whose repositories are discovered. |

The workflow maps those secrets to `GITHUB_TOKEN` and `GITHUB_USERNAME` at runtime. Secret values are never printed or written to state. The workflow requests `contents: write` for its own state commit; a fine-grained token should be restricted to the minimum target repositories and Contents read/write access only. Do not commit `.env`.

## Dry run

Keep `DRY_RUN=true` while validating discovery and rotation. In dry-run mode the engine discovers repositories, persists the queue, selects one repository, records the planned action, and does not clone, modify, commit, or push to the selected repository. The workflow may still commit `state/repos.json` and `logs/pipeline.log` to the automation repository so the queue and audit trail persist.

For a manual test, open **Actions → Daily repository maintenance → Run workflow**, choose `dry_run: true`, and start the run. The Actions summary reports the date, selected repository, position, total queue size, new-repository flag, result, and next rotation position.

## Processing behavior

The processor detects PHP, Laravel, Python, Django, C#, ASP.NET Core, Node.js, JavaScript, TypeScript, React, Next.js, and HTML/CSS markers. It runs safe checks when project manifests support them. Generic edits are prohibited: an approved, project-specific maintenance adapter must identify a real improvement before a target repository can be changed. When no such adapter applies, the correct result is `no_action_needed`.

Before any future adapter is allowed to write, the processor must verify a clean checkout, reject `.env` and history paths, run the appropriate tests or build, use a meaningful commit message, and push without force. Visibility, secrets, unrelated files, and user work are never modified.

## Local validation

```bash
python -m unittest discover -s tests -v
python -m src.main
```

For local execution, copy `.env.example` to `.env`, set the placeholders, and keep `DRY_RUN=true`. The runtime uses only Python’s standard library.

## Troubleshooting

If authentication fails, verify the two Actions Secrets exist and that the token can read the account repositories. If the queue is empty, every repository may be archived, excluded, disabled, or under manual review. If a repository is already processed on the same Pakistan calendar date, the duplicate guard intentionally selects nothing. If a run fails three times, inspect `last_error` and resolve the repository issue before clearing `manual_review`.

GitHub scheduled workflows are best-effort and can be delayed during platform load, but the configured schedule remains 05:00 UTC / 10:00 PKT. The automation remains functional if the dashboard is offline.
