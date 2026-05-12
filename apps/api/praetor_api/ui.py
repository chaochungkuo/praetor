from __future__ import annotations

from datetime import datetime
from typing import Any
from pathlib import Path
from urllib.parse import quote
import asyncio
import json
import threading

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from .config import (
    ANTHROPIC_STATE_SECRET,
    OPENAI_STATE_SECRET,
    TELEGRAM_BOT_TOKEN_STATE_SECRET,
    TELEGRAM_WEBHOOK_SECRET_STATE_SECRET,
    get_anthropic_api_key,
    get_bridge_base_url,
    get_openai_api_key,
    get_telegram_bot_token,
    get_telegram_webhook_secret,
    write_state_secret,
)
from .models import (
    ApprovalCreateRequest,
    ConversationCreateRequest,
    LoginRequest,
    MissionContinueRequest,
    MissionCreateRequest,
    MissionPauseRequest,
    MissionStopRequest,
    OnboardingAnswers,
    RuntimeSelection,
)
from .providers import openai_audio_transcription
from .security import csrf_token, login_rate_limiter, require_csrf, require_setup_token


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
WEB_DIST_DIR = BASE_DIR.parents[1] / "web" / "dist"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
router = APIRouter(include_in_schema=False)

_css_path = STATIC_DIR / "praetor.css"
_STATIC_ASSET_VERSION: int = int(_css_path.stat().st_mtime) if _css_path.exists() else 0

UI_COOKIE_NAME = "praetor_ui_lang"
SUPPORTED_LANGUAGES = {
    "en": "English",
    "zh-TW": "中文（繁體）",
}

from ._translations import (
    EVENT_LABELS,
    PHRASE_LABELS,
    ROLE_NAME_LABELS,
    TRANSLATIONS,
    VALUE_LABELS,
)


def install_ui(app) -> None:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    if (WEB_DIST_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(WEB_DIST_DIR / "assets")), name="office_assets")
    app.include_router(router)


def _flash(request: Request) -> tuple[str | None, str]:
    return request.query_params.get("flash"), request.query_params.get("level", "info")


def _redirect(path: str, flash: str | None = None, level: str = "info") -> RedirectResponse:
    if flash:
        sep = "&" if "?" in path else "?"
        path = f"{path}{sep}flash={quote(flash)}&level={quote(level)}"
    return RedirectResponse(url=path, status_code=303)


def _safe_redirect_path(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    if not value.startswith("/") or value.startswith("//"):
        return fallback
    return value


def _friendly_runtime_error(exc_or_message: Exception | str, t) -> str:
    message = str(exc_or_message)
    lowered = message.lower()
    if "401" in message or "unauthorized" in lowered or "invalid api key" in lowered:
        return t("runtime_auth_error")
    if "404" in message or "not found" in lowered:
        return t("runtime_not_found_error")
    if "connecterror" in lowered or "connection refused" in lowered or "name or service not known" in lowered:
        return t("runtime_network_error")
    if "timed out" in lowered or "timeout" in lowered:
        return t("runtime_network_error")
    return message


def _runtime_unavailable_message(request: Request, t) -> str | None:
    try:
        health = request.app.state.ctx.service.runtime_health()
    except Exception as exc:
        return _friendly_runtime_error(exc, t)
    if health.get("healthy"):
        return None
    reason = health.get("error") or health.get("status") or t("runtime_not_configured")
    return f"{t('ai_runtime_required')} {t('ai_power_outage_reason')}: {reason}"


def _save_provider_api_key(provider: str, api_key: str) -> None:
    key = api_key.strip()
    if not key:
        return
    secret_files = {
        "openai": OPENAI_STATE_SECRET,
        "openai_compatible": OPENAI_STATE_SECRET,
        "anthropic": ANTHROPIC_STATE_SECRET,
    }
    filename = secret_files.get(provider)
    if filename is None:
        raise ValueError("Unsupported provider.")
    write_state_secret(filename, key)


def _ui_language(request: Request, initialized_settings) -> str:
    requested = request.query_params.get("lang")
    if requested in SUPPORTED_LANGUAGES:
        return requested
    cookie_value = request.cookies.get(UI_COOKIE_NAME)
    if cookie_value in SUPPORTED_LANGUAGES:
        return cookie_value
    if initialized_settings is not None and initialized_settings.owner.preferred_language in SUPPORTED_LANGUAGES:
        return initialized_settings.owner.preferred_language
    return "en"


def _translator(language: str):
    bundle = TRANSLATIONS.get(language, TRANSLATIONS["en"])
    fallback = TRANSLATIONS["en"]

    def translate(key: str) -> str:
        return bundle.get(key, fallback.get(key, key))

    return translate


def _value_label(language: str):
    labels = VALUE_LABELS.get(language, VALUE_LABELS["en"])
    fallback = VALUE_LABELS["en"]

    def label(value: Any) -> str:
        if value is None:
            return _translator(language)("not_available")
        if isinstance(value, bool):
            value = str(value).lower()
        raw = str(value)
        key = raw.strip().lower()
        return labels.get(key, fallback.get(key, raw.replace("_", " ")))

    return label


def _role_label(language: str):
    labels = ROLE_NAME_LABELS.get(language, {})

    def label(value: Any) -> str:
        raw = str(value or "")
        return labels.get(raw, raw)

    return label


def _phrase_label(language: str):
    labels = PHRASE_LABELS.get(language, {})

    def label(value: Any) -> str:
        raw = str(value or "")
        translated = labels.get(raw)
        if translated is not None:
            return translated
        for source, target in labels.items():
            raw = raw.replace(source, target)
        return raw

    return label


def _event_label(language: str):
    labels = EVENT_LABELS.get(language, EVENT_LABELS["en"])
    fallback = EVENT_LABELS["en"]

    def label(event_type: Any) -> str:
        raw = str(event_type or "")
        return labels.get(raw, fallback.get(raw, raw.replace("_", " ").title()))

    return label


def _format_datetime(language: str):
    def format_value(value: Any) -> str:
        if value is None:
            return ""
        parsed = value
        if isinstance(value, str):
            raw = value.strip()
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(raw)
            except ValueError:
                return value
        if isinstance(parsed, datetime):
            if language == "zh-TW":
                return parsed.strftime("%Y-%m-%d %H:%M")
            return parsed.strftime("%Y-%m-%d %H:%M")
        return str(value)

    return format_value


def _format_time_short(language: str):
    def format_value(value: Any) -> str:
        if value is None:
            return ""
        parsed = value
        if isinstance(value, str):
            raw = value.strip()
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(raw)
            except ValueError:
                return value
        if isinstance(parsed, datetime):
            return parsed.strftime("%H:%M")
        return str(value)

    return format_value


def _event_summary(language: str):
    t = _translator(language)
    phrase_label = _phrase_label(language)
    value_label = _value_label(language)

    def summarize(event_or_payload: Any) -> str:
        event_type = ""
        payload = event_or_payload
        if isinstance(event_or_payload, dict) and "payload" in event_or_payload:
            event_type = str(event_or_payload.get("type") or "")
            payload = event_or_payload.get("payload")
        if not isinstance(payload, dict):
            return str(payload or t("event_recorded"))
        for key in ("title", "mission_title", "reason", "content", "message", "summary", "category"):
            value = payload.get(key)
            if value:
                if key == "category":
                    return value_label(value)
                return phrase_label(value)
        if event_type in {"owner_login", "ceo_conversation_message", "standing_order_created", "onboarding_completed"}:
            return t("event_recorded")
        mission_id = payload.get("mission_id")
        if mission_id:
            return t("mission_related_event")
        return t("event_recorded")

    return summarize


def _page_title(current_page: str, fallback: str, t) -> str:
    return t(f"page_{current_page}") if current_page else fallback


def _base_context(request: Request, current_page: str, page_title: str) -> dict:
    service = request.app.state.ctx.service
    if not hasattr(request.state, "ui_settings"):
        request.state.ui_settings = service.get_settings()
    initialized_settings = request.state.ui_settings
    ui_language = _ui_language(request, initialized_settings)
    t = _translator(ui_language)
    display_title = _page_title(current_page, page_title, t)
    authenticated = bool(getattr(request.state, "authenticated", False))
    settings = initialized_settings if authenticated or initialized_settings is None else None
    briefing = None
    runtime_health = None
    if initialized_settings is not None and authenticated:
        briefing = service.praetor_briefing()
        runtime_health = service.runtime_health()
    approvals = service.list_approvals(status="pending") if initialized_settings is not None and authenticated else []
    flash, flash_level = _flash(request)
    if flash and flash_level == "error":
        flash = _friendly_runtime_error(flash, t)
    return {
        "request": request,
        "current_url": f"{request.url.path}{'?' + request.url.query if request.url.query else ''}",
        "current_url_quoted": quote(f"{request.url.path}{'?' + request.url.query if request.url.query else ''}", safe=""),
        "page_title": display_title,
        "current_page": current_page,
        "ui_language": ui_language,
        "t": t,
        "label": _value_label(ui_language),
        "role_label": _role_label(ui_language),
        "phrase_label": _phrase_label(ui_language),
        "event_label": _event_label(ui_language),
        "event_summary": _event_summary(ui_language),
        "format_time": _format_datetime(ui_language),
        "format_time_short": _format_time_short(ui_language),
        "language_options": SUPPORTED_LANGUAGES,
        "settings": settings,
        "settings_initialized": initialized_settings is not None,
        "briefing": briefing,
        "flash": flash,
        "flash_level": flash_level,
        "approvals": approvals,
        "runtime_ready": bool(runtime_health and runtime_health.get("healthy")),
        "runtime_health": runtime_health,
        "bridge_base_url": get_bridge_base_url(),
        "openai_transcription_ready": bool(get_openai_api_key()),
        "authenticated": authenticated,
        "session_owner": getattr(request.state, "session_owner", None),
        "csrf_token": csrf_token(request),
        "setup_token": request.query_params.get("setup_token", ""),
        "static_asset_version": _STATIC_ASSET_VERSION,
    }


def _validate_form_csrf(request: Request, form) -> None:
    require_csrf(request, str(form.get("csrf_token", "")))


def _default_onboarding() -> dict:
    return {
        "owner_name": "Founder",
        "owner_email": "",
        "owner_password": "",
        "owner_password_confirm": "",
        "language": "en",
        "leadership_style": "strategic",
        "decision_style": "balanced",
        "organization_style": "lean",
        "autonomy_mode": "hybrid",
        "risk_priority": "avoid_wrong_decisions",
        "workspace_root": "~/praetor-workspace",
        "runtime_mode": "api",
        "runtime_provider": "openai",
        "runtime_model": "gpt-4.1-mini",
        "runtime_base_url": "",
        "runtime_executor": "codex",
        "require_approval": [
            "delete_files",
            "overwrite_important_files",
            "external_communication",
            "spending_money",
            "change_strategy",
            "shell_commands",
        ],
    }


def _starter_missions(t) -> list[dict[str, str]]:
    return [
        {
            "title": t("starter_create_project_title"),
            "summary": t("starter_create_project_summary"),
            "domain": "operations",
            "priority": "high",
            "requested_outputs": "/workspace/Projects/Alpha/PROJECT.md\n/workspace/Projects/Alpha/STATUS.md",
        },
        {
            "title": t("starter_build_wiki_title"),
            "summary": t("starter_build_wiki_summary"),
            "domain": "operations",
            "priority": "normal",
            "requested_outputs": "/workspace/Wiki/Company.md\n/workspace/Wiki/Strategy.md",
        },
        {
            "title": t("starter_review_inbox_title"),
            "summary": t("starter_review_inbox_summary"),
            "domain": "operations",
            "priority": "normal",
            "requested_outputs": "/workspace/Inbox/INBOX_SUMMARY.md",
        },
    ]


def _mission_by_id(missions: list) -> dict[str, Any]:
    return {mission.id: mission for mission in missions}


def _build_inbox_items(service, t, label, phrase_label, event_label, event_summary) -> dict[str, list[dict[str, Any]]]:
    missions = service.list_missions()
    missions_by_id = _mission_by_id(missions)
    approvals = service.list_approvals(status="pending")
    recent_runs = service.list_recent_runs(limit=20)
    audit_events = service.list_audit_events(limit=20)
    runtime_health = service.runtime_health()
    governance_review = service.latest_governance_review()

    pending_decisions = []
    for approval in approvals:
        pending_decisions.append(
            {
                "title": label(approval.category),
                "body": phrase_label(approval.reason),
                "status": label(approval.status),
                "href": f"/app/missions/{approval.mission_id}" if approval.mission_id else "/app/decisions",
                "kind": t("pending_decisions"),
                "created_at": approval.created_at,
            }
        )

    blocked_work = []
    for mission in missions:
        if mission.status in {"failed", "paused"}:
            blocked_work.append(
                {
                    "title": mission.title,
                    "body": mission.summary or label(mission.status),
                    "status": label(mission.status),
                    "href": f"/app/missions/{mission.id}",
                    "kind": t("blocked_work"),
                    "created_at": mission.updated_at,
                }
            )
    for run in recent_runs:
        status = str(run.get("normalized_status") or run.get("status") or "").lower()
        if status in {"failed", "error"}:
            blocked_work.append(
                {
                    "title": str(run.get("executor") or t("executor")),
                    "body": str(run.get("stderr_tail") or run.get("stdout_tail") or t("event_recorded"))[:320],
                    "status": label(status),
                    "href": "/app/activity",
                    "kind": t("blocked_work"),
                    "created_at": run.get("finished_at") or run.get("started_at"),
                }
            )

    risk_signals = []
    if not runtime_health.get("healthy"):
        risk_signals.append(
            {
                "title": t("runtime_watch"),
                "body": runtime_health.get("error") or t("runtime_not_configured"),
                "status": label(runtime_health.get("mode") or "runtime"),
                "href": "/app/settings",
                "kind": t("risk_signals"),
                "created_at": None,
            }
        )
    risk_event_types = {"approval_created", "decision_escalation_created", "standing_order_created"}
    for event in audit_events:
        if event.get("type") in risk_event_types:
            risk_signals.append(
                {
                    "title": event_label(event.get("type") or "event_recorded"),
                    "body": event_summary(event),
                    "status": t("review_item"),
                    "href": "/app/decisions",
                    "kind": t("risk_signals"),
                    "created_at": event.get("ts"),
                }
            )

    completed_for_review = [
        {
            "title": mission.title,
            "body": mission.summary or t("review_item"),
            "status": label(mission.status),
            "href": f"/app/missions/{mission.id}",
            "kind": t("completed_for_review"),
            "created_at": mission.updated_at,
        }
        for mission in missions
        if mission.status == "completed"
    ]

    return {
        "governance_review": governance_review,
        "formal_items": [
            {
                "title": item.title,
                "body": item.body,
                "status": label(item.severity),
                "href": item.href,
                "kind": label(item.kind),
                "created_at": item.created_at,
            }
            for item in governance_review.items
        ][:8],
        "pending_decisions": pending_decisions[:8],
        "blocked_work": blocked_work[:8],
        "risk_signals": risk_signals[:8],
        "completed_for_review": completed_for_review[:8],
    }


def _build_agent_directory(service) -> dict[str, Any]:
    organization = service.organization_snapshot()
    activity = service.office_snapshot().agent_activity
    missions = service.list_missions()
    missions_by_id = _mission_by_id(missions)
    agents_by_id = {agent.id: agent for agent in organization.agents}
    agents_by_role: dict[str, list[Any]] = {}
    for agent in organization.agents:
        agents_by_role.setdefault(agent.role_name, []).append(agent)
    activity_by_role: dict[str, list[Any]] = {}
    for event in activity:
        activity_by_role.setdefault(event.actor.replace("_", " ").title(), []).append(event)
    work_sessions_by_mission: dict[str, list[Any]] = {}
    for session in service.all_work_sessions():
        work_sessions_by_mission.setdefault(session.mission_id, []).append(session)
    contracts_by_agent = {contract.agent_id: contract for contract in organization.agent_contracts}
    delegations_by_agent: dict[str, list[Any]] = {}
    delegations_by_role: dict[str, list[Any]] = {}
    for delegation in organization.delegations:
        if delegation.status in {"done", "cancelled"}:
            continue
        if delegation.to_agent_id:
            delegations_by_agent.setdefault(delegation.to_agent_id, []).append(delegation)
        delegations_by_role.setdefault(delegation.to_role, []).append(delegation)

    def current_session_for(agent: Any) -> Any | None:
        if not agent.mission_id:
            return None
        sessions = work_sessions_by_mission.get(agent.mission_id, [])
        role_names = {agent.role_name, agent.role_name.lower().replace(" ", "_")}
        for session in sessions:
            if session.status in {"completed", "cancelled"}:
                continue
            if session.manager_role in role_names or session.executor_role in role_names:
                return session
        return sessions[0] if sessions else None

    agent_cards = []
    blocked_count = 0
    open_work_session_count = 0
    for sessions in work_sessions_by_mission.values():
        open_work_session_count += len([session for session in sessions if session.status not in {"completed", "cancelled"}])
    for agent in organization.agents:
        mission = missions_by_id.get(agent.mission_id) if agent.mission_id else None
        session = current_session_for(agent)
        assigned = delegations_by_agent.get(agent.id, []) or delegations_by_role.get(agent.role_name, [])
        blocker = session.current_blocker if session and session.current_blocker else None
        if blocker:
            state = "blocked"
            current_work = blocker
            next_step = "waiting_for_owner" if "owner" in blocker.lower() else "review_recent_activity"
            blocked_count += 1
        elif session:
            state = "working"
            current_work = f"{session.manager_role} -> {session.executor_role}"
            next_step = "continue_work_session"
        elif assigned:
            state = "working"
            current_work = assigned[0].title
            next_step = assigned[0].success_criteria[0] if assigned[0].success_criteria else "review_recent_activity"
        elif mission:
            state = "active"
            current_work = mission.summary or "working_on_mission"
            next_step = "review_recent_activity"
        else:
            state = "idle"
            current_work = "monitoring_company" if agent.role_name == "CEO" else "waiting_for_assignment"
            next_step = "ready_for_next_assignment"
        last_activity = agent.updated_at
        if session and session.updated_at > last_activity:
            last_activity = session.updated_at
        agent_cards.append(
            {
                "agent": agent,
                "mission": mission,
                "session": session,
                "status": state,
                "current_work": current_work,
                "next_step": next_step,
                "reports_to": agent.supervisor_role or "ceo",
                "last_activity": last_activity,
                "contract": contracts_by_agent.get(agent.id),
                "href": f"/app/missions/{agent.mission_id}" if agent.mission_id else "/app/agents",
            }
        )

    team_cards = []
    for team in organization.teams:
        mission = missions_by_id.get(team.mission_id)
        lead = agents_by_id.get(team.lead_agent_id) if team.lead_agent_id else None
        members = [agents_by_id[agent_id] for agent_id in team.member_agent_ids if agent_id in agents_by_id]
        team_cards.append(
            {
                "team": team,
                "mission": mission,
                "lead": lead,
                "members": members,
                "href": f"/app/missions/{team.mission_id}",
            }
        )
    return {
        "organization": organization,
        "agents_by_role": agents_by_role,
        "activity_by_role": activity_by_role,
        "recent_activity": activity,
        "agent_cards": agent_cards,
        "team_cards": team_cards,
        "agent_overview": {
            "agents_created": len(organization.agents),
            "active_teams": len(organization.teams),
            "open_work_sessions": open_work_session_count,
            "blocked_agents": blocked_count,
            "contracts": len(organization.agent_contracts),
            "permission_profiles": len(organization.permission_profiles),
        },
    }


def _require_initialized(request: Request):
    if not hasattr(request.state, "ui_settings"):
        request.state.ui_settings = request.app.state.ctx.service.get_settings()
    settings = request.state.ui_settings
    if settings is None:
        return None
    return settings


@router.get("/app/set-language/{language_code}")
def set_language(request: Request, language_code: str):
    if language_code not in SUPPORTED_LANGUAGES:
        language_code = "en"
    next_path = _safe_redirect_path(request.query_params.get("next"), "/app/welcome")
    response = RedirectResponse(url=next_path, status_code=303)
    response.set_cookie(
        UI_COOKIE_NAME,
        language_code,
        max_age=60 * 60 * 24 * 365,
        httponly=False,
        samesite="lax",
    )
    return response


@router.get("/office")
def office_page():
    index = WEB_DIST_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return _redirect("/app/praetor", "Praetor Office frontend has not been built yet.", "error")


@router.get("/app/welcome", response_class=HTMLResponse)
def welcome_page(request: Request):
    ctx = _base_context(request, "welcome", "Welcome")
    if getattr(request.state, "authenticated", False):
        return _redirect("/app/praetor")
    return templates.TemplateResponse(
        request=request,
        name="welcome.html",
        context=ctx,
    )


@router.get("/app/login", response_class=HTMLResponse)
def login_page(request: Request):
    if getattr(request.state, "authenticated", False):
        return _redirect("/app/praetor")
    ctx = _base_context(
        request,
        "login",
        _translator(_ui_language(request, request.app.state.ctx.service.get_settings()))("owner_login"),
    )
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            **ctx,
            "next_path": request.query_params.get("next", "/app/praetor"),
        },
    )


@router.get("/", response_class=HTMLResponse)
def root():
    return RedirectResponse(url="/app/welcome", status_code=303)


@router.get("/app", response_class=HTMLResponse)
def app_root():
    return RedirectResponse(url="/app/welcome", status_code=303)


@router.get("/app/praetor", response_class=HTMLResponse)
def praetor_page(request: Request):
    ctx = _base_context(request, "praetor", "Praetor")
    service = request.app.state.ctx.service
    settings = ctx["settings"]
    missions = service.list_missions() if settings is not None else []
    ceo_messages = service.list_ceo_messages(limit=8) if settings is not None else []
    return templates.TemplateResponse(
        request=request,
        name="praetor.html",
        context={
            **ctx,
            "missions": missions[:8],
            "ceo_messages": ceo_messages,
            "onboarding_defaults": _default_onboarding(),
            "starter_missions": _starter_missions(ctx["t"]),
        },
    )


@router.get("/app/inbox", response_class=HTMLResponse)
def inbox_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    ctx = _base_context(request, "inbox", "Inbox")
    return templates.TemplateResponse(
        request=request,
        name="inbox.html",
        context={
            **ctx,
            "inbox_items": _build_inbox_items(
                service,
                ctx["t"],
                ctx["label"],
                ctx["phrase_label"],
                ctx["event_label"],
                ctx["event_summary"],
            ),
        },
    )


@router.post("/app/inbox/governance-review")
async def run_governance_review_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    await run_in_threadpool(request.app.state.ctx.service.run_governance_review)
    return _redirect("/app/inbox", t("governance_review"), "success")


@router.get("/app/agents", response_class=HTMLResponse)
def agents_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    return templates.TemplateResponse(
        request=request,
        name="agents.html",
        context={
            **_base_context(request, "agents", "Agents"),
            **_build_agent_directory(service),
        },
    )


@router.post("/app/agents/skill-sources")
async def add_skill_source_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    try:
        source = await run_in_threadpool(
            request.app.state.ctx.service.add_skill_source,
            str(form.get("url", "")).strip(),
            str(form.get("name", "")).strip() or None,
            str(form.get("branch", "")).strip() or "main",
        )
        await run_in_threadpool(request.app.state.ctx.service.import_skill_source, source.id)
    except Exception as exc:
        return _redirect("/app/agents", f"{t('skill_source_failed')} {_friendly_runtime_error(exc, t)}", "error")
    return _redirect("/app/agents", t("skill_source_added"), "success")


@router.post("/app/agents/skill-sources/{source_id}/import")
async def import_skill_source_submit(request: Request, source_id: str):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    try:
        await run_in_threadpool(request.app.state.ctx.service.import_skill_source, source_id)
    except Exception as exc:
        return _redirect("/app/agents", f"{t('skill_source_failed')} {_friendly_runtime_error(exc, t)}", "error")
    return _redirect("/app/agents", t("skill_source_added"), "success")


@router.post("/app/agents/skills/{skill_id}/status")
async def update_skill_status_submit(request: Request, skill_id: str):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    try:
        await run_in_threadpool(
            request.app.state.ctx.service.set_agent_skill_status,
            skill_id,
            str(form.get("status", "")).strip(),
        )
    except Exception as exc:
        return _redirect("/app/agents", f"{t('skill_source_failed')} {_friendly_runtime_error(exc, t)}", "error")
    return _redirect("/app/agents", t("skill_status_updated"), "success")


@router.get("/app/overview", response_class=HTMLResponse)
def overview_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    missions = service.list_missions()
    status_counts: dict[str, int] = {}
    for mission in missions:
        status_counts[mission.status] = status_counts.get(mission.status, 0) + 1
    return templates.TemplateResponse(
        request=request,
        name="overview.html",
        context={
            **_base_context(request, "overview", "Overview"),
            "missions": missions[:12],
            "status_counts": status_counts,
            "audit_events": service.list_audit_events(limit=12),
        },
    )


@router.get("/app/tasks", response_class=HTMLResponse)
def tasks_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    missions = service.list_missions()
    status_filter = request.query_params.get("status", "").strip()
    query = request.query_params.get("q", "").strip().lower()
    status_counts: dict[str, int] = {}
    for mission in missions:
        status_counts[mission.status] = status_counts.get(mission.status, 0) + 1
    filtered = list(missions)
    if status_filter:
        filtered = [m for m in filtered if m.status == status_filter]
    if query:
        filtered = [
            m for m in filtered
            if query in (m.title or "").lower()
            or (m.summary and query in m.summary.lower())
        ]
    return templates.TemplateResponse(
        request=request,
        name="tasks.html",
        context={
            **_base_context(request, "tasks", "Tasks"),
            "missions": filtered,
            "all_missions_count": len(missions),
            "status_counts": status_counts,
            "active_status": status_filter,
            "active_query": request.query_params.get("q", ""),
        },
    )


@router.get("/app/search.json")
def search_json(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return JSONResponse({"results": []})
    query = request.query_params.get("q", "").strip().lower()
    if len(query) < 2:
        return JSONResponse({"results": []})
    service = request.app.state.ctx.service
    results: list[dict] = []
    try:
        for mission in service.list_missions():
            if len(results) >= 8:
                break
            haystack = f"{mission.title or ''} {mission.summary or ''}".lower()
            if query in haystack:
                results.append({
                    "type": "mission",
                    "title": mission.title or mission.id,
                    "subtitle": (mission.summary or "")[:120],
                    "url": f"/app/missions/{mission.id}",
                })
    except Exception:
        pass
    try:
        organization = service.organization_snapshot()
        for agent in (organization.agents or [])[:60]:
            if len(results) >= 16:
                break
            name = getattr(agent, "name", "") or getattr(agent, "role_name", "")
            role = getattr(agent, "role_name", "")
            if query in str(name).lower() or query in str(role).lower():
                results.append({
                    "type": "agent",
                    "title": str(name) or str(role),
                    "subtitle": str(role),
                    "url": "/app/agents",
                })
    except Exception:
        pass
    return JSONResponse({"results": results[:20]})


@router.get("/app/activity", response_class=HTMLResponse)
def activity_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    return templates.TemplateResponse(
        request=request,
        name="activity.html",
        context={
            **_base_context(request, "activity", "Activity"),
            "recent_runs": service.list_recent_runs(limit=20),
            "audit_events": service.list_audit_events(limit=30),
        },
    )


@router.get("/app/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    runtime_health = request.app.state.ctx.service.runtime_health()
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={
            **_base_context(request, "settings", "Settings"),
            "runtime_health": runtime_health,
            "provider_keys": {
                "openai": bool(get_openai_api_key()),
                "anthropic": bool(get_anthropic_api_key()),
            },
            "telegram_secrets": {
                "bot_token": bool(get_telegram_bot_token()),
                "webhook_secret": bool(get_telegram_webhook_secret()),
            },
            "telegram_pairing_code": request.session.pop("telegram_pairing_code", ""),
            "telegram_webhook_url": str(request.url_for("telegram_webhook")),
        },
    )


@router.post("/app/settings/runtime")
async def update_runtime_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    mode = str(form.get("runtime_mode", "api")).strip() or "api"
    provider = str(form.get("runtime_provider", "")).strip().lower() or None
    if mode == "subscription_executor":
        provider = None
    runtime = RuntimeSelection(
        mode=mode,
        provider=provider,
        model=None if mode == "subscription_executor" else str(form.get("runtime_model", "")).strip() or None,
        executor=str(form.get("runtime_executor", "")).strip() or None,
        base_url=None if mode == "subscription_executor" else str(form.get("runtime_base_url", "")).strip() or None,
    )
    try:
        await run_in_threadpool(request.app.state.ctx.service.update_runtime, runtime)
        if provider is not None:
            _save_provider_api_key(provider, str(form.get("api_key", "")))
    except Exception as exc:
        return _redirect("/app/settings", str(exc), "error")
    next_path = _safe_redirect_path(str(form.get("next_path", "/app/settings")), "/app/settings")
    return _redirect(next_path, t("runtime_settings_saved"), "success")


@router.post("/app/settings/runtime/test")
async def test_runtime_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    mode = str(form.get("runtime_mode", settings.runtime.mode)).strip() or settings.runtime.mode
    provider = str(form.get("runtime_provider", "")).strip().lower() or None
    if mode == "subscription_executor":
        provider = None
    runtime = RuntimeSelection(
        mode=mode,
        provider=provider,
        model=None if mode == "subscription_executor" else str(form.get("runtime_model", "")).strip() or settings.runtime.model,
        executor=str(form.get("runtime_executor", "")).strip() or settings.runtime.executor,
        base_url=None if mode == "subscription_executor" else str(form.get("runtime_base_url", "")).strip() or None,
    )
    next_path = _safe_redirect_path(str(form.get("next_path", "/app/models")), "/app/models")
    try:
        await run_in_threadpool(request.app.state.ctx.service.test_runtime_connection, runtime, str(form.get("api_key", "")))
    except Exception as exc:
        return _redirect(next_path, f"{t('api_connection_failed')} {_friendly_runtime_error(exc, t)}", "error")
    return _redirect(next_path, t("api_connection_ok"), "success")


@router.post("/app/settings/telegram")
async def update_telegram_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    bot_token = str(form.get("telegram_bot_token", "")).strip()
    webhook_secret = str(form.get("telegram_webhook_secret", "")).strip()
    if bot_token:
        write_state_secret(TELEGRAM_BOT_TOKEN_STATE_SECRET, bot_token)
    if webhook_secret:
        write_state_secret(TELEGRAM_WEBHOOK_SECRET_STATE_SECRET, webhook_secret)
    allowed_raw = str(form.get("telegram_allowed_user_id", "")).strip()
    try:
        allowed_user_id = int(allowed_raw) if allowed_raw else None
    except ValueError:
        return _redirect("/app/settings", "Telegram user ID must be a number.", "error")
    await run_in_threadpool(
        request.app.state.ctx.service.update_telegram_settings,
        settings.telegram.model_copy(
            update={
                "enabled": bool(form.get("telegram_enabled")),
                "bot_token_set": bool(bot_token or get_telegram_bot_token()),
                "webhook_secret_set": bool(webhook_secret or get_telegram_webhook_secret()),
                "allowed_user_id": allowed_user_id,
                "notify_approvals": bool(form.get("telegram_notify_approvals")),
                "allow_low_risk_approval": bool(form.get("telegram_allow_low_risk_approval")),
            }
        ),
    )
    return _redirect("/app/settings", t("telegram_settings_saved"), "success")


@router.post("/app/settings/telegram/pairing-code")
async def create_telegram_pairing_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    code = await run_in_threadpool(request.app.state.ctx.service.create_telegram_pairing_code)
    request.session["telegram_pairing_code"] = code
    return _redirect("/app/settings", t("telegram_pairing_created"), "success")


@router.post("/app/ceo/conversation")
async def create_ceo_conversation_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    body = str(form.get("body", "")).strip()
    if not body:
        return _redirect("/app/praetor", t("message_to_ceo_placeholder"), "error")
    if runtime_message := _runtime_unavailable_message(request, t):
        return _redirect("/app/models", runtime_message, "error")
    try:
        await run_in_threadpool(request.app.state.ctx.service.create_ceo_message, ConversationCreateRequest(body=body))
    except Exception as exc:
        return _redirect("/app/praetor", _friendly_runtime_error(exc, t), "error")
    return _redirect("/app/praetor?focus=ceo-chat", t("ceo_message_sent"), "success")


@router.post("/app/ceo/transcribe")
async def transcribe_ceo_audio_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return JSONResponse({"error": "Complete onboarding first."}, status_code=400)
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    if not get_openai_api_key():
        return JSONResponse({"error": t("voice_openai_key_missing")}, status_code=400)
    upload = form.get("audio")
    if not isinstance(upload, UploadFile):
        return JSONResponse({"error": t("voice_error")}, status_code=400)
    audio = await upload.read()
    if len(audio) > 25 * 1024 * 1024:
        return JSONResponse({"error": t("voice_audio_too_large")}, status_code=413)
    language = "zh" if _ui_language(request, settings) == "zh-TW" else "en"
    try:
        text = await run_in_threadpool(
            openai_audio_transcription,
            audio,
            filename=upload.filename or "praetor-voice.webm",
            content_type=upload.content_type or "audio/webm",
            language=language,
        )
    except Exception as exc:
        return JSONResponse({"error": _friendly_runtime_error(exc, t)}, status_code=502)
    return JSONResponse({"text": text})


@router.get("/app/memory", response_class=HTMLResponse)
def memory_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    return templates.TemplateResponse(
        request=request,
        name="memory.html",
        context={
            **_base_context(request, "memory", "Memory"),
            "wiki_pages": service.list_wiki_pages(),
            "recent_runs": service.list_recent_runs(limit=10),
            "knowledge": service.knowledge_snapshot(),
        },
    )


@router.get("/app/decisions", response_class=HTMLResponse)
def decisions_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    return templates.TemplateResponse(
        request=request,
        name="decisions.html",
        context={
            **_base_context(request, "decisions", "Decisions"),
            "decision_items": service.list_decision_items(),
            "audit_events": service.list_audit_events(limit=25),
        },
    )


@router.get("/app/models", response_class=HTMLResponse)
def models_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    return templates.TemplateResponse(
        request=request,
        name="models.html",
        context={
            **_base_context(request, "models", "Models"),
            "usage_summary": service.usage_summary(),
            "runtime_health": service.runtime_health(),
            "provider_keys": {
                "openai": bool(get_openai_api_key()),
                "anthropic": bool(get_anthropic_api_key()),
            },
        },
    )


@router.get("/app/meetings", response_class=HTMLResponse)
def meetings_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    return templates.TemplateResponse(
        request=request,
        name="meetings.html",
        context={
            **_base_context(request, "meetings", "Meetings"),
            "meetings": service.list_meetings(),
        },
    )


@router.get("/m/briefing", response_class=HTMLResponse)
def mobile_briefing_page(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    missions = service.list_missions()
    return templates.TemplateResponse(
        request=request,
        name="mobile_briefing.html",
        context={
            **_base_context(request, "mobile", "Mobile Briefing"),
            "missions": missions[:8],
        },
    )


@router.get("/app/missions/{mission_id}", response_class=HTMLResponse)
def mission_detail_page(request: Request, mission_id: str):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    service = request.app.state.ctx.service
    try:
        mission = service.get_mission(mission_id)
    except KeyError:
        return _redirect("/app/tasks", f"Mission not found: {mission_id}", "error")
    tasks = service.list_mission_tasks(mission_id)
    texts = service.read_mission_texts(mission_id)
    runs = service.list_mission_runs(mission_id)
    work_sessions = service.mission_work_sessions(mission_id)
    knowledge = service.mission_knowledge_snapshot(mission_id)
    memory_promotion_reviews = service.mission_memory_promotion_reviews(mission_id)
    board_briefings = service.list_board_briefings(mission_id)
    run_attempts = service.list_run_attempts(mission_id)
    workspace_scope = service.mission_workspace_scope(mission_id)
    workflow_contract = service.workflow_contract()
    stage_transitions = service.mission_stage_transitions(mission_id)
    work_trace = service.mission_work_trace(mission_id)
    agent_contracts = service.mission_agent_contracts(mission_id)
    executor_controls = service.storage.list_executor_controls(mission_id=mission_id)
    return templates.TemplateResponse(
        request=request,
        name="mission_detail.html",
        context={
            **_base_context(request, "tasks", mission.title),
            "mission": mission,
            "tasks": tasks,
            "texts": texts,
            "runs": runs,
            "work_sessions": work_sessions,
            "knowledge": knowledge,
            "memory_promotion_reviews": memory_promotion_reviews,
            "board_briefings": board_briefings,
            "run_attempts": run_attempts,
            "workspace_scope": workspace_scope,
            "workflow_contract": workflow_contract,
            "stage_transitions": stage_transitions,
            "work_trace": work_trace,
            "agent_contracts": agent_contracts,
            "executor_controls": executor_controls,
            "mission_stages": ["intake", "staffing", "planning", "execution", "review", "owner_decision", "memory_promotion", "closeout"],
        },
    )


@router.post("/app/onboarding")
async def onboarding_submit(request: Request):
    form = await request.form()
    _validate_form_csrf(request, form)
    require_setup_token(request, str(form.get("setup_token", "")) or None)
    require_approval = form.getlist("require_approval")
    answers = OnboardingAnswers(
        owner_name=str(form.get("owner_name", "Founder")),
        owner_email=str(form.get("owner_email", "")) or None,
        owner_password=str(form.get("owner_password", "")).strip() or None,
        language=str(form.get("language", "en")),
        leadership_style=str(form.get("leadership_style", "strategic")),
        decision_style=str(form.get("decision_style", "balanced")),
        organization_style=str(form.get("organization_style", "lean")),
        autonomy_mode=str(form.get("autonomy_mode", "hybrid")),
        risk_priority=str(form.get("risk_priority", "avoid_wrong_decisions")),
        workspace_root=str(form.get("workspace_root", "~/praetor-workspace")),
        runtime={
            "mode": str(form.get("runtime_mode", "api")),
            "provider": str(form.get("runtime_provider", "")).strip() or None,
            "model": str(form.get("runtime_model", "")).strip() or None,
            "executor": str(form.get("runtime_executor", "codex")),
            "base_url": str(form.get("runtime_base_url", "")).strip() or None,
        },
        require_approval=[str(item) for item in require_approval],
    )
    password_confirm = str(form.get("owner_password_confirm", "")).strip()
    if answers.owner_password != password_confirm:
        return _redirect("/app/praetor", "Password confirmation does not match.", "error")
    try:
        settings = await run_in_threadpool(request.app.state.ctx.service.complete_onboarding, answers)
        provider = answers.runtime.get("provider") if isinstance(answers.runtime, dict) else answers.runtime.provider
        if provider:
            _save_provider_api_key(str(provider), str(form.get("api_key", "")))
    except Exception as exc:
        return _redirect("/app/praetor", str(exc), "error")
    request.session["authenticated"] = True
    request.session["owner_name"] = settings.owner.name
    request.session["owner_email"] = settings.owner.email
    return _redirect("/app/praetor?focus=ceo-chat", "Praetor is initialized. Start by talking with the CEO.", "success")


@router.post("/app/login")
async def login_submit(request: Request):
    form = await request.form()
    _validate_form_csrf(request, form)
    password = str(form.get("password", "")).strip()
    next_path = _safe_redirect_path(str(form.get("next_path", "")).strip(), "/app/praetor")
    rate_key = request.client.host if request.client else "unknown"
    login_rate_limiter.check(rate_key)
    try:
        settings = await run_in_threadpool(request.app.state.ctx.service.authenticate_owner, LoginRequest(password=password))
    except Exception as exc:
        login_rate_limiter.record_failure(rate_key)
        return _redirect("/app/login", str(exc), "error")
    login_rate_limiter.reset(rate_key)
    request.session["authenticated"] = True
    request.session["owner_name"] = settings.owner.name
    request.session["owner_email"] = settings.owner.email
    csrf_token(request)
    return _redirect(next_path, "Login successful.", "success")


@router.post("/app/logout")
async def logout_submit(request: Request):
    form = await request.form()
    _validate_form_csrf(request, form)
    request.session.clear()
    return _redirect("/app/login", "Logged out.", "success")


@router.post("/app/missions")
async def create_mission_submit(request: Request):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    title = str(form.get("title", "")).strip()
    if not title:
        return _redirect("/app/praetor", "Mission title is required.", "error")
    if runtime_message := _runtime_unavailable_message(request, t):
        return _redirect("/app/models", runtime_message, "error")
    requested_outputs_raw = str(form.get("requested_outputs", "")).strip()
    requested_outputs = [line.strip() for line in requested_outputs_raw.splitlines() if line.strip()]
    mission = await run_in_threadpool(
        request.app.state.ctx.service.create_mission,
        MissionCreateRequest(
            title=title,
            summary=str(form.get("summary", "")).strip() or None,
            domains=[str(form.get("domain", "operations"))],
            priority=str(form.get("priority", "normal")),
            requested_outputs=requested_outputs,
        ),
    )
    return _redirect(f"/app/missions/{mission.id}", "Mission created.", "success")


@router.post("/app/missions/{mission_id}/run")
async def run_mission_submit(request: Request, mission_id: str):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    if runtime_message := _runtime_unavailable_message(request, t):
        return _redirect("/app/models", runtime_message, "error")
    ctx = request.app.state.ctx
    registry = ctx.run_registry
    if registry.is_running(mission_id):
        return _redirect(f"/app/missions/{mission_id}", t("mission_already_running"), "error")
    run_id = f"run_{int(datetime.utcnow().timestamp() * 1000)}_{mission_id[:8]}"
    registry.start(mission_id, run_id)

    def _execute() -> None:
        try:
            ctx.service.run_mission(mission_id)
            registry.finish(mission_id, "completed")
        except Exception as exc:
            registry.finish(mission_id, "failed", message=_friendly_runtime_error(exc, t))

    threading.Thread(target=_execute, daemon=True, name=f"mission-run-{mission_id}").start()
    return _redirect(f"/app/missions/{mission_id}", t("mission_run_started"), "success")


@router.get("/app/missions/{mission_id}/events")
async def mission_events_sse(request: Request, mission_id: str):
    settings = _require_initialized(request)
    if settings is None:
        return JSONResponse({"error": "not_initialized"}, status_code=403)
    registry = request.app.state.ctx.run_registry

    async def stream():
        try:
            async for event in registry.subscribe(mission_id):
                if await request.is_disconnected():
                    break
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "finished":
                    break
        except asyncio.CancelledError:
            return
        yield "event: close\ndata: {}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/app/missions/{mission_id}/pause")
async def pause_mission_submit(request: Request, mission_id: str):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    try:
        await run_in_threadpool(request.app.state.ctx.service.pause_mission, mission_id, MissionPauseRequest())
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", _friendly_runtime_error(exc, t), "error")
    return _redirect(f"/app/missions/{mission_id}", t("mission_paused"), "success")


@router.post("/app/missions/{mission_id}/continue")
async def continue_mission_submit(request: Request, mission_id: str):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    try:
        await run_in_threadpool(request.app.state.ctx.service.continue_mission, mission_id, MissionContinueRequest())
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", _friendly_runtime_error(exc, t), "error")
    return _redirect(f"/app/missions/{mission_id}", t("mission_resumed"), "success")


@router.post("/app/missions/{mission_id}/stop")
async def stop_mission_submit(request: Request, mission_id: str):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    try:
        await run_in_threadpool(request.app.state.ctx.service.stop_mission, mission_id, MissionStopRequest())
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", _friendly_runtime_error(exc, t), "error")
    return _redirect(f"/app/missions/{mission_id}", t("mission_stopped"), "success")


@router.post("/app/missions/{mission_id}/executor-control")
async def mission_executor_control_submit(request: Request, mission_id: str):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    try:
        await run_in_threadpool(
            request.app.state.ctx.service.request_executor_control,
            mission_id,
            str(form.get("action", "")).strip(),
            str(form.get("reason", "")).strip() or None,
            str(form.get("target_session_id", "")).strip() or None,
        )
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", _friendly_runtime_error(exc, t), "error")
    return _redirect(f"/app/missions/{mission_id}", t("executor_control_requested"), "success")


@router.post("/app/missions/{mission_id}/meeting")
async def create_meeting_submit(request: Request, mission_id: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    try:
        meeting = await run_in_threadpool(request.app.state.ctx.service.create_review_meeting, mission_id)
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", str(exc), "error")
    return _redirect("/app/meetings", f"Meeting created: {meeting.id}", "success")


@router.post("/app/missions/{mission_id}/memory-promotion")
async def create_memory_promotion_submit(request: Request, mission_id: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    try:
        review = await run_in_threadpool(request.app.state.ctx.service.create_memory_promotion_review, mission_id)
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", str(exc), "error")
    return _redirect(f"/app/missions/{mission_id}", f"Memory promotion review created: {review.id}", "success")


@router.post("/app/missions/{mission_id}/board-briefing")
async def create_board_briefing_submit(request: Request, mission_id: str):
    settings = _require_initialized(request)
    if settings is None:
        return _redirect("/app/praetor", "Complete onboarding first.", "error")
    form = await request.form()
    _validate_form_csrf(request, form)
    t = _translator(_ui_language(request, settings))
    if runtime_message := _runtime_unavailable_message(request, t):
        return _redirect("/app/models", runtime_message, "error")
    try:
        briefing = await run_in_threadpool(request.app.state.ctx.service.create_board_briefing, mission_id)
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", str(exc), "error")
    return _redirect(f"/app/missions/{mission_id}", f"Board briefing ready: {briefing.id}", "success")


@router.post("/app/missions/{mission_id}/approval")
async def create_approval_submit(request: Request, mission_id: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    try:
        await run_in_threadpool(
            request.app.state.ctx.service.create_approval,
            ApprovalCreateRequest(
                mission_id=mission_id,
                category=str(form.get("category", "change_strategy")),
                reason=str(form.get("reason", "Manual checkpoint requested by owner.")),
            ),
        )
    except Exception as exc:
        return _redirect(f"/app/missions/{mission_id}", str(exc), "error")
    return _redirect(f"/app/missions/{mission_id}", "Approval checkpoint created.", "success")


@router.post("/app/approvals/{approval_id}/{status}")
async def resolve_approval_submit(request: Request, approval_id: str, status: str):
    form = await request.form()
    _validate_form_csrf(request, form)
    try:
        await run_in_threadpool(request.app.state.ctx.service.resolve_approval, approval_id, status)
    except Exception as exc:
        return _redirect("/app/overview", str(exc), "error")
    return _redirect("/app/overview", f"Approval {status}.", "success")
