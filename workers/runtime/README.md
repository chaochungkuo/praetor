# Praetor Runtime Worker Skeleton

This directory contains worker-side client code for integrating with `praetor-execd`.

## Official dev workflow

Use the repo root Pixi environment:

```bash
cd /Users/jovesus/glasrocks/praetor
pixi install
pixi run runtime-import-check
```

This worker-side package is not meant to be developed through a separate ad-hoc venv by default.

Current scope:

- `bridge_client.py`
- worker polling contract helpers

It is intentionally small and decoupled from the main app for now.

## Current entry point

- [praetor_runtime/bridge_client.py](/Users/jovesus/glasrocks/praetor/workers/runtime/praetor_runtime/bridge_client.py)

Current responsibilities:

- call bridge health endpoints
- create runs
- poll runs to terminal state
- cancel runs
