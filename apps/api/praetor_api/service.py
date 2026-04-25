from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .auth import hash_password, validate_password_strength, verify_password
from .models import (
    AppSettings,
    ApprovalCreateRequest,
    ApprovalRequest,
    LoginRequest,
    MeetingRecord,
    MissionContinueRequest,
    MissionCreateRequest,
    MissionDefinition,
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
