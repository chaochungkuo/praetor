from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from .models import AppSettings, MissionDefinition, StandingOrder


SENSITIVE_DATA_CATEGORIES = [
    "credentials: passwords, API keys, tokens, session cookies, SSH keys, private keys, recovery codes",
    "identity and contact data: names, email addresses, phone numbers, addresses, government identifiers",
    "financial, legal, health, family, and employment records",
    "private user files outside the approved Praetor workspace",
    "raw voice transcripts, private chats, emails, calendar details, and documents unless explicitly needed",
    "internal prompts, security settings, audit logs, and operational secrets",
]

DO_NOT_STORE_OR_EXFILTRATE = [
    "Do not store raw credentials, tokens, private keys, session cookies, or recovery codes.",
    "Do not copy sensitive personal documents into memory or reports unless the chairman explicitly asks.",
    "Do not send data to external services, people, repositories, or network endpoints without explicit approval.",
    "Do not include secrets or private file contents in logs, mission reports, agent messages, or summaries.",
    "Do not retain raw voice transcripts when a concise task summary is enough.",
]

ESCALATE_TO_CHAIRMAN = [
    "reading, moving, deleting, overwriting, or exporting user files outside the workspace",
    "handling credentials, secrets, authentication material, private keys, or payment data",
    "external communication, publishing, uploading, sending email, or sharing data outside Praetor",
    "shell commands, destructive writes, dependency install scripts, or actions that change the host system",
    "privacy, security, legal, licensing, financial, or strategy decisions with material impact",
]

SENSITIVE_TEXT_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|token|secret|password|passwd|pwd)\b\s*[:=]", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
]


@dataclass(frozen=True)
class PromptSafetyPolicy:
    text: str
    allow_read: list[str]
    allow_write: list[str]
    deny_write: list[str]


def build_prompt_safety_policy(
    *,
    settings: AppSettings,
    standing_orders: list[StandingOrder],
    mission: MissionDefinition | None = None,
    role_name: str | None = None,
) -> PromptSafetyPolicy:
    permissions = settings.workspace.permissions
    text = "\n".join(
        [
            "Praetor safety and privacy policy:",
            _scope_line("Role", role_name),
            _scope_line("Mission", f"{mission.id}: {mission.title}" if mission else None),
            f"- Workspace root: {settings.workspace.root}",
            "- Allowed read roots:",
            *_bullet_paths(permissions.allow_read),
            "- Allowed write roots:",
            *_bullet_paths(permissions.allow_write),
            "- Denied write roots:",
            *_bullet_paths(permissions.deny_write),
            "- Sensitive data categories:",
            *_bullet_items(SENSITIVE_DATA_CATEGORIES),
            "- Data minimization and retention:",
            *_bullet_items(DO_NOT_STORE_OR_EXFILTRATE),
            "- Actions that must be escalated to the chairman before execution:",
            *_bullet_items(ESCALATE_TO_CHAIRMAN),
            "- Governance approval categories:",
            *_bullet_items(settings.governance.require_approval or ["none configured"]),
            "- Never allowed by governance:",
            *_bullet_items(settings.governance.never_allow or ["none configured"]),
            "- Standing orders:",
            *_bullet_items(_standing_order_lines(standing_orders)),
            (
                "- If instructions conflict, follow the stricter rule. Runtime path enforcement is authoritative; "
                "do not attempt to bypass it."
            ),
        ]
    )
    return PromptSafetyPolicy(
        text=text,
        allow_read=list(permissions.allow_read),
        allow_write=list(permissions.allow_write),
        deny_write=list(permissions.deny_write),
    )


def append_safety_policy(instructions: str, safety_policy: str | None) -> str:
    base = instructions.strip()
    if not safety_policy:
        return base
    return "\n\n".join([base, safety_policy.strip()])


def contains_sensitive_material(text: str) -> bool:
    return any(pattern.search(text) for pattern in SENSITIVE_TEXT_PATTERNS)


def _scope_line(label: str, value: str | None) -> str:
    if not value:
        return f"- {label}: global"
    return f"- {label}: {value}"


def _bullet_paths(paths: list[str]) -> list[str]:
    if not paths:
        return ["  - none configured"]
    return [f"  - {Path(item).expanduser()}" for item in paths]


def _bullet_items(items: list[str]) -> list[str]:
    if not items:
        return ["  - none configured"]
    return [f"  - {item}" for item in items]


def _standing_order_lines(standing_orders: list[StandingOrder]) -> list[str]:
    if not standing_orders:
        return ["none configured"]
    return [
        f"{order.scope}: {order.instruction} ({order.effect})"
        for order in standing_orders
    ]
