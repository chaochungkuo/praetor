# Praetor Roadmap

This file is the current execution roadmap for finishing Praetor.

It is the single working checklist we should follow from now on.

## Product Goal

Praetor should become a deployable, founder-facing AI company command center:

- local-first by default
- browser-first for primary use
- governed by roles, approvals, and company memory
- able to use API models and user-owned subscription executors
- simple to install, understandable to trust, and useful immediately

## Working Principles

- Prefer a usable vertical slice over broad unfinished surface area.
- Keep the MVP opinionated.
- Protect trust: auditability, writable scope boundaries, pause/resume, and approvals are core product features.
- Do not expand agent customization before the CEO / role / governance model feels solid.
- Use this roadmap as the source of truth for execution order.

## Current Status

### Foundation

- [x] Product brief written
- [x] System spec written
- [x] UI spec written
- [x] Web / Mobile / Telegram surfaces spec written
- [x] Deployment and security spec written
- [x] Executor bridge spec written
- [x] Brand spec written
- [x] Repo-local Pixi environment established as the official dev baseline

### Runtime / Bridge

- [x] `praetor-execd` OpenAPI and JSON schemas created
- [x] `praetor-execd` FastAPI bridge skeleton implemented
- [x] Worker-side `bridge_client` implemented
- [x] Mock executor end-to-end flow working
- [x] Native `codex` executor path working
- [x] Native `claude_code` executor path working
- [x] Host-side executor model confirmed without reinstalling tools inside Docker

### Product Architecture

- [x] Company memory direction fixed: company memory yes, agent personal memory no for MVP
- [x] Role-first architecture fixed
- [x] Hidden PM architecture fixed
- [x] Web as canonical control plane fixed
- [x] `subscription_executor` deployment boundary fixed

### Still Missing

- [x] Praetor app backend
- [x] Onboarding backend and persistence
- [x] Browser UI implementation
- [x] Mission runtime above the bridge layer
- [x] API mode implementation
- [x] Workspace management implementation
- [x] Audit log UI
- [ ] Docker app stack implementation

## MVP Definition

Praetor MVP is complete when a user can:

- install it with a documented local deployment path
- open a browser UI
- onboard through Praetor
- define company DNA and approval boundaries
- create and run at least one mission inside a controlled workspace
- review mission progress, pauses, and outputs
- use company memory and task logging
- run with API mode or at least one subscription executor mode

## Phase 1: Contracts And Core Models

- [x] Finalize product positioning
- [x] Finalize deployment model split:
  `Quick Start` vs `Bring Your Own Subscription`
- [x] Finalize company memory model
- [x] Finalize role / governance / mission concepts
- [x] Write product, system, UI, surfaces, deployment, and bridge specs
- [x] Create real config schema files for app-level Praetor runtime
- [x] Create app-level company DNA schema
- [x] Create app-level role schema
- [x] Create app-level mission schema
- [x] Create app-level approval schema
- [x] Create app-level meeting schema

## Phase 2: Workspace And Runtime Core

- [x] Implement workspace bootstrap logic
- [x] Implement filesystem-backed company memory structure
- [x] Implement mission folder model as canonical source of truth
- [x] Implement SQLite index/cache layer around missions
- [x] Implement runtime mode config:
  API / local / subscription executor
- [x] Implement writable scope enforcement in app runtime
- [x] Implement mission pause / resume contract in app runtime
- [x] Implement audit log persistence in app runtime

## Phase 3: Onboarding And Founder Control

- [x] Implement owner account bootstrap
- [x] Implement conversational onboarding flow
- [x] Implement company language selection
- [x] Implement company DNA generation
- [x] Implement governance and approval policy setup
- [x] Implement workspace selection / initialization
- [x] Implement runtime selection during onboarding
- [x] Implement first-task handoff at the end of onboarding

## Phase 4: Web MVP

- [x] Implement `Praetor` page
- [x] Implement `Overview` page
- [x] Implement `Tasks` page
- [x] Implement `Settings` page
- [x] Implement right-side approval / checkpoint rail
- [x] Implement mission detail view
- [x] Implement pause / continue / stop controls
- [x] Implement degraded / empty / loading / error states

## Phase 5: Execution Layers

- [x] Implement app-level executor abstraction
- [x] Integrate `praetor-execd` into Praetor worker runtime
- [x] Implement API mode
- [x] Implement model selection / runtime selection logic
- [x] Implement executor health UI
- [x] Implement fallback / retry policy between runtime modes
- [x] Implement usage capture pipeline for models and executors

## Phase 6: Memory, Auditability, And Trust

- [x] Implement Wiki memory UI
- [x] Implement Decisions view
- [x] Implement retrieval preview
- [x] Implement audit log UI
- [x] Implement changed-files / mission-output inspection
- [x] Implement checkpoint approval UX
- [x] Implement run budget and stop-reason UX

## Phase 7: Management Layer

- [x] Implement hidden PM creation rules
- [x] Implement mission complexity / context load scoring
- [x] Implement PM-scoped mission context
- [x] Implement escalation flow from PM to Praetor
- [x] Implement structured meeting mode
- [x] Implement meeting summary persistence

## Phase 8: Mobile And Telegram

- [x] Implement mobile executive dashboard
- [x] Implement mobile approvals flow
- [x] Implement mobile briefing flow
- [ ] Implement Telegram notification channel
- [ ] Implement Telegram quick status commands
- [ ] Implement Telegram approval deep-link flow back to web

## Phase 9: Deployment And Operations

- [x] Implement app `compose.yaml` services for web / api / worker
- [x] Implement production compose variant
- [x] Implement secrets handling for production deployment
- [x] Implement health checks for app services
- [x] Implement backup / restore scripts or documented procedures
- [x] Implement deployment docs for local-only mode
- [x] Implement deployment docs for remote private mode

## Phase 10: Post-MVP

- [x] Implement `Memory` page
- [x] Implement `Models` page
- [x] Implement `Meetings` page
- [x] Implement richer activity / expert mode
- [ ] Implement skill tuning
- [ ] Implement GitHub skill import
- [ ] Implement richer executor ecosystem
- [ ] Implement advanced role tuning

## Immediate Next Milestones

These are the next practical build targets.

- [x] Create app-level config / schema package
- [x] Implement workspace + mission persistence layer
- [x] Build onboarding backend
- [x] Build the first web page set:
  `Praetor`, `Overview`, `Tasks`, `Settings`
- [x] Connect the app worker runtime to `praetor-execd`
- [x] Ship the first vertical slice:
  onboard -> create mission -> run mission -> inspect result

## Done Means

An item should only be checked when:

- code exists in the repo
- the path is wired into the actual runtime or workflow
- the behavior is verified locally
- the user-facing docs are updated if needed

## Reference Specs

- [README.md](/Users/jovesus/glasrocks/praetor/README.md)
- [PRAETOR_PRODUCT_BRIEF.zh-TW.md](/Users/jovesus/glasrocks/praetor/PRAETOR_PRODUCT_BRIEF.zh-TW.md)
- [PRAETOR_SYSTEM_SPEC.zh-TW.md](/Users/jovesus/glasrocks/praetor/docs/PRAETOR_SYSTEM_SPEC.zh-TW.md)
- [PRAETOR_UI_SPEC.zh-TW.md](/Users/jovesus/glasrocks/praetor/docs/PRAETOR_UI_SPEC.zh-TW.md)
- [PRAETOR_SURFACES_SPEC.zh-TW.md](/Users/jovesus/glasrocks/praetor/docs/PRAETOR_SURFACES_SPEC.zh-TW.md)
- [PRAETOR_REPO_ARCHITECTURE.zh-TW.md](/Users/jovesus/glasrocks/praetor/docs/PRAETOR_REPO_ARCHITECTURE.zh-TW.md)
- [DEPLOYMENT_SECURITY_SPEC.zh-TW.md](/Users/jovesus/glasrocks/praetor/docs/DEPLOYMENT_SECURITY_SPEC.zh-TW.md)
- [PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md](/Users/jovesus/glasrocks/praetor/docs/PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md)
