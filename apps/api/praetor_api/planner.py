from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from .models import PlannerAction, PlannerPlan
from .config import get_ceo_planner_mode, get_ceo_planner_model, get_ceo_planner_provider
from .providers import ApiProviderError, generate_json_response, parse_generation_payload


@dataclass(frozen=True)
class CEOPlannerContext:
    instruction: str
    related_mission_id: str | None
    mission_count: int
    pending_approvals: int


class CEOPlanner(Protocol):
    def plan(self, context: CEOPlannerContext) -> PlannerPlan:
        ...


class DeterministicCEOPlanner:
    def plan(self, context: CEOPlannerContext) -> PlannerPlan:
        text = context.instruction.strip()
        lowered = text.lower()
        actions: list[PlannerAction] = []
        intent = "briefing"

        if self._wants_mission(lowered):
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
        return any(word in lowered for word in ["create", "建立", "新增", "任務", "mission"])

    @staticmethod
    def _wants_approval(lowered: str) -> bool:
        return any(word in lowered for word in ["approval", "approve", "批准", "核准", "決策", "checkpoint"])

    @staticmethod
    def _wants_memory(lowered: str) -> bool:
        return any(word in lowered for word in ["memory", "remember", "記住", "記憶", "保存", "原則"])

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
                "",
                "Allowed action types:",
                "- mission_draft: create a planned mission for execution.",
                "- approval_request: request a chairman decision checkpoint. Requires an existing mission_id.",
                "- memory_update: write durable company memory.",
                "- briefing: record status or context without side effects.",
                "",
                "Required JSON shape:",
                "{",
                '  "intent": "mission_draft|approval_request|memory_update|briefing",',
                '  "response": "short CEO response to the chairman",',
                '  "actions": [',
                "    {",
                '      "type": "mission_draft|approval_request|memory_update|briefing",',
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
                "",
                f"Existing mission count: {context.mission_count}",
                f"Pending approvals: {context.pending_approvals}",
                f"Related mission id: {context.related_mission_id or 'none'}",
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


def default_ceo_planner() -> CEOPlanner:
    if get_ceo_planner_mode() == "llm":
        return LLMCEOPlanner(provider=get_ceo_planner_provider(), model=get_ceo_planner_model())
    return DeterministicCEOPlanner()
