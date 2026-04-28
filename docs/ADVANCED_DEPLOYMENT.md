# Advanced Deployment

Use the one-line installer in the README for normal local use. This page is for manual Docker, production-style, and multi-service deployments.

## Manual Local Docker

```bash
export PRAETOR_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export PRAETOR_SETUP_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose -f compose.app.yaml up --build
```

Open:

- `http://127.0.0.1:9741/app/praetor?setup_token=$PRAETOR_SETUP_TOKEN`
- `http://127.0.0.1:9741/m/briefing`

Reference:

- [PRAETOR_LOCAL_DEPLOY.md](PRAETOR_LOCAL_DEPLOY.md)
- [PRAETOR_REMOTE_PRIVATE_DEPLOY.md](PRAETOR_REMOTE_PRIVATE_DEPLOY.md)
- [PRAETOR_BACKUP_RESTORE.md](PRAETOR_BACKUP_RESTORE.md)

## Production-Style Monolithic Docker

Use Docker secrets or `_FILE` environment variables for real secrets.

```bash
docker compose -f compose.app.yaml -f compose.app.production.yaml up --build -d
```

## Multi-Service Stack

```bash
docker compose -f compose.yaml up --build
```

Open:

- http://127.0.0.1:3000/app/praetor
- http://127.0.0.1:3000/office

Production overlay:

```bash
docker compose -f compose.yaml -f compose.production.yaml up --build -d
```

## Host Executor Bridge

Praetor can call host-side tools such as Codex or Claude Code through `praetor-execd`. Keep the bridge outside Docker so the container does not need direct access to host credentials or the Docker socket.

See:

- [PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md](PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md)
- [DEPLOYMENT_SECURITY_SPEC.zh-TW.md](DEPLOYMENT_SECURITY_SPEC.zh-TW.md)
