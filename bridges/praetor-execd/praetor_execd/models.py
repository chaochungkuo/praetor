from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


NormalizedStatus = Literal[
    "completed",
    "paused_budget",
    "paused_decision",
    "paused_risk",
    "auth_required",
    "interactive_approval_required",
    "cancelled",
    "failed_transient",
    "failed_permanent",
]

InternalRunStatus = Literal[
    "accepted",
    "validating",
    "queued",
    "starting",
    "running",
    "collecting",
    "normalizing",
    "completed",
    "paused_budget",
    "paused_decision",
    "paused_risk",
    "auth_required",
    "interactive_approval_required",
    "cancelled",
    "failed_transient",
    "failed_permanent",
]

ExecutorName = Literal["codex", "claude_code"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EnvelopeError(BaseModel):
    code: str
    message: str


class ApiEnvelope(BaseModel):
    ok: bool
    data: Any = None
    error: EnvelopeError | None = None


class PathMapping(BaseModel):
    container_workspace_root: str
    host_workspace_root: str
    target_workdir: str


class ApprovalPolicy(BaseModel):
    allow_destructive_write: bool
    allow_shell: bool


class TaskSpec(BaseModel):
    title: str
    instructions: str
    input_files: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    approval_policy: ApprovalPolicy


class CreateRunRequest(BaseModel):
    request_id: str
    mission_id: str
    task_id: str
    executor: ExecutorName
    timeout_seconds: int = Field(gt=0)
    path_mapping: PathMapping
    task_spec: TaskSpec


class UsageSummary(BaseModel):
    duration_ms: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: float | None = None
    usage_available: bool = False


class RunEvent(BaseModel):
    seq: int
    type: str
    ts: datetime = Field(default_factory=utc_now)
    run_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class RunRecord(BaseModel):
    run_id: str
    request_id: str
    mission_id: str
    task_id: str
    executor: ExecutorName
    status: InternalRunStatus
    normalized_status: NormalizedStatus | None = None
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


class HealthData(BaseModel):
    status: Literal["healthy", "degraded", "unavailable"]
    version: str
    uptime_seconds: float
    configured_executors: list[str]


class ExecutorSummary(BaseModel):
    name: ExecutorName
    enabled: bool
    binary_found: bool
    login_state: Literal["authenticated", "unknown", "not_detected"]
    supports_noninteractive_batch: bool
    supports_cancel: bool


class CreateRunAccepted(BaseModel):
    run_id: str
    status: str
    executor: ExecutorName


class RunEventsPage(BaseModel):
    events: list[RunEvent]
    next_seq: int


class CancelRunResult(BaseModel):
    run_id: str
    status: str
    accepted: bool


TERMINAL_NORMALIZED_STATUSES = {
    "completed",
    "paused_budget",
    "paused_decision",
    "paused_risk",
    "auth_required",
    "interactive_approval_required",
    "cancelled",
    "failed_transient",
    "failed_permanent",
}
