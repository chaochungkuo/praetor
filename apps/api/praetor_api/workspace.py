from __future__ import annotations

import os
from pathlib import Path


DEFAULT_WORKSPACE_DIRS = [
    "Wiki",
    "Projects",
    "Finance",
    "Operations",
    "Development",
    "Decisions",
    "Agents",
    "Missions",
    "Meetings",
    "Inbox",
    "Archive",
    ".praetor",
    ".praetor/history",
]


DEFAULT_WIKI_PAGES = {
    "Wiki/Company.md": "# Company\n",
    "Wiki/Strategy.md": "# Strategy\n",
    "Wiki/Decision Log.md": "# Decision Log\n",
    "Wiki/Agent Handbook.md": "# Agent Handbook\n",
}


DEFAULT_WORKFLOW_CONTRACT = """# Praetor Workflow

This workspace contract is versioned with the company workspace. It defines how Praetor should turn owner intent into isolated, observable company work.

## Operating Model

- The CEO is the owner-facing entry point, not the storage location for every detail.
- The CEO may form a mission team when work needs product, market, design, legal, security, or engineering judgment.
- The Project Manager coordinates role-specific delegations and prepares board briefings before major execution.
- Every mission must have a clear workspace scope before execution.
- Raw conversation is audit material; durable memory is promoted only through confirmed decisions, approved knowledge updates, and document registry records.
- A successful agent run is not the same as a completed matter.

## Team Planning Contract

- Planning teams produce board briefings, not unfiltered agent transcripts.
- Board briefings must separate recommendations, assumptions, risks, decisions needed, and related artifacts.
- Low-risk sequencing can be decided by the PM inside mission scope.
- Security, privacy, legal, spending, external communication, destructive file actions, and material strategy changes must be escalated.

## Workspace Steward Contract

- The owner should not need to manually create folders or classify files.
- Files must be registered as stable file assets; filesystem paths are current locations, not durable identity.
- Uploaded, downloaded, generated, requested, and executor-created files should enter the same file intake and registry flow.
- Folder restructuring should create a reviewable plan before moving important client, legal, privacy, or delivery files.
- Wiki and document registry references should be updated through stable IDs such as praetor://file/<asset_id>, not only raw paths.

## Completion Contract

- Requested outputs are present or explicitly waived.
- Relevant documents are registered with versions and reasons.
- Open questions are answered, closed, or intentionally marked non-blocking.
- Required reviews and approvals are complete.
- A final owner-visible report exists.
- Durable knowledge updates are proposed, approved, applied, or rejected.

## Memory Promotion Contract

- Chat, agent turns, work-session messages, and raw external text are evidence, not durable memory.
- Durable memory must come from confirmed decisions, document registry facts, resolved open questions, or approved knowledge updates.
- Mission closeout should create a memory promotion review before writing new wiki knowledge.
- Abandoned ideas, unresolved speculation, and do-not-promote notes stay in audit logs or promotion review records, not in the wiki.
- Proposed knowledge updates must identify their target page and source records.

## Safety Contract

- Agent writes must stay inside the mission or matter workspace unless explicitly allowed.
- Destructive writes, privacy-sensitive memory updates, external communication, spending, and strategy changes require escalation according to governance settings.
- Credentials, private keys, tokens, and raw sensitive client material must not be promoted into long-term wiki memory.

## Continuation Contract

- If a run succeeds but the matter remains open, Praetor should continue only with a focused continuation prompt.
- If a run stalls, fails, or needs context, Praetor records the blocker and escalates to the manager, CEO, or owner.
"""


def bootstrap_workspace(root: Path) -> None:
    for rel in DEFAULT_WORKSPACE_DIRS:
        path = root.joinpath(rel)
        path.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(path, 0o700)
        except OSError:
            pass
    for rel, content in DEFAULT_WIKI_PAGES.items():
        path = root / rel
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
    workflow_path = root / "PRAETOR_WORKFLOW.md"
    if not workflow_path.exists():
        workflow_path.write_text(DEFAULT_WORKFLOW_CONTRACT, encoding="utf-8")
        try:
            os.chmod(workflow_path, 0o600)
        except OSError:
            pass
