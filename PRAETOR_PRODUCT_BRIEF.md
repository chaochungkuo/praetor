# Praetor Product Brief v0.1

Status: synthesis draft

This document consolidates the current product direction, constraints, and recommended implementation path for `Praetor`.

Important note:
- The direction is stable.
- Many implementation details are still flexible.
- This document is intended to create alignment, not lock every choice permanently.

## 1. Executive Summary

`Praetor` is a local-first, self-hostable AI company operating system for solo founders.

It is not a general AI platform, not a visual workflow builder, and not just a chatbot with tools.

Its core promise is:

**You manage the company through one AI executive. The system organizes roles, assigns work, uses your files as memory, and stops at the right time for your decisions.**

The defining user experience is:
- The user thinks like a founder or chairman.
- `Praetor` acts like an AI CEO.
- Internal agents exist, but are mostly hidden.
- The company works inside a controlled workspace.
- Memory belongs to the company, not to individual agents.
- Work advances proactively until a real checkpoint, risk boundary, or budget limit is reached.

If this product works, the user should feel:
- "My AI company is working even when I am not micromanaging it."
- "I can see what is happening without drowning in operational noise."
- "I only need to step in for the decisions that actually matter."

## 2. The Problem

The target user is not an enterprise operations team. The target user is a solo founder, indie hacker, freelancer, researcher, or early-stage builder who is forced to constantly switch roles.

Today, one person often has to act as:
- CEO
- Project manager
- Operator
- Researcher
- Developer
- Finance owner
- Reviewer

The core pain is not only lack of automation. The deeper pain is:
- attention fragmentation
- constant context switching
- lack of structured delegation
- weak continuity between tasks
- too much low-level decision burden

Most current AI products help with isolated tasks. Very few help one person run a structured, ongoing "company" of AI workers with governance, memory, and bounded autonomy.

## 3. Product Definition

### 3.1 What Praetor Is

Praetor is:
- a founder-facing AI command center
- a role-based AI organization system
- a local-first workspace automation product
- a governance layer over AI execution
- a self-hostable web application with a controlled filesystem workspace

### 3.2 What Praetor Is Not

Praetor is not:
- a generic multi-agent playground
- a drag-and-drop workflow builder
- a pure developer orchestration framework
- a no-code chatbot builder
- an enterprise RPA suite

### 3.3 One-line Positioning

Recommended positioning:

**Praetor is a local-first AI company operating system for solo founders.**

Alternative external phrasing:

**Run your company through an AI CEO that works with files, roles, memory, and human checkpoints.**

## 4. Stable Direction vs Flexible Choices

### 4.1 Stable Direction

These ideas are now strong enough to treat as core product direction:

- The primary user interacts with one executive layer, not with many peer agents.
- The main abstraction for the user is `role`, not `agent`.
- The company has shared memory.
- Individual agent memory should not exist in MVP.
- Filesystem data is the source of truth for business memory.
- The system must be deployable and usable quickly through Docker and a browser UI.
- The system must support governance, approvals, and safe writable scope.
- The product must support multiple AI runtime modes, including user-owned executor tools.
- The system must remain useful on day one with a small set of built-in capabilities.

### 4.2 Flexible Choices

These are still open for refinement:

- exact visual design language
- exact repo layout
- exact frontend/backend split
- whether the first release exposes meetings as a separate page or a CEO mode
- how many templates ship in v1
- how many built-in skills ship in v1
- exact PM creation thresholds
- exact pricing and packaging

## 5. Market Context

As of April 24, 2026, the current landscape is crowded, but the categories are still distinct.

### 5.1 What Existing Tools Do Well

`ChatGPT` and `Codex`:
- excellent conversational assistance
- coding help
- delegated tasks
- strong reasoning and execution surfaces across app, CLI, IDE, and cloud

`Dify`:
- visual workflow and chatflow building
- app-oriented workflow composition
- strong node/canvas model

`Flowise`:
- visual builder for AI agents and LLM workflows
- beginner-friendly and flow-centric

`LangGraph`:
- low-level orchestration runtime for long-running, stateful agents
- good for developers building custom agent systems

`CrewAI`:
- multi-agent teams, workflows, and enterprise automation abstractions

### 5.2 Where the Market Gap Still Exists

Praetor does not need to beat those tools at their own categories.

The gap it should attack is:

**a founder-facing operating layer that turns AI into a governed company structure instead of a collection of equal agents, prompts, or flows**

What is still missing in the market:
- a product that feels like managing an AI company, not just triggering AI tasks
- a role-first system where the user defines responsibilities, not prompt internals
- a local-first command center with controlled filesystem boundaries
- company-level memory with explicit approvals and checkpoints
- a product that supports "bring your own AI subscription" as a first-class execution model

### 5.3 Differentiation in One Table

| Product category | Primary abstraction | User experience | Gap Praetor fills |
|---|---|---|---|
| ChatGPT / Codex | conversation or delegated task | assistant or coding partner | no persistent company operating model |
| Dify / Flowise | workflow / visual graph | builder canvas | not founder-centric organizational governance |
| LangGraph | orchestration runtime | developer framework | too low-level for direct founder use |
| CrewAI | agent teams and flows | multi-agent automation | still framework/platform oriented |
| Praetor | company roles + CEO governance | founder command center | organizational, governed, file-native AI company |

## 6. Why This Product Can Matter

Praetor is interesting because it does not compete mainly on raw model intelligence.

It competes on:
- structure
- delegation
- trust
- memory
- clarity of responsibility
- bounded autonomy

That is a stronger wedge than "we have agents too."

The product thesis is:

**AI is already good enough to do real work. The harder problem is how to organize, govern, and supervise that work so one person can actually use it continuously.**

## 7. Target User

Primary target user:
- solo founder
- indie hacker
- freelancer
- consultant
- researcher
- creator with operational complexity
- technical or semi-technical builder who wants leverage, not more tooling overhead

Not the primary target for v1:
- multi-user enterprise deployments
- heavily regulated teams
- large operations teams
- organizations requiring full RBAC, SSO, audit integrations, and advanced compliance on day one

## 8. Core Product Principles

### 8.1 Files Are the Source of Truth

The company remembers through files.

Persistent truth should live in:
- workspace folders
- markdown wiki
- decision logs
- mission files

Operational metadata may live in SQLite, but only as:
- index
- cache
- state tracking
- UI support

Business truth should not depend on a hidden database.

### 8.2 The User Manages Roles, Not Agents

The user should define:
- what kind of work is needed
- what the role is responsible for
- what outputs are expected
- what constraints apply

The system should decide:
- what agent is instantiated
- how it is styled
- which skills it uses
- whether a PM layer is needed

### 8.3 Governance Is the Product

Praetor is not just "AI with tools."

Its core value comes from:
- authority boundaries
- escalation rules
- approval policies
- checkpoint design
- termination conditions
- inspectable work history

### 8.4 Memory Belongs to the Company

Praetor should not build personality-driven agents with private memory in v1.

Instead:
- the company remembers
- the mission remembers
- the agent executes from current role + company context

This is more controllable, more reproducible, and easier to trust.

### 8.5 The Product Should Feel Complete on Day One

The user should not need to spend a week wiring tools together.

The product should be:
- easy to deploy
- easy to onboard
- immediately useful
- visibly progressing after the first session

## 9. Core User Experience

The right mental model is:

**Onboarding is the first meeting with Praetor.**

The user should feel:
- "I am defining how this company works."
- "Praetor is translating that into structure and execution."
- "I do not have to configure everything manually."

### 9.1 The Ideal Experience

The user says:

`I want to start a new project.`

Praetor replies:
- what it understands
- what it can do automatically
- what needs approval
- what team structure it will use
- what the next checkpoint will be

This is the core experience:

**Praetor decides how to run the work. The user decides direction and key approvals.**

## 10. Company DNA

One of the strongest ideas in the current direction is `Company DNA`.

This should be generated during onboarding and stored in:

`workspace/Wiki/Company/DNA.md`

It should define:
- leadership style
- decision style
- organization style
- autonomy mode
- risk preference
- operating principles
- communication norms

Example structure:

```yaml
company_dna:
  leadership_style: strategic
  decision_style: balanced
  organization_style: lean
  autonomy_mode: hybrid
  risk_priority: avoid_wrong_decisions
  communication_style: concise
  operating_principles:
    - default_to_action_escalate_when_uncertain
    - keep_roles_minimal_but_clear
    - document_important_decisions
    - avoid_unnecessary_user_interruption
```

This is a strong design choice because it lets the user shape culture without micromanaging agents.

## 11. Role-Based Organization

Praetor should be role-first.

Example role definition:

```yaml
role:
  name: Project Execution
  responsibility:
    - create_project_structure
    - maintain_project_status
    - organize_related_documents
  output:
    - project_folder
    - project_plan
    - status_updates
  constraints:
    - no_strategic_decisions
    - no_financial_actions
```

The user owns this level.

The system then maps:
- role -> agent form
- role -> skills
- role -> workflow placement

This is one of Praetor's clearest product differentiators.

## 12. Organizational Hierarchy

### 12.1 MVP Hierarchy

Recommended logical structure:

```txt
Owner
  ↓
Praetor (CEO layer)
  ↓
Manager or PM layer when needed
  ↓
Worker roles
  ↓
Reviewer
  ↓
Executors
```

### 12.2 Why This Works

It gives:
- one stable user-facing interface
- room for internal complexity
- clearer accountability
- easier context isolation

The user should not normally manage PMs directly.

Praetor remains the main interface.

### 12.3 Hidden Complexity Principle

The correct principle is:

**Hierarchy exists, but complexity is hidden.**

This is central to keeping the UI understandable while allowing the system to scale.

## 13. CEO Load Management

Praetor should not manually carry all mission context forever.

When context grows too large, the CEO layer should be allowed to instantiate mission-scoped managers.

### 13.1 Signals for PM Creation

Recommended signals:
- context token load
- estimated steps
- number of domains involved
- active mission count
- blocked count
- decision queue size

Illustrative policy:

```yaml
ceo_context:
  warning_at_tokens: 70000
  split_at_tokens: 90000

complexity:
  max_steps_without_pm: 5
  max_domains_without_pm: 1

organization:
  max_active_missions_per_ceo: 3

blocked:
  create_pm_after_blocked_count: 2
```

### 13.2 PM Scope

PMs should be:
- mission-scoped
- functionally defined
- dissolvable after mission completion

Not permanent personalities.

### 13.3 Context Split

Praetor CEO should read:
- company DNA
- mission summaries
- PM reports
- pending owner decisions

PM should own:
- full mission history
- task breakdown
- local decisions
- execution logs
- detailed context

This is one of the main technical mechanisms for avoiding context explosion.

## 14. Memory Architecture

Recommended memory model:

### 14.1 Company Memory

Persistent, shared, durable memory:
- wiki
- decisions
- rules
- project files
- SOPs

### 14.2 Task Memory

Mission- or task-scoped working memory:
- input
- intermediate outputs
- notes
- review comments
- checkpoints

This should be archivable.

### 14.3 Agent Memory

Recommendation for MVP:
- no personal agent memory
- no personality drift
- no inter-agent relationship simulation

Reason:
- more predictable
- more reproducible
- easier to debug
- consistent with role-first design

### 14.4 Product Philosophy for Memory

The cleanest product rule is:

**Do not let the agent remember. Let the company remember.**

## 15. Skills and Capability Layer

Skills should not be treated as prompt bundles.

They should be treated as executable capabilities.

Example:

```yaml
skill:
  name: create_project_structure
  description: create_standardized_project_folder
  input:
    - project_name
  output:
    - folder_created
  actions:
    - create_folder
    - create_files
    - write_markdown
```

### 15.1 Skill Categories

Recommended categories:

- core file skills
- knowledge skills
- execution skills
- external imported skills

Examples:
- `file_read`
- `file_write`
- `create_folder`
- `update_markdown`
- `summarize_document`
- `extract_info`
- `generate_plan`
- `run_codex`
- `run_claude_code`
- `run_script`

### 15.2 Marketplace Timing

The idea of GitHub-imported skills is strong, but not for MVP.

Recommended rollout:
- MVP: built-in internal skills only
- Phase 2: enable/disable and custom import
- Phase 3: GitHub skill ecosystem

## 16. AI Runtime Modes

This is one of the most important product decisions.

Praetor should support three runtime modes.

### 16.1 API Mode

Use provider APIs directly:
- OpenAI API
- Anthropic API
- Gemini API

Best for:
- predictable integration
- backend-controlled execution
- standard production behavior

### 16.2 Local Mode

Use local models:
- Ollama
- other local runtimes later

Best for:
- privacy-first usage
- experimentation
- low external dependency

### 16.3 Subscription Executor Mode

Use the user's existing logged-in tool:
- Codex CLI
- Claude Code
- OpenClaw-style executors

Best for:
- users who already pay for AI tools
- coding-heavy workflows
- avoiding separate API billing

### 16.4 Why This Matters

This is not a small implementation detail.

It changes the economic attractiveness of the product.

Praetor should be able to say:

**Bring your own AI. Praetor provides structure, memory, governance, and workflow.**

## 17. Execution and Executor Abstraction

Praetor should not assume one execution backend.

Recommended abstraction:

```yaml
ai_runtime:
  mode: subscription_executor

executors:
  codex:
    enabled: true
    requires_user_login: true
    workspace: /workspace
  api:
    enabled: false
  local:
    enabled: false
```

The core contract should cover:
- task spec input
- allowed workspace scope
- execution approval mode
- expected outputs
- logs
- exit state

This abstraction is essential if Praetor is going to support both API-driven tasks and external coding executors cleanly.

## 18. Deployment Model

Praetor should be easy to run in two primary ways.

### 18.1 Local Desktop / Laptop

Recommended entry:

```bash
docker compose up -d
```

Then open:

`http://localhost:3000`

### 18.2 Remote Self-Hosted

Deploy to a VPS or private server with:
- HTTPS reverse proxy
- auth enabled
- persistent workspace volume
- persistent config and state

Recommended principle:

**Local-first, not local-only.**

The product should feel native to self-hosting, but not require cloud dependency.

## 19. Workspace Model

Recommended workspace shape:

```txt
workspace/
├── Inbox/
├── Wiki/
├── Projects/
├── Finance/
├── Operations/
├── Development/
├── Decisions/
├── Missions/
├── Archive/
```

Key roles of each area:

- `Inbox`: raw input from the user
- `Wiki`: durable company memory
- `Projects`: long-lived execution outputs
- `Decisions`: explicit governance trail
- `Missions`: scoped task-level execution context
- `Archive`: closed items

Missions likely deserve their own scoped structure:

```txt
workspace/Missions/<mission_id>/
├── MISSION.md
├── STATUS.md
├── TASKS.md
├── DECISIONS.md
├── CONTEXT.md
├── REPORT.md
└── logs/
```

## 20. Safety and Governance

Praetor's safety model should be explicit and productized.

### 20.1 Writable Scope

The system must not be able to edit arbitrary machine state by default.

Recommended config:

```yaml
permissions:
  allow_read:
    - /app/workspace
  allow_write:
    - /app/workspace/Projects
    - /app/workspace/Wiki
    - /app/workspace/Decisions
    - /app/workspace/Missions
  deny_write:
    - /app/workspace/Archive
```

### 20.2 Approval Categories

The system should distinguish:
- auto-allowed actions
- batched report actions
- approval-required actions
- never-allowed actions

High-risk examples:
- delete files
- overwrite important documents
- spend money
- send external messages
- run shell commands
- change strategy

### 20.3 Governance Is a First-Class UI Area

This should not be buried in a config file only.

Users should be able to see and adjust:
- autonomy mode
- approval rules
- checkpoint policy
- role definitions
- executor policy

## 21. Onboarding

Onboarding should be conversational, not configuration-first.

The correct mental model is:

**Onboarding is the first meeting with Praetor.**

### 21.1 Recommended Onboarding Sequence

1. language
2. leadership style
3. decision style
4. organization style
5. autonomy preference
6. risk preference
7. runtime mode
8. workspace path
9. company type template
10. approval boundaries
11. first mission

### 21.2 Why This Matters

Good onboarding should do three things:
- establish trust
- establish company identity
- create momentum immediately

The user should leave onboarding with:
- a workspace
- a company DNA file
- an initial role structure
- a clear first task

## 22. User Interface

The UI should feel like:
- a command center
- a founder dashboard
- an AI company operating console

Not like:
- a generic chat app
- a debug console
- a node graph editor

### 22.1 Primary Navigation

Recommended top-level pages:
- CEO
- Overview
- Tasks
- Meetings
- Memory
- Models
- Settings

### 22.2 Primary Layout

Recommended shell:
- left navigation
- central workspace
- right context panel
- top bar for company/runtime status

### 22.3 CEO Page

This should be the main operational surface.

It should include:
- summary briefing
- CEO chat
- pending decisions
- suggested actions
- escalation queue

The user should spend most time here.

### 22.4 Overview

A chairman-level summary:
- active projects
- blocked items
- deadlines
- recent outputs
- tasks running
- owner decisions waiting

### 22.5 Tasks

Task transparency without noise.

Must support:
- board view
- list view
- task detail
- checkpoint actions
- status history
- outputs and logs

### 22.6 Meetings

Meetings should be structured review spaces, not free-form chat rooms.

Output format should emphasize:
- summary
- risks
- decisions needed
- next actions

### 22.7 Memory

This page should expose:
- wiki
- decisions
- source files
- retrieval preview

`Retrieval Preview` is especially valuable for trust.

### 22.8 Models

Model usage needs a first-class page.

It should show:
- current runtime mode
- active models and executors
- token usage
- estimated cost
- provider breakdown
- executor activity
- budget and fallback policy

### 22.9 Settings

Recommended settings groups:
- General
- Governance
- Workspace
- Roles
- AI / Executors
- Security
- Advanced

## 23. Speed, Checkpoints, and Run Budgets

One of the most important UX policies is:

**AI should wait for humans at the right time. Humans should not wait for AI at every small step.**

### 23.1 Run Budget

Each mission should have a clear budget:

```yaml
run_budget:
  max_steps: 20
  max_tokens: 100000
  max_time_minutes: 30
  max_cost_eur: 2.00
```

### 23.2 Stop Conditions

The main stop conditions should be:
- token or cost budget reached
- decision checkpoint
- risk checkpoint
- mission completion

### 23.3 Default Autonomy Policy

Recommended policy:

```yaml
autonomy_policy:
  low_risk_tasks: auto_continue
  medium_risk_tasks: report_after_batch
  high_risk_tasks: require_approval
```

This avoids the "Codex keeps stopping every minute" problem while still keeping the founder in control at meaningful moments.

### 23.4 User-Visible Controls

When paused, the UI should offer:
- Continue
- Continue with larger budget
- Stop
- Ask Praetor

### 23.5 Suggested Presets

Recommended presets:
- Careful
- Balanced
- Fast

Balanced should be the default.

## 24. Technical Architecture

Recommended practical architecture:

### 24.1 Frontend

- Next.js or React app
- browser-first
- responsive
- clear dashboard and task views

### 24.2 Backend

- Python runtime recommended
- FastAPI for API layer
- modular service boundaries

Reason:
- strong filesystem ergonomics
- easier model integration
- easier document processing
- easier CLI and automation support

### 24.3 Runtime Services

Suggested core subsystems:
- governance engine
- mission runtime
- role-to-agent mapper
- executor adapter layer
- memory retrieval layer
- audit/logging layer

### 24.4 Storage

- filesystem for company truth
- SQLite for operational metadata
- JSONL or structured logs for traceability

### 24.5 Recommended Internal Modules

```txt
backend/
├── api/
├── governance/
├── runtime/
├── roles/
├── executors/
├── memory/
├── missions/
├── models/
└── storage/
```

This is more of a logical decomposition than a mandatory repo layout.

## 25. Scalability

Praetor should scale in layers.

### 25.1 Human-Facing Scalability

The user should still see one executive interface even as:
- missions multiply
- PMs are created
- different runtime backends are used

### 25.2 Technical Scalability

The system should scale by:
- mission-scoped context
- hidden PM layers
- modular executors
- explicit run budgets
- summarized upward reporting

### 25.3 Product Scalability

Praetor should become more powerful without becoming harder to understand.

That means:
- more internal capability
- not more visible user burden

## 26. What Makes It Immediately Useful

This is one of the most important product questions.

The user needs to feel progress on day one.

Recommended immediate wins:

### 26.1 Create Project

Input:
- "Create a new project for X"

Output:
- project folder
- project plan
- status page
- tasks page

### 26.2 Review Inbox

Input:
- raw files dropped in `Inbox`

Output:
- summaries
- extracted facts
- suggested actions
- mission proposals

### 26.3 Build Company Wiki

Input:
- company answers from onboarding
- current files

Output:
- DNA
- strategy page
- operating principles
- decision log

### 26.4 Update Status

Input:
- existing project files

Output:
- refreshed status
- highlighted blockers
- next decisions

These are powerful because they create visible artifacts in the workspace immediately.

## 27. What Makes It Feel Complete

Users judge completeness quickly.

Praetor should feel complete even before it is huge.

The product should include:
- a clear onboarding flow
- a usable dashboard
- a functioning CEO interface
- visible tasks and decisions
- clear memory model
- model usage visibility
- real file outputs
- safe boundaries
- clear pause and continue behavior

If those pieces exist, users can forgive missing integrations.

If those pieces are missing, no amount of future roadmap will matter.

## 28. Risks and Mitigations

### 28.1 Risk: Product Becomes Too Broad

Mitigation:
- keep MVP focused
- restrict v1 use cases
- avoid enterprise feature creep

### 28.2 Risk: CEO Layer Becomes a Bottleneck

Mitigation:
- hidden PM creation
- mission-scoped context
- load-based delegation

### 28.3 Risk: Too Much Prompt Magic, Not Enough System

Mitigation:
- explicit governance rules
- explicit mission files
- explicit logs
- executable skills instead of prompt bundles

### 28.4 Risk: Users Do Not Trust the System

Mitigation:
- retrieval preview
- task logs
- run budgets
- approvals
- diff-like visibility for file changes

### 28.5 Risk: Cost or Token Usage Feels Uncontrolled

Mitigation:
- model page
- budget controls
- executor selection
- per-task policy

### 28.6 Risk: Coding Executors Keep Interrupting Too Much

Mitigation:
- run budget policy
- PM-managed batch execution
- only pause at meaningful checkpoints

## 29. Recommended MVP Scope

Praetor should not try to ship the whole vision in v1.

Recommended MVP:

- Docker deployment
- browser UI
- conversational onboarding with Praetor
- company DNA generation
- role-based internal organization
- CEO page
- overview page
- tasks page
- settings page
- workspace filesystem
- wiki memory
- mission/task logging
- approval rules
- API mode
- at least one executor mode
- 3 to 5 built-in use cases

Recommended MVP use cases:
- create project
- organize workspace
- review inbox
- build company wiki
- update project status

## 30. Suggested Build Sequence

Recommended implementation order:

### Phase 1

- product spec
- repo structure
- workspace model
- governance model
- company DNA
- role schema

### Phase 2

- onboarding
- CEO interaction layer
- mission runtime
- task pages
- file outputs

### Phase 3

- executor abstraction
- API mode
- subscription executor mode
- model usage page

### Phase 4

- hidden PM creation
- meetings
- retrieval preview
- skill tuning

### Phase 5

- GitHub skill import
- richer executor ecosystem
- advanced role tuning

## 31. Product Thesis in Final Form

The strongest current thesis is:

**Praetor is a founder-facing AI company command center.**

It gives one person:
- an AI executive layer
- a governed organization of roles
- company-owned memory
- bounded autonomy
- safe execution in a controlled workspace

The user does not configure agents.

The user defines:
- direction
- culture
- responsibilities
- approvals

Praetor defines:
- organization
- delegation
- execution flow
- skill use
- escalation timing

## 32. Final Recommendation

The current product direction is strong.

It is strong because it is opinionated in the right places:
- founder-first
- CEO-centered UX
- role-first abstraction
- company memory over agent memory
- self-hosted and local-first
- multi-runtime support
- visible governance

The biggest discipline required from here is not more ideation.

It is refusing to dilute the core.

The core is not "many agents."

The core is:

**an AI company with structure, memory, and governance that a solo founder can actually use every day**

## 33. Source Notes

The market framing in this synthesis was cross-checked against official product materials current as of April 24, 2026:

- [Dify workflow and chatflow docs](https://docs.dify.ai/en/use-dify/build/workflow-chatflow)
- [Flowise introduction docs](https://docs.flowiseai.com/)
- [LangGraph overview docs](https://docs.langchain.com/oss/python/langgraph)
- [CrewAI introduction docs](https://docs.crewai.com/introduction)
- [OpenAI Codex overview](https://platform.openai.com/docs/codex/overview)
- [OpenAI: Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540/)
- [OpenAI: Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/)
- [Anthropic Claude Code overview](https://docs.anthropic.com/en/docs/claude-code/overview)
