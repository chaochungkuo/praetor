# Praetor Team Planning

Praetor should feel like a company operating system, not a multi-agent toy.

The chairman talks to the CEO. The CEO decides whether the work needs a mission,
a planning team, a board briefing, execution, review, or escalation. Internal AI
roles are visible for accountability, but the user should not need to manually
operate every agent.

## Core Flow

1. The chairman gives the CEO an idea, instruction, or question.
2. The CEO planner converts the instruction into explicit actions.
3. If the work needs structure, Praetor creates a mission.
4. The CEO forms a mission team with clear roles and reporting lines.
5. The Project Manager opens role-specific delegations.
6. The team produces a board briefing for the chairman.
7. The chairman approves, revises, or authorizes execution.
8. Execution creates documents, decisions, open questions, run records, and
   reviewer checks.
9. Closeout uses memory promotion before anything becomes durable company
   knowledge.

## Board Briefing

`BoardBriefing` is the formal artifact between planning and execution.

It contains:

- participants
- executive summary
- recommendations
- assumptions
- risks
- decisions needed
- related artifacts

This keeps AI-to-AI discussion from becoming the product. Raw messages remain
evidence. The briefing is the owner-facing result.

## Role Pattern

Default planning teams can include:

- CEO
- Project Manager
- Product Manager
- Marketing Lead
- Design Lead
- Developer
- Reviewer
- Sales Manager
- Legal Counsel
- Security Officer

Praetor should create only the roles needed for the mission. Roles are
mission-scoped unless they become durable company roles later.

## Escalation

The PM can decide low-risk sequencing and implementation details. The PM must
escalate:

- security or privacy risk
- legal or contract risk
- external communication
- spending
- destructive file operations
- material strategy changes
- unresolved role disagreement

The CEO can resolve ordinary business tradeoffs. The chairman decides anything
that changes authority, risk, budget, external commitments, or final direction.

## Memory Boundary

Team planning does not write durable memory directly. It creates structured
records:

- `BoardBriefing`
- `DelegationRecord`
- `MeetingRecord`
- `MatterDecisionRecord`
- `OpenQuestionRecord`
- `DocumentRecord`
- `MemoryPromotionReview`

Only confirmed conclusions should be promoted to wiki knowledge.
