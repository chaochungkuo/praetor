from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


AutonomyMode = Literal["strict", "hybrid", "autonomous"]
DecisionStyle = Literal["careful", "balanced", "fast"]
LeadershipStyle = Literal["hands_on", "strategic", "delegator"]
OrganizationStyle = Literal["structured", "flexible", "lean"]
RiskPriority = Literal[
    "avoid_wrong_decisions",
    "avoid_being_slow",
    "avoid_losing_information",
    "avoid_acting_without_approval",
]
RuntimeMode = Literal["api", "local_model", "subscription_executor"]
PermissionCategory = Literal[
    "delete_files",
    "overwrite_important_files",
    "external_communication",
    "spending_money",
    "change_strategy",
    "shell_commands",
]
MissionStatus = Literal[
    "planned",
    "active",
    "review",
    "waiting_approval",
    "paused",
    "resumed",
    "completed",
    "archived",
    "failed",
]
TaskStatus = Literal[
    "planned",
    "assigned",
    "running",
    "review",
    "waiting_approval",
    "done",
    "failed",
]
ApprovalStatus = Literal["pending", "approved", "rejected"]
MeetingType = Literal["project_review", "risk_review", "weekly_planning", "decision_review"]
ConversationRole = Literal["chairman", "ceo", "system"]
AgentMessageRole = Literal["ceo", "project_manager", "developer", "reviewer", "system"]
TimelineEventType = Literal[
    "conversation",
    "agent_message",
    "mission",
    "task",
    "run",
    "approval",
    "meeting",
    "audit",
]


class ApiEnvelope(BaseModel):
    ok: bool
    data: Any = None
    error: dict[str, Any] | None = None


class OwnerProfile(BaseModel):
    name: str
    email: str | None = None
    role: str = "Founder"
    preferred_language: str = "en"


class OwnerAuthRecord(BaseModel):
    password_hash: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_login_at: datetime | None = None


class LoginRequest(BaseModel):
    password: str


class RuntimeSelection(BaseModel):
    mode: RuntimeMode = "api"
    provider: str | None = None
    model: str | None = None
    executor: str | None = None


class WorkspacePermissions(BaseModel):
    allow_read: list[str] = Field(default_factory=list)
    allow_write: list[str] = Field(default_factory=list)
    deny_write: list[str] = Field(default_factory=list)


class WorkspaceConfig(BaseModel):
    root: str
    permissions: WorkspacePermissions


class RunBudgetPolicy(BaseModel):
    max_steps: int = 20
    max_tokens: int = 100_000
    max_time_minutes: int = 30
    max_cost_eur: float = 2.0


class GovernancePolicy(BaseModel):
    autonomy_mode: AutonomyMode = "hybrid"
    require_approval: list[PermissionCategory] = Field(default_factory=list)
    auto_execute: list[str] = Field(default_factory=list)
    never_allow: list[str] = Field(default_factory=list)
    run_budget: RunBudgetPolicy = Field(default_factory=RunBudgetPolicy)


class CompanyDNA(BaseModel):
    language: str = "en"
    leadership_style: LeadershipStyle = "strategic"
    decision_style: DecisionStyle = "balanced"
    organization_style: OrganizationStyle = "lean"
    autonomy_mode: AutonomyMode = "hybrid"
    risk_priority: RiskPriority = "avoid_wrong_decisions"
    operating_principles: list[str] = Field(default_factory=list)


class RoleDefinition(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("role"))
    name: str
    responsibilities: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    auto_created: bool = True


class TaskCheckpointPolicy(BaseModel):
    checkpoints: list[str] = Field(default_factory=list)


class TaskDefinition(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("task"))
    mission_id: str
    title: str
    role_owner: str
    current_executor: str | None = None
    status: TaskStatus = "planned"
    checkpoint_policy: TaskCheckpointPolicy = Field(default_factory=TaskCheckpointPolicy)
    outputs: list[str] = Field(default_factory=list)


class UsageSummary(BaseModel):
    duration_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None
    usage_available: bool = False


class MissionRunBudget(BaseModel):
    max_steps: int = 20
    max_tokens: int = 100_000
    max_time_minutes: int = 30
    max_cost_eur: float = 2.0


class MissionDefinition(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("mission"))
    title: str
    requested_by: str = "owner"
    owner_layer: str = "praetor"
    manager_layer: str = "pm_auto"
    pm_required: bool = False
    complexity_score: float = 0.0
    escalation_reason: str | None = None
    status: MissionStatus = "planned"
    priority: str = "normal"
    domains: list[str] = Field(default_factory=list)
    summary: str | None = None
    requested_outputs: list[str] = Field(default_factory=list)
    run_budget: MissionRunBudget = Field(default_factory=MissionRunBudget)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DecisionOption(BaseModel):
    value: str
    label: str | None = None


class DecisionRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("decision"))
    mission_id: str
    summary: str
    requested_by: str = "praetor"
    impact: str = "strategic"
    status: ApprovalStatus = "pending"
    options: list[DecisionOption] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ApprovalRequest(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("approval"))
    category: PermissionCategory
    mission_id: str
    raised_by: str
    reason: str
    status: ApprovalStatus = "pending"
    actions: list[str] = Field(default_factory=lambda: ["approve_once", "approve_for_mission", "reject"])
    created_at: datetime = Field(default_factory=utc_now)


class ApprovalCreateRequest(BaseModel):
    mission_id: str
    category: PermissionCategory
    reason: str


class MeetingRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("meeting"))
    mission_id: str
    type: MeetingType
    moderator: str = "praetor"
    participants: list[str] = Field(default_factory=list)
    agenda: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)


class ConversationMessage(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("msg"))
    thread_id: str = "office"
    role: ConversationRole
    body: str
    created_at: datetime = Field(default_factory=utc_now)
    related_mission_id: str | None = None


class ConversationCreateRequest(BaseModel):
    body: str
    related_mission_id: str | None = None


class ConversationCreateResult(BaseModel):
    messages: list[ConversationMessage] = Field(default_factory=list)
    created_mission: MissionDefinition | None = None
    agent_messages: list["AgentMessage"] = Field(default_factory=list)
    intent: str = "briefing"


class AgentMessage(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("agentmsg"))
    mission_id: str
    role: AgentMessageRole
    body: str
    created_at: datetime = Field(default_factory=utc_now)
    task_id: str | None = None
    run_id: str | None = None


class MissionTimelineEvent(BaseModel):
    id: str
    mission_id: str | None = None
    type: TimelineEventType
    title: str
    body: str | None = None
    actor: str = "praetor"
    status: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OfficeSnapshot(BaseModel):
    briefing: PraetorBriefing
    missions: list[MissionDefinition] = Field(default_factory=list)
    approvals: list[ApprovalRequest] = Field(default_factory=list)
    recent_runs: list[dict[str, Any]] = Field(default_factory=list)
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    ceo_thread: list[ConversationMessage] = Field(default_factory=list)
    agent_activity: list[MissionTimelineEvent] = Field(default_factory=list)
    runtime_health: dict[str, Any] = Field(default_factory=dict)


class AppSettings(BaseModel):
    owner: OwnerProfile
    runtime: RuntimeSelection
    workspace: WorkspaceConfig
    governance: GovernancePolicy
    company_dna: CompanyDNA
    roles: list[RoleDefinition] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class OnboardingAnswers(BaseModel):
    owner_name: str
    owner_email: str | None = None
    owner_password: str | None = None
    language: str = "en"
    leadership_style: LeadershipStyle = "strategic"
    decision_style: DecisionStyle = "balanced"
    organization_style: OrganizationStyle = "lean"
    autonomy_mode: AutonomyMode = "hybrid"
    risk_priority: RiskPriority = "avoid_wrong_decisions"
    workspace_root: str
    runtime: RuntimeSelection = Field(default_factory=RuntimeSelection)
    require_approval: list[PermissionCategory] = Field(default_factory=list)


class OnboardingPreview(BaseModel):
    company_dna: CompanyDNA
    governance: GovernancePolicy
    suggested_roles: list[RoleDefinition]
    workspace_root: str
    runtime: RuntimeSelection


class MissionCreateRequest(BaseModel):
    title: str
    summary: str | None = None
    domains: list[str] = Field(default_factory=list)
    priority: str = "normal"
    requested_outputs: list[str] = Field(default_factory=list)


class MissionPauseRequest(BaseModel):
    reason: str = "owner_requested"


class MissionContinueRequest(BaseModel):
    reason: str = "owner_continue"


class MissionStopRequest(BaseModel):
    reason: str = "owner_stop"


class PraetorBriefing(BaseModel):
    active_missions: int
    paused_missions: int
    approvals_pending: int
    recent_missions: list[MissionDefinition] = Field(default_factory=list)


class RunRecord(BaseModel):
    run_id: str
    request_id: str
    mission_id: str
    task_id: str
    executor: str
    status: str
    normalized_status: str | None = None
    requires_owner_action: bool = False
    pause_reason: str | None = None
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    exit_code: int | None = None
    host_workdir: str
    changed_files: list[str] = Field(default_factory=list)
    usage: UsageSummary = Field(default_factory=UsageSummary)
    stdout_tail: str | None = None
    stderr_tail: str | None = None
    retrieval_preview: list[str] = Field(default_factory=list)
