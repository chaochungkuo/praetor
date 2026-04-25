# Praetor API

This package contains the first Praetor app backend skeleton.

Current scope:

- app-level settings and runtime schemas
- onboarding preview / complete endpoints
- filesystem-backed workspace bootstrap
- mission folder persistence as canonical state
- SQLite mission index/cache
- basic Praetor briefing and mission APIs
- first browser UI pages:
  `Praetor`, `Overview`, `Tasks`, `Memory`, `Decisions`, `Models`, `Settings`, mission detail
- mission runtime through `praetor-execd`
- API mode through OpenAI-compatible and Anthropic-compatible providers
- fallback from API mode to subscription executor when configured
- audit event persistence
- usage and retrieval preview surfaces
- meetings page with structured review persistence

Run locally from the repo root:

```bash
pixi install
pixi run app-serve
```

Open:

- [http://127.0.0.1:9741/app/praetor](http://127.0.0.1:9741/app/praetor)

Smoke test:

```bash
pixi run app-smoke
pixi run app-ui-smoke
pixi run app-api-smoke
pixi run app-fallback-smoke
```
