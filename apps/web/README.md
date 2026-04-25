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
- planner actions currently support mission drafts, approval requests, and memory updates
- mission room with timeline and AI internal conversation
- browser speech recognition as the first voice input path
