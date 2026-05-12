# Praetor Roadmap

Status: 2026-05-12 refreshed after foundation cleanup.

This file is the current execution roadmap. It is the single working checklist
for getting Praetor to a real v1 release. Anything that changes scope or order
should be reflected here, not in scattered specs.

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
- Protect trust: auditability, writable scope boundaries, pause/resume,
  and approvals are core product features.
- Do not expand agent customization before the CEO / role / governance
  model feels solid.
- **Refactor before features.** When a layer is being used by tests but
  not by users, demote it before adding the next thing on top.
- Use this roadmap as the source of truth for execution order.

---

## MVP Definition

Praetor MVP ships when a chairman can:

- install it with a documented local deployment path
- open a browser UI
- onboard through Praetor
- define company DNA and approval boundaries
- create and run at least one mission inside a controlled workspace
- review mission progress, pauses, and outputs through a real-time
  background worker (not blocked by the API request thread)
- use company memory and task logging
- run with API mode or at least one subscription executor mode
- recover gracefully from API restart (in-flight missions get marked
  `interrupted` rather than silently disappearing)

---

## Current Track Summary (2026-05-12)

Three independent tracks are in flight:

| Track | Owner | Status |
|---|---|---|
| **Foundation cleanup** | landed in `claude/crazy-taussig-d75255` (6 commits) | Done. See "Foundation cleanup" section. |
| **UI rebuild** | Codex, following [UI_REBUILD_PLAYBOOK](docs/UI_REBUILD_PLAYBOOK.zh-TW.md) | Not started. 9 commits planned. |
| **Docker app stack** | unassigned | Open. compose.yaml exists; production hardening + install script are partial. |

Phase 1–10 historical milestones are preserved at the bottom for context, but
they no longer drive day-to-day execution.

---

## Foundation cleanup (DONE, May 2026)

Six commits on `claude/crazy-taussig-d75255` that cleared the path for the UI
rebuild:

- [x] **Cut workspace-steward layer** — removed `file_assets`, `file_moves`,
      `workspace_reconciliation_reports`, `workspace_restructure_plans` tables
      and ~1,600 LoC of code that was wired into every mission create but never
      read from a user-facing flow. Design preserved as
      [Phase-2 deferred](docs/PRAETOR_WORKSPACE_STEWARD.md).
- [x] **Mission worker queue + crash recovery** — added a `mission_jobs`
      SQLite table and a `MissionWorker` daemon thread. Mission execution moved
      off the API request thread. Jobs left in `running` after an API restart
      get marked `interrupted` instead of silently disappearing.
      New endpoints: `POST /api/missions/{id}/enqueue`,
      `GET /api/missions/{id}/jobs`, `GET /api/mission-jobs/{id}`.
- [x] **Retrieval-windowed CEO planner context** — CEO chat no longer dumps
      every mission / wiki page / standing order into every prompt. Keyword
      overlap ranks candidates, pinned `related_mission_id` always included,
      fixed budget (3 missions, 3 wiki pages, 5 orders, 6 conversation turns).
      Token cost stops scaling with workspace size.
- [x] **Extract FilesystemStore** — `storage.py` went from 2,796 → 2,069
      lines. The workspace-Markdown / legacy JSON migration shim is in
      `_filesystem_store.py`. Domain seam between SQL index and filesystem
      writes is now visible.
- [x] **Extract Jinja translations** — `ui.py` went from 3,030 → 1,552 lines.
      `_translations.py` is now a single source the React rebuild can consume
      via build-time export.
- [x] **UI rebuild playbook written** — [docs/UI_REBUILD_PLAYBOOK.zh-TW.md](docs/UI_REBUILD_PLAYBOOK.zh-TW.md)
      is the self-contained brief for Codex to execute the React SPA rebuild.

Total: −1,197 net lines, 4 SQLite tables removed, 1 background worker added.

---

## UI rebuild (NEXT)

Driven by [docs/UI_REBUILD_PLAYBOOK.zh-TW.md](docs/UI_REBUILD_PLAYBOOK.zh-TW.md).
Codex should execute commits in the order listed there. Acceptance checklist
must pass before each next commit.

- [ ] **Commit 1** — Wipe legacy SPA + install foundation (Tailwind, tokens,
      Inter + Noto Sans TC fonts)
- [ ] **Commit 2** — App shell + routing + theme (5 empty pages, ⌘K shell,
      dark mode toggle)
- [ ] **Commit 3** — `/office` lands (Good morning header, CEO chat, mission
      portfolio, Needs Decision rail)
- [ ] **Commit 4** — `/missions` and `/missions/:id` land; delete the matching
      Jinja routes and templates
- [ ] **Commit 5** — `/memory` lands (wiki + decisions + open questions merged);
      delete Jinja `/app/memory`, `/app/decisions`, `/app/meetings`,
      `/app/inbox`
- [ ] **Commit 6** — `/runtime` lands (health hero + tabs); delete Jinja
      `/app/models`; add the one new backend endpoint `POST /api/settings/runtime`
- [ ] **Commit 7** — `/settings` lands; delete Jinja `/app/agents`
- [ ] **Commit 8** — Onboarding and login pages get the sky-gradient visual
      refresh (these stay as Jinja, but updated to match brand v0.2)
- [ ] **Commit 9** — i18n unified via build-time extract from
      `_translations.py`

Definition of done:
- `apps/web/frontend/src/main.tsx` < 100 lines
- `apps/api/praetor_api/ui.py` < 600 lines (only onboarding + login + mobile briefing left)
- backend routes total < 90 (was 102)
- bundle size < 700 KB gzipped
- all pixi smokes pass

---

## Docker app stack (OPEN)

- [x] `compose.yaml` for web / api / worker exists
- [x] Production compose variant exists
- [x] Healthchecks defined
- [x] Local + remote private deploy docs written
- [x] Backup / restore documented
- [ ] One-line install script tested against fresh macOS / Linux / WSL2
- [ ] Production secrets rotation documented
- [ ] Subscription-executor bridge install path documented end-to-end

---

## Phase 8 leftovers (Telegram)

- [x] Mobile executive dashboard
- [x] Mobile approvals flow
- [x] Mobile briefing flow
- [x] Telegram notification channel (webhook receiver, pairing code,
      approve / reject buttons)
- [ ] Telegram quick status commands (`/status`, `/missions`)
- [ ] Telegram approval deep-link flow back to web

Telegram notifications and pairing have shipped; the remaining items are
power-user commands. Not blocking MVP.

---

## Post-MVP (deferred)

- [ ] Skill tuning (replaces the deleted `agent_skills` workflow with a
      simpler in-app editor)
- [ ] GitHub skill import (Phase-3 idea from the product brief)
- [ ] Richer executor ecosystem (beyond codex / claude_code)
- [ ] Advanced role tuning (per-role permission profiles editable in UI)
- [ ] **Workspace steward layer (Phase-2)** — see
      [PRAETOR_WORKSPACE_STEWARD.md](docs/PRAETOR_WORKSPACE_STEWARD.md)
      for the deferred design. Only resume when a real user pain motivates it.

---

## Done means

An item is only checked when:

- code exists in the repo
- the path is wired into the actual runtime or workflow
- the behavior is verified locally (smoke or manual)
- the user-facing docs are updated if needed

Items that are checked but later become wrong should be unchecked, not deleted —
the history matters for "we tried this and learned".

---

## Reference Specs

Active source of truth:

- [docs/UI_REBUILD_PLAYBOOK.zh-TW.md](docs/UI_REBUILD_PLAYBOOK.zh-TW.md) ← UI work track
- [docs/PRAETOR_UI_SPEC.zh-TW.md](docs/PRAETOR_UI_SPEC.zh-TW.md) ← durable UI principles
- [docs/PRAETOR_BRAND_SPEC.zh-TW.md](docs/PRAETOR_BRAND_SPEC.zh-TW.md) ← visual baseline
- [docs/PRAETOR_SURFACES_SPEC.zh-TW.md](docs/PRAETOR_SURFACES_SPEC.zh-TW.md) ← Web / Mobile / Telegram boundaries
- [docs/PRAETOR_SYSTEM_SPEC.zh-TW.md](docs/PRAETOR_SYSTEM_SPEC.zh-TW.md) ← backend architecture
- [docs/PRAETOR_REPO_ARCHITECTURE.zh-TW.md](docs/PRAETOR_REPO_ARCHITECTURE.zh-TW.md) ← repo layout
- [docs/PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md](docs/PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md) ← bridge contract
- [docs/DEPLOYMENT_SECURITY_SPEC.zh-TW.md](docs/DEPLOYMENT_SECURITY_SPEC.zh-TW.md) ← deployment / security
- [PRAETOR_PRODUCT_BRIEF.zh-TW.md](PRAETOR_PRODUCT_BRIEF.zh-TW.md) ← product north star

Historical / deferred:

- [docs/PRAETOR_WORKSPACE_STEWARD.md](docs/PRAETOR_WORKSPACE_STEWARD.md) ← Phase-2 design
- [PRODUCT_INTAKE.md](PRODUCT_INTAKE.md) ← raw discussion material, not curated

---

## Historical Phase 1–10 (preserved for context, no longer drives execution)

The original 10-phase plan is preserved below because some Phase items are
still useful as reference (e.g. "what was the original scope of meeting mode")
but the actual current execution is tracked in the three tracks above.

### Phase 1: Contracts And Core Models — done
### Phase 2: Workspace And Runtime Core — done
### Phase 3: Onboarding And Founder Control — done
### Phase 4: Web MVP — done in v0; **being rebuilt as React SPA**
### Phase 5: Execution Layers — done
### Phase 6: Memory, Auditability, And Trust — done
### Phase 7: Management Layer — done
### Phase 8: Mobile And Telegram — mobile done, Telegram partial (see active section above)
### Phase 9: Deployment And Operations — mostly done (see Docker app stack section)
### Phase 10: Post-MVP — partial; remaining items moved to Post-MVP section above
