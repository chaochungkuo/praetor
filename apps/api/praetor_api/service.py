from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .auth import hash_password, validate_password_strength, verify_password
from .models import (
    AgentMessage,
    AppSettings,
    ApprovalCreateRequest,
    ApprovalRequest,
    ConversationCreateRequest,
    ConversationMessage,
    ConversationCreateResult,
    LoginRequest,
    MeetingRecord,
    MissionContinueRequest,
    MissionCreateRequest,
    MissionDefinition,
    MissionTimelineEvent,
    OfficeSnapshot,
    MissionPauseRequest,
    MissionStopRequest,
    OnboardingAnswers,
    OwnerAuthRecord,
    PraetorBriefing,
    RoleDefinition,
    RuntimeSelection,
    TaskDefinition,
    WorkspaceConfig,
    WorkspacePermissions,
    utc_now,
)
from .recommendations import assess_mission_complexity, preview_onboarding
from .runtime import MissionRuntime
from .storage import AppStorage
from .workspace import bootstrap_workspace


def parse_datetime(value: str | None) -> datetime:
    if not value:
        return utc_now()
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass
class PraetorService:
    storage: AppStorage

    def preview_onboarding(self, answers: OnboardingAnswers):
        return preview_onboarding(answers)

    def complete_onboarding(self, answers: OnboardingAnswers) -> AppSettings:
        if self.get_settings() is not None:
            raise RuntimeError("Praetor is already initialized.")
        if not answers.owner_password:
            raise RuntimeError("Owner password is required to initialize Praetor.")
        validate_password_strength(answers.owner_password)
        preview = self.preview_onboarding(answers)
        workspace_root = Path(answers.workspace_root).expanduser()
        bootstrap_workspace(workspace_root)
        settings = AppSettings(
            owner={
                "name": answers.owner_name,
                "email": answers.owner_email,
                "preferred_language": answers.language,
            },
            runtime=preview.runtime,
            workspace=WorkspaceConfig(
                root=str(workspace_root),
                permissions=WorkspacePermissions(
                    allow_read=[str(workspace_root)],
                    allow_write=[
                        str(workspace_root / "Projects"),
                        str(workspace_root / "Wiki"),
                        str(workspace_root / "Decisions"),
                        str(workspace_root / "Missions"),
                    ],
                    deny_write=[
                        str(workspace_root / "Archive"),
                        str(workspace_root / "Finance" / "Locked"),
                    ],
                ),
            ),
            governance=preview.governance,
            company_dna=preview.company_dna,
            roles=preview.suggested_roles,
        )
        self.storage.save_settings(settings)
        self.storage.save_auth(
            OwnerAuthRecord(
                password_hash=hash_password(answers.owner_password),
            )
        )
        self._audit(
            "onboarding_completed",
            {
                "owner": settings.owner.name,
                "workspace_root": settings.workspace.root,
                "runtime_mode": settings.runtime.mode,
            },
        )
        return settings

    def has_owner_auth(self) -> bool:
        return self.storage.load_auth() is not None

    def authenticate_owner(self, payload: LoginRequest) -> AppSettings:
        settings = self._require_settings()
        auth_record = self.storage.load_auth()
        if auth_record is None:
            raise RuntimeError("Owner auth is not configured.")
        if not verify_password(payload.password, auth_record.password_hash):
            raise ValueError("Invalid password.")
        auth_record.last_login_at = utc_now()
        auth_record.updated_at = utc_now()
        self.storage.save_auth(auth_record)
        self._audit("owner_login", {"owner": settings.owner.name})
        return settings

    def get_settings(self) -> AppSettings | None:
        return self.storage.load_settings()

    def create_mission(self, request: MissionCreateRequest) -> MissionDefinition:
        settings = self._require_settings()
        complexity_score, pm_required, escalation_reason = assess_mission_complexity(request)
        mission = MissionDefinition(
            title=request.title,
            summary=request.summary,
            domains=request.domains,
            priority=request.priority,
            requested_outputs=request.requested_outputs,
            manager_layer="pm_auto" if pm_required else "praetor_direct",
            pm_required=pm_required,
            complexity_score=complexity_score,
            escalation_reason=escalation_reason,
            status="planned",
        )
        self.storage.save_mission(Path(settings.workspace.root), mission)
        if mission.pm_required:
            self.storage.append_pm_report(
                Path(settings.workspace.root),
                mission.id,
                "\n".join(
                    [
                        f"Complexity score: {mission.complexity_score}",
                        f"Escalation reason: {mission.escalation_reason or 'none'}",
                        "PM owner created for mission-scoped context.",
                    ]
                ),
            )
        self._audit(
            "mission_created",
            {
                "mission_id": mission.id,
                "title": mission.title,
                "priority": mission.priority,
                "complexity_score": mission.complexity_score,
                "pm_required": mission.pm_required,
            },
        )
        self.storage.append_agent_message(
            AgentMessage(
                mission_id=mission.id,
                role="ceo",
                body=f"Mission created and assigned to {mission.manager_layer}: {mission.title}",
            )
        )
        if mission.pm_required:
            self.storage.append_agent_message(
                AgentMessage(
                    mission_id=mission.id,
                    role="project_manager",
                    body=(
                        "I will break this mission into execution work, monitor risk, "
                        "and report back to Praetor before escalation."
                    ),
                )
            )
        return mission

    def list_missions(self) -> list[MissionDefinition]:
        settings = self._require_settings()
        return self.storage.list_missions(Path(settings.workspace.root))

    def get_mission(self, mission_id: str) -> MissionDefinition:
        settings = self._require_settings()
        mission = self.storage.load_mission(Path(settings.workspace.root), mission_id)
        if mission is None:
            raise KeyError(mission_id)
        return mission

    def list_mission_tasks(self, mission_id: str) -> list[TaskDefinition]:
        settings = self._require_settings()
        return self.storage.list_tasks(Path(settings.workspace.root), mission_id)

    def read_mission_texts(self, mission_id: str) -> dict[str, str]:
        settings = self._require_settings()
        return self.storage.read_mission_texts(Path(settings.workspace.root), mission_id)

    def list_mission_runs(self, mission_id: str) -> list[dict]:
        settings = self._require_settings()
        return self.storage.list_bridge_runs(Path(settings.workspace.root), mission_id)

    def list_audit_events(self, limit: int = 20) -> list[dict]:
        return self.storage.list_audit_events(limit=limit)

    def list_approvals(self, status: str | None = None) -> list[ApprovalRequest]:
        items = self.storage.list_approvals()
        if status is not None:
            items = [item for item in items if item.status == status]
        return items

    def list_recent_runs(self, limit: int = 25) -> list[dict]:
        settings = self._require_settings()
        return self.storage.list_recent_runs(Path(settings.workspace.root), limit=limit)

    def list_wiki_pages(self) -> list[dict[str, str]]:
        settings = self._require_settings()
        return self.storage.list_wiki_pages(Path(settings.workspace.root))

    def list_meetings(self, mission_id: str | None = None) -> list[MeetingRecord]:
        settings = self._require_settings()
        return self.storage.list_meetings(Path(settings.workspace.root), mission_id=mission_id)

    def list_decision_items(self) -> list[dict[str, str]]:
        settings = self._require_settings()
        workspace_root = Path(settings.workspace.root)
        items: list[dict[str, str]] = []
        for mission in self.storage.list_missions(workspace_root):
            texts = self.storage.read_mission_texts(workspace_root, mission.id)
            for line in texts.get("DECISIONS.md", "").splitlines():
                stripped = line.strip()
                if stripped.startswith("- "):
                    items.append(
                        {
                            "mission_id": mission.id,
                            "mission_title": mission.title,
                            "text": stripped[2:],
                        }
                    )
        return items

    def usage_summary(self) -> dict[str, Any]:
        runs = self.list_recent_runs(limit=100)
        grouped: dict[str, dict[str, Any]] = {}
        for run in runs:
            key = run.get("executor") or "unknown"
            usage = run.get("usage") or {}
            bucket = grouped.setdefault(
                key,
                {
                    "executor": key,
                    "runs": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "estimated_cost": 0.0,
                },
            )
            bucket["runs"] += 1
            bucket["input_tokens"] += usage.get("input_tokens") or 0
            bucket["output_tokens"] += usage.get("output_tokens") or 0
            bucket["estimated_cost"] += usage.get("estimated_cost") or 0.0
        return {"runs": runs[:25], "by_executor": list(grouped.values())}

    def create_review_meeting(self, mission_id: str) -> MeetingRecord:
        mission = self.get_mission(mission_id)
        tasks = self.list_mission_tasks(mission_id)
        runs = self.list_mission_runs(mission_id)
        texts = self.read_mission_texts(mission_id)
        latest_run = runs[0] if runs else {}
        meeting = MeetingRecord(
            mission_id=mission_id,
            type="project_review",
            participants=["Praetor", "Project Execution", "Reviewer"],
            agenda=[
                "current status",
                "latest execution result",
                "risks and missing items",
                "next recommended step",
            ],
            outputs=[
                f"Mission status: {mission.status}",
                f"Task count: {len(tasks)}",
                f"Latest run executor: {latest_run.get('executor', 'none')}",
                f"Latest run status: {latest_run.get('normalized_status', 'none')}",
                f"Report excerpt: {texts.get('REPORT.md', '').splitlines()[-1] if texts.get('REPORT.md') else 'none'}",
            ],
        )
        self.storage.save_meeting(Path(self._require_settings().workspace.root), meeting)
        self.storage.append_pm_report(
            Path(self._require_settings().workspace.root),
            mission_id,
            "\n".join(
                [
                    f"Meeting created: {meeting.id}",
                    *meeting.outputs,
                ]
            ),
        )
        self._audit("meeting_created", {"meeting_id": meeting.id, "mission_id": mission_id, "type": meeting.type})
        return meeting

    def resolve_approval(self, approval_id: str, status: str) -> ApprovalRequest:
        for approval in self.storage.list_approvals():
            if approval.id == approval_id:
                approval.status = status
                self.storage.save_approval(approval)
                self._audit("approval_resolved", {"approval_id": approval.id, "status": status})
                return approval
        raise KeyError(approval_id)

    def create_approval(self, request: ApprovalCreateRequest) -> ApprovalRequest:
        approval = ApprovalRequest(
            mission_id=request.mission_id,
            category=request.category,
            raised_by="owner",
            reason=request.reason,
        )
        self.storage.save_approval(approval)
        self._audit("approval_created", {"approval_id": approval.id, "mission_id": request.mission_id})
        return approval

    def pause_mission(self, mission_id: str, _: MissionPauseRequest) -> MissionDefinition:
        mission = self.get_mission(mission_id)
        mission.status = "paused"
        mission.updated_at = utc_now()
        self.storage.save_mission(Path(self._require_settings().workspace.root), mission)
        self._audit("mission_paused", {"mission_id": mission.id, "status": mission.status})
        return mission

    def continue_mission(self, mission_id: str, _: MissionContinueRequest) -> MissionDefinition:
        mission = self.get_mission(mission_id)
        mission.status = "resumed"
        mission.updated_at = utc_now()
        self.storage.save_mission(Path(self._require_settings().workspace.root), mission)
        self._audit("mission_resumed", {"mission_id": mission.id, "status": mission.status})
        return mission

    def stop_mission(self, mission_id: str, _: MissionStopRequest) -> MissionDefinition:
        mission = self.get_mission(mission_id)
        mission.status = "archived"
        mission.updated_at = utc_now()
        self.storage.save_mission(Path(self._require_settings().workspace.root), mission)
        self._audit("mission_stopped", {"mission_id": mission.id, "status": mission.status})
        return mission

    def praetor_briefing(self) -> PraetorBriefing:
        missions = self.list_missions()
        active = [mission for mission in missions if mission.status in {"active", "resumed", "review"}]
        paused = [mission for mission in missions if mission.status == "paused"]
        approvals_pending = len(
            [mission for mission in missions if mission.status == "waiting_approval"]
        )
        return PraetorBriefing(
            active_missions=len(active),
            paused_missions=len(paused),
            approvals_pending=approvals_pending,
            recent_missions=missions[:5],
        )

    def run_mission(self, mission_id: str) -> dict:
        settings = self._require_settings()
        mission = self.get_mission(mission_id)
        runtime_engine = MissionRuntime()

        mission.status = "active"
        mission.updated_at = utc_now()
        workspace_root = Path(settings.workspace.root)
        self.storage.save_mission(workspace_root, mission)

        primary_result = runtime_engine.run_mission(
            workspace_root=workspace_root,
            mission=mission,
            runtime=settings.runtime,
            permissions=settings.workspace.permissions,
        )
        self.storage.save_task(workspace_root, primary_result.task)
        self.storage.save_bridge_run(workspace_root, mission.id, primary_result.run_record.model_dump(mode="json"))
        self.storage.append_agent_message(
            AgentMessage(
                mission_id=mission.id,
                role="developer",
                task_id=primary_result.task.id,
                run_id=primary_result.run_record.run_id,
                body=(
                    f"Execution finished with status {primary_result.run_record.normalized_status}. "
                    f"Changed files: {', '.join(primary_result.run_record.changed_files) or 'none'}."
                ),
            )
        )

        final_result = primary_result
        fallback_runtime = self._fallback_runtime(settings.runtime)
        if self._should_fallback(primary_result.run_record.normalized_status) and fallback_runtime is not None:
            fallback_health = runtime_engine.probe(fallback_runtime)
            if fallback_health.get("healthy"):
                self._audit(
                    "mission_run_fallback_started",
                    {
                        "mission_id": mission.id,
                        "from_runtime": settings.runtime.mode,
                        "to_runtime": fallback_runtime.mode,
                        "from_executor": primary_result.run_record.executor,
                    },
                )
                fallback_result = runtime_engine.run_mission(
                    workspace_root=workspace_root,
                    mission=mission,
                    runtime=fallback_runtime,
                    permissions=settings.workspace.permissions,
                )
                self.storage.save_task(workspace_root, fallback_result.task)
                self.storage.save_bridge_run(
                    workspace_root,
                    mission.id,
                    fallback_result.run_record.model_dump(mode="json"),
                )
                self.storage.append_agent_message(
                    AgentMessage(
                        mission_id=mission.id,
                        role="developer",
                        task_id=fallback_result.task.id,
                        run_id=fallback_result.run_record.run_id,
                        body=(
                            f"Fallback execution finished with status {fallback_result.run_record.normalized_status}. "
                            f"Changed files: {', '.join(fallback_result.run_record.changed_files) or 'none'}."
                        ),
                    )
                )
                final_result = fallback_result

        final_status = final_result.run_record.normalized_status
        mission.status = self._mission_status_from_bridge(final_status)
        mission.updated_at = utc_now()
        self.storage.save_mission(workspace_root, mission)
        self.storage.append_report(
            workspace_root,
            mission.id,
            "\n".join(
                [
                    f"Run status: {final_status}",
                    f"Executor: {final_result.run_record.executor}",
                    f"Changed files: {', '.join(final_result.run_record.changed_files) or 'none'}",
                    f"Summary: {final_result.run_record.stdout_tail or ''}",
                ]
            ),
        )
        if mission.pm_required:
            self.storage.append_pm_report(
                workspace_root,
                mission.id,
                "\n".join(
                    [
                        f"Escalated to Praetor after run status: {final_status}",
                        f"Executor used: {final_result.run_record.executor}",
                        f"Changed files: {', '.join(final_result.run_record.changed_files) or 'none'}",
                    ]
                ),
            )
            self.storage.append_agent_message(
                AgentMessage(
                    mission_id=mission.id,
                    role="project_manager",
                    task_id=final_result.task.id,
                    run_id=final_result.run_record.run_id,
                    body=(
                        f"Reviewing final run status {final_status}. "
                        f"Owner-visible report has been updated."
                    ),
                )
            )
        self._audit(
            "mission_run_finished",
            {
                "mission_id": mission.id,
                "task_id": final_result.task.id,
                "status": mission.status,
                "executor": final_result.task.current_executor,
                "run_status": final_status,
                "usage": final_result.run_record.usage.model_dump(mode="json"),
            },
        )
        if final_status in {"paused_budget", "paused_decision", "paused_risk", "interactive_approval_required", "auth_required"}:
            approval = ApprovalRequest(
                category=self._approval_category_from_status(final_status),
                mission_id=mission.id,
                raised_by="praetor",
                reason=final_result.run_record.pause_reason or f"Run stopped with status: {final_status}",
            )
            self.storage.save_approval(approval)
            self._audit(
                "approval_requested",
                {"approval_id": approval.id, "mission_id": mission.id, "category": approval.category},
            )
        return {
            "mission": mission,
            "task": final_result.task,
            "bridge_run": final_result.run_record,
        }

    def office_snapshot(self) -> OfficeSnapshot:
        settings = self._require_settings()
        missions = self.storage.list_missions(Path(settings.workspace.root))
        recent_runs = self.storage.list_recent_runs(Path(settings.workspace.root), limit=12)
        audit_events = self.storage.list_audit_events(limit=12)
        approvals = self.storage.list_approvals()
        pending_approvals = [item for item in approvals if item.status == "pending"]
        return OfficeSnapshot(
            briefing=self.praetor_briefing(),
            missions=missions[:12],
            approvals=pending_approvals,
            recent_runs=recent_runs,
            audit_events=audit_events,
            ceo_thread=self.storage.list_conversation_messages(limit=30),
            agent_activity=self._recent_agent_activity(limit=30),
            runtime_health=self.runtime_health(),
        )

    def create_ceo_message(self, request: ConversationCreateRequest) -> ConversationCreateResult:
        settings = self._require_settings()
        text = request.body.strip()
        if not text:
            raise ValueError("Message body is required.")
        intent = self._infer_ceo_intent(text)
        created_mission: MissionDefinition | None = None
        agent_messages: list[AgentMessage] = []

        chairman = ConversationMessage(
            role="chairman",
            body=text,
            related_mission_id=request.related_mission_id,
        )
        related_mission_id = request.related_mission_id
        if intent == "create_mission":
            created_mission = self._create_mission_from_ceo_instruction(text)
            related_mission_id = created_mission.id
            chairman.related_mission_id = created_mission.id
            agent_messages = self._seed_agent_thread_for_ceo_mission(created_mission, text)

        response = ConversationMessage(
            role="ceo",
            body=self._ceo_response(
                text,
                intent=intent,
                created_mission=created_mission,
                mission_count=len(self.storage.list_missions(Path(settings.workspace.root))),
                pending_approvals=len([item for item in self.storage.list_approvals() if item.status == "pending"]),
            ),
            related_mission_id=related_mission_id,
        )
        self.storage.append_conversation_message(chairman)
        self.storage.append_conversation_message(response)
        self._audit(
            "ceo_conversation_message",
            {
                "message_id": chairman.id,
                "related_mission_id": related_mission_id,
                "intent": intent,
                "created_mission_id": created_mission.id if created_mission else None,
            },
        )
        return ConversationCreateResult(
            messages=[chairman, response],
            created_mission=created_mission,
            agent_messages=agent_messages,
            intent=intent,
        )

    def list_ceo_messages(self, limit: int = 50) -> list[ConversationMessage]:
        self._require_settings()
        return self.storage.list_conversation_messages(limit=limit)

    def mission_timeline(self, mission_id: str) -> list[MissionTimelineEvent]:
        settings = self._require_settings()
        workspace_root = Path(settings.workspace.root)
        mission = self.storage.load_mission(workspace_root, mission_id)
        if mission is None:
            raise KeyError(mission_id)
        events: list[MissionTimelineEvent] = [
            MissionTimelineEvent(
                id=f"mission_created_{mission.id}",
                mission_id=mission.id,
                type="mission",
                title="Mission created",
                body=mission.summary,
                actor="ceo",
                status=mission.status,
                created_at=mission.created_at,
            )
        ]
        for task in self.storage.list_tasks(workspace_root, mission_id):
            events.append(
                MissionTimelineEvent(
                    id=f"task_{task.id}",
                    mission_id=mission_id,
                    type="task",
                    title=task.title,
                    body=f"Executor: {task.current_executor or 'n/a'}",
                    actor=task.role_owner,
                    status=task.status,
                    created_at=mission.updated_at,
                    metadata={"task_id": task.id},
                )
            )
        for run in self.storage.list_bridge_runs(workspace_root, mission_id):
            usage = run.get("usage") or {}
            events.append(
                MissionTimelineEvent(
                    id=f"run_{run.get('run_id', 'unknown')}",
                    mission_id=mission_id,
                    type="run",
                    title=f"Run {run.get('normalized_status') or run.get('status')}",
                    body=run.get("stdout_tail") or run.get("stderr_tail") or run.get("pause_reason"),
                    actor=run.get("executor") or "executor",
                    status=run.get("normalized_status") or run.get("status"),
                    created_at=parse_datetime(run.get("finished_at") or run.get("started_at")),
                    metadata={
                        "run_id": run.get("run_id"),
                        "changed_files": run.get("changed_files") or [],
                        "usage": usage,
                    },
                )
            )
        for message in self.storage.list_agent_messages(mission_id=mission_id, limit=100):
            events.append(
                MissionTimelineEvent(
                    id=message.id,
                    mission_id=mission_id,
                    type="agent_message",
                    title=message.role.replace("_", " ").title(),
                    body=message.body,
                    actor=message.role,
                    created_at=message.created_at,
                    metadata={"task_id": message.task_id, "run_id": message.run_id},
                )
            )
        for approval in self.storage.list_approvals():
            if approval.mission_id == mission_id:
                events.append(
                    MissionTimelineEvent(
                        id=approval.id,
                        mission_id=mission_id,
                        type="approval",
                        title=f"Approval: {approval.category}",
                        body=approval.reason,
                        actor=approval.raised_by,
                        status=approval.status,
                        created_at=approval.created_at,
                    )
                )
        events.sort(key=lambda item: item.created_at)
        return events

    def mission_agent_messages(self, mission_id: str, limit: int = 100) -> list[AgentMessage]:
        settings = self._require_settings()
        if self.storage.load_mission(Path(settings.workspace.root), mission_id) is None:
            raise KeyError(mission_id)
        return self.storage.list_agent_messages(mission_id=mission_id, limit=limit)

    def _create_mission_from_ceo_instruction(self, text: str) -> MissionDefinition:
        title, summary = self._mission_fields_from_instruction(text)
        request = MissionCreateRequest(
            title=title,
            summary=summary,
            domains=self._domains_from_instruction(text),
            priority=self._priority_from_instruction(text),
            requested_outputs=[],
        )
        return self.create_mission(request)

    def _seed_agent_thread_for_ceo_mission(self, mission: MissionDefinition, instruction: str) -> list[AgentMessage]:
        messages = [
            AgentMessage(
                mission_id=mission.id,
                role="ceo",
                body=f"Chairman instruction accepted. Strategic intent: {instruction}",
            ),
            AgentMessage(
                mission_id=mission.id,
                role="project_manager",
                body=(
                    "I will convert the chairman's instruction into an execution plan, identify required outputs, "
                    "and keep decision boundaries visible."
                ),
            ),
            AgentMessage(
                mission_id=mission.id,
                role="developer",
                body="I am standing by for a scoped implementation task and will report changed files and blockers.",
            ),
            AgentMessage(
                mission_id=mission.id,
                role="reviewer",
                body="I will review outputs against mission intent, safety boundaries, and completion criteria.",
            ),
        ]
        for message in messages:
            self.storage.append_agent_message(message)
        return messages

    def _recent_agent_activity(self, limit: int = 30) -> list[MissionTimelineEvent]:
        events: list[MissionTimelineEvent] = []
        for message in self.storage.list_agent_messages(limit=limit):
            events.append(
                MissionTimelineEvent(
                    id=message.id,
                    mission_id=message.mission_id,
                    type="agent_message",
                    title=message.role.replace("_", " ").title(),
                    body=message.body,
                    actor=message.role,
                    created_at=message.created_at,
                    metadata={"task_id": message.task_id, "run_id": message.run_id},
                )
            )
        events.sort(key=lambda item: item.created_at, reverse=True)
        return events[:limit]

    @staticmethod
    def _infer_ceo_intent(text: str) -> str:
        lowered = text.lower()
        if any(word in lowered for word in ["create", "建立", "新增", "任務", "mission"]):
            return "create_mission"
        if any(word in lowered for word in ["status", "進度", "狀態", "卡住"]):
            return "status_briefing"
        if any(word in lowered for word in ["risk", "安全", "風險", "privacy"]):
            return "risk_review"
        return "briefing"

    @staticmethod
    def _ceo_response(
        text: str,
        *,
        intent: str,
        created_mission: MissionDefinition | None,
        mission_count: int,
        pending_approvals: int,
    ) -> str:
        if intent == "create_mission" and created_mission is not None:
            return (
                f"我已把你的指令建立成 mission：{created_mission.title}。"
                "我會先讓 PM 拆解工作，Developer 等待具體執行範圍，Reviewer 會負責檢查輸出與風險。"
            )
        if intent == "status_briefing":
            return (
                f"目前共有 {mission_count} 個 mission，待你批准的事項有 {pending_approvals} 個。"
                "我會持續把卡點、風險與需要董事長判斷的事項浮到右側決策欄。"
            )
        if intent == "risk_review":
            return "我會優先檢查資料邊界、執行權限、外部 provider 暴露面與需要人工批准的動作。"
        _ = text
        return "收到。我會把這段指示納入公司脈絡，整理成可執行的下一步，並在需要決策時回到你這裡。"

    @staticmethod
    def _mission_fields_from_instruction(text: str) -> tuple[str, str]:
        cleaned = text.strip()
        for marker in ["建立任務", "新增任務", "create mission", "Create mission", "mission:"]:
            cleaned = cleaned.replace(marker, "")
        cleaned = cleaned.lstrip("：: -").strip()
        if not cleaned:
            cleaned = "Chairman-directed mission"
        title = cleaned.splitlines()[0][:90]
        summary = cleaned if len(cleaned) > len(title) else f"Chairman instruction: {cleaned}"
        return title, summary

    @staticmethod
    def _domains_from_instruction(text: str) -> list[str]:
        lowered = text.lower()
        domains = []
        if any(word in lowered for word in ["code", "developer", "開發", "程式", "ui", "frontend", "backend"]):
            domains.append("development")
        if any(word in lowered for word in ["finance", "cost", "成本", "財務"]):
            domains.append("finance")
        if any(word in lowered for word in ["operation", "ops", "流程", "營運"]):
            domains.append("operations")
        return domains or ["operations"]

    @staticmethod
    def _priority_from_instruction(text: str) -> str:
        lowered = text.lower()
        if any(word in lowered for word in ["urgent", "critical", "緊急", "重要", "立刻"]):
            return "critical"
        if any(word in lowered for word in ["high", "優先"]):
            return "high"
        return "normal"

    def runtime_health(self) -> dict:
        runtime = MissionRuntime()
        return runtime.probe(self._require_settings().runtime)

    def export_schemas(self, output_dir: Path) -> list[Path]:
        from .schemas import export_json_schemas

        return export_json_schemas(output_dir)

    @staticmethod
    def _mission_status_from_bridge(normalized_status: str | None) -> str:
        if normalized_status == "completed":
            return "completed"
        if normalized_status in {"paused_budget", "paused_decision", "paused_risk", "interactive_approval_required"}:
            return "waiting_approval"
        if normalized_status == "auth_required":
            return "paused"
        return "failed"

    def _require_settings(self) -> AppSettings:
        settings = self.storage.load_settings()
        if settings is None:
            raise RuntimeError("Praetor is not initialized. Complete onboarding first.")
        return settings

    @staticmethod
    def _should_fallback(normalized_status: str | None) -> bool:
        return normalized_status in {"failed_permanent", "failed_transient", "auth_required"}

    @staticmethod
    def _fallback_runtime(runtime: RuntimeSelection) -> RuntimeSelection | None:
        if runtime.mode == "api" and runtime.executor:
            return RuntimeSelection(mode="subscription_executor", executor=runtime.executor)
        if runtime.mode == "subscription_executor" and runtime.provider:
            return RuntimeSelection(mode="api", provider=runtime.provider, model=runtime.model)
        return None

    @staticmethod
    def _approval_category_from_status(status: str) -> str:
        mapping = {
            "paused_budget": "spending_money",
            "paused_decision": "change_strategy",
            "paused_risk": "overwrite_important_files",
            "interactive_approval_required": "shell_commands",
            "auth_required": "shell_commands",
        }
        return mapping.get(status, "change_strategy")

    def _audit(self, event_type: str, payload: dict[str, Any]) -> None:
        self.storage.append_audit_event(
            {
                "ts": utc_now().isoformat().replace("+00:00", "Z"),
                "type": event_type,
                "payload": payload,
            }
        )
