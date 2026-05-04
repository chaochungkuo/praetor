from __future__ import annotations

import re
from typing import Any

from .models import (
    AgentInstance,
    AgentMessage,
    AgentRoleSpec,
    AgentSkillSpec,
    DelegationRecord,
    MissionDefinition,
    MissionTeam,
    OrganizationSnapshot,
    utc_now,
)
from .safety_policy import append_safety_policy, build_prompt_safety_policy


class AgentsMixin:
    """Agent and team lifecycle, org snapshot, planning delegations."""

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

            skills=self._skills_for_agent(role, mission),

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

            if skill.status not in {"imported_requires_review", "approved", "active"}:

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



    @staticmethod



    def _agent_message_role(role_name: str) -> str:

        return role_name.lower().replace(" ", "_").replace("-", "_")





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




