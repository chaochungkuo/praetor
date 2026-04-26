# Praetor Command Center UX Plan

## Product Direction

Praetor should feel like a chairman's office for an AI-run company. The default experience is not configuration or raw logs. The default experience is a working command center where the chairman talks to the CEO, sees what the AI organization is doing, approves important decisions, and understands risk before work touches files, credentials, external APIs, or private data.

## Design Principles

1. CEO first: the primary action is always talking to the CEO.
2. Work is visible: missions, blockers, approvals, and agent activity must be readable without opening raw JSON.
3. Agents are teammates: each AI role needs a purpose, skills, authority, supervisor, and current workload.
4. Trust is visible: safety, privacy, approvals, runtime health, and audit context should appear next to the work they affect.
5. Technical detail is available but secondary: raw payloads, run IDs, and timestamps stay behind details panels or audit pages.
6. Mobile is a first-class surface: the chairman must be able to review, approve, and ask the CEO from a phone.

## Information Architecture

- Praetor: CEO briefing and direct CEO chat.
- Inbox: all items requiring chairman attention, including approvals, blocked work, runtime issues, risks, and completed work awaiting review.
- Tasks: mission board and mission detail.
- Agents: AI organization directory with roles, active agents, skills, authority, and recent activity.
- Activity: execution and audit stream for deeper inspection.
- Memory: company wiki and durable memory.
- Decisions: structured decision records and audit trail.
- Models: runtime, usage, and provider health.
- Settings: owner, runtime, workspace, governance, and provider keys.

## Visual System

- Keep the executive dark office tone, but make operational surfaces denser and easier to scan.
- Use panels for command surfaces, repeated cards for inbox items and agent roles, and small status chips for urgency, owner, and runtime state.
- Avoid raw technical values in the main reading path. Use natural labels and progressive disclosure.
- Keep cards flat and compact. The product is an operating room, not a marketing landing page.

## Implementation Steps

1. Add Inbox as a first-class navigation item.
2. Add Agent Directory as a first-class navigation item.
3. Wire Inbox to existing approvals, missions, recent runs, audit events, and runtime health.
4. Wire Agent Directory to existing organization snapshot, agent roles, agent instances, and recent agent activity.
5. Add localized Traditional Chinese and English labels for all new surfaces.
6. Add responsive CSS for command cards, role cards, and risk/attention chips.
7. Update smoke tests so these surfaces cannot regress silently.
8. Verify locally in the browser and through CI.

## Next Iterations

- Add filtered Inbox states: urgent, security, blocked, approvals, completed.
- Add per-agent profile pages with full conversation, current mission load, permissions, and memory access.
- Add explicit risk review cards before file writes, external API calls, credential use, and destructive operations.
- Add chairman standing-order controls directly from Inbox decisions.
