# Praetor Local Deploy

This is the fastest way to run the current Praetor app with Docker.

It uses the current monolithic FastAPI app that serves both:

- browser UI
- JSON API

## Prerequisites

- Docker Engine or Docker Desktop running
- a local `workspace/` directory
- optional:
  - `OPENAI_API_KEY` for API mode
  - host `praetor-execd` for subscription executor mode

## Start

```bash
docker compose -f compose.app.yaml up --build
```

Then open:

- `http://127.0.0.1:9741/app/praetor`

## Environment

Common environment variables:

- `PRAETOR_APP_BIND_HOST`
- `PRAETOR_APP_PORT`
- `PRAETOR_WORKSPACE_DIR`
- `PRAETOR_DATA_DIR`
- `PRAETOR_SESSION_SECRET`
- `PRAETOR_SETUP_TOKEN`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `PRAETOR_BRIDGE_BASE_URL`
- `PRAETOR_BRIDGE_TOKEN`

Example:

```bash
export OPENAI_API_KEY=...
export PRAETOR_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export PRAETOR_SETUP_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose -f compose.app.yaml up --build
```

## Production-style overlay

If you want Docker secrets instead of plain environment variables:

```bash
mkdir -p secrets
python -c 'import secrets; print(secrets.token_urlsafe(32))' > secrets/praetor_session_secret.txt
python -c 'import secrets; print(secrets.token_urlsafe(32))' > secrets/praetor_setup_token.txt
python -c 'import secrets; print(secrets.token_urlsafe(32))' > secrets/praetor_bridge_token.txt
printf 'sk-...' > secrets/openai_api_key.txt

docker compose -f compose.app.yaml -f compose.app.production.yaml up --build -d
```

The current app supports `*_FILE` environment variables for:

- `PRAETOR_SESSION_SECRET_FILE`
- `PRAETOR_SETUP_TOKEN_FILE`
- `PRAETOR_BRIDGE_TOKEN_FILE`
- `OPENAI_API_KEY_FILE`
- `ANTHROPIC_API_KEY_FILE`

## Subscription executor mode

If you want to use existing host-side tools such as Codex or Claude Code:

1. run `praetor-execd` on the host
2. point the container at it:

```bash
export PRAETOR_BRIDGE_BASE_URL=http://host.docker.internal:9417
export PRAETOR_BRIDGE_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose -f compose.app.yaml up --build
```

## Notes

- This is the practical local deployment path for the current implementation.
- The split `web / api / worker` stack is now available in `compose.yaml`.
- The monolithic app stack remains the simplest path for first local use.
