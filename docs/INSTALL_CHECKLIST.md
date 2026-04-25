# Praetor Install Checklist

Status: beta readiness checklist.

Use this checklist before publishing a release candidate or asking users to install Praetor.

## Local Docker smoke path

```bash
cp .env.example .env
mkdir -p workspace data config secrets
python -c 'import secrets; print(secrets.token_urlsafe(32))' > secrets/praetor_session_secret.txt
python -c 'import secrets; print(secrets.token_urlsafe(32))' > secrets/praetor_setup_token.txt
python -c 'import secrets; print(secrets.token_urlsafe(32))' > secrets/praetor_bridge_token.txt
touch secrets/openai_api_key.txt secrets/anthropic_api_key.txt
docker compose -f compose.app.yaml -f compose.app.production.yaml up --build
```

Then open:

- `http://127.0.0.1:9741/app/praetor`

Expected result:

- healthcheck passes
- onboarding requires setup token
- owner login is created
- logout/login works
- mission creation works
- generated workspace files are owned by the local user or container user and are not world-readable

## Pixi smoke path

```bash
pixi install
pixi run check
pixi run app-auth-smoke
pixi run app-security-smoke
pixi run app-api-smoke
pixi run app-fallback-smoke
pixi run stack-smoke
pixi run docs-site
```

Expected result:

- all tasks exit successfully
- `public/index.html` is generated
- local state is not committed

## Release candidate checks

- `README.md` quickstart is accurate.
- `SECURITY.md` contact path is accurate.
- [Praetor public security review](PRAETOR_PUBLIC_SECURITY_REVIEW.zh-TW.md) has no unresolved blocker for the intended release mode.
- [Praetor privacy boundaries](PRAETOR_PRIVACY_BOUNDARIES.zh-TW.md) matches current behavior.
- GitHub Actions are green on `main`.
- OpenSSF Scorecard completes successfully.
- GitHub Pages deploys successfully.
- Branch protection required checks match the current workflow names.

## Release command

```bash
git tag v0.1.0-rc.1
git push origin v0.1.0-rc.1
```

The release workflow creates the GitHub release and source archive.

