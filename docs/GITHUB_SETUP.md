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
- `Pages`: builds and deploys the static documentation site from `README.md` and selected `docs/` files.
- `Release`: creates a GitHub Release with generated notes when a `v*.*.*` tag is pushed.
- `Scorecard`: runs OpenSSF Scorecard on a weekly schedule and uploads SARIF results.
- `Dependabot`: weekly GitHub Actions dependency updates.

## Public Documentation

- Pages site: https://chaochungkuo.github.io/praetor/
- Scorecard: https://securityscorecards.dev/viewer/?uri=github.com/chaochungkuo/praetor

## Recommended Next Steps

- Add signed release artifacts before publishing downloadable binaries or installers.
- Turn on code owner review once the maintainer model expands beyond a single owner.
- Add package/container publishing once versioning and deployment targets are stable.
- Add preview deployments for pull requests if the documentation site starts changing frequently.
