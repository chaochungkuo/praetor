from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from .models import PlannerAction, PlannerPlan, RuntimeSelection
from .config import (
    get_anthropic_api_key,
    get_ceo_planner_mode,
    get_ceo_planner_model,
    get_ceo_planner_provider,
    get_openai_api_key,
)
from .providers import ApiProviderError, generate_json_response, parse_generation_payload


@dataclass(frozen=True)
class CEOPlannerContext:
    instruction: str
    related_mission_id: str | None
    mission_count: int
    pending_approvals: int
    safety_policy: str = ""


class CEOPlanner(Protocol):
    def plan(self, context: CEOPlannerContext) -> PlannerPlan:
        ...


class DeterministicCEOPlanner:
    def plan(self, context: CEOPlannerContext) -> PlannerPlan:
        text = context.instruction.strip()
        lowered = text.lower()
        actions: list[PlannerAction] = []
        intent = "briefing"

        wants_staffing = self._wants_staffing(lowered)
        wants_board_briefing = self._wants_board_briefing(lowered)
        wants_new_mission = self._wants_mission(lowered) and not (
            context.related_mission_id and wants_staffing and not self._explicit_new_mission(lowered)
        )

        if wants_new_mission:
            title, summary = self._mission_fields(text)
            actions.append(
                PlannerAction(
                    type="mission_draft",
                    title=title,
                    body=summary,
                    metadata={
                        "domains": self._domains(lowered),
                        "priority": self._priority(lowered),
                        "requested_outputs": [],
                        "auto_create": True,
                    },
                )
            )
            intent = "mission_draft"

        if self._wants_approval(lowered):
            actions.append(
                PlannerAction(
                    type="approval_request",
                    title="Chairman decision checkpoint",
                    body="CEO raised a decision checkpoint from the chairman conversation.",
                    mission_id=context.related_mission_id,
                    metadata={
                        "category": "change_strategy",
                        "requires_existing_mission": True,
                    },
                )
            )
            if intent == "briefing":
                intent = "approval_request"

        if self._wants_memory(lowered):
            actions.append(
                PlannerAction(
                    type="memory_update",
                    title="CEO conversation memory",
                    body=text,
                    metadata={
                        "page": "CEO Memory.md",
                        "source": "office_conversation",
                    },
                )
            )
            if intent == "briefing":
                intent = "memory_update"

        if wants_staffing:
            roles = self._staffing_roles(lowered)
            actions.append(
                PlannerAction(
                    type="staffing_proposal",
                    title="AI organization staffing proposal",
                    body="CEO recommends forming a mission team with explicit reporting lines, skills, and escalation rules.",
                    mission_id=context.related_mission_id,
                    metadata={"roles": roles, "requires_existing_mission": True},
                )
            )
            if context.related_mission_id:
                actions.append(
                    PlannerAction(
                        type="delegation_create",
                        title="Create mission operating plan",
                        body="Convert chairman intent into work orders, blockers, review criteria, and escalation checkpoints.",
                        mission_id=context.related_mission_id,
                        metadata={
                            "to_role": "Project Manager",
                            "success_criteria": [
                                "team roles are clear",
                                "work orders have owners",
                                "review and escalation checkpoints are visible",
                            ],
                            "constraints": ["escalate safety, privacy, legal, spending, or destructive actions"],
                        },
                    )
                )
            if intent == "briefing":
                intent = "staffing_proposal"

        if wants_board_briefing:
            actions.append(
                PlannerAction(
                    type="board_briefing",
                    title="Prepare board briefing",
                    body=(
                        "Form the mission planning team, assign role-specific planning work, "
                        "and produce an owner-visible briefing before execution."
                    ),
                    mission_id=context.related_mission_id,
                    metadata={"requires_existing_mission": True},
                )
            )
            if intent == "briefing":
                intent = "board_briefing"

        if self._wants_escalation(lowered):
            actions.append(
                PlannerAction(
                    type="decision_escalation",
                    title="Chairman escalation rule",
                    body="This instruction touches authority boundaries or sensitive operating policy and should be visible as an escalation.",
                    mission_id=context.related_mission_id,
                    metadata={"to_level": "chairman", "category": "change_strategy"},
                )
            )
            if intent == "briefing":
                intent = "decision_escalation"

        if self._wants_standing_order(lowered):
            actions.append(
                PlannerAction(
                    type="standing_order_update",
                    title="Chairman standing order",
                    body=text,
                    metadata={"scope": self._standing_order_scope(lowered), "effect": "governance_rule"},
                )
            )
            if intent == "briefing":
                intent = "standing_order_update"

        if not actions:
            actions.append(
                PlannerAction(
                    type="briefing",
                    title="Executive briefing",
                    body=(
                        f"Current mission count: {context.mission_count}. "
                        f"Pending approvals: {context.pending_approvals}."
                    ),
                )
            )

        return PlannerPlan(
            intent=intent,
            response=self._response(intent, context, actions),
            actions=actions,
        )

    @staticmethod
    def _wants_mission(lowered: str) -> bool:
        return any(
            word in lowered
            for word in ["create", "start", "建立", "新增", "開始", "开始", "任務", "任务", "專案", "项目", "project", "mission"]
        )

    @staticmethod
    def _explicit_new_mission(lowered: str) -> bool:
        return any(word in lowered for word in ["建立任務", "新增任務", "create mission", "new mission", "mission:"])

    @staticmethod
    def _wants_approval(lowered: str) -> bool:
        return any(word in lowered for word in ["approval", "approve", "批准", "核准", "決策", "checkpoint"])

    @staticmethod
    def _wants_memory(lowered: str) -> bool:
        return any(word in lowered for word in ["memory", "remember", "記住", "記憶", "保存", "原則"])

    @staticmethod
    def _wants_staffing(lowered: str) -> bool:
        return any(
            word in lowered
            for word in [
                "staff",
                "staffing",
                "agent",
                "team",
                "hire",
                "role",
                "pm",
                "project manager",
                "reviewer",
                "lawyer",
                "legal",
                "security",
                "sales",
                "組隊",
                "團隊",
                "团队",
                "角色",
                "法務",
                "法律",
                "律師",
                "安全",
                "隱私",
                "隐私",
            ]
        )

    @staticmethod
    def _wants_board_briefing(lowered: str) -> bool:
        return any(
            word in lowered
            for word in [
                "board briefing",
                "briefing",
                "presentation",
                "proposal",
                "plan",
                "planning",
                "product",
                "revenue",
                "logo",
                "ui",
                "ux",
                "簡報",
                "汇报",
                "匯報",
                "規劃",
                "规划",
                "產品",
                "产品",
                "收益",
                "介面",
                "界面",
                "設計",
                "设计",
            ]
        )

    @staticmethod
    def _wants_escalation(lowered: str) -> bool:
        return any(word in lowered for word in ["escalate", "升級", "升级", "裁示", "決策", "decision", "approval"])

    @staticmethod
    def _wants_standing_order(lowered: str) -> bool:
        return any(word in lowered for word in ["以后", "以後", "不用再問", "不用再问", "standing order", "policy", "規則", "规则"])

    @staticmethod
    def _staffing_roles(lowered: str) -> list[str]:
        roles = ["Project Manager", "Developer", "Reviewer"]
        if any(word in lowered for word in ["security", "安全", "privacy", "隱私", "隐私"]):
            roles.append("Security Officer")
        if any(word in lowered for word in ["lawyer", "legal", "法務", "法律", "律師"]):
            roles.append("Legal Counsel")
        if any(word in lowered for word in ["sales", "業務", "销售", "銷售"]):
            roles.append("Sales Manager")
        return roles

    @staticmethod
    def _standing_order_scope(lowered: str) -> str:
        if any(word in lowered for word in ["security", "安全"]):
            return "security"
        if any(word in lowered for word in ["privacy", "隱私", "隐私"]):
            return "privacy"
        if any(word in lowered for word in ["legal", "law", "法務", "法律"]):
            return "legal"
        if any(word in lowered for word in ["finance", "spending", "money", "財務", "金錢"]):
            return "finance"
        return "global"

    @staticmethod
    def _mission_fields(text: str) -> tuple[str, str]:
        cleaned = text.strip()
        for marker in ["建立任務", "新增任務", "create mission", "Create mission", "mission:"]:
            cleaned = cleaned.replace(marker, "")
        cleaned = cleaned.lstrip("：: -").strip() or "Chairman-directed mission"
        title = cleaned.splitlines()[0][:90]
        summary = cleaned if len(cleaned) > len(title) else f"Chairman instruction: {cleaned}"
        return title, summary

    @staticmethod
    def _domains(lowered: str) -> list[str]:
        domains = []
        if any(word in lowered for word in ["code", "developer", "開發", "程式", "ui", "frontend", "backend"]):
            domains.append("development")
        if any(word in lowered for word in ["finance", "cost", "成本", "財務"]):
            domains.append("finance")
        if any(word in lowered for word in ["operation", "ops", "流程", "營運"]):
            domains.append("operations")
        return domains or ["operations"]

    @staticmethod
    def _priority(lowered: str) -> str:
        if any(word in lowered for word in ["urgent", "critical", "緊急", "重要", "立刻"]):
            return "critical"
        if any(word in lowered for word in ["high", "優先"]):
            return "high"
        return "normal"

    @staticmethod
    def _response(intent: str, context: CEOPlannerContext, actions: list[PlannerAction]) -> str:
        if intent == "mission_draft":
            mission = next((item for item in actions if item.type == "mission_draft"), None)
            title = mission.title if mission else "new mission"
            return f"我已產生 mission draft：{title}，並交給 PM / Developer / Reviewer 建立內部工作 thread。"
        if intent == "approval_request":
            return "我已把這段指令轉成 approval request；若有指定 mission，會直接掛到該 mission。"
        if intent == "memory_update":
            return "我已把這段內容整理成 memory update，寫入公司記憶，之後的任務會參考它。"
        if intent == "board_briefing":
            return "我會讓 PM 組成任務小組，整理角色意見並產生董事長簡報；在你授權前不會直接進入高風險執行。"
        _ = context
        return "收到。我會用 briefing action 保留這段脈絡，並在需要任務、記憶或批准時轉成明確 action。"


class LLMCEOPlanner:
    def __init__(self, *, provider: str, model: str, fallback: CEOPlanner | None = None) -> None:
        self.provider = provider
        self.model = model
        self.fallback = fallback or DeterministicCEOPlanner()

    def plan(self, context: CEOPlannerContext) -> PlannerPlan:
        prompt = self._build_prompt(context)
        try:
            response_text, _ = generate_json_response(provider=self.provider, model=self.model, prompt=prompt)
            raw = parse_generation_payload(response_text)
            plan = PlannerPlan.model_validate(raw)
            return self._sanitize_plan(plan)
        except (ApiProviderError, json.JSONDecodeError, ValueError, KeyError) as exc:
            fallback = self.fallback.plan(context)
            fallback.actions.append(
                PlannerAction(
                    type="briefing",
                    status="applied",
                    title="Planner fallback",
                    body=f"LLM planner unavailable or invalid; deterministic planner used. Reason: {type(exc).__name__}",
                    metadata={"provider": self.provider, "model": self.model},
                )
            )
            return fallback

    @staticmethod
    def _build_prompt(context: CEOPlannerContext) -> str:
        return "\n".join(
            [
                "You are the Praetor CEO planner.",
                "Return valid JSON only. Do not include markdown.",
                "Your job is to convert the chairman instruction into explicit planner actions.",
                "Apply the safety policy before proposing actions. If protected data or authority boundaries are involved, create an approval_request or decision_escalation instead of silent execution.",
                "",
                "Allowed action types:",
                "- mission_draft: create a planned mission for execution.",
                "- approval_request: request a chairman decision checkpoint. Requires an existing mission_id.",
                "- memory_update: write durable company memory.",
                "- briefing: record status or context without side effects.",
                "- staffing_proposal: recommend or create a mission team with roles and reporting lines.",
                "- agent_create: create one mission-scoped AI agent.",
                "- delegation_create: assign work from one AI role to another AI role.",
                "- decision_escalation: escalate a decision to PM, CEO, or chairman.",
                "- mission_closeout: request mission completion against the completion contract.",
                "- standing_order_update: record durable chairman policy or authority guidance.",
                "- board_briefing: form a planning team and produce an owner-visible briefing before execution.",
                "",
                "Required JSON shape:",
                "{",
                '  "intent": "mission_draft|approval_request|memory_update|briefing|staffing_proposal|agent_create|delegation_create|decision_escalation|mission_closeout|standing_order_update|board_briefing",',
                '  "response": "short CEO response to the chairman",',
                '  "actions": [',
                "    {",
                '      "type": "mission_draft|approval_request|memory_update|briefing|staffing_proposal|agent_create|delegation_create|decision_escalation|mission_closeout|standing_order_update|board_briefing",',
                '      "title": "short title",',
                '      "body": "details",',
                '      "mission_id": "optional existing mission id",',
                '      "metadata": {}',
                "    }",
                "  ]",
                "}",
                "",
                "Action metadata rules:",
                '- mission_draft metadata may include "domains", "priority", "requested_outputs".',
                '- approval_request metadata may include "category"; default category is "change_strategy".',
                '- memory_update metadata may include "page"; default page is "CEO Memory.md".',
                '- staffing_proposal metadata may include "roles".',
                '- agent_create metadata must include "role" when possible.',
                '- delegation_create metadata may include "from_role", "to_role", "success_criteria", "constraints".',
                '- decision_escalation metadata may include "from_role", "to_level", "category", "options".',
                '- standing_order_update metadata may include "scope" and "effect".',
                "- board_briefing requires a mission_id or should follow a mission_draft action.",
                "",
                f"Existing mission count: {context.mission_count}",
                f"Pending approvals: {context.pending_approvals}",
                f"Related mission id: {context.related_mission_id or 'none'}",
                "",
                context.safety_policy or "No additional safety policy supplied.",
                "",
                "Chairman instruction:",
                context.instruction,
            ]
        )

    @staticmethod
    def _sanitize_plan(plan: PlannerPlan) -> PlannerPlan:
        actions: list[PlannerAction] = []
        for action in plan.actions[:6]:
            metadata = dict(action.metadata)
            title = LLMCEOPlanner._clean_text(action.title, limit=120) or action.type.replace("_", " ").title()
            body = LLMCEOPlanner._clean_text(action.body, limit=2000) if action.body else None
            if action.type == "mission_draft":
                domains = LLMCEOPlanner._clean_string_list(metadata.get("domains"), limit=6) or ["operations"]
                priority = metadata.get("priority") or "normal"
                if priority not in {"normal", "high", "critical"}:
                    priority = "normal"
                outputs = [
                    item
                    for item in LLMCEOPlanner._clean_string_list(metadata.get("requested_outputs"), limit=8)
                    if LLMCEOPlanner._is_workspace_output(item)
                ]
                metadata.update({"domains": domains, "priority": priority, "requested_outputs": outputs})
            elif action.type == "approval_request":
                category = metadata.get("category") or "change_strategy"
                allowed = {"delete_files", "overwrite_important_files", "external_communication", "spending_money", "change_strategy", "shell_commands"}
                if category not in allowed:
                    category = "change_strategy"
                metadata["category"] = category
            elif action.type == "memory_update":
                page = str(metadata.get("page") or "CEO Memory.md").replace("/", "-").replace("\\", "-")
                metadata["page"] = page or "CEO Memory.md"
            elif action.type == "staffing_proposal":
                roles = LLMCEOPlanner._clean_string_list(metadata.get("roles"), limit=10)
                metadata["roles"] = roles or ["Project Manager", "Developer", "Reviewer"]
            elif action.type == "agent_create":
                metadata["role"] = LLMCEOPlanner._clean_text(str(metadata.get("role") or title), limit=80)
            elif action.type == "delegation_create":
                metadata["from_role"] = LLMCEOPlanner._clean_text(str(metadata.get("from_role") or "ceo"), limit=80)
                metadata["to_role"] = LLMCEOPlanner._clean_text(str(metadata.get("to_role") or "Project Manager"), limit=80)
                metadata["success_criteria"] = LLMCEOPlanner._clean_string_list(metadata.get("success_criteria"), limit=8)
                metadata["constraints"] = LLMCEOPlanner._clean_string_list(metadata.get("constraints"), limit=8)
            elif action.type == "decision_escalation":
                level = metadata.get("to_level") or "chairman"
                if level not in {"project_manager", "ceo", "chairman"}:
                    level = "chairman"
                category = metadata.get("category") or "change_strategy"
                allowed = {"delete_files", "overwrite_important_files", "external_communication", "spending_money", "change_strategy", "shell_commands"}
                if category not in allowed:
                    category = "change_strategy"
                metadata["to_level"] = level
                metadata["category"] = category
                metadata["options"] = [
                    {"value": LLMCEOPlanner._clean_text(str(item.get("value") or item.get("label") or ""), limit=80),
                     "label": LLMCEOPlanner._clean_text(str(item.get("label") or item.get("value") or ""), limit=120)}
                    for item in (metadata.get("options") or [])[:5]
                    if isinstance(item, dict)
                ]
            elif action.type == "standing_order_update":
                scope = metadata.get("scope") or "global"
                if scope not in {"global", "mission", "security", "privacy", "legal", "finance", "product", "engineering"}:
                    scope = "global"
                metadata["scope"] = scope
                metadata["effect"] = LLMCEOPlanner._clean_text(str(metadata.get("effect") or "guidance"), limit=80)
            elif action.type == "board_briefing":
                metadata["requires_existing_mission"] = True
            actions.append(action.model_copy(update={"title": title, "body": body, "metadata": metadata}))
        if not actions:
            actions = [PlannerAction(type="briefing", title="Planner produced no action", body=plan.response)]
        return plan.model_copy(update={"actions": actions})

    @staticmethod
    def _clean_text(value: str | None, *, limit: int) -> str:
        return " ".join(str(value or "").split())[:limit]

    @staticmethod
    def _clean_string_list(value: object, *, limit: int) -> list[str]:
        if not isinstance(value, list):
            return []
        cleaned = []
        for item in value[:limit]:
            text = LLMCEOPlanner._clean_text(str(item), limit=240)
            if text:
                cleaned.append(text)
        return cleaned

    @staticmethod
    def _is_workspace_output(path: str) -> bool:
        if ".." in path or path.startswith(("/", "~")) and not path.startswith("/workspace/"):
            return False
        return bool(path)


def default_ceo_planner(runtime: RuntimeSelection | None = None) -> CEOPlanner:
    mode = get_ceo_planner_mode()
    if mode == "llm":
        return LLMCEOPlanner(provider=get_ceo_planner_provider(), model=get_ceo_planner_model())
    if mode == "auto" and runtime is not None and runtime.mode == "api":
        provider = (runtime.provider or get_ceo_planner_provider()).lower()
        model = runtime.model or get_ceo_planner_model()
        api_key = get_openai_api_key() if provider == "openai" else get_anthropic_api_key()
        if api_key and api_key != "fake-key":
            return LLMCEOPlanner(provider=provider, model=model)
    return DeterministicCEOPlanner()
