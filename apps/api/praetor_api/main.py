from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from . import __version__
from .config import get_require_login, get_secure_cookie, get_session_max_age_seconds, get_session_secret, get_state_dir
from .models import (
    ApiEnvelope,
    ApprovalCreateRequest,
    ConversationCreateRequest,
    LoginRequest,
    MissionContinueRequest,
    MissionCreateRequest,
    MissionPauseRequest,
    MissionStopRequest,
    OnboardingAnswers,
)
from .service import PraetorService
from .security import csrf_token, login_rate_limiter, require_csrf, require_setup_token, validate_runtime_security
from .storage import AppStorage
from .ui import install_ui


class AppState:
    def __init__(self) -> None:
        state_dir = get_state_dir()
        self.state_dir = state_dir
        self.storage = AppStorage(state_dir)
        self.service = PraetorService(self.storage)


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_runtime_security()
    app.state.ctx = AppState()
    yield


app = FastAPI(title="praetor-api", version=__version__, lifespan=lifespan)
install_ui(app)


def get_ctx() -> AppState:
    return app.state.ctx


def ok(data):
    return ApiEnvelope(ok=True, data=data, error=None)


def fail(status_code: int, code: str, message: str):
    raise HTTPException(
        status_code=status_code,
        detail=ApiEnvelope(ok=False, data=None, error={"code": code, "message": message}).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc: HTTPException):
    if isinstance(exc.detail, dict) and {"ok", "data", "error"} <= set(exc.detail.keys()):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    if isinstance(exc.detail, dict) and {"code", "message"} <= set(exc.detail.keys()):
        return JSONResponse(
            status_code=exc.status_code,
            content=ApiEnvelope(ok=False, data=None, error=exc.detail).model_dump(),
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiEnvelope(
            ok=False,
            data=None,
            error={"code": "http_error", "message": str(exc.detail)},
        ).model_dump(),
    )


@app.exception_handler(ValueError)
async def value_error_handler(_, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content=ApiEnvelope(
            ok=False,
            data=None,
            error={"code": "invalid_request", "message": str(exc)},
        ).model_dump(),
    )


def _is_authenticated(request: Request) -> bool:
    return bool(request.session.get("authenticated"))


def _is_public_path(path: str) -> bool:
    if path in {"/health", "/", "/app", "/app/welcome", "/app/login", "/auth/login", "/auth/logout", "/auth/session"}:
        return True
    if path.startswith("/app/set-language/"):
        return True
    if path.startswith("/static/"):
        return True
    return False


class AuthGuardMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.authenticated = False
        request.state.session_owner = None
        path = request.url.path
        ctx = getattr(request.app.state, "ctx", None)
        if ctx is None:
            return await call_next(request)

        settings = ctx.service.get_settings()
        request.state.settings_initialized = settings is not None

        if settings is None or not get_require_login() or not ctx.service.has_owner_auth():
            return await call_next(request)

        session = request.scope.get("session") or {}
        authenticated = bool(session.get("authenticated"))
        request.state.authenticated = authenticated
        request.state.session_owner = session.get("owner_name")
        if authenticated or _is_public_path(path):
            return await call_next(request)

        if path.startswith("/app/") or path.startswith("/m/"):
            next_path = request.url.path
            if request.url.query:
                next_path = f"{next_path}?{request.url.query}"
            return RedirectResponse(url=f"/app/login?next={next_path}", status_code=303)

        return JSONResponse(
            status_code=401,
            content=ApiEnvelope(
                ok=False,
                data=None,
                error={"code": "unauthorized", "message": "Login required."},
            ).model_dump(),
        )


class ApiCSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
            return await call_next(request)
        path = request.url.path
        if path.startswith("/app/") or path.startswith("/m/"):
            return await call_next(request)
        if path in {"/auth/login", "/onboarding/complete"}:
            return await call_next(request)
        if path.startswith("/static/"):
            return await call_next(request)
        session = request.scope.get("session") or {}
        if session.get("authenticated"):
            try:
                require_csrf(request)
            except HTTPException as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content=ApiEnvelope(
                        ok=False,
                        data=None,
                        error={"code": "csrf_failed", "message": "Invalid CSRF token."},
                    ).model_dump(),
                )
        return await call_next(request)


app.add_middleware(AuthGuardMiddleware)
app.add_middleware(ApiCSRFMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=get_session_secret(),
    session_cookie="praetor_session",
    max_age=get_session_max_age_seconds(),
    same_site="lax",
    https_only=get_secure_cookie(),
)


@app.get("/health")
def health():
    return ok({"status": "healthy", "version": __version__})


@app.get("/auth/session")
def auth_session(request: Request):
    settings = get_ctx().service.get_settings()
    ui_language = request.cookies.get("praetor_ui_lang")
    if ui_language not in {"en", "zh-TW"}:
        ui_language = settings.owner.preferred_language if settings is not None else "en"
    return ok(
        {
            "initialized": settings is not None,
            "authenticated": _is_authenticated(request),
            "owner_name": request.session.get("owner_name"),
            "ui_language": ui_language,
            "csrf_token": csrf_token(request),
        }
    )


@app.post("/auth/login")
def auth_login(request: Request, payload: LoginRequest):
    rate_key = request.client.host if request.client else "unknown"
    login_rate_limiter.check(rate_key)
    try:
        settings = get_ctx().service.authenticate_owner(payload)
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))
    except ValueError as exc:
        login_rate_limiter.record_failure(rate_key)
        fail(401, "invalid_credentials", str(exc))
    login_rate_limiter.reset(rate_key)
    request.session["authenticated"] = True
    request.session["owner_name"] = settings.owner.name
    request.session["owner_email"] = settings.owner.email
    csrf_token(request)
    return ok({"authenticated": True, "owner_name": settings.owner.name})


@app.post("/auth/logout")
def auth_logout(request: Request):
    request.session.clear()
    return ok({"authenticated": False})


@app.get("/settings")
def get_settings():
    settings = get_ctx().service.get_settings()
    return ok(settings)


@app.post("/onboarding/preview")
def onboarding_preview(payload: OnboardingAnswers):
    return ok(get_ctx().service.preview_onboarding(payload))


@app.post("/onboarding/complete")
def onboarding_complete(request: Request, payload: OnboardingAnswers):
    require_setup_token(request)
    try:
        settings = get_ctx().service.complete_onboarding(payload)
    except RuntimeError as exc:
        fail(400, "onboarding_error", str(exc))
    request.session["authenticated"] = True
    request.session["owner_name"] = settings.owner.name
    request.session["owner_email"] = settings.owner.email
    csrf_token(request)
    return ok(settings)


@app.get("/praetor/briefing")
def praetor_briefing():
    try:
        return ok(get_ctx().service.praetor_briefing())
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))


@app.get("/missions")
def list_missions():
    try:
        return ok({"missions": get_ctx().service.list_missions()})
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))


@app.post("/missions")
def create_mission(payload: MissionCreateRequest):
    try:
        return ok(get_ctx().service.create_mission(payload))
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))


@app.get("/missions/{mission_id}")
def get_mission(mission_id: str):
    try:
        return ok(get_ctx().service.get_mission(mission_id))
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))
    except KeyError:
        fail(404, "not_found", f"Mission not found: {mission_id}")


@app.post("/missions/{mission_id}/pause")
def pause_mission(mission_id: str, payload: MissionPauseRequest):
    try:
        return ok(get_ctx().service.pause_mission(mission_id, payload))
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))
    except KeyError:
        fail(404, "not_found", f"Mission not found: {mission_id}")


@app.post("/missions/{mission_id}/continue")
def continue_mission(mission_id: str, payload: MissionContinueRequest):
    try:
        return ok(get_ctx().service.continue_mission(mission_id, payload))
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))
    except KeyError:
        fail(404, "not_found", f"Mission not found: {mission_id}")


@app.post("/missions/{mission_id}/stop")
def stop_mission(mission_id: str, payload: MissionStopRequest):
    try:
        return ok(get_ctx().service.stop_mission(mission_id, payload))
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))
    except KeyError:
        fail(404, "not_found", f"Mission not found: {mission_id}")


@app.post("/missions/{mission_id}/run")
def run_mission(mission_id: str):
    try:
        return ok(get_ctx().service.run_mission(mission_id))
    except RuntimeError as exc:
        fail(400, "runtime_error", str(exc))
    except KeyError:
        fail(404, "not_found", f"Mission not found: {mission_id}")


@app.post("/missions/{mission_id}/meeting")
def create_review_meeting(mission_id: str):
    try:
        return ok(get_ctx().service.create_review_meeting(mission_id))
    except RuntimeError as exc:
        fail(400, "runtime_error", str(exc))
    except KeyError:
        fail(404, "not_found", f"Mission not found: {mission_id}")


@app.get("/approvals")
def list_approvals():
    return ok({"approvals": get_ctx().service.list_approvals()})


@app.post("/approvals")
def create_approval(payload: ApprovalCreateRequest):
    try:
        return ok(get_ctx().service.create_approval(payload))
    except RuntimeError as exc:
        fail(400, "runtime_error", str(exc))


@app.post("/approvals/{approval_id}/{status}")
def resolve_approval(approval_id: str, status: str):
    try:
        return ok(get_ctx().service.resolve_approval(approval_id, status))
    except KeyError:
        fail(404, "not_found", f"Approval not found: {approval_id}")


@app.post("/schemas/export")
def export_schemas():
    output_dir = get_ctx().state_dir / "schemas"
    paths = get_ctx().service.export_schemas(output_dir)
    return ok({"paths": [str(path) for path in paths]})


@app.get("/api/office/snapshot")
def office_snapshot():
    try:
        return ok(get_ctx().service.office_snapshot())
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))


@app.get("/api/organization")
def organization_snapshot():
    try:
        return ok(get_ctx().service.organization_snapshot())
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))


@app.get("/api/missions/{mission_id}/organization")
def mission_organization_snapshot(mission_id: str):
    try:
        return ok(get_ctx().service.organization_snapshot(mission_id=mission_id))
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))


@app.get("/api/missions/{mission_id}/completion-contract")
def mission_completion_contract(mission_id: str):
    try:
        return ok(get_ctx().service.mission_completion_contract(mission_id))
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))
    except KeyError:
        fail(404, "not_found", f"Mission not found: {mission_id}")


@app.get("/api/office/conversation")
def office_conversation():
    try:
        return ok({"messages": get_ctx().service.list_ceo_messages()})
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))


@app.post("/api/office/conversation")
def create_office_conversation(payload: ConversationCreateRequest):
    try:
        result = get_ctx().service.create_ceo_message(payload)
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))
    except ValueError as exc:
        fail(400, "invalid_request", str(exc))
    return ok(result)


@app.get("/api/missions/{mission_id}/timeline")
def mission_timeline(mission_id: str):
    try:
        return ok({"events": get_ctx().service.mission_timeline(mission_id)})
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))
    except KeyError:
        fail(404, "not_found", f"Mission not found: {mission_id}")


@app.get("/api/missions/{mission_id}/agent-messages")
def mission_agent_messages(mission_id: str):
    try:
        return ok({"messages": get_ctx().service.mission_agent_messages(mission_id)})
    except RuntimeError as exc:
        fail(400, "not_initialized", str(exc))
    except KeyError:
        fail(404, "not_found", f"Mission not found: {mission_id}")


@app.get("/debug/state")
def debug_state():
    from .config import get_debug_routes_enabled

    if not get_debug_routes_enabled():
        fail(404, "not_found", "Debug routes are disabled.")
    state_dir = get_ctx().state_dir
    return ok(
        {
            "state_dir": str(state_dir),
            "settings_exists": (state_dir / "settings.json").exists(),
            "sqlite_exists": (state_dir / "index.sqlite3").exists(),
        }
    )
