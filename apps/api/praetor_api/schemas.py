from __future__ import annotations

import json
from pathlib import Path

from .models import (
    AgentInstance,
    AgentRoleSpec,
    AppSettings,
    ApprovalCreateRequest,
    ApprovalRequest,
    ChairmanInboxItem,
    ClientRecord,
    CompanyDNA,
    CompletionContract,
    DecisionRecord,
    DelegationRecord,
    DocumentRecord,
    DocumentVersion,
    EscalationRecord,
    GovernanceReview,
    KnowledgeSnapshot,
    KnowledgeUpdate,
    MemoryPromotionReview,
    MatterDecisionRecord,
    MatterRecord,
    MeetingRecord,
    MissionDefinition,
    MissionTeam,
    OnboardingAnswers,
    OnboardingPreview,
    OpenQuestionRecord,
    OrganizationSnapshot,
    PlannerAction,
    PlannerPlan,
    PraetorBriefing,
    PromotionFinding,
    ReviewPolicy,
    RunAttempt,
    RunRecord,
    RoleDefinition,
    StandingOrder,
    TaskDefinition,
    WorkflowContract,
    WorkspaceScope,
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
    "chairman_inbox_item": ChairmanInboxItem,
    "meeting_record": MeetingRecord,
    "onboarding_answers": OnboardingAnswers,
    "onboarding_preview": OnboardingPreview,
    "planner_action": PlannerAction,
    "planner_plan": PlannerPlan,
    "praetor_briefing": PraetorBriefing,
    "run_attempt": RunAttempt,
    "run_record": RunRecord,
    "workflow_contract": WorkflowContract,
    "workspace_scope": WorkspaceScope,
    "work_session": WorkSession,
    "work_session_turn": WorkSessionTurn,
    "client_record": ClientRecord,
    "matter_record": MatterRecord,
    "document_record": DocumentRecord,
    "document_version": DocumentVersion,
    "matter_decision_record": MatterDecisionRecord,
    "open_question_record": OpenQuestionRecord,
    "knowledge_update": KnowledgeUpdate,
    "knowledge_snapshot": KnowledgeSnapshot,
    "memory_promotion_review": MemoryPromotionReview,
    "promotion_finding": PromotionFinding,
    "governance_review": GovernanceReview,
    "review_policy": ReviewPolicy,
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
