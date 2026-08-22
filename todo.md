# GitHub-first refactor checklist

- [ ] Audit current files and confirm the Manus dashboard is not required by the automation.
- [ ] Refactor automation code into `src/github_api`, `src/queue`, `src/processor`, `src/detectors`, `src/validators`, and `src/logging`.
- [ ] Add persistent `state/repos.json` with deterministic queue position and failure metadata.
- [ ] Add execution logs and GitHub Actions step summary output.
- [ ] Add safe legitimate-maintenance adapter behavior with tests/build checks and no fake commits.
- [ ] Add concurrency protection and verify the 05:00 UTC schedule plus `workflow_dispatch`.
- [ ] Create the private GitHub repository `github-daily-pipeline` and push the complete source.
- [ ] Verify the remote repository contains the required workflow and primary files.
- [ ] Report the exact GitHub Secrets and minimum permissions required.
