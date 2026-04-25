from __future__ import annotations

from .models import (
    CompanyDNA,
    GovernancePolicy,
    MissionCreateRequest,
    OnboardingAnswers,
    OnboardingPreview,
    RoleDefinition,
    RuntimeSelection,
)


DEFAULT_OPERATING_PRINCIPLES = {
    "hands_on": [
        "Escalate early and visibly.",
        "Prefer explicit checkpoints over silent action.",
    ],
    "strategic": [
        "Default to action, escalate when uncertainty is material.",
        "Protect the founder's attention for directional decisions.",
    ],
    "delegator": [
        "Move forward autonomously on low-risk work.",
        "Report crisply instead of interrupting often.",
    ],
}


def generate_company_dna(answers: OnboardingAnswers) -> CompanyDNA:
    principles = list(DEFAULT_OPERATING_PRINCIPLES[answers.leadership_style])
    if answers.organization_style == "lean":
        principles.append("Keep structure minimal and responsibilities clear.")
    if answers.risk_priority == "avoid_losing_information":
        principles.append("Document important decisions and preserve source materials.")
    return CompanyDNA(
        language=answers.language,
        leadership_style=answers.leadership_style,
        decision_style=answers.decision_style,
        organization_style=answers.organization_style,
        autonomy_mode=answers.autonomy_mode,
        risk_priority=answers.risk_priority,
        operating_principles=principles,
    )


def generate_governance(answers: OnboardingAnswers) -> GovernancePolicy:
    auto_execute = [
        "create_files",
        "draft_documents",
        "summarize_documents",
        "organize_workspace",
    ]
    never_allow = [
        "access_outside_workspace",
        "silent_destructive_actions",
        "external_send_without_explicit_rule",
    ]
    return GovernancePolicy(
        autonomy_mode=answers.autonomy_mode,
        require_approval=answers.require_approval,
        auto_execute=auto_execute,
        never_allow=never_allow,
    )


def suggest_roles(answers: OnboardingAnswers) -> list[RoleDefinition]:
    roles = [
        RoleDefinition(
            name="Project Execution",
            responsibilities=[
                "create and maintain project structure",
                "update project status and tasks",
            ],
            outputs=["project folders", "status documents", "task updates"],
            constraints=["no strategic decisions", "no spending decisions"],
        ),
        RoleDefinition(
            name="Reviewer",
            responsibilities=[
                "review outputs for quality and completeness",
                "identify missing information or risky changes",
            ],
            outputs=["review notes", "risk summaries"],
            constraints=["no final decisions"],
        ),
    ]
    if answers.organization_style in {"structured", "flexible"}:
        roles.insert(
            0,
            RoleDefinition(
                name="Project Manager",
                responsibilities=[
                    "own mission context",
                    "coordinate task sequencing and reporting",
                ],
                outputs=["mission summaries", "next-step recommendations"],
                constraints=["no company-wide strategy changes"],
            ),
        )
    return roles


def preview_onboarding(answers: OnboardingAnswers) -> OnboardingPreview:
    runtime = RuntimeSelection.model_validate(answers.runtime.model_dump())
    if runtime.mode == "api":
        runtime.provider = runtime.provider or "openai"
        runtime.model = runtime.model or "gpt-4.1-mini"
    elif runtime.mode == "subscription_executor":
        runtime.executor = runtime.executor or "codex"
    return OnboardingPreview(
        company_dna=generate_company_dna(answers),
        governance=generate_governance(answers),
        suggested_roles=suggest_roles(answers),
        workspace_root=answers.workspace_root,
        runtime=runtime,
    )


def assess_mission_complexity(request: MissionCreateRequest) -> tuple[float, bool, str | None]:
    score = 0.0
    score += min(len(request.domains), 3) * 0.2
    score += min(len(request.requested_outputs), 5) * 0.1
    score += 0.25 if request.priority in {"high", "critical"} else 0.0
    if request.summary and len(request.summary) > 140:
        score += 0.15
    pm_required = score >= 0.5
    reason = None
    if pm_required:
        parts = []
        if len(request.domains) > 1:
            parts.append("multiple domains")
        if len(request.requested_outputs) >= 3:
            parts.append("many requested outputs")
        if request.priority in {"high", "critical"}:
            parts.append("high priority")
        reason = ", ".join(parts) or "mission complexity threshold exceeded"
    return round(score, 2), pm_required, reason
