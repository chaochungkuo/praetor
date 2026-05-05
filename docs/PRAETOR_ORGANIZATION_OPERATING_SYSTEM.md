# Praetor Organization Operating System

Praetor treats an AI-run company as a governed organization, not a loose group of chat agents. The core objects below define how work moves from chairman intent to staffed execution, visible trace, review, durable memory, and closeout.

## Mission lifecycle

Every mission has a `current_stage` and append-only `MissionStageTransition` records.

Stages:

- `intake`: chairman request is captured.
- `staffing`: Praetor creates the workspace and chooses the team.
- `planning`: agents and delegations are ready to plan execution.
- `execution`: executor work is running or resumed.
- `review`: outputs need PM or reviewer validation.
- `owner_decision`: the chairman needs to approve, decide, or review a briefing.
- `memory_promotion`: raw work is being converted into durable knowledge.
- `closeout`: the mission is completed, stopped, or archived.

The mission status still records operational state such as `active`, `paused`, `ready_for_ceo`, or `archived`. Stage records explain the business lifecycle.

## Agent employment contracts

When Praetor creates an agent, it also creates an `AgentEmploymentContract`. The contract records:

- mission and role
- charter
- approved skills
- tools
- permission profile
- decision authority
- escalation triggers
- completion criteria

This gives the CEO and PM a stable way to tell an executor what it may do, when it must stop, and what "done" means.

## Permission profiles

`AgentPermissionProfile` is the reusable safety envelope for agents. Defaults are:

- `restricted_planner`: planning and drafts only.
- `standard_operator`: normal mission work inside approved folders.
- `execution_worker`: scoped implementation and tests inside the workspace.
- `risk_review`: privacy, security, legal, and quality review.

Profiles intentionally separate agent role from permissions. A future LLM planner can recommend a role, while governance decides the permission profile.

## Skill review

Imported skills enter the registry as `imported_requires_review`. They are not assigned to new agents until approved. The UI and API can set a skill to:

- `approved`
- `rejected`
- `deprecated`
- `imported_requires_review`

This keeps open-source skill libraries useful without silently trusting external prompts or tool definitions.

## Work trace

`WorkTraceEvent` is the chairman-readable event stream for AI-to-AI coordination. It records staffing, stage transitions, executor control requests, skill reviews, and other operational events.

Raw agent messages and work-session turns remain available for audit. Work trace is the concise operating log that belongs in the main mission view.

## Executive cadence

Praetor defaults to quiet formal cadence:

- notify on approvals, blocked work, security, privacy, legal, or finance risk
- produce digest-style briefings on demand
- avoid personal-assistant-style notification noise

This matches Praetor's purpose: running serious company work through a CEO interface.
