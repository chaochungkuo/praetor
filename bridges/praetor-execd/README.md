# praetor-execd

Host-side executor bridge for Praetor subscription executor mode.

This package is intentionally separate from the Docker app stack.

## Official dev workflow

The official development path is now the **repo root Pixi environment**.

Preferred usage:

```bash
cd <repo-root>
pixi install
pixi run bridge-import-check
pixi run bridge-e2e
pixi run claude-e2e
```

To run the bridge itself:

```bash
export PRAETOR_EXECD_CONFIG=/absolute/path/to/config.yaml
export PRAETOR_EXECUTOR_BRIDGE_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
pixi run bridge-serve
```

The standalone venv flow below is still possible, but it is no longer the primary repo workflow.

## Scope

Current skeleton includes:

- FastAPI server
- bearer-token auth
- config loader
- executor registry summary
- path mapping validation
- in-memory run store
- background subprocess execution
- JSON log persistence
- run / status / events / cancel endpoints
- OpenAPI and JSON schemas
- executor-specific native runners for `codex` and `claude_code`
- executor health probes
- Codex JSONL usage parsing

Not implemented yet:

- artifact diffing
- persistent run recovery
- executor-specific login probes beyond command health

## Executor installation notes

For `claude_code`, prefer Anthropic's native install or the official Homebrew cask.

The older npm global package runs on your host Node.js runtime and can break on unsupported
Node versions. The native/Homebrew install ships the supported runtime path and is the
recommended setup for `praetor-execd`.

## Quick Start

Preferred:

```bash
cd <repo-root>
pixi install
pixi run bridge-e2e
pixi run claude-e2e
```

Standalone fallback:

```bash
cd bridges/praetor-execd
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp config.example.yaml config.yaml
export PRAETOR_EXECD_CONFIG=$PWD/config.yaml
export PRAETOR_EXECUTOR_BRIDGE_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
uvicorn praetor_execd.main:app --host 127.0.0.1 --port 9417 --reload
```

## Mock Smoke Test

You can point the `codex.command` in `config.yaml` to the bundled mock executor:

```yaml
executors:
  codex:
    enabled: true
    command: /Users/you/miniforge3/envs/work/bin/python3.12
    args:
      - /absolute/path/to/bridges/praetor-execd/dev/mock_executor.py
```

When `command` points to a non-native binary such as the bundled mock executor, the bridge automatically falls back to the generic stdin JSON contract instead of trying to pass native `codex` flags.

## Config

Use `config.example.yaml` as the starting point.

## Files

- `openapi/praetor-execd.openapi.yaml`
- `schemas/*.schema.json`
- `praetor_execd/`
