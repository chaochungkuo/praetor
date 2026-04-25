<p align="center">
  <img src="./branding/praetor-logo-dark.svg" alt="Praetor logo" width="720" />
</p>

# Praetor

[![CI](https://github.com/chaochungkuo/praetor/actions/workflows/ci.yml/badge.svg)](https://github.com/chaochungkuo/praetor/actions/workflows/ci.yml)
[![Docker Build](https://github.com/chaochungkuo/praetor/actions/workflows/docker-build.yml/badge.svg)](https://github.com/chaochungkuo/praetor/actions/workflows/docker-build.yml)
[![CodeQL](https://github.com/chaochungkuo/praetor/actions/workflows/codeql.yml/badge.svg)](https://github.com/chaochungkuo/praetor/actions/workflows/codeql.yml)
[![Pages](https://github.com/chaochungkuo/praetor/actions/workflows/pages.yml/badge.svg)](https://chaochungkuo.github.io/praetor/)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/chaochungkuo/praetor/badge)](https://securityscorecards.dev/viewer/?uri=github.com/chaochungkuo/praetor)

Praetor is a local-first AI company operating system for solo founders.

You define direction, roles, and approval boundaries. Praetor acts like an AI CEO that organizes work, maintains company memory, delegates to execution layers, and stops at the right checkpoints.

## Current repo status

This repository currently contains:

- product and system specs
- deployment and security specs
- `praetor-execd` host-side executor bridge
- worker-side bridge client skeleton
- app backend with onboarding, mission persistence, browser UI, and API mode
- v2 React/TypeScript Praetor Office shell with CEO chat and mission timeline APIs
- authentication, setup-token, CSRF, and deployment hardening basics
- repo-local Pixi development environment

This is still an active build-stage repo, not a finished product release.

## Roadmap

- [ROADMAP.md](ROADMAP.md)

## Documentation

- [GitHub Pages documentation site](https://chaochungkuo.github.io/praetor/)
- [GitHub repository setup](docs/GITHUB_SETUP.md)
- [Public security review](docs/PRAETOR_PUBLIC_SECURITY_REVIEW.zh-TW.md)
- [Privacy boundaries](docs/PRAETOR_PRIVACY_BOUNDARIES.zh-TW.md)
- [Install checklist](docs/INSTALL_CHECKLIST.md)

## Official development baseline

Praetor now uses a **repo-local Pixi environment** as the official development baseline.

That means:

- do not rely on system Python
- do not treat ad-hoc venvs as the default workflow
- use the repo root `pixi.toml`
- Python 3.12 is the development baseline

## Quick Start

### 1. Install the workspace environment

```bash
pixi install
```

### 2. Verify the environment

```bash
pixi run py
pixi run bridge-import-check
pixi run runtime-import-check
```

### 3. Run the bridge end-to-end smoke test

```bash
pixi run bridge-e2e
```

This boots a local `praetor-execd` instance, runs the bundled mock executor, waits for completion, and verifies the polling contract.

### 4. Run the real Claude Code bridge check

```bash
pixi run claude-e2e
```

This boots a local `praetor-execd` instance, calls the real host `claude` CLI through the
bridge, and verifies the non-interactive `claude_code` path end-to-end.

### 5. Run the Praetor app

```bash
pixi run app-serve
```

Then open:

- [http://127.0.0.1:9741/app/praetor](http://127.0.0.1:9741/app/praetor)
- [http://127.0.0.1:9741/m/briefing](http://127.0.0.1:9741/m/briefing)

### 5b. Run with Docker

```bash
export PRAETOR_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export PRAETOR_SETUP_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose -f compose.app.yaml up --build
```

Then open:

- [http://127.0.0.1:9741/app/praetor?setup_token=$PRAETOR_SETUP_TOKEN](http://127.0.0.1:9741/app/praetor)
- [http://127.0.0.1:9741/m/briefing](http://127.0.0.1:9741/m/briefing)

Reference:

- [docs/PRAETOR_LOCAL_DEPLOY.md](docs/PRAETOR_LOCAL_DEPLOY.md)
- [docs/PRAETOR_REMOTE_PRIVATE_DEPLOY.md](docs/PRAETOR_REMOTE_PRIVATE_DEPLOY.md)
- [docs/PRAETOR_BACKUP_RESTORE.md](docs/PRAETOR_BACKUP_RESTORE.md)

For a production-style monolithic deploy with Docker secrets:

```bash
docker compose -f compose.app.yaml -f compose.app.production.yaml up --build -d
```

### 5c. Run the multi-service stack

```bash
docker compose -f compose.yaml up --build
```

Then open:

- [http://127.0.0.1:3000/app/praetor](http://127.0.0.1:3000/app/praetor)
- [http://127.0.0.1:3000/office](http://127.0.0.1:3000/office)

For the production overlay:

```bash
docker compose -f compose.yaml -f compose.production.yaml up --build -d
```

### 6. Run app smoke tests

```bash
pixi run app-smoke
pixi run app-ui-smoke
pixi run app-auth-smoke
pixi run app-security-smoke
pixi run app-api-smoke
pixi run app-fallback-smoke
pixi run stack-smoke
pixi run web-build
pixi run office-smoke
```

`app-smoke` verifies the backend vertical slice:

- onboarding preview
- onboarding complete
- mission creation
- mission runtime through `praetor-execd`
- mission completion and schema export

`app-ui-smoke` verifies the first browser pages:

- `Praetor`
- `Overview`
- `Tasks`
- `Memory`
- `Decisions`
- `Models`
- `Settings`

`app-auth-smoke` verifies owner account protection:

- onboarding creates the owner account
- anonymous API access is rejected
- login succeeds with the correct password
- logout clears the authenticated session

`app-security-smoke` verifies security-critical request handling:

- setup-token protected onboarding
- CSRF rejection for authenticated write requests
- successful write requests with a valid CSRF token

`app-api-smoke` verifies API mode without external dependencies:

- starts a fake OpenAI-compatible local server
- completes onboarding in `api` mode
- runs a mission through the app provider runtime
- writes requested output files
- records decisions and usage

`app-fallback-smoke` verifies runtime fallback:

- starts with `api` mode and no OpenAI key
- detects the API path failure
- falls back to the configured subscription executor
- completes the mission through the host bridge

`stack-smoke` verifies the split `web / api / worker` shape:

- `web` proxies successfully to `api`
- `worker` reports healthy visibility to `api`
- onboarding and mission creation still work through the `web` entrypoint

`office-smoke` verifies the v2 Office surface:

- initializes the app
- creates a mission
- reads the Office snapshot API
- sends a CEO conversation message
- reads the mission timeline
- verifies the React Office entrypoint is served

## Key tasks

```bash
pixi run py
pixi run check
pixi run bridge-serve
pixi run bridge-e2e
pixi run claude-e2e
pixi run app-serve
pixi run app-smoke
pixi run app-ui-smoke
pixi run app-auth-smoke
pixi run app-security-smoke
pixi run app-api-smoke
pixi run app-fallback-smoke
pixi run stack-smoke
pixi run web-build
pixi run office-smoke
pixi run bridge-smoke
pixi run bridge-import-check
pixi run runtime-import-check
pixi run py-compile
```

## Development workflow

### Repo-level workflow

Use Pixi from the repo root:

```bash
pixi install
pixi run check
```

### Run `praetor-execd`

Start the bridge with the repo environment:

```bash
export PRAETOR_EXECD_CONFIG=/absolute/path/to/config.yaml
export PRAETOR_EXECUTOR_BRIDGE_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
pixi run bridge-serve
```

### Worker-side bridge client

The worker-side client lives in:

- [workers/runtime/praetor_runtime/bridge_client.py](workers/runtime/praetor_runtime/bridge_client.py)

It provides:

- bridge health calls
- executor discovery
- run creation
- run polling
- run cancellation

## Important directories

- [docs/](docs)
- [bridges/praetor-execd/](bridges/praetor-execd)
- [workers/runtime/](workers/runtime)
- [tools/](tools)
- [pixi.toml](pixi.toml)

## Main specs

- [PRAETOR_PRODUCT_BRIEF.zh-TW.md](PRAETOR_PRODUCT_BRIEF.zh-TW.md)
- [docs/PRAETOR_SYSTEM_SPEC.zh-TW.md](docs/PRAETOR_SYSTEM_SPEC.zh-TW.md)
- [docs/PRAETOR_UI_SPEC.zh-TW.md](docs/PRAETOR_UI_SPEC.zh-TW.md)
- [docs/DEPLOYMENT_SECURITY_SPEC.zh-TW.md](docs/DEPLOYMENT_SECURITY_SPEC.zh-TW.md)
- [docs/PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md](docs/PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md)
- [docs/PRAETOR_BRAND_SPEC.zh-TW.md](docs/PRAETOR_BRAND_SPEC.zh-TW.md)
