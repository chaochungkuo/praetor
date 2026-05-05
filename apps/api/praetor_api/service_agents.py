from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .models import (
    AgentEmploymentContract,
    AgentInstance,
    AgentMessage,
    AgentPermissionProfile,
    AgentRoleSpec,
    AgentSkillSpec,
    DelegationRecord,
    ExecutiveCadence,
    ExecutorControlRecord,
    MissionDefinition,
    MissionStageTransition,
    MissionTeam,
    OrganizationSnapshot,
    TeamTemplate,
    WorkTraceEvent,
    utc_now,
)
from .safety_policy import append_safety_policy, build_prompt_safety_policy


class AgentsMixin:
    """Agent and team lifecycle, org snapshot, planning delegations."""

    def _ensure_mission_team(self, mission: MissionDefinition, requested_roles: list[str] | None = None) -> MissionTeam:
        self._ensure_default_team_templates()

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
            self._record_work_trace(
                mission_id=mission.id,
                layer="manager",
                event_type="team_expanded",
                title="Mission team expanded",
                body=f"Added roles: {', '.join(missing_roles)}",
                actor="praetor",
                status="active",
            )

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
        self._record_work_trace(
            mission_id=mission.id,
            layer="manager",
            event_type="team_created",
            title="Mission team created",
            body=f"Created team with roles: {', '.join([agent.role_name for agent in agents])}",
            actor="praetor",
            status="active",
        )

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
        template = self._team_template_for_mission(mission)
        if template is not None:
            roles = list(template.roles)

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
        self._ensure_default_permission_profiles()

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

        permission_profile = self._permission_profile_for_role(role.name)

        agent = AgentInstance(

            role_name=role.name,

            display_name=f"{role.name} - {mission.title[:48]}",

            mission_id=mission.id,

            supervisor_role=role.default_supervisor_role,

            charter=self._agent_charter(role, mission),

            skills=self._skills_for_agent(role, mission),

            tools=role.tools,

            permission_profile=permission_profile.name,

            memory_access=["company_dna", "standing_orders", f"mission:{mission.id}"],

            decision_authority=role.decision_authority,

            escalation_triggers=role.escalation_triggers,

        )

        self.storage.save_agent(agent)
        contract = self._create_agent_contract(agent, role, permission_profile, mission)

        self.storage.append_agent_message(

            AgentMessage(

                mission_id=mission.id,

                role=self._agent_message_role(role.name),

                body=f"Onboarded as {role.name}. Charter: {agent.charter}",

            )

        )
        self._record_work_trace(
            mission_id=mission.id,
            layer="manager",
            event_type="agent_onboarded",
            title=f"{role.name} onboarded",
            body=f"Employment contract {contract.id} created with {permission_profile.name} permissions.",
            actor="praetor",
            status="active",
            metadata={"agent_id": agent.id, "contract_id": contract.id},
        )

        return agent





    def _skills_for_agent(self, role: AgentRoleSpec, mission: MissionDefinition) -> list[str]:

        base_skills = list(role.skills)

        recommended = self._recommend_agent_skills(role, mission)

        imported_names = [skill.name for skill in recommended]

        return list(dict.fromkeys([*base_skills, *imported_names]))





    def _recommend_agent_skills(self, role: AgentRoleSpec, mission: MissionDefinition, limit: int = 4) -> list[AgentSkillSpec]:

        text = " ".join(

            [

                role.name,

                role.purpose,

                " ".join(role.skills),

                mission.title,

                mission.summary or "",

                " ".join(mission.domains),

            ]

        ).lower()

        scored: list[tuple[int, AgentSkillSpec]] = []

        for skill in self.storage.list_agent_skills():

            if skill.status not in {"approved"}:

                continue

            score = 0

            terms = [skill.name, *(skill.domains or []), *(skill.suitable_for or []), *(skill.responsibilities[:4] or [])]

            for term in terms:

                for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", str(term).lower()):

                    if token in text:

                        score += 1

            if role.name.lower().replace(" ", "") in (skill.source_path or "").lower().replace("-", "").replace("_", ""):

                score += 3

            if mission.domains and set(mission.domains).intersection(set(skill.domains)):

                score += 4

            if score:

                scored.append((score, skill))

        scored.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)

        return [skill for _, skill in scored[:limit]]





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

    def _ensure_default_permission_profiles(self) -> None:
        existing = {profile.name for profile in self.storage.list_agent_permission_profiles()}
        defaults = [
            AgentPermissionProfile(
                name="restricted_planner",
                level="strict",
                description="Can analyze, plan, and draft. Cannot change files or call external systems without approval.",
                allowed_tools=["read_workspace", "search_memory", "draft_documents"],
                allowed_workspace_scopes=["mission", "wiki"],
                forbidden_actions=["delete_files", "external_communication", "spending_money", "shell_commands"],
                required_approvals=["write_files", "external_communication", "credential_access"],
                memory_access=["company_dna", "standing_orders", "mission_context"],
                max_autonomy="strict",
            ),
            AgentPermissionProfile(
                name="standard_operator",
                level="standard",
                description="Can work inside assigned mission folders and propose durable memory updates.",
                allowed_tools=["read_workspace", "write_mission_workspace", "search_memory", "draft_documents"],
                allowed_workspace_scopes=["mission", "matter", "wiki"],
                forbidden_actions=["delete_protected_files", "external_communication", "spending_money"],
                required_approvals=["delete_files", "strategy_change", "privacy_sensitive_output"],
                memory_access=["company_dna", "standing_orders", "mission_context", "approved_knowledge"],
                max_autonomy="hybrid",
            ),
            AgentPermissionProfile(
                name="execution_worker",
                level="trusted",
                description="Can run scoped implementation work inside the approved workspace with trace logging.",
                allowed_tools=["read_workspace", "write_mission_workspace", "shell_commands", "tests"],
                allowed_workspace_scopes=["mission", "project_repository"],
                forbidden_actions=["credential_exfiltration", "write_outside_workspace", "external_spending"],
                required_approvals=["delete_files", "network_publish", "security_boundary_change"],
                memory_access=["mission_context", "approved_knowledge", "work_artifacts"],
                max_autonomy="hybrid",
            ),
            AgentPermissionProfile(
                name="risk_review",
                level="risk_review",
                description="Can inspect outputs and block closeout when privacy, security, legal, or quality risk remains.",
                allowed_tools=["read_workspace", "search_memory", "audit_trace"],
                allowed_workspace_scopes=["mission", "wiki", "decisions"],
                forbidden_actions=["mutate_outputs_without_assignment", "external_communication"],
                required_approvals=["override_review_blocker"],
                memory_access=["company_dna", "standing_orders", "mission_context", "approved_knowledge"],
                max_autonomy="strict",
            ),
        ]
        for profile in defaults:
            if profile.name not in existing:
                self.storage.save_agent_permission_profile(profile)

    def _permission_profile_for_role(self, role_name: str) -> AgentPermissionProfile:
        self._ensure_default_permission_profiles()
        profiles = {profile.name: profile for profile in self.storage.list_agent_permission_profiles()}
        if role_name in {"Developer"}:
            return profiles["execution_worker"]
        if role_name in {"Reviewer", "Security Officer", "Legal Counsel"}:
            return profiles["risk_review"]
        if role_name in {"CEO", "Project Manager"}:
            return profiles["standard_operator"]
        return profiles["restricted_planner"]

    def _create_agent_contract(
        self,
        agent: AgentInstance,
        role: AgentRoleSpec,
        permission_profile: AgentPermissionProfile,
        mission: MissionDefinition,
    ) -> AgentEmploymentContract:
        existing = [item for item in self.storage.list_agent_contracts(mission_id=mission.id) if item.agent_id == agent.id]
        if existing:
            return existing[0]
        contract = AgentEmploymentContract(
            agent_id=agent.id,
            mission_id=mission.id,
            role_name=agent.role_name,
            title=f"{agent.role_name} contract for {mission.title}",
            charter=agent.charter,
            permission_profile=permission_profile.name,
            skills=agent.skills,
            tools=agent.tools,
            memory_access=agent.memory_access,
            decision_authority=agent.decision_authority,
            escalation_triggers=agent.escalation_triggers,
            completion_criteria=[
                "Report progress in work trace.",
                "Separate draft discussion from approved memory.",
                "Escalate restricted actions before execution.",
                "List outputs, tests, blockers, and open questions before closeout.",
            ],
        )
        self.storage.save_agent_contract(contract)
        return contract

    def _ensure_default_team_templates(self) -> None:
        existing = {template.name for template in self.storage.list_team_templates()}
        defaults = [
            TeamTemplate(
                name="Product launch cell",
                purpose="Plan and execute a new product or feature with product, design, engineering, marketing, and review coverage.",
                domains=["product", "engineering", "design", "marketing"],
                roles=["Project Manager", "Product Manager", "Design Lead", "Developer", "Marketing Lead", "Reviewer"],
                default_outputs=["product brief", "execution plan", "UI options", "release risk review"],
                escalation_policy=["strategy changes go to CEO", "external promises require chairman approval"],
            ),
            TeamTemplate(
                name="Contract matter cell",
                purpose="Handle customer contracts with workspace organization, document versions, legal review, and decision capture.",
                domains=["legal", "client", "documents"],
                roles=["Project Manager", "Legal Counsel", "Reviewer"],
                default_outputs=["contract draft", "version history", "legal risk memo", "open questions"],
                escalation_policy=["legal commitments require chairman approval", "external communication requires approval"],
            ),
            TeamTemplate(
                name="Security review cell",
                purpose="Assess privacy, credential, computer-safety, and release risks before broad use.",
                domains=["security", "privacy"],
                roles=["Project Manager", "Security Officer", "Developer", "Reviewer"],
                default_outputs=["risk register", "mitigation plan", "verification evidence"],
                escalation_policy=["privacy and host-safety decisions go to chairman"],
            ),
        ]
        for template in defaults:
            if template.name not in existing:
                self.storage.save_team_template(template)

    def _team_template_for_mission(self, mission: MissionDefinition) -> TeamTemplate | None:
        self._ensure_default_team_templates()
        text = " ".join([mission.title, mission.summary or "", " ".join(mission.domains)]).lower()
        templates = self.storage.list_team_templates()
        scored: list[tuple[int, TeamTemplate]] = []
        for template in templates:
            score = sum(1 for domain in template.domains if domain.lower() in text)
            if template.name == "Contract matter cell" and any(word in text for word in ["contract", "合約", "合同", "legal"]):
                score += 3
            if template.name == "Product launch cell" and any(word in text for word in ["product", "feature", "ui", "ux", "產品", "功能"]):
                score += 3
            if template.name == "Security review cell" and any(word in text for word in ["security", "privacy", "安全", "隱私", "隐私"]):
                score += 3
            if score:
                scored.append((score, template))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1] if scored else None

    def _ensure_default_executive_cadences(self) -> None:
        existing = {cadence.name for cadence in self.storage.list_executive_cadences()}
        defaults = [
            ExecutiveCadence(
                name="Approval required",
                cadence_type="event",
                description="Notify only when a mission requires chairman approval, legal/privacy/security decision, or blocked work.",
                notification_threshold="approval_required",
                silent_if_clear=True,
            ),
            ExecutiveCadence(
                name="Executive digest",
                cadence_type="manual",
                description="Generate a concise chairman briefing on demand instead of sending frequent assistant-style updates.",
                notification_threshold="digest",
                silent_if_clear=True,
            ),
        ]
        for cadence in defaults:
            if cadence.name not in existing:
                self.storage.save_executive_cadence(cadence)

    def _transition_mission_stage(
        self,
        mission: MissionDefinition,
        stage: str,
        reason: str,
        actor: str = "praetor",
    ) -> MissionStageTransition:
        if mission.current_stage == stage and self.storage.list_mission_stage_transitions(mission.id):
            return self.storage.list_mission_stage_transitions(mission.id)[-1]
        mission.current_stage = stage  # type: ignore[assignment]
        mission.updated_at = utc_now()
        settings = self._require_settings()
        self.storage.save_mission(Path(settings.workspace.root), mission)
        transition = MissionStageTransition(
            mission_id=mission.id,
            stage=stage,  # type: ignore[arg-type]
            actor=actor,
            reason=reason,
            status_snapshot=mission.status,
        )
        self.storage.save_mission_stage_transition(transition)
        self._record_work_trace(
            mission_id=mission.id,
            layer="system",
            event_type="stage_transition",
            title=f"Mission stage: {stage}",
            body=reason,
            actor=actor,
            status=mission.status,
        )
        return transition

    def _record_work_trace(
        self,
        mission_id: str | None,
        layer: str,
        event_type: str,
        title: str,
        body: str | None = None,
        actor: str = "praetor",
        status: str = "recorded",
        metadata: dict[str, Any] | None = None,
    ) -> WorkTraceEvent:
        event = WorkTraceEvent(
            mission_id=mission_id,
            layer=layer,  # type: ignore[arg-type]
            event_type=event_type,
            title=title,
            body=body,
            actor=actor,
            status=status,
            metadata=metadata or {},
        )
        self.storage.save_work_trace_event(event)
        return event

    def mission_stage_transitions(self, mission_id: str) -> list[MissionStageTransition]:
        return self.storage.list_mission_stage_transitions(mission_id=mission_id)

    def mission_work_trace(self, mission_id: str, limit: int = 100) -> list[WorkTraceEvent]:
        return self.storage.list_work_trace_events(mission_id=mission_id, limit=limit)

    def mission_agent_contracts(self, mission_id: str) -> list[AgentEmploymentContract]:
        return self.storage.list_agent_contracts(mission_id=mission_id)

    def request_executor_control(
        self,
        mission_id: str,
        action: str,
        reason: str | None = None,
        target_session_id: str | None = None,
    ) -> ExecutorControlRecord:
        self.get_mission(mission_id)
        control = ExecutorControlRecord(
            mission_id=mission_id,
            action=action,  # type: ignore[arg-type]
            target_session_id=target_session_id,
            reason=reason,
        )
        self.storage.save_executor_control(control)
        self._record_work_trace(
            mission_id=mission_id,
            layer="chairman",
            event_type="executor_control",
            title=f"Executor control: {action}",
            body=reason,
            actor="chairman",
            status="requested",
            metadata={"control_id": control.id, "target_session_id": target_session_id},
        )
        return control

    def set_agent_skill_status(self, skill_id: str, status: str) -> AgentSkillSpec:
        allowed = {"approved", "rejected", "deprecated", "imported_requires_review"}
        if status not in allowed:
            raise ValueError("Unsupported skill status.")
        for skill in self.storage.list_agent_skills():
            if skill.id == skill_id:
                skill.status = status  # type: ignore[assignment]
                skill.updated_at = utc_now()
                self.storage.save_agent_skill(skill)
                self._record_work_trace(
                    mission_id=None,
                    layer="review",
                    event_type="skill_review",
                    title=f"Skill {status}: {skill.name}",
                    body=skill.description,
                    actor="praetor",
                    status=status,
                    metadata={"skill_id": skill.id, "source_id": skill.source_id},
                )
                return skill
        raise KeyError(f"Skill not found: {skill_id}")



    @staticmethod



    def _agent_message_role(role_name: str) -> str:

        return role_name.lower().replace(" ", "_").replace("-", "_")





    def organization_snapshot(self, mission_id: str | None = None) -> OrganizationSnapshot:

        self._require_settings()

        self._ensure_default_agent_roles()

        self._ensure_default_standing_orders()
        self._ensure_default_permission_profiles()
        self._ensure_default_team_templates()
        self._ensure_default_executive_cadences()

        return OrganizationSnapshot(

            agent_roles=self.storage.list_agent_roles(),

            agents=self.storage.list_agents(mission_id=mission_id),

            permission_profiles=self.storage.list_agent_permission_profiles(),

            agent_contracts=self.storage.list_agent_contracts(mission_id=mission_id),

            team_templates=self.storage.list_team_templates(),

            executive_cadences=self.storage.list_executive_cadences(),

            teams=self.storage.list_teams(mission_id=mission_id),

            delegations=self.storage.list_delegations(mission_id=mission_id),

            escalations=self.storage.list_escalations(mission_id=mission_id),

            standing_orders=self.storage.list_standing_orders(),

            skill_sources=self.storage.list_skill_sources(),

            skill_registry=self.storage.list_agent_skills(),

        )





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

