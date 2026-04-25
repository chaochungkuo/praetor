from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI

from . import __version__


API_BASE_URL = os.getenv("PRAETOR_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
BRIDGE_BASE_URL = os.getenv("PRAETOR_BRIDGE_BASE_URL", "").rstrip("/")
RUNTIME_MODE = os.getenv("PRAETOR_RUNTIME_MODE", "api")
ALLOWED_EXECUTORS = os.getenv("PRAETOR_ALLOWED_EXECUTORS", "codex,claude_code")
STARTED_AT = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

app = FastAPI(title="praetor-worker", version=__version__)


async def _probe(url: str) -> str:
    if not url:
        return "not_configured"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            return "healthy" if response.is_success else "degraded"
    except Exception:
        return "unreachable"


@app.get("/health")
async def health():
    api_health = await _probe(f"{API_BASE_URL}/health")
    bridge_health = await _probe(f"{BRIDGE_BASE_URL}/health") if BRIDGE_BASE_URL else "not_configured"
    return {
        "status": "healthy",
        "service": "worker",
        "version": __version__,
        "started_at": STARTED_AT,
        "runtime_mode": RUNTIME_MODE,
        "allowed_executors": [item.strip() for item in ALLOWED_EXECUTORS.split(",") if item.strip()],
        "api_base_url": API_BASE_URL,
        "api_health": api_health,
        "bridge_base_url": BRIDGE_BASE_URL or None,
        "bridge_health": bridge_health,
    }


@app.get("/status")
async def status():
    return {
        "service": "worker",
        "started_at": STARTED_AT,
        "runtime_mode": RUNTIME_MODE,
        "queue_mode": "inline_runtime_until_async_queue_exists",
    }
