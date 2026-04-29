from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import hashlib
import secrets
from typing import TYPE_CHECKING, Any

import httpx

from .config import get_telegram_api_base_url, get_telegram_bot_token
from .models import ApprovalRequest, ConversationCreateRequest, TelegramIntegrationSettings, utc_now

if TYPE_CHECKING:
    from .service import PraetorService


HIGH_RISK_APPROVALS = {
    "delete_files",
    "overwrite_important_files",
    "external_communication",
    "spending_money",
    "shell_commands",
}


@dataclass
class TelegramReply:
    chat_id: int | None
    text: str
    reply_markup: dict[str, Any] | None = None


class TelegramAuthError(RuntimeError):
    pass


class TelegramClient:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or get_telegram_bot_token()
        self.base_url = get_telegram_api_base_url().rstrip("/")

    @property
    def configured(self) -> bool:
        return bool(self.token)

    def call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.token:
            return {"ok": False, "skipped": True, "description": "Telegram bot token is not configured."}
        url = f"{self.base_url}/bot{self.token}/{method}"
        with httpx.Client(timeout=12.0) as client:
            response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def send_message(self, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text[:3900],
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self.call("sendMessage", payload)

    def answer_callback_query(self, callback_query_id: str, text: str) -> dict[str, Any]:
        return self.call("answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text[:180]})


def generate_pairing_code() -> str:
    return secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].upper()


def hash_pairing_code(code: str) -> str:
    return hashlib.sha256(code.strip().upper().encode("utf-8")).hexdigest()


def pairing_code_matches(settings: TelegramIntegrationSettings, code: str) -> bool:
    if not settings.pairing_code_hash:
        return False
    if settings.pairing_code_expires_at and settings.pairing_code_expires_at < utc_now():
        return False
    return secrets.compare_digest(settings.pairing_code_hash, hash_pairing_code(code))


def new_pairing_settings(settings: TelegramIntegrationSettings, code: str) -> TelegramIntegrationSettings:
    return settings.model_copy(
        update={
            "enabled": True,
            "pairing_code_hash": hash_pairing_code(code),
            "pairing_code_expires_at": utc_now() + timedelta(minutes=15),
        }
    )


def approval_reply_markup(approval: ApprovalRequest, allow_approve: bool) -> dict[str, Any] | None:
    buttons = []
    if allow_approve:
        buttons.append({"text": "Approve", "callback_data": f"approval:approved:{approval.id}"})
    buttons.append({"text": "Reject", "callback_data": f"approval:rejected:{approval.id}"})
    return {"inline_keyboard": [buttons]}


def approval_notification_text(approval: ApprovalRequest) -> str:
    return "\n".join(
        [
            "Approval requested",
            f"Category: {approval.category}",
            f"Mission: {approval.mission_id}",
            f"Reason: {approval.reason[:900]}",
            "",
            "High-risk approvals should be reviewed in the Praetor web UI before approval.",
        ]
    )


def can_approve_from_telegram(settings: TelegramIntegrationSettings, approval: ApprovalRequest) -> bool:
    return settings.allow_low_risk_approval and approval.category not in HIGH_RISK_APPROVALS


def send_approval_notification(settings: TelegramIntegrationSettings, approval: ApprovalRequest) -> dict[str, Any]:
    if not (settings.enabled and settings.notify_approvals and settings.linked_chat_id):
        return {"ok": False, "skipped": True, "description": "Telegram approval notification is not enabled or linked."}
    return TelegramClient().send_message(
        settings.linked_chat_id,
        approval_notification_text(approval),
        reply_markup=approval_reply_markup(approval, can_approve_from_telegram(settings, approval)),
    )


def process_update(service: PraetorService, update: dict[str, Any]) -> list[TelegramReply]:
    settings = service._require_settings().telegram
    if callback := update.get("callback_query"):
        return [_process_callback(service, settings, callback)]
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    chat_id = chat.get("id")
    user_id = sender.get("id")
    text = str(message.get("text") or "").strip()
    if not isinstance(chat_id, int) or not isinstance(user_id, int):
        return []

    if text.lower().startswith("/link "):
        code = text.split(maxsplit=1)[1]
        if not pairing_code_matches(settings, code):
            return [TelegramReply(chat_id, "Pairing failed. Generate a fresh code in Praetor Settings and try again.")]
        if settings.allowed_user_id and settings.allowed_user_id != user_id:
            return [TelegramReply(chat_id, "Pairing failed. This Telegram user is not on the Praetor allowlist.")]
        service.link_telegram_chat(chat_id=chat_id, user_id=user_id, username=sender.get("username"))
        return [TelegramReply(chat_id, "Telegram is now connected to Praetor CEO.")]

    _ensure_authorized(settings, chat_id, user_id)
    if text.startswith("/"):
        return [_process_command(service, settings, chat_id, text)]
    result = service.create_ceo_message(ConversationCreateRequest(body=text))
    response = result.messages[-1].body if result.messages else "CEO received your message."
    if result.created_mission:
        response += f"\n\nMission draft: {result.created_mission.title}\n{result.created_mission.id}"
    if result.created_approval:
        response += f"\n\nApproval requested: {result.created_approval.category}"
    return [TelegramReply(chat_id, response)]


def _ensure_authorized(settings: TelegramIntegrationSettings, chat_id: int, user_id: int) -> None:
    if not settings.enabled or not settings.linked_chat_id or not settings.linked_user_id:
        raise TelegramAuthError("Telegram is not linked. Open Praetor Settings and send /link <code> from Telegram.")
    if settings.linked_chat_id != chat_id:
        raise TelegramAuthError("This Telegram chat is not linked to Praetor.")
    if settings.allowed_user_id and settings.allowed_user_id != user_id:
        raise TelegramAuthError("This Telegram user is not allowed to control Praetor.")
    if settings.linked_user_id != user_id:
        raise TelegramAuthError("This Telegram user is not linked to Praetor.")


def _process_command(
    service: PraetorService,
    settings: TelegramIntegrationSettings,
    chat_id: int,
    text: str,
) -> TelegramReply:
    command = text.split()[0].lower()
    if command in {"/start", "/help"}:
        return TelegramReply(chat_id, "Praetor commands: /briefing, /missions, /inbox, /help. Send any other message to talk to the CEO.")
    if command == "/briefing":
        briefing = service.praetor_briefing()
        return TelegramReply(
            chat_id,
            f"Briefing\nActive missions: {briefing.active_missions}\nPaused missions: {briefing.paused_missions}\nApprovals pending: {briefing.approvals_pending}",
        )
    if command == "/missions":
        missions = service.list_missions()[:5]
        if not missions:
            return TelegramReply(chat_id, "No missions yet.")
        return TelegramReply(chat_id, "Recent missions\n" + "\n".join(f"- {item.title}: {item.status}" for item in missions))
    if command == "/inbox":
        approvals = service.list_approvals(status="pending")[:5]
        if not approvals:
            return TelegramReply(chat_id, "Inbox clear. No pending approvals.")
        first = approvals[0]
        return TelegramReply(
            chat_id,
            "Pending approvals\n" + "\n".join(f"- {item.category}: {item.reason[:120]}" for item in approvals),
            reply_markup=approval_reply_markup(first, can_approve_from_telegram(settings, first)),
        )
    return TelegramReply(chat_id, "Unknown command. Use /help.")


def _process_callback(
    service: PraetorService,
    settings: TelegramIntegrationSettings,
    callback: dict[str, Any],
) -> TelegramReply:
    message = callback.get("message") or {}
    chat = message.get("chat") or {}
    sender = callback.get("from") or {}
    chat_id = chat.get("id")
    user_id = sender.get("id")
    callback_id = callback.get("id")
    data = str(callback.get("data") or "")
    if not isinstance(chat_id, int) or not isinstance(user_id, int):
        return TelegramReply(None, "Invalid callback.")
    _ensure_authorized(settings, chat_id, user_id)
    if not data.startswith("approval:"):
        return TelegramReply(chat_id, "Unknown Telegram action.")
    _prefix, status, approval_id = data.split(":", 2)
    approval = next((item for item in service.list_approvals() if item.id == approval_id), None)
    if approval is None:
        return TelegramReply(chat_id, "Approval not found.")
    if status == "approved" and not can_approve_from_telegram(settings, approval):
        if callback_id:
            TelegramClient().answer_callback_query(callback_id, "Open Praetor web UI to approve this high-risk request.")
        return TelegramReply(chat_id, "This approval is too sensitive for Telegram approval. Please review it in Praetor web UI.")
    if status not in {"approved", "rejected"}:
        return TelegramReply(chat_id, "Unsupported approval action.")
    service.resolve_approval(approval_id, status)
    if callback_id:
        TelegramClient().answer_callback_query(callback_id, f"Approval {status}.")
    return TelegramReply(chat_id, f"Approval {status}: {approval.category}")
