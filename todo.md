# GitHub-first refactor checklist

- [x] Audit current files and confirm the Manus dashboard is not required by the automation.
- [x] Refactor automation code into `src/github_api`, `src/queue`, `src/processor`, `src/detectors`, `src/validators`, and `src/logging`.
- [x] Add persistent `state/repos.json` with deterministic queue position and failure metadata.
- [x] Add execution logs and GitHub Actions summary output.
- [x] Add safe legitimate-maintenance adapter behavior with tests/build checks and no fake commits.
- [x] Add concurrency protection and verify the 05:00 UTC schedule plus `workflow_dispatch`.
- [x] Create the private GitHub repository `github-daily-pipeline` and push the complete source.
- [x] Verify the remote repository contains the required workflow and primary files.
- [x] Report the exact GitHub Secrets and minimum permissions required.
