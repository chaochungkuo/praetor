from __future__ import annotations

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


def bootstrap_workspace(root: Path) -> None:
    for rel in DEFAULT_WORKSPACE_DIRS:
        root.joinpath(rel).mkdir(parents=True, exist_ok=True)
    for rel, content in DEFAULT_WIKI_PAGES.items():
        path = root / rel
        if not path.exists():
            path.write_text(content, encoding="utf-8")
