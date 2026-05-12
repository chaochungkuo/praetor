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
    "staffing",
    "active",
    "review",
    "reviewing",
    "ready_for_ceo",
    "needs_decision",
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
AgentMessageRole = str
TimelineEventType = Literal[
    "conversation",
    "agent_message",
    "mission",
    "task",
    "run",
    "approval",
    "delegation",
    "escalation",
    "team",
    "meeting",
    "audit",
]
PlannerActionType = Literal[
    "mission_draft",
    "approval_request",
    "memory_update",
    "briefing",
    "staffing_proposal",
    "agent_create",
    "delegation_create",
    "decision_escalation",
    "mission_closeout",
    "standing_order_update",
    "board_briefing",
]
PlannerActionStatus = Literal["proposed", "applied", "skipped"]
AgentStatus = Literal["active", "paused", "retired"]
EscalationLevel = Literal["project_manager", "ceo", "chairman"]
EscalationStatus = Literal["pending", "resolved", "dismissed"]
DelegationStatus = Literal["assigned", "running", "blocked", "review", "done", "cancelled"]
BoardBriefingStatus = Literal["draft", "ready_for_chairman", "approved", "superseded"]
StandingOrderScope = Literal["global", "mission", "security", "privacy", "legal", "finance", "product", "engineering"]
WorkSessionStatus = Literal["open", "running", "waiting_manager", "waiting_approval", "completed", "failed", "blocked"]
WorkSessionTurnType = Literal[
    "manager_instruction",
    "executor_result",
    "executor_question",
    "manager_decision",
    "escalation",
]
MissionStage = Literal[
    "intake",
    "staffing",
    "planning",
    "execution",
    "review",
    "owner_decision",
    "memory_promotion",
    "closeout",
]
SkillReviewStatus = Literal["imported_requires_review", "approved", "active", "rejected", "deprecated"]
PermissionProfileLevel = Literal["strict", "standard", "trusted", "risk_review"]
WorkTraceLayer = Literal["chairman", "ceo", "manager", "executor", "review", "memory", "system"]
ExecutorControlAction = Literal["request_summary", "pause", "resume", "escalate_manager", "escalate_ceo", "mark_blocked"]
MatterStatus = Literal["open", "waiting_owner", "waiting_external", "review", "closed", "archived"]
DocumentStatus = Literal["draft", "under_review", "approved", "sent", "obsolete"]
DecisionStatus = Literal["proposed", "confirmed", "replaced", "rejected"]
OpenQuestionStatus = Literal["open", "waiting_owner", "waiting_external", "answered", "closed"]
KnowledgeUpdateStatus = Literal["proposed", "approved", "applied", "rejected"]
PromotionFindingType = Literal["decision", "fact", "document_change", "open_question", "discarded_idea", "do_not_promote"]
PromotionReviewStatus = Literal["draft", "ready_for_review", "applied", "rejected"]
ReviewCadence = Literal["on_open", "daily", "weekly", "manual"]
NotificationThreshold = Literal["never", "approval_required", "high_only", "digest"]
InboxSeverity = Literal["low", "medium", "high"]
InboxStatus = Literal["open", "acknowledged", "resolved", "dismissed"]
MissionJobStatus = Literal[
    "queued",
    "running",
    "completed",
    "failed",
    "interrupted",
    "cancelled",
]
RunAttemptStatus = Literal[
    "preparing_workspace",
    "building_prompt",
    "launching_agent",
    "streaming_turn",
    "succeeded",
    "failed",
    "timed_out",
    "stalled",
    "canceled",
    "retry_queued",
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
    base_url: str | None = None


class WorkspacePermissions(BaseModel):
    allow_read: list[str] = Field(default_factory=list)
    allow_write: list[str] = Field(default_factory=list)
    deny_write: list[str] = Field(default_factory=list)


class WorkspaceConfig(BaseModel):
    root: str
    permissions: WorkspacePermissions


class WorkspaceScope(BaseModel):
    mission_id: str
    matter_id: str | None = None
    root: str
    allowed_read: list[str] = Field(default_factory=list)
    allowed_write: list[str] = Field(default_factory=list)
    denied_write: list[str] = Field(default_factory=list)
    workflow_path: str | None = None


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


class ReviewPolicy(BaseModel):
    cadence: ReviewCadence = "on_open"
    notification_threshold: NotificationThreshold = "approval_required"
    quiet_mode: bool = True
    stale_mission_hours: int = 48
    stalled_run_minutes: int = 30
    max_items: int = 12
    always_escalate_domains: list[str] = Field(default_factory=lambda: ["legal", "security", "privacy", "finance"])


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


class AgentRoleSpec(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("agentrole"))
    name: str
    purpose: str
    responsibilities: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    escalation_triggers: list[str] = Field(default_factory=list)
    decision_authority: list[str] = Field(default_factory=list)
    default_supervisor_role: str = "ceo"
    created_at: datetime = Field(default_factory=utc_now)


class SkillSource(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("skillsrc"))
    name: str
    url: str
    source_type: str = "github"
    branch: str = "main"
    status: str = "enabled"
    trust_status: str = "unreviewed"
    last_imported_at: datetime | None = None
    imported_skill_count: int = 0
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AgentSkillSpec(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("agentskill"))
    source_id: str | None = None
    source_url: str | None = None
    source_path: str | None = None
    name: str
    description: str | None = None
    domains: list[str] = Field(default_factory=list)
    suitable_for: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    escalation_triggers: list[str] = Field(default_factory=list)
    output_contract: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    status: SkillReviewStatus = "imported_requires_review"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AgentPermissionProfile(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("permprof"))
    name: str
    level: PermissionProfileLevel = "standard"
    description: str
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_workspace_scopes: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    memory_access: list[str] = Field(default_factory=list)
    max_autonomy: AutonomyMode = "hybrid"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AgentInstance(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("agent"))
    role_name: str
    display_name: str
    mission_id: str | None = None
    supervisor_agent_id: str | None = None
    supervisor_role: str = "ceo"
    status: AgentStatus = "active"
    charter: str
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    permission_profile: str | None = None
    memory_access: list[str] = Field(default_factory=list)
    decision_authority: list[str] = Field(default_factory=list)
    escalation_triggers: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MissionTeam(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("team"))
    mission_id: str
    name: str
    lead_agent_id: str | None = None
    member_agent_ids: list[str] = Field(default_factory=list)
    status: str = "forming"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AgentEmploymentContract(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("contract"))
    agent_id: str
    mission_id: str | None = None
    role_name: str
    title: str
    charter: str
    permission_profile: str
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    memory_access: list[str] = Field(default_factory=list)
    decision_authority: list[str] = Field(default_factory=list)
    escalation_triggers: list[str] = Field(default_factory=list)
    completion_criteria: list[str] = Field(default_factory=list)
    status: str = "active"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TeamTemplate(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("teamtpl"))
    name: str
    purpose: str
    domains: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    default_outputs: list[str] = Field(default_factory=list)
    escalation_policy: list[str] = Field(default_factory=list)
    status: str = "active"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DelegationRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("delegation"))
    mission_id: str
    from_agent_id: str | None = None
    to_agent_id: str | None = None
    from_role: str = "ceo"
    to_role: str
    title: str
    instructions: str
    success_criteria: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    status: DelegationStatus = "assigned"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class BoardBriefing(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("briefing"))
    mission_id: str
    title: str
    status: BoardBriefingStatus = "ready_for_chairman"
    participants: list[str] = Field(default_factory=list)
    executive_summary: str
    recommendations: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    decisions_needed: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class EscalationRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("escalation"))
    mission_id: str | None = None
    from_agent_id: str | None = None
    from_role: str = "system"
    to_level: EscalationLevel = "ceo"
    category: PermissionCategory | str = "change_strategy"
    reason: str
    options: list[dict[str, str]] = Field(default_factory=list)
    status: EscalationStatus = "pending"
    created_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None


class StandingOrder(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("order"))
    scope: StandingOrderScope = "global"
    instruction: str
    authority: str = "chairman"
    effect: str = "guidance"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CompletionContract(BaseModel):
    mission_id: str
    required_outputs_present: bool = False
    delegations_done: bool = False
    review_passed: bool = False
    no_pending_escalations: bool = False
    final_report_ready: bool = False
    memory_updated: bool = False
    no_open_questions: bool = False
    documents_registered: bool = False
    knowledge_updates_reviewed: bool = False
    workspace_scope_defined: bool = False
    can_close: bool = False
    blockers: list[str] = Field(default_factory=list)


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


class RunAttempt(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("attempt"))
    mission_id: str
    task_id: str | None = None
    run_id: str | None = None
    attempt: int = 1
    status: RunAttemptStatus = "preparing_workspace"
    executor: str | None = None
    workspace_path: str
    last_event: str | None = None
    last_message: str | None = None
    error: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    turn_count: int = 0
    started_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None


class MissionJob(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("job"))
    mission_id: str
    status: MissionJobStatus = "queued"
    error: str | None = None
    result: dict | None = None
    enqueued_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None


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
    current_stage: MissionStage = "intake"
    priority: str = "normal"
    domains: list[str] = Field(default_factory=list)
    summary: str | None = None
    requested_outputs: list[str] = Field(default_factory=list)
    client_id: str | None = None
    matter_id: str | None = None
    run_budget: MissionRunBudget = Field(default_factory=MissionRunBudget)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MissionStageTransition(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("stage"))
    mission_id: str
    stage: MissionStage
    actor: str = "praetor"
    reason: str
    status_snapshot: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ExecutiveCadence(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("cadence"))
    name: str
    cadence_type: str = "manual"
    description: str
    notification_threshold: NotificationThreshold = "approval_required"
    silent_if_clear: bool = True
    enabled: bool = True
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


class PlannerAction(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("action"))
    type: PlannerActionType
    status: PlannerActionStatus = "proposed"
    title: str
    body: str | None = None
    mission_id: str | None = None
    result_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlannerPlan(BaseModel):
    intent: str
    response: str
    actions: list[PlannerAction] = Field(default_factory=list)


class ConversationCreateResult(BaseModel):
    messages: list[ConversationMessage] = Field(default_factory=list)
    created_mission: MissionDefinition | None = None
    created_approval: ApprovalRequest | None = None
    agent_messages: list["AgentMessage"] = Field(default_factory=list)
    actions: list[PlannerAction] = Field(default_factory=list)
    intent: str = "briefing"


class OrganizationSnapshot(BaseModel):
    agent_roles: list[AgentRoleSpec] = Field(default_factory=list)
    agents: list[AgentInstance] = Field(default_factory=list)
    permission_profiles: list[AgentPermissionProfile] = Field(default_factory=list)
    agent_contracts: list[AgentEmploymentContract] = Field(default_factory=list)
    team_templates: list[TeamTemplate] = Field(default_factory=list)
    executive_cadences: list[ExecutiveCadence] = Field(default_factory=list)
    teams: list[MissionTeam] = Field(default_factory=list)
    delegations: list[DelegationRecord] = Field(default_factory=list)
    escalations: list[EscalationRecord] = Field(default_factory=list)
    standing_orders: list[StandingOrder] = Field(default_factory=list)
    skill_sources: list[SkillSource] = Field(default_factory=list)
    skill_registry: list[AgentSkillSpec] = Field(default_factory=list)


class AgentMessage(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("agentmsg"))
    mission_id: str
    role: AgentMessageRole
    body: str
    created_at: datetime = Field(default_factory=utc_now)
    task_id: str | None = None
    run_id: str | None = None


class WorkSessionTurn(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("turn"))
    turn_type: WorkSessionTurnType
    from_role: str
    to_role: str
    body: str
    status: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    task_id: str | None = None
    run_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkSession(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("worksession"))
    mission_id: str
    manager_role: str = "project_manager"
    executor_role: str = "developer"
    executor: str | None = None
    status: WorkSessionStatus = "open"
    current_blocker: str | None = None
    completion_contract: list[str] = Field(default_factory=list)
    turns: list[WorkSessionTurn] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class WorkTraceEvent(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("trace"))
    mission_id: str | None = None
    layer: WorkTraceLayer = "system"
    event_type: str
    title: str
    body: str | None = None
    actor: str = "praetor"
    status: str = "recorded"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ExecutorControlRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("execctl"))
    mission_id: str
    action: ExecutorControlAction
    requested_by: str = "chairman"
    target_session_id: str | None = None
    reason: str | None = None
    status: str = "requested"
    created_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None


class ClientRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("client"))
    name: str
    slug: str
    summary: str | None = None
    folder: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MatterRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("matter"))
    client_id: str
    mission_id: str | None = None
    title: str
    slug: str
    status: MatterStatus = "open"
    folder: str
    brief_path: str
    decisions_path: str
    open_questions_path: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class DocumentVersion(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("docver"))
    version: int
    path: str
    label: str
    reason: str
    source_ids: list[str] = Field(default_factory=list)
    created_by: str = "praetor"
    created_at: datetime = Field(default_factory=utc_now)


class DocumentRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("doc"))
    matter_id: str
    client_id: str
    mission_id: str | None = None
    title: str
    document_type: str = "working_document"
    status: DocumentStatus = "draft"
    current_version: int = 1
    versions: list[DocumentVersion] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class MatterDecisionRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("matterdecision"))
    matter_id: str
    client_id: str
    mission_id: str | None = None
    summary: str
    rationale: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    status: DecisionStatus = "confirmed"
    created_by: str = "praetor"
    created_at: datetime = Field(default_factory=utc_now)


class OpenQuestionRecord(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("question"))
    matter_id: str
    client_id: str
    mission_id: str | None = None
    question: str
    owner: str = "chairman"
    blocking: str | None = None
    status: OpenQuestionStatus = "open"
    asked_at: datetime = Field(default_factory=utc_now)
    answered_at: datetime | None = None


class KnowledgeUpdate(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("knowledge"))
    matter_id: str | None = None
    client_id: str | None = None
    mission_id: str | None = None
    target_page: str = "CEO Memory.md"
    summary: str
    content: str
    source_ids: list[str] = Field(default_factory=list)
    status: KnowledgeUpdateStatus = "proposed"
    created_at: datetime = Field(default_factory=utc_now)
    applied_at: datetime | None = None


class KnowledgeSnapshot(BaseModel):
    clients: list[ClientRecord] = Field(default_factory=list)
    matters: list[MatterRecord] = Field(default_factory=list)
    documents: list[DocumentRecord] = Field(default_factory=list)
    decisions: list[MatterDecisionRecord] = Field(default_factory=list)
    open_questions: list[OpenQuestionRecord] = Field(default_factory=list)
    knowledge_updates: list[KnowledgeUpdate] = Field(default_factory=list)


class PromotionFinding(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("finding"))
    type: PromotionFindingType
    summary: str
    disposition: str = "review"
    target: str | None = None
    source_ids: list[str] = Field(default_factory=list)
    rationale: str | None = None


class MemoryPromotionReview(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("promotion"))
    mission_id: str
    matter_id: str | None = None
    client_id: str | None = None
    status: PromotionReviewStatus = "ready_for_review"
    summary: str
    findings: list[PromotionFinding] = Field(default_factory=list)
    proposed_knowledge_update_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class WorkflowContract(BaseModel):
    path: str = "PRAETOR_WORKFLOW.md"
    version: str = "1"
    title: str = "Praetor workflow"
    body: str
    default_completion_contract: list[str] = Field(default_factory=list)
    approval_policy: dict[str, Any] = Field(default_factory=dict)
    workspace_policy: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=utc_now)


class ChairmanInboxItem(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("inbox"))
    title: str
    body: str
    severity: InboxSeverity = "medium"
    status: InboxStatus = "open"
    kind: str = "governance"
    href: str = "/app/inbox"
    source: str = "governance_review"
    mission_id: str | None = None
    matter_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceReview(BaseModel):
    id: str = Field(default_factory=lambda: generate_id("review"))
    status: str = "completed"
    policy: ReviewPolicy = Field(default_factory=ReviewPolicy)
    summary: str = "No formal issues require owner attention."
    items: list[ChairmanInboxItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    next_review_hint: str = "Review again when the chairman opens Praetor."


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
    recent_planner_actions: list[PlannerAction] = Field(default_factory=list)
    runtime_health: dict[str, Any] = Field(default_factory=dict)
    organization: OrganizationSnapshot = Field(default_factory=OrganizationSnapshot)
    governance_review: GovernanceReview | None = None


class TelegramIntegrationSettings(BaseModel):
    enabled: bool = False
    bot_token_set: bool = False
    webhook_secret_set: bool = False
    allowed_user_id: int | None = None
    linked_chat_id: int | None = None
    linked_user_id: int | None = None
    linked_username: str | None = None
    notify_approvals: bool = True
    allow_low_risk_approval: bool = True
    pairing_code_hash: str | None = None
    pairing_code_expires_at: datetime | None = None
    linked_at: datetime | None = None


class AppSettings(BaseModel):
    owner: OwnerProfile
    runtime: RuntimeSelection
    workspace: WorkspaceConfig
    governance: GovernancePolicy
    review_policy: ReviewPolicy = Field(default_factory=ReviewPolicy)
    company_dna: CompanyDNA
    roles: list[RoleDefinition] = Field(default_factory=list)
    telegram: TelegramIntegrationSettings = Field(default_factory=TelegramIntegrationSettings)
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
