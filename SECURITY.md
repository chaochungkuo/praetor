# Security Policy

## Supported Status

Praetor is an active build-stage project. Treat public deployments as experimental until a stable release is tagged.

## Reporting a Vulnerability

Please report security issues privately through GitHub Security Advisories for this repository when available. Do not open public issues containing exploit details, private tokens, user data, workspace contents, or logs with secrets.

## Security Boundaries

Praetor is local-first. The safest default deployment binds services to `127.0.0.1`.

Important boundaries:

- `PRAETOR_SETUP_TOKEN` protects first-time initialization.
- `PRAETOR_SESSION_SECRET` signs owner sessions.
- `PRAETOR_BRIDGE_TOKEN` protects the host executor bridge.
- API mode can send selected workspace memory to external model providers.
- `subscription_executor` runs host-side tools and should be used only on machines or runners the operator controls.

Never commit `workspace/`, `data/`, `config/`, `secrets/`, `backups/`, `.env`, model logs, or API keys.
