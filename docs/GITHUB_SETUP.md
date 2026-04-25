# GitHub Setup

This repository is configured for a modern GitHub workflow.

## Repository Settings

- Default branch: `main`
- Merge strategy: squash merge only
- Delete head branches after merge: enabled
- Issues: enabled
- Wiki: disabled
- Projects: disabled
- Secret scanning: enabled
- Secret scanning push protection: enabled

## Branch Protection

`main` is protected with:

- pull request required before merge
- one approving review required
- stale reviews dismissed after new pushes
- conversation resolution required
- linear history required
- force pushes disabled
- branch deletion disabled
- required status checks:
  - `Pixi checks and smoke tests`
  - `Build service images (api, apps/api/Dockerfile)`
  - `Build service images (web, apps/web/Dockerfile)`
  - `Build service images (worker, apps/worker/Dockerfile)`
  - `Analyze Python`

## Automation

- `CI`: Pixi import/compile checks plus security, auth, API, fallback, stack, and bridge smoke tests.
- `Docker Build`: builds API, web, and worker images.
- `CodeQL`: Python static security analysis on push, PR, and weekly schedule.
- `Dependabot`: weekly GitHub Actions dependency updates.

## Recommended Next Steps

- Add release automation once versioning and packaging are stable.
- Add OpenSSF Scorecard after the repository has a few normal PR cycles.
- Add a dedicated documentation site when user-facing docs outgrow `README.md`.
- Add signed release artifacts before publishing downloadable binaries or installers.
- Turn on code owner review once the maintainer model expands beyond a single owner.
