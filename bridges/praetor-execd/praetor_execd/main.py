from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request

from . import __version__
from .auth import authorization_header, require_bearer_token
from .config import AppConfig, load_config
from .models import (
    ApiEnvelope,
    CancelRunResult,
    CreateRunAccepted,
    CreateRunRequest,
    EnvelopeError,
    HealthData,
    RunEventsPage,
)
from .runner import RunManager
from .service import BridgeService
from .store import RunStore


class AppState:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.started_at = time.monotonic()
        self.service = BridgeService(config)
        self.store = RunStore(
            max_event_buffer=config.runtime.max_event_buffer,
            persist_run_logs=config.runtime.persist_run_logs,
            log_dir=config.runtime.log_dir,
        )
        self.runner = RunManager(config, self.service, self.store)


def build_state() -> AppState:
    return AppState(load_config())


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ctx = build_state()
    yield


app = FastAPI(title="praetor-execd", version=__version__, lifespan=lifespan)


def get_ctx(request: Request) -> AppState:
    return request.app.state.ctx


def require_auth(
    request: Request,
    authorization: str | None = Depends(authorization_header),
) -> AppState:
    ctx = get_ctx(request)
    require_bearer_token(authorization, ctx.config.server.auth_token)
    return ctx


def error_envelope(code: str, message: str, status_code: int) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ApiEnvelope(
            ok=False,
            data=None,
            error=EnvelopeError(code=code, message=message),
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and {"ok", "data", "error"} <= set(exc.detail.keys()):
        return fastapi_json(exc.status_code, exc.detail)
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "http_error", "message": str(exc.detail)}
    return fastapi_json(
        exc.status_code,
        ApiEnvelope(ok=False, data=None, error=EnvelopeError(**detail)).model_dump(),
    )


def fastapi_json(status_code: int, payload: dict):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status_code, content=payload)


@app.get("/health")
def get_health(ctx: AppState = Depends(require_auth)):
    data = HealthData(
        status="healthy",
        version=__version__,
        uptime_seconds=round(time.monotonic() - ctx.started_at, 3),
        configured_executors=sorted(ctx.config.executors.keys()),
    )
    return ApiEnvelope(ok=True, data=data, error=None)


@app.get("/executors")
def get_executors(ctx: AppState = Depends(require_auth)):
    return ApiEnvelope(ok=True, data={"executors": ctx.service.executor_summaries()}, error=None)


@app.post("/runs")
def create_run(payload: CreateRunRequest, ctx: AppState = Depends(require_auth)):
    try:
        ctx.service.validate_executor(payload.executor)
        host_workdir = ctx.service.map_target_workdir(payload)
    except ValueError as exc:
        raise error_envelope("executor_not_available", str(exc), 400) from exc
    except PermissionError as exc:
        raise error_envelope("permission_error", str(exc), 400) from exc

    record = ctx.store.create_run(payload, host_workdir)
    ctx.runner.enqueue(payload, record.run_id, host_workdir)
    accepted = CreateRunAccepted(
        run_id=record.run_id,
        status=record.status,
        executor=record.executor,
    )
    return ApiEnvelope(ok=True, data=accepted, error=None)


@app.get("/runs/{run_id}")
def get_run(run_id: str, ctx: AppState = Depends(require_auth)):
    record = ctx.store.get_run(run_id)
    if record is None:
        raise error_envelope("not_found", f"Run not found: {run_id}", 404)
    return ApiEnvelope(ok=True, data=record, error=None)


@app.get("/runs/{run_id}/events")
def get_run_events(
    run_id: str,
    after_seq: int = Query(default=0, ge=0),
    ctx: AppState = Depends(require_auth),
):
    record = ctx.store.get_run(run_id)
    if record is None:
        raise error_envelope("not_found", f"Run not found: {run_id}", 404)
    events = ctx.store.list_events(run_id, after_seq=after_seq)
    payload = RunEventsPage(events=events, next_seq=(events[-1].seq + 1) if events else after_seq + 1)
    return ApiEnvelope(ok=True, data=payload, error=None)


@app.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str, ctx: AppState = Depends(require_auth)):
    record = ctx.store.cancel_run(run_id)
    if record is None:
        raise error_envelope("not_found", f"Run not found: {run_id}", 404)
    ctx.runner.cancel(run_id)
    result = CancelRunResult(
        run_id=run_id,
        status=record.status,
        accepted=record.status == "cancelled",
    )
    return ApiEnvelope(ok=True, data=result, error=None)
