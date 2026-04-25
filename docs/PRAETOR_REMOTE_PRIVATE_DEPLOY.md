# Praetor Remote Private Deploy

This document describes the practical self-hosted path for running the current Praetor app on a private server.

Recommended target:

- single VPS or private host
- Docker running
- reverse proxy with HTTPS
- access restricted to you or a small trusted team

## Use case

Choose this mode when:

- you want to access Praetor away from your laptop
- you want browser access over HTTPS
- you do **not** want to expose a broad public SaaS surface

## Current deploy shape

The current implementation is a monolithic app container that serves:

- UI
- API

Use:

- [compose.app.yaml](<repo-root>/compose.app.yaml)

## Recommended setup

1. Put the app behind a reverse proxy such as Caddy, Nginx, or Traefik.
2. Terminate TLS at the proxy.
3. Do not bind the app directly on a public wildcard interface unless the proxy is in front.
4. Use strong secrets for:
   - `PRAETOR_SESSION_SECRET`
   - `PRAETOR_SETUP_TOKEN`
   - `PRAETOR_BRIDGE_TOKEN`
5. Prefer Docker secrets or mounted secret files for production-style deployment.
5. Prefer `API mode` for the simplest remote deployment story.

## Subscription executor warning

`subscription_executor` mode is still best for:

- local-only deployments
- remote hosts you directly control and can log into

If you use `Codex` or `Claude Code` remotely, those tools must exist and be authenticated on that remote host or be reachable through a secure host-side bridge.

## Example

```bash
export OPENAI_API_KEY=...
export PRAETOR_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export PRAETOR_SETUP_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose -f compose.app.yaml up --build -d
```

Then publish only through a private HTTPS reverse proxy.

If you want to avoid raw env vars, use:

```bash
docker compose -f compose.app.yaml -f compose.app.production.yaml up --build -d
```

with secret files placed under `${PRAETOR_SECRETS_DIR:-./secrets}`.

## What is still not done

- the multi-service `web / api / worker` production stack is still roadmap work
- backup automation is still roadmap work

This document is the practical private-deploy path for the current repo state, not the final production architecture.
