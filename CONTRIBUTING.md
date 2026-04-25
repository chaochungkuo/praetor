# Contributing

Praetor is built around a repo-local Pixi environment.

## Development

```bash
pixi install
pixi run check
```

Run targeted smoke tests when changing runtime, auth, deployment, or UI behavior:

```bash
pixi run app-security-smoke
pixi run app-auth-smoke
pixi run app-api-smoke
pixi run app-fallback-smoke
pixi run stack-smoke
pixi run bridge-smoke
```

Do not commit local runtime state, workspaces, backups, secrets, API keys, model logs, or generated caches.

## Pull Requests

Pull requests should include:

- a concise summary of user-visible behavior
- verification commands run locally
- any security, privacy, or deployment risk

Changes touching executor behavior, file permissions, authentication, CSRF, deployment secrets, or model-provider data flow should be treated as security-sensitive.
