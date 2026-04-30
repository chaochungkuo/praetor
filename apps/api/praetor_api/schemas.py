from __future__ import annotations

import json
from pathlib import Path

from .models import (
    AgentInstance,
    AgentRoleSpec,
    AppSettings,
    ApprovalCreateRequest,
    ApprovalRequest,
    CompanyDNA,
    CompletionContract,
    DecisionRecord,
    DelegationRecord,
    EscalationRecord,
    MeetingRecord,
    MissionDefinition,
    MissionTeam,
    OnboardingAnswers,
    OnboardingPreview,
    OrganizationSnapshot,
    PlannerAction,
    PlannerPlan,
    PraetorBriefing,
    RunRecord,
    RoleDefinition,
    StandingOrder,
    TaskDefinition,
    WorkSession,
    WorkSessionTurn,
)


SCHEMA_MODELS = {
    "app_settings": AppSettings,
    "company_dna": CompanyDNA,
    "agent_role_spec": AgentRoleSpec,
    "agent_instance": AgentInstance,
    "mission_team": MissionTeam,
    "delegation_record": DelegationRecord,
    "escalation_record": EscalationRecord,
    "standing_order": StandingOrder,
    "completion_contract": CompletionContract,
    "organization_snapshot": OrganizationSnapshot,
    "role_definition": RoleDefinition,
    "mission_definition": MissionDefinition,
    "task_definition": TaskDefinition,
    "decision_record": DecisionRecord,
    "approval_request": ApprovalRequest,
    "approval_create_request": ApprovalCreateRequest,
    "meeting_record": MeetingRecord,
    "onboarding_answers": OnboardingAnswers,
    "onboarding_preview": OnboardingPreview,
    "planner_action": PlannerAction,
    "planner_plan": PlannerPlan,
    "praetor_briefing": PraetorBriefing,
    "run_record": RunRecord,
    "work_session": WorkSession,
    "work_session_turn": WorkSessionTurn,
}


def export_json_schemas(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    for name, model in SCHEMA_MODELS.items():
        path = output_dir / f"{name}.schema.json"
        path.write_text(
            json.dumps(model.model_json_schema(), indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        generated.append(path)
    return generated
