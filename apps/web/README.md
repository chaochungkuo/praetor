# Praetor Web

This service is the browser-facing entrypoint for the multi-service stack.

Current role:

- health endpoint
- serves the React/TypeScript Praetor Office app at `/office`
- reverse proxy to the Praetor API app
- browser-facing shell for the split `web / api / worker` stack

It does not run mission logic itself.

## Frontend

The v2 Office frontend lives in `frontend/` and is built with Vite, React, and TypeScript.

```bash
npm --prefix apps/web install
npm --prefix apps/web run dev
npm --prefix apps/web run build
```

The production Docker image builds `frontend/` into `dist/` and serves it from the FastAPI web entrypoint.

Current Office capabilities:

- CEO chat backed by `/api/office/conversation`
- chairman instructions run through a replaceable CEO planner interface
- planner actions support mission drafts, approval requests, memory updates, and briefings
- organization actions support staffing proposals, agent creation, delegations, decision escalations, mission closeout, and standing orders
- deterministic planner mode by default; LLM planner mode via `PRAETOR_CEO_PLANNER_MODE=llm`
- mission room with timeline and AI internal conversation
- AI organization panel with mission team, delegation, escalation, and standing order telemetry
- browser speech recognition as the first voice input path

The LLM planner uses `PRAETOR_CEO_PLANNER_PROVIDER` and `PRAETOR_CEO_PLANNER_MODEL` on the API service. Invalid or unavailable LLM output falls back to the deterministic planner and records a briefing action.
