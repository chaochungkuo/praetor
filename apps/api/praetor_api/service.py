from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .auth import hash_password, validate_password_strength, verify_password
from .models import (
    AgentMessage,
    AgentInstance,
    AgentRoleSpec,
    AppSettings,
    ApprovalCreateRequest,
    ApprovalRequest,
    CompletionContract,
    ConversationCreateRequest,
    ConversationMessage,
    ConversationCreateResult,
    DelegationRecord,
    EscalationRecord,
    LoginRequest,
    MeetingRecord,
    MissionContinueRequest,
    MissionCreateRequest,
    MissionDefinition,
    MissionTeam,
    MissionTimelineEvent,
    OfficeSnapshot,
    OrganizationSnapshot,
    MissionPauseRequest,
    MissionStopRequest,
    OnboardingAnswers,
    OwnerAuthRecord,
    PlannerAction,
    PraetorBriefing,
    RoleDefinition,
    RuntimeSelection,
    StandingOrder,
    TaskDefinition,
    TelegramIntegrationSettings,
    WorkspaceConfig,
    WorkspacePermissions,
    utc_now,
)
from .planner import CEOPlanner, CEOPlannerContext, default_ceo_planner
from .providers import test_provider_connection
from .recommendations import assess_mission_complexity, preview_onboarding
from .runtime import MissionRuntime
from .safety_policy import append_safety_policy, build_prompt_safety_policy, contains_sensitive_material
from .storage import AppStorage
from .telegram import generate_pairing_code, new_pairing_settings, process_update, send_approval_notification
from .workspace import bootstrap_workspace


def parse_datetime(value: str | None) -> datetime:
    if not value:
        return utc_now()
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass
class PraetorService:
    storage: AppStorage
    planner: CEOPlanner | None = None

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
        self._ensure_default_agent_roles()
        self._ensure_default_standing_orders()
        self._audit(
            "onboarding_completed",
            {
                "owner": settings.owner.name,
                "workspace_root": settings.workspace.root,
                "runtime_mode": settings.runtime.mode,
            },
        )
        return settings

    def _ensure_default_agent_roles(self) -> None:
        existing = {role.name for role in self.storage.list_agent_roles()}
        defaults = [
            AgentRoleSpec(
                name="CEO",
                purpose="Translate chairman intent into missions, teams, decisions, and durable company memory.",
                responsibilities=["set strategic intent", "assign teams", "escalate sensitive decisions"],
                skills=["executive planning", "risk triage", "memory stewardship"],
                constraints=["must escalate privacy, safety, legal, spending, and destructive actions"],
                escalation_triggers=["privacy risk", "security risk", "legal exposure", "external spending"],
                decision_authority=["mission staffing", "low-risk product execution", "internal prioritization"],
                default_supervisor_role="chairman",
            ),
            AgentRoleSpec(
                name="Project Manager",
                purpose="Convert CEO direction into scoped work orders, progress tracking, and risk reports.",
                responsibilities=["break down work", "coordinate agents", "surface blockers"],
                skills=["planning", "coordination", "status reporting"],
                constraints=["cannot approve high-risk policy or privacy changes"],
                escalation_triggers=["scope conflict", "blocked execution", "role disagreement"],
                decision_authority=["task sequencing", "low-risk implementation tradeoffs"],
            ),
            AgentRoleSpec(
                name="Developer",
                purpose="Implement scoped engineering tasks and report changed files, tests, and blockers.",
                responsibilities=["implement", "test", "report"],
                skills=["software engineering", "debugging", "local verification"],
                constraints=["cannot silently delete or overwrite important user files"],
                escalation_triggers=["unsafe file operation", "unclear requirement", "test failure"],
                decision_authority=["local code structure within assigned scope"],
                default_supervisor_role="project_manager",
            ),
            AgentRoleSpec(
                name="Reviewer",
                purpose="Validate outputs against mission intent, safety boundaries, and completion criteria.",
                responsibilities=["review outputs", "check tests", "block incomplete closeout"],
                skills=["quality control", "risk review", "acceptance testing"],
                constraints=["must record unresolved risks"],
                escalation_triggers=["privacy issue", "security issue", "missing acceptance criteria"],
                decision_authority=["block mission closeout until criteria pass"],
                default_supervisor_role="project_manager",
            ),
            AgentRoleSpec(
                name="Security Officer",
                purpose="Protect user privacy, files, credentials, and local computer safety.",
                responsibilities=["security review", "privacy review", "permission boundary checks"],
                skills=["threat modeling", "secure defaults", "data handling review"],
                constraints=["must escalate user-data and host-safety risks to chairman"],
                escalation_triggers=["credential exposure", "user file access", "network data sharing"],
                decision_authority=["block risky release until mitigated"],
                default_supervisor_role="ceo",
            ),
            AgentRoleSpec(
                name="Legal Counsel",
                purpose="Identify legal, licensing, contractual, and external communication risks.",
                responsibilities=["license review", "policy review", "legal risk memo"],
                skills=["legal triage", "license classification", "policy drafting"],
                constraints=["cannot provide final legal approval without chairman instruction"],
                escalation_triggers=["contract", "non-permissive license", "external claim"],
                decision_authority=["request legal escalation"],
                default_supervisor_role="ceo",
            ),
        ]
        for role in defaults:
            if role.name not in existing:
                self.storage.save_agent_role(role)

    def _ensure_default_standing_orders(self) -> None:
        existing = {(order.scope, order.effect) for order in self.storage.list_standing_orders()}
        defaults = [
            StandingOrder(
                scope="security",
                instruction="Any action that can affect user files, credentials, privacy, or host safety must be escalated to the chairman with options.",
                effect="requires_chairman_escalation",
            ),
            StandingOrder(
                scope="privacy",
                instruction="Never store raw credentials, tokens, private keys, payment data, or unnecessary personal file contents in memory, logs, reports, or agent messages.",
                effect="data_minimization_required",
            ),
            StandingOrder(
                scope="privacy",
                instruction="Do not send, upload, publish, email, or share user data outside Praetor unless the chairman explicitly approved that exact action.",
                effect="external_sharing_requires_approval",
            ),
            StandingOrder(
                scope="engineering",
                instruction="Low-risk implementation details may be decided by the PM and Developer if tests and reviewer checks pass.",
                effect="delegate_low_risk_execution",
            ),
        ]
        for order in defaults:
            if (order.scope, order.effect) not in existing:
                self.storage.save_standing_order(order)

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

    def update_runtime(self, runtime: RuntimeSelection) -> AppSettings:
        settings = self._require_settings()
        settings.runtime = runtime
        settings.updated_at = utc_now()
        self.storage.save_settings(settings)
        self._audit(
            "runtime_settings_updated",
            {
                "mode": runtime.mode,
                "provider": runtime.provider,
                "model": runtime.model,
                "executor": runtime.executor,
            },
        )
        return settings

    def update_telegram_settings(self, telegram: TelegramIntegrationSettings) -> AppSettings:
        settings = self._require_settings()
        current = settings.telegram
        settings.telegram = current.model_copy(
            update={
                "enabled": telegram.enabled,
                "bot_token_set": telegram.bot_token_set,
                "webhook_secret_set": telegram.webhook_secret_set,
                "allowed_user_id": telegram.allowed_user_id,
                "notify_approvals": telegram.notify_approvals,
                "allow_low_risk_approval": telegram.allow_low_risk_approval,
            }
        )
        settings.updated_at = utc_now()
        self.storage.save_settings(settings)
        self._audit(
            "telegram_settings_updated",
            {
                "enabled": settings.telegram.enabled,
                "allowed_user_id": settings.telegram.allowed_user_id,
                "notify_approvals": settings.telegram.notify_approvals,
                "allow_low_risk_approval": settings.telegram.allow_low_risk_approval,
            },
        )
        return settings

    def create_telegram_pairing_code(self) -> str:
        settings = self._require_settings()
        code = generate_pairing_code()
        settings.telegram = new_pairing_settings(settings.telegram, code)
        settings.updated_at = utc_now()
        self.storage.save_settings(settings)
        self._audit("telegram_pairing_code_created", {"expires_at": settings.telegram.pairing_code_expires_at.isoformat()})
        return code

    def link_telegram_chat(self, *, chat_id: int, user_id: int, username: str | None = None) -> AppSettings:
        settings = self._require_settings()
        settings.telegram = settings.telegram.model_copy(
            update={
                "enabled": True,
                "linked_chat_id": chat_id,
                "linked_user_id": user_id,
                "linked_username": username,
                "pairing_code_hash": None,
                "pairing_code_expires_at": None,
                "linked_at": utc_now(),
            }
        )
        settings.updated_at = utc_now()
        self.storage.save_settings(settings)
        self._audit("telegram_chat_linked", {"chat_id": chat_id, "user_id": user_id, "username": username})
        return settings

    def handle_telegram_update(self, update: dict[str, Any]) -> list[dict[str, Any]]:
        replies = process_update(self, update)
        results = []
        from .telegram import TelegramClient

        client = TelegramClient()
        for reply in replies:
            if reply.chat_id is None:
                continue
            results.append(client.send_message(reply.chat_id, reply.text, reply_markup=reply.reply_markup))
        self._audit("telegram_update_processed", {"update_id": update.get("update_id"), "replies": len(results)})
        return results

    def create_mission(self, request: MissionCreateRequest) -> MissionDefinition:
        settings = self._require_settings()
        self._ensure_default_agent_roles()
        self._ensure_default_standing_orders()
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
        self._ensure_mission_team(mission)
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

    def _ensure_mission_team(self, mission: MissionDefinition, requested_roles: list[str] | None = None) -> MissionTeam:
        existing = self.storage.list_teams(mission_id=mission.id)
        if existing:
            return existing[0]
        roles = requested_roles or self._recommended_roles_for_mission(mission)
        agents = [self._create_agent_for_role(role, mission) for role in roles]
        pm = next((agent for agent in agents if agent.role_name == "Project Manager"), None)
        team = MissionTeam(
            mission_id=mission.id,
            name=f"{mission.title} team",
            lead_agent_id=pm.id if pm else agents[0].id if agents else None,
            member_agent_ids=[agent.id for agent in agents],
            status="active",
        )
        self.storage.save_team(team)
        self._audit(
            "mission_team_created",
            {
                "mission_id": mission.id,
                "team_id": team.id,
                "roles": [agent.role_name for agent in agents],
            },
        )
        return team

    def _recommended_roles_for_mission(self, mission: MissionDefinition) -> list[str]:
        roles = ["Project Manager", "Developer", "Reviewer"]
        text = " ".join([mission.title, mission.summary or "", " ".join(mission.domains)]).lower()
        if any(word in text for word in ["security", "privacy", "安全", "隱私", "隐私"]):
            roles.append("Security Officer")
        if any(word in text for word in ["legal", "law", "license", "合約", "法律", "法務"]):
            roles.append("Legal Counsel")
        return roles

    def _create_agent_for_role(self, role_name: str, mission: MissionDefinition) -> AgentInstance:
        existing = [agent for agent in self.storage.list_agents(mission_id=mission.id) if agent.role_name == role_name]
        if existing:
            return existing[0]
        role = next((item for item in self.storage.list_agent_roles() if item.name == role_name), None)
        if role is None:
            role = AgentRoleSpec(
                name=role_name,
                purpose=f"Handle {role_name} responsibilities for a mission.",
                responsibilities=["complete assigned mission work", "report blockers"],
                escalation_triggers=["unclear requirement", "safety or privacy risk"],
            )
            self.storage.save_agent_role(role)
        agent = AgentInstance(
            role_name=role.name,
            display_name=f"{role.name} - {mission.title[:48]}",
            mission_id=mission.id,
            supervisor_role=role.default_supervisor_role,
            charter=self._agent_charter(role, mission),
            skills=role.skills,
            tools=role.tools,
            memory_access=["company_dna", "standing_orders", f"mission:{mission.id}"],
            decision_authority=role.decision_authority,
            escalation_triggers=role.escalation_triggers,
        )
        self.storage.save_agent(agent)
        self.storage.append_agent_message(
            AgentMessage(
                mission_id=mission.id,
                role=self._agent_message_role(role.name),
                body=f"Onboarded as {role.name}. Charter: {agent.charter}",
            )
        )
        return agent

    def _agent_charter(self, role: AgentRoleSpec, mission: MissionDefinition) -> str:
        settings = self._require_settings()
        responsibilities = "; ".join(role.responsibilities[:4]) or "complete assigned work"
        constraints = "; ".join(role.constraints[:3]) or "stay within mission scope and escalation rules"
        base = (
            f"You are the {role.name} for mission {mission.id}. Mission: {mission.title}. "
            f"Responsibilities: {responsibilities}. Constraints: {constraints}."
        )
        safety_policy = build_prompt_safety_policy(
            settings=settings,
            standing_orders=self.storage.list_standing_orders(),
            mission=mission,
            role_name=role.name,
        ).text
        return append_safety_policy(base, safety_policy)

    @staticmethod
    def _agent_message_role(role_name: str) -> str:
        return role_name.lower().replace(" ", "_").replace("-", "_")

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

    def organization_snapshot(self, mission_id: str | None = None) -> OrganizationSnapshot:
        self._require_settings()
        self._ensure_default_agent_roles()
        self._ensure_default_standing_orders()
        return OrganizationSnapshot(
            agent_roles=self.storage.list_agent_roles(),
            agents=self.storage.list_agents(mission_id=mission_id),
            teams=self.storage.list_teams(mission_id=mission_id),
            delegations=self.storage.list_delegations(mission_id=mission_id),
            escalations=self.storage.list_escalations(mission_id=mission_id),
            standing_orders=self.storage.list_standing_orders(),
        )

    def mission_completion_contract(self, mission_id: str) -> CompletionContract:
        settings = self._require_settings()
        workspace_root = Path(settings.workspace.root)
        mission = self.get_mission(mission_id)
        delegations = self.storage.list_delegations(mission_id=mission_id)
        pending_escalations = self.storage.list_escalations(mission_id=mission_id, status="pending")
        reports = self.storage.read_mission_texts(workspace_root, mission_id)
        missing_outputs = [
            output
            for output in mission.requested_outputs
            if not (workspace_root / output.removeprefix("/workspace/")).exists()
        ]
        required_outputs_present = not missing_outputs
        delegations_done = not delegations or all(item.status == "done" for item in delegations)
        review_passed = any(
            message.role == "reviewer" and "pass" in message.body.lower()
            for message in self.storage.list_agent_messages(mission_id=mission_id, limit=100)
        ) or mission.status == "completed"
        final_report_ready = bool(reports.get("REPORT.md", "").strip())
        memory_updated = any(page["name"] == "CEO Memory.md" for page in self.storage.list_wiki_pages(workspace_root))
        blockers: list[str] = []
        if not required_outputs_present:
            blockers.append(f"Missing requested outputs: {', '.join(missing_outputs)}")
        if not delegations_done:
            blockers.append("Delegations are still open.")
        if pending_escalations:
            blockers.append("Pending escalations require resolution.")
        if not review_passed:
            blockers.append("Reviewer has not passed the mission.")
        can_close = required_outputs_present and delegations_done and not pending_escalations and final_report_ready
        return CompletionContract(
            mission_id=mission_id,
            required_outputs_present=required_outputs_present,
            delegations_done=delegations_done,
            review_passed=review_passed,
            no_pending_escalations=not pending_escalations,
            final_report_ready=final_report_ready,
            memory_updated=memory_updated,
            can_close=can_close,
            blockers=blockers,
        )

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
        self._notify_telegram_approval(approval)
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
        self._ensure_default_standing_orders()
        mission = self.get_mission(mission_id)
        runtime_engine = MissionRuntime()
        safety_policy = build_prompt_safety_policy(
            settings=settings,
            standing_orders=self.storage.list_standing_orders(),
            mission=mission,
            role_name="Project Execution",
        ).text

        mission.status = "active"
        mission.updated_at = utc_now()
        workspace_root = Path(settings.workspace.root)
        self.storage.save_mission(workspace_root, mission)

        primary_result = runtime_engine.run_mission(
            workspace_root=workspace_root,
            mission=mission,
            runtime=settings.runtime,
            permissions=settings.workspace.permissions,
            safety_policy=safety_policy,
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
                    safety_policy=safety_policy,
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
            self._notify_telegram_approval(approval)
            self._audit(
                "approval_requested",
                {"approval_id": approval.id, "mission_id": mission.id, "category": approval.category},
            )
        return {
            "mission": mission,
            "task": final_result.task,
            "bridge_run": final_result.run_record,
        }

    def _notify_telegram_approval(self, approval: ApprovalRequest) -> None:
        settings = self._require_settings()
        try:
            result = send_approval_notification(settings.telegram, approval)
            self._audit(
                "telegram_approval_notification",
                {
                    "approval_id": approval.id,
                    "sent": bool(result.get("ok")),
                    "skipped": bool(result.get("skipped")),
                },
            )
        except Exception as exc:
            self._audit("telegram_approval_notification_failed", {"approval_id": approval.id, "error": str(exc)})

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
            recent_planner_actions=self._recent_planner_actions(audit_events, limit=8),
            runtime_health=self.runtime_health(),
            organization=self.organization_snapshot(),
        )

    def create_ceo_message(self, request: ConversationCreateRequest) -> ConversationCreateResult:
        settings = self._require_settings()
        self._ensure_default_standing_orders()
        text = request.body.strip()
        if not text:
            raise ValueError("Message body is required.")
        planner = self.planner or default_ceo_planner(settings.runtime)
        safety_policy = build_prompt_safety_policy(
            settings=settings,
            standing_orders=self.storage.list_standing_orders(),
            role_name="CEO",
        ).text
        plan = planner.plan(
            CEOPlannerContext(
                instruction=text,
                related_mission_id=request.related_mission_id,
                mission_count=len(self.storage.list_missions(Path(settings.workspace.root))),
                pending_approvals=len([item for item in self.storage.list_approvals() if item.status == "pending"]),
                safety_policy=safety_policy,
            )
        )
        created_mission: MissionDefinition | None = None
        created_approval: ApprovalRequest | None = None
        agent_messages: list[AgentMessage] = []
        actions: list[PlannerAction] = []

        chairman = ConversationMessage(
            role="chairman",
            body=text,
            related_mission_id=request.related_mission_id,
        )
        related_mission_id = request.related_mission_id
        for action in plan.actions:
            applied = self._apply_planner_action(action, text, related_mission_id)
            actions.append(applied)
            if applied.type == "mission_draft" and applied.result_id:
                created_mission = self.storage.load_mission(Path(settings.workspace.root), applied.result_id)
                related_mission_id = applied.result_id
                chairman.related_mission_id = applied.result_id
                if created_mission is not None:
                    agent_messages.extend(self._seed_agent_thread_for_ceo_mission(created_mission, text))
            elif applied.type == "approval_request" and applied.result_id:
                created_approval = next(
                    (item for item in self.storage.list_approvals() if item.id == applied.result_id),
                    None,
                )

        response = ConversationMessage(
            role="ceo",
            body=plan.response,
            related_mission_id=related_mission_id,
        )
        self.storage.append_conversation_message(chairman)
        self.storage.append_conversation_message(response)
        self._audit(
            "ceo_conversation_message",
            {
                "message_id": chairman.id,
                "related_mission_id": related_mission_id,
                "intent": plan.intent,
                "created_mission_id": created_mission.id if created_mission else None,
                "created_approval_id": created_approval.id if created_approval else None,
                "actions": [item.model_dump(mode="json") for item in actions],
            },
        )
        return ConversationCreateResult(
            messages=[chairman, response],
            created_mission=created_mission,
            created_approval=created_approval,
            agent_messages=agent_messages,
            actions=actions,
            intent=plan.intent,
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
        for team in self.storage.list_teams(mission_id=mission_id):
            events.append(
                MissionTimelineEvent(
                    id=team.id,
                    mission_id=mission_id,
                    type="team",
                    title=f"Team: {team.name}",
                    body=f"Members: {len(team.member_agent_ids)}",
                    actor="ceo",
                    status=team.status,
                    created_at=team.created_at,
                    metadata={"lead_agent_id": team.lead_agent_id, "member_agent_ids": team.member_agent_ids},
                )
            )
        for delegation in self.storage.list_delegations(mission_id=mission_id):
            events.append(
                MissionTimelineEvent(
                    id=delegation.id,
                    mission_id=mission_id,
                    type="delegation",
                    title=delegation.title,
                    body=delegation.instructions,
                    actor=delegation.from_role,
                    status=delegation.status,
                    created_at=delegation.created_at,
                    metadata={"to_role": delegation.to_role, "to_agent_id": delegation.to_agent_id},
                )
            )
        for escalation in self.storage.list_escalations(mission_id=mission_id):
            events.append(
                MissionTimelineEvent(
                    id=escalation.id,
                    mission_id=mission_id,
                    type="escalation",
                    title=f"Escalation to {escalation.to_level}",
                    body=escalation.reason,
                    actor=escalation.from_role,
                    status=escalation.status,
                    created_at=escalation.created_at,
                    metadata={"category": escalation.category, "options": escalation.options},
                )
            )
        events.sort(key=lambda item: item.created_at)
        return events

    def mission_agent_messages(self, mission_id: str, limit: int = 100) -> list[AgentMessage]:
        settings = self._require_settings()
        if self.storage.load_mission(Path(settings.workspace.root), mission_id) is None:
            raise KeyError(mission_id)
        return self.storage.list_agent_messages(mission_id=mission_id, limit=limit)

    def _apply_planner_action(
        self,
        action: PlannerAction,
        instruction: str,
        related_mission_id: str | None,
    ) -> PlannerAction:
        if action.type == "mission_draft":
            metadata = action.metadata
            mission = self.create_mission(
                MissionCreateRequest(
                    title=action.title.strip() or "Chairman-directed mission",
                    summary=action.body or f"Chairman instruction: {instruction}",
                    domains=list(metadata.get("domains") or ["operations"]),
                    priority=str(metadata.get("priority") or "normal"),
                    requested_outputs=list(metadata.get("requested_outputs") or []),
                )
            )
            return action.model_copy(update={"status": "applied", "mission_id": mission.id, "result_id": mission.id})

        if action.type == "approval_request":
            mission_id = action.mission_id or related_mission_id
            if not mission_id:
                return action.model_copy(
                    update={
                        "status": "skipped",
                        "metadata": {**action.metadata, "skip_reason": "approval_request requires a mission_id"},
                    }
                )
            approval = self.create_approval(
                ApprovalCreateRequest(
                    mission_id=mission_id,
                    category=action.metadata.get("category") or "change_strategy",
                    reason=action.body or action.title,
                )
            )
            return action.model_copy(update={"status": "applied", "mission_id": mission_id, "result_id": approval.id})

        if action.type == "memory_update":
            settings = self._require_settings()
            memory_text = action.body or instruction
            if contains_sensitive_material(memory_text):
                escalation = EscalationRecord(
                    mission_id=action.mission_id or related_mission_id,
                    from_role="ceo",
                    to_level="chairman",
                    category="privacy",
                    reason="Memory update blocked because it appears to contain credentials, tokens, private keys, or similarly sensitive material.",
                )
                self.storage.save_escalation(escalation)
                self._audit(
                    "memory_update_blocked_sensitive_material",
                    {"escalation_id": escalation.id, "mission_id": escalation.mission_id},
                )
                return action.model_copy(
                    update={
                        "status": "skipped",
                        "result_id": escalation.id,
                        "metadata": {**action.metadata, "skip_reason": "sensitive material cannot be stored in memory"},
                    }
                )
            path = self.storage.append_wiki_page(
                Path(settings.workspace.root),
                str(action.metadata.get("page") or "CEO Memory.md"),
                "\n".join(
                    [
                        f"## {utc_now().isoformat().replace('+00:00', 'Z')}",
                        "",
                        memory_text,
                    ]
                ),
            )
            return action.model_copy(update={"status": "applied", "result_id": str(path)})

        if action.type == "staffing_proposal":
            mission_id = action.mission_id or related_mission_id
            if not mission_id:
                return action.model_copy(
                    update={
                        "status": "skipped",
                        "metadata": {**action.metadata, "skip_reason": "staffing requires a mission_id"},
                    }
                )
            mission = self.get_mission(mission_id)
            roles = list(action.metadata.get("roles") or self._recommended_roles_for_mission(mission))
            team = self._ensure_mission_team(mission, requested_roles=roles)
            self.storage.append_pm_report(
                Path(self._require_settings().workspace.root),
                mission_id,
                "\n".join(
                    [
                        f"Staffing proposal applied: {action.title}",
                        f"Roles: {', '.join(roles)}",
                        action.body or "",
                    ]
                ),
            )
            return action.model_copy(update={"status": "applied", "mission_id": mission_id, "result_id": team.id})

        if action.type == "agent_create":
            mission_id = action.mission_id or related_mission_id
            if not mission_id:
                return action.model_copy(
                    update={
                        "status": "skipped",
                        "metadata": {**action.metadata, "skip_reason": "agent creation requires a mission_id"},
                    }
                )
            mission = self.get_mission(mission_id)
            role_name = str(action.metadata.get("role") or action.title or "Specialist")
            agent = self._create_agent_for_role(role_name, mission)
            return action.model_copy(update={"status": "applied", "mission_id": mission_id, "result_id": agent.id})

        if action.type == "delegation_create":
            mission_id = action.mission_id or related_mission_id
            if not mission_id:
                return action.model_copy(
                    update={
                        "status": "skipped",
                        "metadata": {**action.metadata, "skip_reason": "delegation requires a mission_id"},
                    }
                )
            to_role = str(action.metadata.get("to_role") or "Project Manager")
            mission = self.get_mission(mission_id)
            to_agent = next(
                (agent for agent in self.storage.list_agents(mission_id=mission_id) if agent.role_name == to_role),
                None,
            )
            delegation = DelegationRecord(
                mission_id=mission_id,
                to_agent_id=to_agent.id if to_agent else None,
                from_role=str(action.metadata.get("from_role") or "ceo"),
                to_role=to_role,
                title=action.title,
                instructions=append_safety_policy(
                    action.body or instruction,
                    build_prompt_safety_policy(
                        settings=self._require_settings(),
                        standing_orders=self.storage.list_standing_orders(),
                        mission=mission,
                        role_name=to_role,
                    ).text,
                ),
                success_criteria=list(action.metadata.get("success_criteria") or []),
                constraints=list(action.metadata.get("constraints") or []),
            )
            self.storage.save_delegation(delegation)
            self.storage.append_agent_message(
                AgentMessage(
                    mission_id=mission_id,
                    role=self._agent_message_role(to_role),
                    body=f"Delegation received: {delegation.title}. Success criteria: {', '.join(delegation.success_criteria) or 'report completion and blockers'}.",
                )
            )
            self._audit("delegation_created", {"delegation_id": delegation.id, "mission_id": mission_id, "to_role": to_role})
            return action.model_copy(update={"status": "applied", "mission_id": mission_id, "result_id": delegation.id})

        if action.type == "decision_escalation":
            to_level = str(action.metadata.get("to_level") or "chairman")
            if to_level not in {"project_manager", "ceo", "chairman"}:
                to_level = "chairman"
            category = str(action.metadata.get("category") or "change_strategy")
            if category not in {"delete_files", "overwrite_important_files", "external_communication", "spending_money", "change_strategy", "shell_commands"}:
                category = "change_strategy"
            escalation = EscalationRecord(
                mission_id=action.mission_id or related_mission_id,
                from_role=str(action.metadata.get("from_role") or "ceo"),
                to_level=to_level,
                category=category,
                reason=action.body or action.title,
                options=list(action.metadata.get("options") or []),
            )
            self.storage.save_escalation(escalation)
            if escalation.mission_id:
                self.storage.append_agent_message(
                    AgentMessage(
                        mission_id=escalation.mission_id,
                        role="ceo",
                        body=f"Escalation opened for {escalation.to_level}: {escalation.reason}",
                    )
                )
            self._audit(
                "decision_escalation_created",
                {"escalation_id": escalation.id, "mission_id": escalation.mission_id, "to_level": escalation.to_level},
            )
            return action.model_copy(update={"status": "applied", "mission_id": escalation.mission_id, "result_id": escalation.id})

        if action.type == "standing_order_update":
            scope = str(action.metadata.get("scope") or "global")
            if scope not in {"global", "mission", "security", "privacy", "legal", "finance", "product", "engineering"}:
                scope = "global"
            order = StandingOrder(
                scope=scope,
                instruction=action.body or action.title,
                effect=str(action.metadata.get("effect") or "guidance"),
            )
            self.storage.save_standing_order(order)
            self._audit("standing_order_created", {"standing_order_id": order.id, "scope": order.scope})
            return action.model_copy(update={"status": "applied", "result_id": order.id})

        if action.type == "mission_closeout":
            mission_id = action.mission_id or related_mission_id
            if not mission_id:
                return action.model_copy(
                    update={
                        "status": "skipped",
                        "metadata": {**action.metadata, "skip_reason": "mission closeout requires a mission_id"},
                    }
                )
            contract = self.mission_completion_contract(mission_id)
            if not contract.can_close:
                escalation = EscalationRecord(
                    mission_id=mission_id,
                    from_role="reviewer",
                    to_level="ceo",
                    category="change_strategy",
                    reason="Mission closeout blocked: " + "; ".join(contract.blockers),
                )
                self.storage.save_escalation(escalation)
                return action.model_copy(
                    update={
                        "status": "skipped",
                        "mission_id": mission_id,
                        "result_id": escalation.id,
                        "metadata": {**action.metadata, "completion_contract": contract.model_dump(mode="json")},
                    }
                )
            mission = self.get_mission(mission_id)
            mission.status = "completed"
            mission.updated_at = utc_now()
            self.storage.save_mission(Path(self._require_settings().workspace.root), mission)
            return action.model_copy(update={"status": "applied", "mission_id": mission_id, "result_id": mission.id})

        return action.model_copy(update={"status": "applied"})

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
    def _recent_planner_actions(audit_events: list[dict], limit: int = 8) -> list[PlannerAction]:
        actions: list[PlannerAction] = []
        for event in audit_events:
            payload = event.get("payload") or {}
            for item in payload.get("actions") or []:
                try:
                    actions.append(PlannerAction.model_validate(item))
                except Exception:
                    continue
                if len(actions) >= limit:
                    return actions
        return actions

    def runtime_health(self) -> dict:
        runtime = MissionRuntime()
        return runtime.probe(self._require_settings().runtime)

    def test_runtime_connection(self, runtime: RuntimeSelection | None = None, api_key: str | None = None) -> dict:
        selected = runtime or self._require_settings().runtime
        if selected.mode != "api":
            return MissionRuntime().probe(selected)
        provider = selected.provider or "openai"
        model = selected.model or ("claude-3-5-sonnet-latest" if provider == "anthropic" else "gpt-4.1-mini")
        return test_provider_connection(
            provider=provider,
            model=model,
            base_url=selected.base_url,
            api_key=api_key.strip() if api_key else None,
        )

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
