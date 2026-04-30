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
- Every mission must have a clear workspace scope before execution.
- Raw conversation is audit material; durable memory is promoted only through confirmed decisions, approved knowledge updates, and document registry records.
- A successful agent run is not the same as a completed matter.

## Completion Contract

- Requested outputs are present or explicitly waived.
- Relevant documents are registered with versions and reasons.
- Open questions are answered, closed, or intentionally marked non-blocking.
- Required reviews and approvals are complete.
- A final owner-visible report exists.
- Durable knowledge updates are proposed, approved, applied, or rejected.

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
