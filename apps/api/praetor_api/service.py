from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
from pathlib import Path
import re
import subprocess
from typing import Any

from .auth import hash_password, validate_password_strength, verify_password
from .models import (
    AgentMessage,
    AgentInstance,
    AgentRoleSpec,
    AppSettings,
    ApprovalCreateRequest,
    ApprovalRequest,
    BoardBriefing,
    ChairmanInboxItem,
    ClientRecord,
    CompletionContract,
    ConversationCreateRequest,
    ConversationMessage,
    ConversationCreateResult,
    DelegationRecord,
    DocumentRecord,
    DocumentVersion,
    EscalationRecord,
    FileAssetRecord,
    FileMoveRecord,
    GovernanceReview,
    KnowledgeSnapshot,
    KnowledgeUpdate,
    MemoryPromotionReview,
    MatterDecisionRecord,
    MatterRecord,
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
    OpenQuestionRecord,
    OwnerAuthRecord,
    PlannerAction,
    PraetorBriefing,
    PromotionFinding,
    ReviewPolicy,
    RunAttempt,
    RoleDefinition,
    RuntimeSelection,
    StandingOrder,
    TaskDefinition,
    TelegramIntegrationSettings,
    WorkspaceConfig,
    WorkspacePermissions,
    WorkspaceReconciliationIssue,
    WorkspaceReconciliationReport,
    WorkspaceRestructurePlan,
    WorkspaceScope,
    WorkspaceStewardSnapshot,
    WorkSession,
    WorkSessionTurn,
    utc_now,
)
from .planner import CEOPlanner, CEOPlannerContext, default_ceo_planner
from .providers import test_provider_connection
from .recommendations import assess_mission_complexity, preview_onboarding
from .runtime import MissionRuntime
from .safety_policy import append_safety_policy, build_prompt_safety_policy, contains_sensitive_material
from .storage import AppStorage
from .telegram import generate_pairing_code, new_pairing_settings, process_update, send_approval_notification
from .workspace import DEFAULT_WORKFLOW_CONTRACT, bootstrap_workspace


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
            AgentRoleSpec(
                name="Product Manager",
                purpose="Clarify product intent, target users, scope, success metrics, and release shape.",
                responsibilities=["product framing", "scope definition", "success criteria"],
                skills=["product strategy", "user research synthesis", "prioritization"],
                constraints=["must separate assumptions from confirmed chairman decisions"],
                escalation_triggers=["unclear target user", "conflicting product goals", "material strategy choice"],
                decision_authority=["low-risk product tradeoffs inside approved mission scope"],
                default_supervisor_role="project_manager",
            ),
            AgentRoleSpec(
                name="Marketing Lead",
                purpose="Define positioning, audience, go-to-market assumptions, and revenue hypotheses.",
                responsibilities=["positioning", "audience analysis", "business assumptions"],
                skills=["market research", "messaging", "pricing and revenue hypothesis"],
                constraints=["must not treat unverified market claims as durable company knowledge"],
                escalation_triggers=["external communication", "unverified claims", "pricing commitment"],
                decision_authority=["draft positioning and forecast assumptions for review"],
                default_supervisor_role="project_manager",
            ),
            AgentRoleSpec(
                name="Design Lead",
                purpose="Explore product experience, interface direction, and visual presentation options.",
                responsibilities=["UX framing", "interface proposal", "visual direction"],
                skills=["UX design", "interaction design", "visual systems"],
                constraints=["must present design options before committing major brand or UX changes"],
                escalation_triggers=["brand change", "accessibility risk", "unclear user workflow"],
                decision_authority=["draft design directions and interface recommendations"],
                default_supervisor_role="project_manager",
            ),
            AgentRoleSpec(
                name="Sales Manager",
                purpose="Clarify customer-facing path, buyer assumptions, and sales risks.",
                responsibilities=["customer discovery", "sales assumptions", "external communication review"],
                skills=["sales strategy", "customer qualification", "business development"],
                constraints=["cannot contact customers or make commitments without chairman approval"],
                escalation_triggers=["external communication", "pricing commitment", "customer promise"],
                decision_authority=["draft sales options and customer discovery questions"],
                default_supervisor_role="project_manager",
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
        self._ensure_mission_knowledge_workspace(mission)
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
        self._register_requested_output_assets(mission)
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

    def _ensure_mission_knowledge_workspace(self, mission: MissionDefinition) -> MatterRecord:
        settings = self._require_settings()
        workspace_root = Path(settings.workspace.root)
        existing = self.storage.list_matters(mission_id=mission.id)
        if existing:
            matter = existing[0]
            mission.client_id = matter.client_id
            mission.matter_id = matter.id
            return matter

        client_name = self._infer_client_name(mission)
        client = self._ensure_client(workspace_root, client_name)
        base_slug = self._slugify(mission.title)[:40] or "matter"
        matter_slug = f"{base_slug}-{mission.id.removeprefix('mission_')[:8]}"
        matter_folder = f"clients/{client.slug}/matters/{matter_slug}"
        matter = MatterRecord(
            client_id=client.id,
            mission_id=mission.id,
            title=mission.title,
            slug=matter_slug,
            folder=matter_folder,
            brief_path=f"{matter_folder}/brief.md",
            decisions_path=f"{matter_folder}/decisions.md",
            open_questions_path=f"{matter_folder}/open-questions.md",
        )
        self.storage.save_matter(workspace_root, matter)
        mission.client_id = client.id
        mission.matter_id = matter.id
        self._ensure_workspace_scope(mission, matter)
        self._seed_matter_registry(workspace_root, mission, client, matter)
        self._audit(
            "knowledge_workspace_created",
            {
                "mission_id": mission.id,
                "client_id": client.id,
                "matter_id": matter.id,
                "folder": matter.folder,
            },
        )
        return matter

    def _ensure_workspace_scope(self, mission: MissionDefinition, matter: MatterRecord | None = None) -> WorkspaceScope:
        settings = self._require_settings()
        workspace_root = Path(settings.workspace.root)
        existing = self.storage.load_workspace_scope(workspace_root, mission.id)
        if existing is not None:
            return existing
        matter = matter or next(iter(self.storage.list_matters(mission_id=mission.id)), None)
        root = matter.folder if matter is not None else f"Missions/{mission.id}"
        scope = WorkspaceScope(
            mission_id=mission.id,
            matter_id=matter.id if matter is not None else None,
            root=root,
            allowed_read=[
                root,
                f"Missions/{mission.id}",
                "Wiki",
                "PRAETOR_WORKFLOW.md",
            ],
            allowed_write=[
                root,
                f"Missions/{mission.id}",
            ],
            denied_write=[
                "Archive",
                ".praetor",
            ],
            workflow_path="PRAETOR_WORKFLOW.md",
        )
        self.storage.save_workspace_scope(workspace_root, scope)
        return scope

    def _ensure_client(self, workspace_root: Path, name: str) -> ClientRecord:
        slug = self._slugify(name) or "general"
        for client in self.storage.list_clients():
            if client.slug == slug:
                return client
        client = ClientRecord(
            name=name,
            slug=slug,
            folder=f"clients/{slug}",
            summary="Created automatically from a Praetor mission. Confirmed client facts should be promoted here.",
        )
        self.storage.save_client(workspace_root, client)
        return client

    def _seed_matter_registry(
        self,
        workspace_root: Path,
        mission: MissionDefinition,
        client: ClientRecord,
        matter: MatterRecord,
    ) -> None:
        self.storage.save_matter_decision(
            workspace_root,
            MatterDecisionRecord(
                matter_id=matter.id,
                client_id=client.id,
                mission_id=mission.id,
                summary="Matter workspace opened; no final business decision has been confirmed yet.",
                rationale="Praetor separates raw conversation from durable memory until decisions are confirmed.",
            ),
        )
        self.storage.save_open_question(
            workspace_root,
            OpenQuestionRecord(
                matter_id=matter.id,
                client_id=client.id,
                mission_id=mission.id,
                question="What final output should be treated as the authoritative version for this matter?",
                blocking="final archive and knowledge promotion",
                status="waiting_owner",
            ),
        )
        self.storage.save_knowledge_update(
            KnowledgeUpdate(
                matter_id=matter.id,
                client_id=client.id,
                mission_id=mission.id,
                target_page=f"Clients/{client.slug}.md",
                summary="Client matter opened",
                content=(
                    f"Praetor opened matter '{matter.title}' for {client.name}. "
                    "This is a proposed memory update, not confirmed client knowledge."
                ),
                status="proposed",
            )
        )
        for document in self._planned_documents_for_mission(mission, client, matter):
            self.storage.save_document(document)
            self._register_document_assets(document)

    def _planned_documents_for_mission(
        self,
        mission: MissionDefinition,
        client: ClientRecord,
        matter: MatterRecord,
    ) -> list[DocumentRecord]:
        documents: list[DocumentRecord] = []
        outputs = mission.requested_outputs or []
        for index, output in enumerate(outputs, start=1):
            title = Path(output).name or f"Requested output {index}"
            documents.append(
                DocumentRecord(
                    matter_id=matter.id,
                    client_id=client.id,
                    mission_id=mission.id,
                    title=title,
                    document_type=self._document_type_for_path(title),
                    status="draft",
                    versions=[
                        DocumentVersion(
                            version=1,
                            path=output,
                            label="v001 planned output",
                            reason="Requested when the mission was created.",
                        )
                    ],
                )
            )
        text = " ".join([mission.title, mission.summary or "", " ".join(mission.domains)]).lower()
        if not documents and any(term in text for term in ["contract", "agreement", "legal", "合約", "合同", "法律", "法務"]):
            path = f"{matter.folder}/versions/v001-contract-draft.docx"
            documents.append(
                DocumentRecord(
                    matter_id=matter.id,
                    client_id=client.id,
                    mission_id=mission.id,
                    title="Contract draft",
                    document_type="contract",
                    status="draft",
                    versions=[
                        DocumentVersion(
                            version=1,
                            path=path,
                            label="v001 planned contract draft",
                            reason="Reserved for the first contract draft; content is not created until execution.",
                        )
                    ],
                )
            )
        return documents

    @staticmethod
    def _document_type_for_path(path: str) -> str:
        suffix = Path(path).suffix.lower()
        if suffix == ".docx":
            return "docx"
        if suffix == ".pdf":
            return "pdf"
        if suffix in {".md", ".txt"}:
            return "note"
        return "working_document"

    @staticmethod
    def _slugify(value: str) -> str:
        value = value.strip().lower()
        value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value).strip("-")
        return value or "general"

    @staticmethod
    def _infer_client_name(mission: MissionDefinition) -> str:
        texts = [mission.title, mission.summary or ""]
        patterns = [
            (r"(?:client|customer)\s+([A-Za-z0-9][A-Za-z0-9 _.-]{1,48})", re.IGNORECASE),
            (r"(?:for|with)\s+([A-Z][A-Za-z0-9 _.-]{1,48})", 0),
            (r"客[戶户]\s*([A-Za-z0-9\u4e00-\u9fff _.-]{1,32})", 0),
            (r"([A-Za-z0-9\u4e00-\u9fff _.-]{1,32})\s*客[戶户]", 0),
        ]
        for text in texts:
            for pattern, flags in patterns:
                match = re.search(pattern, text, flags=flags)
                if match:
                    name = match.group(1).strip(" .。,:，：")
                    if name:
                        return name
        return "General"

    def _ensure_mission_team(self, mission: MissionDefinition, requested_roles: list[str] | None = None) -> MissionTeam:
        existing = self.storage.list_teams(mission_id=mission.id)
        roles = list(dict.fromkeys(requested_roles or self._recommended_roles_for_mission(mission)))
        if existing:
            team = existing[0]
            existing_agents = self.storage.list_agents(mission_id=mission.id)
            existing_roles = {agent.role_name for agent in existing_agents}
            missing_roles = [role for role in roles if role not in existing_roles]
            if not missing_roles:
                return team
            new_agents = [self._create_agent_for_role(role, mission) for role in missing_roles]
            member_ids = list(dict.fromkeys([*team.member_agent_ids, *[agent.id for agent in new_agents]]))
            pm = next((agent for agent in [*existing_agents, *new_agents] if agent.role_name == "Project Manager"), None)
            team.member_agent_ids = member_ids
            team.lead_agent_id = team.lead_agent_id or (pm.id if pm else member_ids[0] if member_ids else None)
            team.status = "active"
            team.updated_at = utc_now()
            self.storage.save_team(team)
            self._audit(
                "mission_team_expanded",
                {
                    "mission_id": mission.id,
                    "team_id": team.id,
                    "roles": missing_roles,
                },
            )
            return team
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
        if any(word in text for word in ["product", "產品", "产品", "feature", "功能", "專案", "项目"]):
            roles.append("Product Manager")
        if any(word in text for word in ["marketing", "market", "revenue", "sales", "收益", "市場", "市场", "行銷", "营销", "業務", "销售"]):
            roles.append("Marketing Lead")
        if any(word in text for word in ["design", "ui", "ux", "logo", "interface", "介面", "界面", "設計", "设计"]):
            roles.append("Design Lead")
        if any(word in text for word in ["security", "privacy", "安全", "隱私", "隐私"]):
            roles.append("Security Officer")
        if any(word in text for word in ["legal", "law", "license", "合約", "法律", "法務"]):
            roles.append("Legal Counsel")
        return list(dict.fromkeys(roles))

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

    def list_run_attempts(self, mission_id: str, limit: int = 20) -> list[RunAttempt]:
        settings = self._require_settings()
        if self.storage.load_mission(Path(settings.workspace.root), mission_id) is None:
            raise KeyError(mission_id)
        return self.storage.list_run_attempts(mission_id=mission_id, limit=limit)

    def mission_workspace_scope(self, mission_id: str) -> WorkspaceScope:
        settings = self._require_settings()
        mission = self.get_mission(mission_id)
        scope = self.storage.load_workspace_scope(Path(settings.workspace.root), mission_id)
        if scope is not None:
            return scope
        matter = next(iter(self.storage.list_matters(mission_id=mission.id)), None)
        return self._ensure_workspace_scope(mission, matter)

    def workflow_contract(self):
        settings = self._require_settings()
        workspace_root = Path(settings.workspace.root)
        workflow_path = workspace_root / "PRAETOR_WORKFLOW.md"
        if not workflow_path.exists():
            workflow_path.write_text(DEFAULT_WORKFLOW_CONTRACT, encoding="utf-8")
            try:
                workflow_path.chmod(0o600)
            except OSError:
                pass
        return self.storage.load_workflow_contract(workspace_root)

    def workspace_steward_snapshot(self, mission_id: str | None = None, limit: int = 100) -> WorkspaceStewardSnapshot:
        settings = self._require_settings()
        assets = self.storage.list_file_assets(mission_id=mission_id, limit=limit)
        plans = self.storage.list_workspace_restructure_plans(mission_id=mission_id, limit=20)
        reports = self.storage.list_workspace_reconciliation_reports(mission_id=mission_id, limit=20)
        moves = self.storage.list_file_moves(limit=50)
        self.storage.write_workspace_manifest(Path(settings.workspace.root), self.storage.list_file_assets(limit=100_000))
        return WorkspaceStewardSnapshot(
            assets=assets,
            restructure_plans=plans,
            reconciliation_reports=reports,
            recent_moves=moves,
        )

    def list_workspace_reconciliation_reports(
        self,
        mission_id: str | None = None,
        limit: int = 20,
    ) -> list[WorkspaceReconciliationReport]:
        self._require_settings()
        return self.storage.list_workspace_reconciliation_reports(mission_id=mission_id, limit=limit)

    def reconcile_workspace(self, mission_id: str | None = None) -> WorkspaceReconciliationReport:
        settings = self._require_settings()
        workspace_root = Path(settings.workspace.root).resolve()
        mission = self.get_mission(mission_id) if mission_id else None
        scope = self.storage.load_workspace_scope(workspace_root, mission_id) if mission_id else None
        tracked_assets = self.storage.list_file_assets(mission_id=mission_id, limit=100_000)
        existing_by_path = {asset.current_path: asset for asset in tracked_assets}
        scanned = self._scan_workspace_files(workspace_root)
        scanned_by_path = {item["path"]: item for item in scanned}
        scanned_by_hash: dict[str, list[dict[str, Any]]] = {}
        for item in scanned:
            if item.get("sha256"):
                scanned_by_hash.setdefault(str(item["sha256"]), []).append(item)

        missing: list[WorkspaceReconciliationIssue] = []
        changed: list[WorkspaceReconciliationIssue] = []
        moved: list[WorkspaceReconciliationIssue] = []

        for asset in tracked_assets:
            current = scanned_by_path.get(asset.current_path)
            if current is None:
                candidate = None
                if asset.sha256:
                    candidate = next(
                        (item for item in scanned_by_hash.get(asset.sha256, []) if item["path"] != asset.current_path),
                        None,
                    )
                if candidate is not None:
                    issue = WorkspaceReconciliationIssue(
                        type="moved_candidate",
                        summary=f"Tracked asset appears to have moved: {asset.current_path} -> {candidate['path']}",
                        path=asset.current_path,
                        asset_id=asset.id,
                        candidate_path=str(candidate["path"]),
                        recommended_action="Review and update current_path while preserving previous_paths.",
                        requires_approval=asset.sensitivity in {"confidential", "restricted"},
                    )
                    moved.append(issue)
                    asset = asset.model_copy(
                        update={
                            "exists": False,
                            "sync_status": "moved_candidate",
                            "last_seen_at": utc_now(),
                            "updated_at": utc_now(),
                        }
                    )
                else:
                    issue = WorkspaceReconciliationIssue(
                        type="missing_asset",
                        summary=f"Tracked asset is missing from disk: {asset.current_path}",
                        path=asset.current_path,
                        asset_id=asset.id,
                        recommended_action="Review whether the file was intentionally deleted or moved outside Praetor.",
                        requires_approval=asset.sensitivity in {"confidential", "restricted"},
                    )
                    missing.append(issue)
                    asset = asset.model_copy(
                        update={
                            "exists": False,
                            "sync_status": "missing",
                            "last_seen_at": utc_now(),
                            "updated_at": utc_now(),
                        }
                    )
                self.storage.save_file_asset(asset)
                continue

            updates: dict[str, Any] = {
                "size_bytes": current["size_bytes"],
                "modified_at": current["modified_at"],
                "sha256": current["sha256"],
                "exists": True,
                "last_seen_at": utc_now(),
                "updated_at": utc_now(),
            }
            if asset.sha256 and current["sha256"] and asset.sha256 != current["sha256"]:
                changed.append(
                    WorkspaceReconciliationIssue(
                        type="changed_asset",
                        summary=f"Tracked asset content changed outside its last registry fingerprint: {asset.current_path}",
                        path=asset.current_path,
                        asset_id=asset.id,
                        recommended_action="Register a new document version or accept the external edit into the file registry.",
                        requires_approval=asset.sensitivity in {"confidential", "restricted"},
                    )
                )
                updates["sync_status"] = "changed"
            else:
                updates["sync_status"] = "tracked"
            self.storage.save_file_asset(asset.model_copy(update=updates))

        untracked: list[WorkspaceReconciliationIssue] = []
        for item in scanned:
            path = str(item["path"])
            if path in existing_by_path:
                continue
            if mission_id and not self._path_belongs_to_mission(path, mission, scope):
                continue
            untracked.append(
                WorkspaceReconciliationIssue(
                    type="untracked_file",
                    summary=f"File exists on disk but is not in the Workspace Steward registry: {path}",
                    path=path,
                    recommended_action="Classify and register this file, or ignore it if it is temporary.",
                    requires_approval=self._infer_file_sensitivity(path) in {"confidential", "restricted"},
                )
            )

        git_changes = self._scan_git_changes(workspace_root, mission=mission, scope=scope)
        suggested_actions = []
        if missing:
            suggested_actions.append("Review missing assets before closing the mission.")
        if changed:
            suggested_actions.append("Convert accepted external edits into new document versions or registry fingerprints.")
        if moved:
            suggested_actions.append("Confirm moved candidates and update current_path / previous_paths.")
        if untracked:
            suggested_actions.append("Classify untracked files through Workspace Steward intake.")
        if git_changes:
            suggested_actions.append("Review Git changes and decide whether they should become mission artifacts.")

        report = WorkspaceReconciliationReport(
            mission_id=mission_id,
            scanned_files=len(scanned),
            tracked_assets=len(tracked_assets),
            missing_assets=missing,
            changed_assets=changed,
            moved_candidates=moved,
            untracked_files=untracked[:100],
            git_changes=git_changes[:100],
            suggested_actions=suggested_actions,
        )
        self.storage.save_workspace_reconciliation_report(report)
        self.storage.write_workspace_manifest(workspace_root, self.storage.list_file_assets(limit=100_000))
        self._audit(
            "workspace_reconciliation_completed",
            {
                "report_id": report.id,
                "mission_id": mission_id,
                "scanned_files": report.scanned_files,
                "missing": len(missing),
                "changed": len(changed),
                "moved": len(moved),
                "untracked": len(untracked),
                "git_changes": len(git_changes),
            },
        )
        return report

    def create_workspace_restructure_plan(self, mission_id: str | None = None) -> WorkspaceRestructurePlan:
        settings = self._require_settings()
        workspace_root = Path(settings.workspace.root)
        mission = self.get_mission(mission_id) if mission_id else None
        matter = next(iter(self.storage.list_matters(mission_id=mission_id)), None) if mission_id else None
        assets = self.storage.list_file_assets(mission_id=mission_id, limit=100_000)
        moves: list[FileMoveRecord] = []
        for asset in assets:
            target = self._canonical_asset_path(asset, matter)
            if not target or target == asset.current_path:
                continue
            moves.append(
                FileMoveRecord(
                    asset_id=asset.id,
                    from_path=asset.current_path,
                    to_path=target,
                    reason="Workspace Steward recommends canonical matter/project organization.",
                    requires_approval=asset.sensitivity in {"confidential", "restricted"},
                )
            )
        requires_approval = bool(moves) and (len(moves) > 10 or any(move.requires_approval for move in moves))
        plan = WorkspaceRestructurePlan(
            mission_id=mission.id if mission else None,
            matter_id=matter.id if matter else None,
            client_id=matter.client_id if matter else None,
            summary=f"Workspace Steward reviewed {len(assets)} file asset(s) and proposed {len(moves)} move(s).",
            rationale=(
                "Praetor keeps stable file asset IDs and treats filesystem paths as changeable locations. "
                "This plan can be reviewed before files are moved or Wiki links are updated."
            ),
            moves=moves,
            wiki_updates=[
                "Update wiki links to stable praetor://file/<asset_id> references after move execution."
            ] if moves else [],
            registry_updates=[
                "Update document registry paths and previous_paths after move execution."
            ] if moves else [],
            risks=[
                "Do not execute moves that affect client, legal, privacy, or delivery files without approval.",
                "External links or manually written Markdown paths may need review after restructuring.",
            ] if moves else [],
            requires_approval=requires_approval,
        )
        self.storage.save_workspace_restructure_plan(plan)
        for move in moves:
            self.storage.save_file_move(move)
        self.storage.write_workspace_manifest(workspace_root, self.storage.list_file_assets(limit=100_000))
        self._audit(
            "workspace_restructure_plan_created",
            {
                "plan_id": plan.id,
                "mission_id": mission_id,
                "moves": len(moves),
                "requires_approval": requires_approval,
            },
        )
        return plan

    def _register_requested_output_assets(self, mission: MissionDefinition) -> None:
        for output in mission.requested_outputs:
            self._save_file_asset(
                FileAssetRecord(
                    current_path=self._workspace_relative_path(output),
                    source="requested_output",
                    sensitivity=self._infer_file_sensitivity(output),
                    title=Path(output).name,
                    purpose="Requested mission output.",
                    client_id=mission.client_id,
                    matter_id=mission.matter_id,
                    mission_id=mission.id,
                    steward_notes="Registered from mission requested_outputs.",
                )
            )

    def _register_document_assets(self, document: DocumentRecord) -> None:
        for version in document.versions:
            self._save_file_asset(
                FileAssetRecord(
                    current_path=self._workspace_relative_path(version.path),
                    source="document_version",
                    sensitivity=self._infer_file_sensitivity(version.path),
                    title=document.title,
                    purpose=version.reason,
                    client_id=document.client_id,
                    matter_id=document.matter_id,
                    mission_id=document.mission_id,
                    document_id=document.id,
                    document_version_id=version.id,
                    steward_notes=f"Registered from document registry version v{version.version:03d}.",
                )
            )

    def _register_runtime_output_assets(self, mission: MissionDefinition, changed_files: list[str]) -> None:
        for path in changed_files:
            self._save_file_asset(
                FileAssetRecord(
                    current_path=self._workspace_relative_path(path),
                    source="runtime_output",
                    sensitivity=self._infer_file_sensitivity(path),
                    title=Path(path).name,
                    purpose="Executor changed or generated this file.",
                    client_id=mission.client_id,
                    matter_id=mission.matter_id,
                    mission_id=mission.id,
                    steward_notes="Registered from runtime changed_files.",
                )
            )

    def _save_file_asset(self, asset: FileAssetRecord) -> None:
        settings = self._require_settings()
        workspace_root = Path(settings.workspace.root).resolve()
        fingerprint = self._file_fingerprint(workspace_root / asset.current_path)
        if fingerprint is not None:
            asset = asset.model_copy(
                update={
                    "size_bytes": fingerprint["size_bytes"],
                    "modified_at": fingerprint["modified_at"],
                    "sha256": fingerprint["sha256"],
                    "last_seen_at": utc_now(),
                    "exists": True,
                    "sync_status": "tracked",
                    "updated_at": utc_now(),
                }
            )
        existing = next(
            (
                item
                for item in self.storage.list_file_assets(limit=100_000)
                if item.current_path == asset.current_path
                or (
                    asset.document_version_id is not None
                    and item.document_version_id == asset.document_version_id
                )
            ),
            None,
        )
        if existing is not None:
            asset = existing.model_copy(
                update={
                    "source": asset.source,
                    "sensitivity": asset.sensitivity,
                    "title": asset.title or existing.title,
                    "purpose": asset.purpose or existing.purpose,
                    "client_id": asset.client_id or existing.client_id,
                    "matter_id": asset.matter_id or existing.matter_id,
                    "mission_id": asset.mission_id or existing.mission_id,
                    "document_id": asset.document_id or existing.document_id,
                    "document_version_id": asset.document_version_id or existing.document_version_id,
                    "steward_notes": asset.steward_notes or existing.steward_notes,
                    "updated_at": utc_now(),
                }
            )
        self.storage.save_file_asset(asset)
        self.storage.write_workspace_manifest(Path(settings.workspace.root), self.storage.list_file_assets(limit=100_000))

    def _scan_workspace_files(self, workspace_root: Path) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        skip_dirs = {".git", ".praetor", "node_modules", ".venv", "__pycache__", ".pytest_cache", "dist", "build"}
        for path in workspace_root.rglob("*"):
            if any(part in skip_dirs for part in path.relative_to(workspace_root).parts[:-1]):
                continue
            if not path.is_file():
                continue
            rel = path.relative_to(workspace_root).as_posix()
            fingerprint = self._file_fingerprint(path)
            if fingerprint is None:
                continue
            files.append({"path": rel, **fingerprint})
        return files

    @staticmethod
    def _file_fingerprint(path: Path) -> dict[str, Any] | None:
        try:
            stat = path.stat()
            if not path.is_file():
                return None
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            return {
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=utc_now().tzinfo),
                "sha256": digest.hexdigest(),
            }
        except OSError:
            return None

    def _scan_git_changes(
        self,
        workspace_root: Path,
        *,
        mission: MissionDefinition | None = None,
        scope: WorkspaceScope | None = None,
    ) -> list:
        repos = self._find_git_repos(workspace_root)
        changes = []
        from .models import GitChangeRecord

        for repo in repos:
            try:
                result = subprocess.run(
                    ["git", "-C", str(repo), "status", "--porcelain"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if result.returncode != 0:
                continue
            repo_rel = repo.relative_to(workspace_root).as_posix() if repo != workspace_root else "."
            for line in result.stdout.splitlines():
                if not line:
                    continue
                status = line[:2].strip() or line[:2]
                raw_path = line[3:] if len(line) > 3 else ""
                rel_path = raw_path.split(" -> ")[-1]
                workspace_rel = rel_path if repo_rel == "." else f"{repo_rel}/{rel_path}"
                if mission and not self._path_belongs_to_mission(workspace_rel, mission, scope):
                    continue
                changes.append(GitChangeRecord(repo_path=repo_rel, path=workspace_rel, status=status))
        return changes

    @staticmethod
    def _find_git_repos(workspace_root: Path) -> list[Path]:
        repos = []
        if (workspace_root / ".git").exists():
            repos.append(workspace_root)
        for git_dir in workspace_root.glob("**/.git"):
            repo = git_dir.parent
            if repo == workspace_root:
                continue
            if any(part in {"node_modules", ".praetor"} for part in repo.relative_to(workspace_root).parts):
                continue
            repos.append(repo)
            if len(repos) >= 20:
                break
        return repos

    @staticmethod
    def _path_belongs_to_mission(path: str, mission: MissionDefinition | None, scope: WorkspaceScope | None) -> bool:
        if mission is None:
            return True
        prefixes = [f"Missions/{mission.id}/"]
        if scope is not None:
            prefixes.append(scope.root.rstrip("/") + "/")
        return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)

    def _canonical_asset_path(self, asset: FileAssetRecord, matter: MatterRecord | None = None) -> str | None:
        if matter is None:
            return None
        filename = Path(asset.current_path).name
        if not filename:
            return None
        if asset.document_id or asset.source == "document_version":
            return f"{matter.folder}/versions/{filename}"
        if asset.source == "runtime_output":
            return f"{matter.folder}/outputs/{filename}"
        if asset.source == "requested_output":
            return f"{matter.folder}/requested/{filename}"
        return f"{matter.folder}/files/{filename}"

    @staticmethod
    def _workspace_relative_path(path: str) -> str:
        path = path.strip()
        for prefix in ["/app/workspace/", "/workspace/"]:
            if path.startswith(prefix):
                return path[len(prefix) :].lstrip("/")
        return path.lstrip("/")

    @staticmethod
    def _infer_file_sensitivity(path: str) -> str:
        lowered = path.lower()
        if any(term in lowered for term in ["secret", "token", "key", "credential", "private"]):
            return "restricted"
        if any(term in lowered for term in ["contract", "legal", "合約", "合同", "client", "customer"]):
            return "confidential"
        return "internal"

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
        open_questions = [
            item
            for item in self.storage.list_open_questions(mission_id=mission_id)
            if item.status not in {"answered", "closed"}
        ]
        documents = self.storage.list_documents(mission_id=mission_id)
        knowledge_updates = self.storage.list_knowledge_updates(mission_id=mission_id)
        workspace_scope = self.storage.load_workspace_scope(workspace_root, mission_id)
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
        if open_questions:
            blockers.append(f"Open questions remain: {len(open_questions)}")
        if not workspace_scope:
            blockers.append("Workspace scope has not been defined.")
        knowledge_updates_reviewed = not knowledge_updates or all(
            item.status in {"applied", "rejected"} for item in knowledge_updates
        )
        if not knowledge_updates_reviewed:
            blockers.append("Knowledge updates are still proposed or awaiting approval.")
        documents_registered = bool(documents) or not mission.requested_outputs
        if mission.requested_outputs and not documents_registered:
            blockers.append("Requested documents are not registered.")
        can_close = (
            required_outputs_present
            and delegations_done
            and not pending_escalations
            and final_report_ready
            and not open_questions
            and workspace_scope is not None
            and knowledge_updates_reviewed
        )
        return CompletionContract(
            mission_id=mission_id,
            required_outputs_present=required_outputs_present,
            delegations_done=delegations_done,
            review_passed=review_passed,
            no_pending_escalations=not pending_escalations,
            final_report_ready=final_report_ready,
            memory_updated=memory_updated,
            no_open_questions=not open_questions,
            documents_registered=documents_registered,
            knowledge_updates_reviewed=knowledge_updates_reviewed,
            workspace_scope_defined=workspace_scope is not None,
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

    def latest_governance_review(self) -> GovernanceReview:
        settings = self._require_settings()
        reviews = self.storage.list_governance_reviews(limit=1)
        if reviews:
            latest = reviews[0]
            if settings.review_policy.cadence == "manual":
                return latest
            if settings.review_policy.cadence == "on_open" and utc_now() - latest.created_at < timedelta(hours=6):
                return latest
            if settings.review_policy.cadence == "daily" and utc_now() - latest.created_at < timedelta(hours=24):
                return latest
            if settings.review_policy.cadence == "weekly" and utc_now() - latest.created_at < timedelta(days=7):
                return latest
        return self.run_governance_review(persist=True)

    def run_governance_review(self, *, persist: bool = True) -> GovernanceReview:
        settings = self._require_settings()
        policy = settings.review_policy
        workspace_root = Path(settings.workspace.root)
        missions = self.storage.list_missions(workspace_root)
        now = utc_now()
        items: list[ChairmanInboxItem] = []

        for approval in self.storage.list_approvals():
            if approval.status != "pending":
                continue
            severity = "high" if approval.category in {"external_communication", "spending_money", "delete_files"} else "medium"
            items.append(
                ChairmanInboxItem(
                    title=f"Approval required: {approval.category}",
                    body=approval.reason,
                    severity=severity,
                    kind="pending_decision",
                    href=f"/app/missions/{approval.mission_id}",
                    mission_id=approval.mission_id,
                    created_at=approval.created_at,
                    metadata={"approval_id": approval.id, "category": approval.category},
                )
            )

        for mission in missions:
            if mission.status in {"failed", "paused", "waiting_approval"}:
                severity = "high" if set(mission.domains) & set(policy.always_escalate_domains) else "medium"
                items.append(
                    ChairmanInboxItem(
                        title=f"Mission needs attention: {mission.title}",
                        body=mission.summary or f"Mission status is {mission.status}.",
                        severity=severity,
                        kind="blocked_work",
                        href=f"/app/missions/{mission.id}",
                        mission_id=mission.id,
                        matter_id=mission.matter_id,
                        created_at=mission.updated_at,
                        metadata={"status": mission.status},
                    )
                )
            if mission.status in {"planned", "active", "review", "reviewing", "ready_for_ceo"}:
                age = now - mission.updated_at
                if age >= timedelta(hours=policy.stale_mission_hours):
                    items.append(
                        ChairmanInboxItem(
                            title=f"Stale mission: {mission.title}",
                            body=f"No mission update for at least {policy.stale_mission_hours} hours.",
                            severity="medium",
                            kind="stale_mission",
                            href=f"/app/missions/{mission.id}",
                            mission_id=mission.id,
                            matter_id=mission.matter_id,
                            created_at=mission.updated_at,
                        )
                    )
            if mission.status == "completed":
                contract = self.mission_completion_contract(mission.id)
                if not contract.can_close:
                    items.append(
                        ChairmanInboxItem(
                            title=f"Completed mission needs closeout: {mission.title}",
                            body="Completion contract still has blockers: " + "; ".join(contract.blockers[:3]),
                            severity="medium",
                            kind="closeout_review",
                            href=f"/app/missions/{mission.id}",
                            mission_id=mission.id,
                            matter_id=mission.matter_id,
                            created_at=mission.updated_at,
                            metadata={"blockers": contract.blockers},
                        )
                    )

        for question in self.storage.list_open_questions():
            if question.status in {"answered", "closed"}:
                continue
            items.append(
                ChairmanInboxItem(
                    title="Open question requires a decision",
                    body=question.question,
                    severity="high" if question.status == "waiting_owner" else "medium",
                    kind="open_question",
                    href=f"/app/missions/{question.mission_id}" if question.mission_id else "/app/memory",
                    mission_id=question.mission_id,
                    matter_id=question.matter_id,
                    created_at=question.asked_at,
                    metadata={"owner": question.owner, "blocking": question.blocking},
                )
            )

        stalled_cutoff = now - timedelta(minutes=policy.stalled_run_minutes)
        for attempt in self.storage.list_run_attempts(limit=100):
            if attempt.status in {"failed", "timed_out", "stalled"} or (
                attempt.status not in {"succeeded", "canceled"} and attempt.updated_at <= stalled_cutoff
            ):
                items.append(
                    ChairmanInboxItem(
                        title=f"Run attempt needs review: {attempt.executor or 'executor'}",
                        body=attempt.error or attempt.last_message or f"Run attempt status is {attempt.status}.",
                        severity="medium",
                        kind="run_attempt",
                        href=f"/app/missions/{attempt.mission_id}",
                        mission_id=attempt.mission_id,
                        created_at=attempt.updated_at,
                        metadata={"attempt_id": attempt.id, "status": attempt.status},
                    )
                )

        for update in self.storage.list_knowledge_updates(status="proposed"):
            items.append(
                ChairmanInboxItem(
                    title=f"Knowledge update awaits review: {update.summary}",
                    body=update.content,
                    severity="low",
                    kind="knowledge_update",
                    href=f"/app/missions/{update.mission_id}" if update.mission_id else "/app/memory",
                    mission_id=update.mission_id,
                    matter_id=update.matter_id,
                    created_at=update.created_at,
                    metadata={"target_page": update.target_page},
                )
            )

        severity_order = {"high": 0, "medium": 1, "low": 2}
        items.sort(key=lambda item: (severity_order.get(item.severity, 9), item.created_at), reverse=False)
        items = items[: policy.max_items]
        high_count = len([item for item in items if item.severity == "high"])
        medium_count = len([item for item in items if item.severity == "medium"])
        if not items:
            summary = "Governance review found no formal issues requiring owner attention."
        else:
            summary = f"Governance review found {len(items)} item(s): {high_count} high, {medium_count} medium."
        review = GovernanceReview(
            policy=policy,
            summary=summary,
            items=items,
            next_review_hint=self._next_review_hint(policy),
        )
        if persist:
            self.storage.save_governance_review(review)
            self._audit(
                "governance_review_completed",
                {
                    "review_id": review.id,
                    "items": len(items),
                    "high": high_count,
                    "medium": medium_count,
                    "notification_threshold": policy.notification_threshold,
                },
            )
        return review

    @staticmethod
    def _next_review_hint(policy: ReviewPolicy) -> str:
        if policy.cadence == "daily":
            return "Review again during the next daily governance cycle."
        if policy.cadence == "weekly":
            return "Review again during the next weekly company review."
        if policy.cadence == "manual":
            return "Review again only when the chairman requests it."
        return "Review again when the chairman opens Praetor."

    def list_recent_runs(self, limit: int = 25) -> list[dict]:
        settings = self._require_settings()
        return self.storage.list_recent_runs(Path(settings.workspace.root), limit=limit)

    def list_wiki_pages(self) -> list[dict[str, str]]:
        settings = self._require_settings()
        return self.storage.list_wiki_pages(Path(settings.workspace.root))

    def knowledge_snapshot(self) -> KnowledgeSnapshot:
        self._require_settings()
        return KnowledgeSnapshot(
            clients=self.storage.list_clients(),
            matters=self.storage.list_matters(),
            documents=self.storage.list_documents(),
            decisions=self.storage.list_matter_decisions(),
            open_questions=self.storage.list_open_questions(),
            knowledge_updates=self.storage.list_knowledge_updates(),
        )

    def mission_knowledge_snapshot(self, mission_id: str) -> KnowledgeSnapshot:
        mission = self.get_mission(mission_id)
        matter_id = mission.matter_id
        client_id = mission.client_id
        matters = self.storage.list_matters(mission_id=mission_id)
        if matter_id is None and matters:
            matter_id = matters[0].id
            client_id = matters[0].client_id
        return KnowledgeSnapshot(
            clients=[item for item in self.storage.list_clients() if client_id is None or item.id == client_id],
            matters=matters,
            documents=self.storage.list_documents(matter_id=matter_id, mission_id=mission_id),
            decisions=self.storage.list_matter_decisions(matter_id=matter_id, mission_id=mission_id),
            open_questions=self.storage.list_open_questions(matter_id=matter_id, mission_id=mission_id),
            knowledge_updates=self.storage.list_knowledge_updates(matter_id=matter_id, mission_id=mission_id),
        )

    def mission_memory_promotion_reviews(self, mission_id: str, limit: int = 10) -> list[MemoryPromotionReview]:
        self.get_mission(mission_id)
        return self.storage.list_memory_promotion_reviews(mission_id=mission_id, limit=limit)

    def create_memory_promotion_review(self, mission_id: str) -> MemoryPromotionReview:
        settings = self._require_settings()
        workspace_root = Path(settings.workspace.root)
        mission = self.get_mission(mission_id)
        existing = self.storage.list_memory_promotion_reviews(mission_id=mission_id, limit=1)
        if existing and existing[0].status in {"draft", "ready_for_review"}:
            return existing[0]

        reports = self.storage.read_mission_texts(workspace_root, mission_id)
        decisions = self.storage.list_matter_decisions(mission_id=mission_id)
        questions = self.storage.list_open_questions(mission_id=mission_id)
        documents = self.storage.list_documents(mission_id=mission_id)
        findings: list[PromotionFinding] = []

        for decision in decisions:
            findings.append(
                PromotionFinding(
                    type="decision",
                    summary=decision.summary,
                    disposition="promote_to_decision_record",
                    target="matter_decisions",
                    rationale=decision.rationale,
                    source_ids=[decision.id],
                )
            )
        for question in questions:
            findings.append(
                PromotionFinding(
                    type="open_question",
                    summary=question.question,
                    disposition="track_until_answered" if question.status not in {"answered", "closed"} else "closed",
                    target="open_questions",
                    rationale=question.blocking,
                    source_ids=[question.id],
                )
            )
        for document in documents:
            latest = document.versions[-1] if document.versions else None
            findings.append(
                PromotionFinding(
                    type="document_change",
                    summary=f"{document.title}: v{document.current_version:03d} is {document.status}.",
                    disposition="preserve_in_document_registry",
                    target=latest.path if latest else None,
                    rationale=latest.reason if latest else None,
                    source_ids=[document.id],
                )
            )

        report_text = reports.get("REPORT.md", "").strip()
        if report_text:
            excerpt = report_text.splitlines()[-1][:300]
            findings.append(
                PromotionFinding(
                    type="fact",
                    summary=f"Final report excerpt: {excerpt}",
                    disposition="review_for_wiki_promotion",
                    target="CEO Memory.md",
                    rationale="Generated from owner-visible mission report, not raw chat.",
                )
            )
        findings.append(
            PromotionFinding(
                type="do_not_promote",
                summary="Raw CEO chat, agent turns, and work-session messages remain evidence only.",
                disposition="archive_as_audit_trail",
                target="conversation_logs",
                rationale="Discussion text may include abandoned ideas or unresolved context.",
            )
        )

        proposed_updates = []
        if mission.matter_id and mission.client_id:
            update = KnowledgeUpdate(
                matter_id=mission.matter_id,
                client_id=mission.client_id,
                mission_id=mission.id,
                target_page="CEO Memory.md",
                summary=f"Mission closeout: {mission.title}",
                content="\n".join(
                    [
                        f"Mission: {mission.title}",
                        f"Status: {mission.status}",
                        "Promote only confirmed decisions, document registry facts, and resolved open questions.",
                    ]
                ),
                status="proposed",
            )
            self.storage.save_knowledge_update(update)
            proposed_updates.append(update.id)

        review = MemoryPromotionReview(
            mission_id=mission.id,
            matter_id=mission.matter_id,
            client_id=mission.client_id,
            summary=(
                "Raw discussion is preserved as evidence. This review extracts only decisions, "
                "document facts, open questions, and proposed durable knowledge."
            ),
            findings=findings,
            proposed_knowledge_update_ids=proposed_updates,
        )
        self.storage.save_memory_promotion_review(review)
        self._audit(
            "memory_promotion_review_created",
            {
                "review_id": review.id,
                "mission_id": mission.id,
                "findings": len(findings),
                "proposed_updates": len(proposed_updates),
            },
        )
        return review

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

    def list_board_briefings(self, mission_id: str, limit: int = 10) -> list[BoardBriefing]:
        self.get_mission(mission_id)
        return self.storage.list_board_briefings(mission_id=mission_id, limit=limit)

    def create_board_briefing(self, mission_id: str) -> BoardBriefing:
        settings = self._require_settings()
        workspace_root = Path(settings.workspace.root)
        mission = self.get_mission(mission_id)
        existing = self.storage.list_board_briefings(mission_id=mission_id, limit=1)
        if existing and existing[0].status in {"draft", "ready_for_chairman"}:
            return existing[0]

        roles = self._planning_roles_for_mission(mission)
        team = self._ensure_mission_team(mission, requested_roles=roles)
        agents = self.storage.list_agents(mission_id=mission_id)
        role_to_agent = {agent.role_name: agent for agent in agents}
        delegations = self._ensure_planning_delegations(mission, roles, role_to_agent)

        participants = [role for role in roles if role in role_to_agent or role == "Project Manager"]
        title = f"Board briefing: {mission.title}"
        briefing = BoardBriefing(
            mission_id=mission.id,
            title=title,
            participants=participants,
            executive_summary=(
                f"CEO formed a mission planning team for '{mission.title}'. "
                "The team is expected to clarify scope, assumptions, risks, owner decisions, and the next authorized execution step."
            ),
            recommendations=[
                "Keep this mission in planning until the chairman approves the next execution step.",
                "Separate confirmed decisions from assumptions before promoting anything to company knowledge.",
                "Use the mission workspace as the source of truth for documents, versions, decisions, and open questions.",
            ],
            assumptions=[
                mission.summary or "The chairman's latest instruction is the current source of intent.",
                "Team members may decide low-risk sequencing details inside the mission scope.",
            ],
            risks=[
                "Unverified product, market, legal, or revenue claims must stay as assumptions.",
                "Security, privacy, external communication, spending, and destructive file actions still require escalation.",
            ],
            decisions_needed=[
                "Approve the proposed direction, ask for a revised briefing, or authorize execution.",
                "Confirm which output should become the authoritative deliverable for closeout.",
            ],
            artifacts=[
                f"Missions/{mission.id}/PM_REPORT.md",
                f"Missions/{mission.id}/meetings/",
                *(mission.requested_outputs or []),
            ],
        )
        self.storage.save_board_briefing(briefing)
        self.storage.save_meeting(
            workspace_root,
            MeetingRecord(
                mission_id=mission.id,
                type="project_review",
                moderator="project_manager",
                participants=participants,
                agenda=[
                    "confirm chairman intent",
                    "assign role-specific planning work",
                    "identify assumptions, risks, and decisions needed",
                    "prepare owner-visible board briefing",
                ],
                outputs=[
                    briefing.executive_summary,
                    *briefing.recommendations,
                    f"Delegations opened: {len(delegations)}",
                ],
            ),
        )
        self.storage.append_pm_report(
            workspace_root,
            mission.id,
            "\n".join(
                [
                    f"Board briefing created: {briefing.id}",
                    f"Team: {team.name}",
                    f"Participants: {', '.join(participants)}",
                    "Recommendations:",
                    *[f"- {item}" for item in briefing.recommendations],
                    "Decisions needed:",
                    *[f"- {item}" for item in briefing.decisions_needed],
                ]
            ),
        )
        mission.status = "ready_for_ceo"
        mission.updated_at = utc_now()
        self.storage.save_mission(workspace_root, mission)
        self.storage.append_agent_message(
            AgentMessage(
                mission_id=mission.id,
                role="ceo",
                body=f"Board briefing is ready for chairman review: {briefing.title}",
            )
        )
        self._audit(
            "board_briefing_created",
            {
                "briefing_id": briefing.id,
                "mission_id": mission.id,
                "team_id": team.id,
                "roles": roles,
                "delegations": len(delegations),
            },
        )
        return briefing

    def _planning_roles_for_mission(self, mission: MissionDefinition) -> list[str]:
        roles = ["Project Manager", "Product Manager", "Marketing Lead", "Developer", "Reviewer"]
        text = " ".join([mission.title, mission.summary or "", " ".join(mission.domains)]).lower()
        if any(word in text for word in ["design", "ui", "ux", "logo", "介面", "界面", "設計", "设计"]):
            roles.insert(3, "Design Lead")
        if any(word in text for word in ["sales", "customer", "客戶", "客户", "業務", "銷售", "销售"]):
            roles.append("Sales Manager")
        if any(word in text for word in ["legal", "law", "contract", "合約", "合同", "法律", "法務"]):
            roles.append("Legal Counsel")
        if any(word in text for word in ["security", "privacy", "安全", "隱私", "隐私"]):
            roles.append("Security Officer")
        return list(dict.fromkeys(roles))

    def _ensure_planning_delegations(
        self,
        mission: MissionDefinition,
        roles: list[str],
        role_to_agent: dict[str, AgentInstance],
    ) -> list[DelegationRecord]:
        existing = {
            (delegation.to_role, delegation.title)
            for delegation in self.storage.list_delegations(mission_id=mission.id)
        }
        templates = {
            "Project Manager": (
                "Coordinate planning team",
                "Create the planning sequence, reconcile role outputs, and prepare the owner-visible briefing.",
                ["role outputs are reconciled", "blockers and owner decisions are visible"],
            ),
            "Product Manager": (
                "Define product scope",
                "Clarify user problem, target audience, scope boundaries, success metrics, and first useful version.",
                ["target user is explicit", "scope and success metrics are reviewable"],
            ),
            "Marketing Lead": (
                "Draft market and revenue assumptions",
                "Prepare positioning, audience assumptions, competitive questions, and revenue hypothesis without treating unverified claims as facts.",
                ["assumptions are labeled", "revenue hypothesis is reviewable"],
            ),
            "Design Lead": (
                "Explore interface direction",
                "Propose practical UI/UX directions, key screens, and visual constraints for chairman review.",
                ["design options are understandable", "accessibility and workflow risks are noted"],
            ),
            "Developer": (
                "Assess implementation path",
                "Identify feasible technical approach, first-version milestones, dependencies, and engineering risks.",
                ["first build step is concrete", "technical risks are visible"],
            ),
            "Reviewer": (
                "Prepare acceptance review",
                "Define quality checks, completion criteria, and what would block mission closeout.",
                ["acceptance criteria are clear", "closeout blockers are explicit"],
            ),
            "Legal Counsel": (
                "Review legal exposure",
                "Identify contract, licensing, external claim, or compliance issues that require escalation.",
                ["legal assumptions are separated from advice", "escalation items are visible"],
            ),
            "Security Officer": (
                "Review security and privacy boundaries",
                "Identify user data, credential, file safety, and external sharing risks before execution.",
                ["safety boundaries are explicit", "privacy risks are escalated"],
            ),
            "Sales Manager": (
                "Assess customer-facing path",
                "Draft customer discovery questions, sales assumptions, and external communication risks.",
                ["customer assumptions are explicit", "external communication needs approval"],
            ),
        }
        created: list[DelegationRecord] = []
        for role in roles:
            title, instructions, success_criteria = templates.get(
                role,
                (
                    f"Plan {role} contribution",
                    f"Contribute {role} expertise to the board briefing and report blockers.",
                    ["contribution is clear", "blockers are reported"],
                ),
            )
            if (role, title) in existing:
                continue
            delegation = DelegationRecord(
                mission_id=mission.id,
                from_role="Project Manager" if role != "Project Manager" else "CEO",
                to_role=role,
                to_agent_id=role_to_agent.get(role).id if role_to_agent.get(role) else None,
                title=title,
                instructions=append_safety_policy(
                    instructions,
                    build_prompt_safety_policy(
                        settings=self._require_settings(),
                        standing_orders=self.storage.list_standing_orders(),
                        mission=mission,
                        role_name=role,
                    ).text,
                ),
                success_criteria=success_criteria,
                constraints=[
                    "Do not promote raw discussion into durable memory.",
                    "Escalate security, privacy, legal, spending, external communication, and destructive file actions.",
                ],
            )
            self.storage.save_delegation(delegation)
            self.storage.append_agent_message(
                AgentMessage(
                    mission_id=mission.id,
                    role=self._agent_message_role(role),
                    body=f"Planning delegation received: {title}.",
                )
            )
            created.append(delegation)
        return created

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
        scope = self.mission_workspace_scope(mission_id)
        workflow = self.workflow_contract()
        target_workdir = (Path(settings.workspace.root) / scope.root).resolve()
        runtime_engine = MissionRuntime()
        safety_policy = build_prompt_safety_policy(
            settings=settings,
            standing_orders=self.storage.list_standing_orders(),
            mission=mission,
            role_name="Project Execution",
        ).text
        safety_policy = append_safety_policy(
            safety_policy,
            "\n".join(
                [
                    "Praetor workflow contract:",
                    workflow.body[:4000],
                    "",
                    "Workspace scope:",
                    f"- root: {scope.root}",
                    f"- allowed_write: {', '.join(scope.allowed_write)}",
                    f"- denied_write: {', '.join(scope.denied_write)}",
                ]
            ),
        )

        mission.status = "active"
        mission.updated_at = utc_now()
        workspace_root = Path(settings.workspace.root)
        self.storage.save_mission(workspace_root, mission)
        work_session = self._open_work_session(mission)
        self._append_work_session_turn(
            work_session,
            WorkSessionTurn(
                turn_type="manager_instruction",
                from_role=work_session.manager_role,
                to_role=work_session.executor_role,
                body=(
                    f"Run mission '{mission.title}'. Produce requested outputs, report blockers, "
                    "and escalate safety, privacy, destructive-write, shell, or strategy risks."
                ),
                status="assigned",
            ),
        )

        primary_attempt = self._open_run_attempt(
            mission=mission,
            executor=settings.runtime.executor or settings.runtime.provider or settings.runtime.mode,
            workspace_path=str(target_workdir),
            attempt_number=1,
        )
        self._update_run_attempt(primary_attempt, "building_prompt", "Built mission prompt with workflow contract.")
        self._update_run_attempt(primary_attempt, "launching_agent", "Launching primary executor.")
        primary_result = runtime_engine.run_mission(
            workspace_root=workspace_root,
            mission=mission,
            runtime=settings.runtime,
            permissions=settings.workspace.permissions,
            safety_policy=safety_policy,
            target_workdir=target_workdir,
        )
        self._finish_run_attempt(primary_attempt, primary_result.task.id, primary_result.run_record)
        self.storage.save_task(workspace_root, primary_result.task)
        self.storage.save_bridge_run(workspace_root, mission.id, primary_result.run_record.model_dump(mode="json"))
        work_session.executor = primary_result.task.current_executor
        self._record_executor_turn(work_session, primary_result.task.id, primary_result.run_record)
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
                self._append_work_session_turn(
                    work_session,
                    WorkSessionTurn(
                        turn_type="manager_decision",
                        from_role=work_session.manager_role,
                        to_role=work_session.executor_role,
                        body=(
                            f"Primary executor returned {primary_result.run_record.normalized_status}; "
                            f"PM is switching to fallback runtime {fallback_runtime.mode}."
                        ),
                        status="fallback_started",
                        task_id=primary_result.task.id,
                        run_id=primary_result.run_record.run_id,
                    ),
                )
                self._audit(
                    "mission_run_fallback_started",
                    {
                        "mission_id": mission.id,
                        "from_runtime": settings.runtime.mode,
                        "to_runtime": fallback_runtime.mode,
                        "from_executor": primary_result.run_record.executor,
                    },
                )
                fallback_attempt = self._open_run_attempt(
                    mission=mission,
                    executor=fallback_runtime.executor or fallback_runtime.provider or fallback_runtime.mode,
                    workspace_path=str(target_workdir),
                    attempt_number=2,
                )
                self._update_run_attempt(fallback_attempt, "launching_agent", "Launching fallback executor.")
                fallback_result = runtime_engine.run_mission(
                    workspace_root=workspace_root,
                    mission=mission,
                    runtime=fallback_runtime,
                    permissions=settings.workspace.permissions,
                    safety_policy=safety_policy,
                    target_workdir=target_workdir,
                )
                self._finish_run_attempt(fallback_attempt, fallback_result.task.id, fallback_result.run_record)
                self.storage.save_task(workspace_root, fallback_result.task)
                self.storage.save_bridge_run(
                    workspace_root,
                    mission.id,
                    fallback_result.run_record.model_dump(mode="json"),
                )
                work_session.executor = fallback_result.task.current_executor
                self._record_executor_turn(work_session, fallback_result.task.id, fallback_result.run_record)
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
        self._record_manager_decision(work_session, mission.status, final_result.task.id, final_result.run_record)
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
        self._register_runtime_output_assets(mission, final_result.run_record.changed_files)
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
            "work_session": work_session,
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
            governance_review=self.latest_governance_review(),
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
        for session in self.storage.list_work_sessions(mission_id=mission_id, limit=20):
            events.append(
                MissionTimelineEvent(
                    id=session.id,
                    mission_id=mission_id,
                    type="audit",
                    title=f"Work session: {session.status}",
                    body=session.current_blocker or f"{session.manager_role} managing {session.executor_role}",
                    actor=session.manager_role,
                    status=session.status,
                    created_at=session.updated_at,
                    metadata={"turns": len(session.turns), "executor": session.executor},
                )
            )
        events.sort(key=lambda item: item.created_at)
        return events

    def mission_agent_messages(self, mission_id: str, limit: int = 100) -> list[AgentMessage]:
        settings = self._require_settings()
        if self.storage.load_mission(Path(settings.workspace.root), mission_id) is None:
            raise KeyError(mission_id)
        return self.storage.list_agent_messages(mission_id=mission_id, limit=limit)

    def mission_work_sessions(self, mission_id: str, limit: int = 20) -> list[WorkSession]:
        settings = self._require_settings()
        if self.storage.load_mission(Path(settings.workspace.root), mission_id) is None:
            raise KeyError(mission_id)
        return self.storage.list_work_sessions(mission_id=mission_id, limit=limit)

    def _open_run_attempt(
        self,
        *,
        mission: MissionDefinition,
        executor: str,
        workspace_path: str,
        attempt_number: int,
    ) -> RunAttempt:
        attempt = RunAttempt(
            mission_id=mission.id,
            attempt=attempt_number,
            status="preparing_workspace",
            executor=executor,
            workspace_path=workspace_path,
            last_event="preparing_workspace",
            last_message="Preparing isolated mission workspace.",
        )
        self.storage.save_run_attempt(attempt)
        self._audit(
            "run_attempt_started",
            {
                "attempt_id": attempt.id,
                "mission_id": mission.id,
                "executor": executor,
                "workspace_path": workspace_path,
            },
        )
        return attempt

    def _update_run_attempt(
        self,
        attempt: RunAttempt,
        status: str,
        message: str,
        *,
        error: str | None = None,
    ) -> RunAttempt:
        attempt.status = status
        attempt.last_event = status
        attempt.last_message = message
        attempt.error = error
        attempt.updated_at = utc_now()
        self.storage.save_run_attempt(attempt)
        return attempt

    def _finish_run_attempt(self, attempt: RunAttempt, task_id: str, run_record) -> RunAttempt:
        normalized = run_record.normalized_status or run_record.status
        attempt.task_id = task_id
        attempt.run_id = run_record.run_id
        attempt.executor = run_record.executor
        attempt.status = "succeeded" if normalized == "completed" else "failed"
        attempt.last_event = normalized
        attempt.last_message = run_record.pause_reason or run_record.stdout_tail or f"Executor finished with {normalized}."
        attempt.error = run_record.stderr_tail if attempt.status == "failed" else None
        attempt.input_tokens = run_record.usage.input_tokens or 0
        attempt.output_tokens = run_record.usage.output_tokens or 0
        attempt.total_tokens = attempt.input_tokens + attempt.output_tokens
        attempt.turn_count += 1
        attempt.finished_at = run_record.finished_at or utc_now()
        attempt.updated_at = utc_now()
        self.storage.save_run_attempt(attempt)
        self._audit(
            "run_attempt_finished",
            {
                "attempt_id": attempt.id,
                "mission_id": attempt.mission_id,
                "run_id": attempt.run_id,
                "status": attempt.status,
                "normalized_status": normalized,
            },
        )
        return attempt

    def _open_work_session(self, mission: MissionDefinition) -> WorkSession:
        session = WorkSession(
            mission_id=mission.id,
            manager_role="project_manager" if mission.pm_required else "praetor",
            executor_role="developer",
            status="running",
            completion_contract=[
                "requested outputs are present or explicitly waived",
                "executor result is reviewed by the manager",
                "blockers and escalation needs are recorded",
                "owner-visible report is updated",
            ],
        )
        self.storage.save_work_session(session)
        self._audit("work_session_opened", {"session_id": session.id, "mission_id": mission.id, "manager_role": session.manager_role})
        return session

    def _append_work_session_turn(self, session: WorkSession, turn: WorkSessionTurn) -> None:
        session.turns.append(turn)
        session.updated_at = utc_now()
        self.storage.save_work_session(session)

    def _record_executor_turn(self, session: WorkSession, task_id: str, run_record) -> None:
        normalized = run_record.normalized_status or run_record.status
        turn_type = "executor_result"
        body = (
            f"Executor returned {normalized}. "
            f"Changed files: {', '.join(run_record.changed_files) or 'none'}."
        )
        if normalized in {"paused_budget", "paused_decision", "paused_risk", "interactive_approval_required", "auth_required"}:
            turn_type = "executor_question"
            body = run_record.pause_reason or f"Executor needs manager or owner action: {normalized}."
            session.status = "waiting_manager"
            session.current_blocker = body
        self._append_work_session_turn(
            session,
            WorkSessionTurn(
                turn_type=turn_type,
                from_role=session.executor_role,
                to_role=session.manager_role,
                body=body,
                status=normalized,
                task_id=task_id,
                run_id=run_record.run_id,
                metadata={
                    "executor": run_record.executor,
                    "changed_files": run_record.changed_files,
                    "pause_reason": run_record.pause_reason,
                },
            ),
        )

    def _record_manager_decision(self, session: WorkSession, mission_status: str, task_id: str, run_record) -> None:
        normalized = run_record.normalized_status or run_record.status
        if mission_status == "completed":
            session.status = "completed"
            session.current_blocker = None
            body = "PM reviewed the executor result and marked the session completed."
            turn_status = "completed"
        elif mission_status == "waiting_approval":
            session.status = "waiting_approval"
            session.current_blocker = run_record.pause_reason or f"Approval required after executor status {normalized}."
            body = f"PM escalated this blocker into Praetor approval flow: {session.current_blocker}"
            turn_status = "escalated"
        elif mission_status == "paused":
            session.status = "blocked"
            session.current_blocker = run_record.pause_reason or f"Mission paused after executor status {normalized}."
            body = f"PM blocked the session until the executor issue is resolved: {session.current_blocker}"
            turn_status = "blocked"
        else:
            session.status = "failed"
            session.current_blocker = run_record.stderr_tail or run_record.stdout_tail or f"Executor status {normalized}."
            body = f"PM marked the session failed and preserved the executor output for review: {session.current_blocker}"
            turn_status = "failed"
        self._append_work_session_turn(
            session,
            WorkSessionTurn(
                turn_type="manager_decision",
                from_role=session.manager_role,
                to_role="ceo" if session.status in {"waiting_approval", "blocked", "failed"} else session.executor_role,
                body=body,
                status=turn_status,
                task_id=task_id,
                run_id=run_record.run_id,
            ),
        )
        self._audit(
            "work_session_updated",
            {
                "session_id": session.id,
                "mission_id": session.mission_id,
                "status": session.status,
                "current_blocker": session.current_blocker,
            },
        )

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

        if action.type == "board_briefing":
            mission_id = action.mission_id or related_mission_id
            if not mission_id:
                return action.model_copy(
                    update={
                        "status": "skipped",
                        "metadata": {**action.metadata, "skip_reason": "board briefing requires a mission_id"},
                    }
                )
            briefing = self.create_board_briefing(mission_id)
            return action.model_copy(update={"status": "applied", "mission_id": mission_id, "result_id": briefing.id})

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
