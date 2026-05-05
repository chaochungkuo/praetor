# Developer Setup

This page is for contributors and technical users. If you only want to run Praetor locally, use the one-line installer in the main README.

## Baseline

Praetor uses a repo-local Pixi environment as the official development baseline.

- Do not rely on system Python.
- Do not treat ad-hoc virtual environments as the default workflow.
- Use the repo root `pixi.toml`.
- Python 3.12 is the development baseline.

## Install the Development Environment

```bash
pixi install
```

## Run the App from Source

```bash
pixi run app-serve
```

Open:

- http://127.0.0.1:9741/app/praetor
- http://127.0.0.1:9741/m/briefing

On first launch, Praetor guides you through owner account creation, model/API connection, workspace selection, and approval rules.

For a fresh local reinstall, stop Praetor and remove the state directory you started it with. If you did not set `PRAETOR_STATE_DIR`, the default local state is `/tmp/praetor-app-state`.

## Key Commands

```bash
pixi run py
pixi run check
pixi run py-compile
pixi run app-import-check
pixi run web-import-check
pixi run worker-import-check
pixi run bridge-import-check
pixi run runtime-import-check
```

## Smoke Tests

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
pixi run planner-smoke
pixi run organization-smoke
pixi run safety-policy-smoke
```

What they cover:

- `app-smoke`: backend vertical slice, onboarding, mission creation, runtime, schema export.
- `app-ui-smoke`: first browser pages including Praetor, Overview, Tasks, Memory, Decisions, Models, Settings.
- `app-auth-smoke`: owner account protection, login, logout.
- `app-security-smoke`: setup-token onboarding and CSRF checks.
- `app-api-smoke`: fake OpenAI-compatible API mode with file output and usage recording.
- `app-fallback-smoke`: API failure fallback to subscription executor.
- `stack-smoke`: split web/API/worker shape.
- `office-smoke`: v2 Office APIs and React entrypoint.
- `planner-smoke`: deterministic and LLM planner contract.
- `organization-smoke`: AI team, delegation, escalation, standing orders, completion contract.
- `safety-policy-smoke`: prompt safety policy injection and sensitive memory blocking.

## CEO Planner Modes

The app install default is automatic: an API runtime with a real provider key uses the LLM planner, while missing or unavailable AI falls back to the deterministic planner. For local development or CI, force deterministic mode when you do not want paid API access.

```bash
PRAETOR_CEO_PLANNER_MODE=deterministic
```

To try an LLM-backed planner:

```bash
PRAETOR_CEO_PLANNER_MODE=llm
PRAETOR_CEO_PLANNER_PROVIDER=openai
PRAETOR_CEO_PLANNER_MODEL=gpt-4.1-mini
OPENAI_API_KEY=...
```

The planner emits explicit action types for mission creation, approvals, memory, briefings, staffing, agent creation, delegation, escalation, closeout, and standing orders. LLM output is parsed as JSON, validated, sanitized before side effects, and falls back to the deterministic planner if the provider is unavailable or returns invalid output.

## AI Organization Lifecycle

Praetor models AI-to-AI work as a company operating system:

- `AgentRoleSpec`: reusable job descriptions such as CEO, Project Manager, Developer, Reviewer, Security Officer, and Legal Counsel.
- `AgentInstance`: mission-scoped AI workers with charter, skills, tools, memory access, decision authority, and escalation triggers.
- `MissionTeam`: temporary team assigned to one mission.
- `DelegationRecord`: formal work order from one AI role to another.
- `EscalationRecord`: upward decision request to PM, CEO, or chairman.
- `StandingOrder`: durable chairman policy for autonomous action and approval boundaries.
- `CompletionContract`: closeout checks for outputs, delegation status, review, escalations, final report, and memory update.

## Run `praetor-execd`

Start the bridge with the repo environment:

```bash
export PRAETOR_EXECD_CONFIG=/absolute/path/to/config.yaml
export PRAETOR_EXECUTOR_BRIDGE_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
pixi run bridge-serve
```

Bridge checks:

```bash
pixi run bridge-smoke
pixi run bridge-e2e
pixi run claude-e2e
```

## Important Directories

- [apps/api/](../apps/api)
- [apps/web/](../apps/web)
- [bridges/praetor-execd/](../bridges/praetor-execd)
- [workers/runtime/](../workers/runtime)
- [tools/](../tools)
- [pixi.toml](../pixi.toml)
