from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import PlannerAction, PlannerPlan


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


def default_ceo_planner() -> CEOPlanner:
    return DeterministicCEOPlanner()

