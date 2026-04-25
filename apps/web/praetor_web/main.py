from __future__ import annotations

import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__


UPSTREAM = os.getenv("PRAETOR_WEB_UPSTREAM", "http://127.0.0.1:9741").rstrip("/")
DIST_DIR = Path(__file__).resolve().parents[1] / "dist"
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
}

app = FastAPI(title="praetor-web", version=__version__)

if (DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")


@app.get("/health")
async def health():
    upstream_health = "unknown"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{UPSTREAM}/health")
            upstream_health = "healthy" if response.is_success else "degraded"
    except Exception:
        upstream_health = "unreachable"
    return {
        "status": "healthy",
        "service": "web",
        "version": __version__,
        "upstream": UPSTREAM,
        "upstream_health": upstream_health,
    }


@app.get("/office")
async def office_app():
    index = DIST_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse(
        status_code=503,
        content={
            "ok": False,
            "error": {
                "code": "office_not_built",
                "message": "Praetor Office frontend has not been built.",
            },
        },
    )


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy(path: str, request: Request):
    upstream_url = f"{UPSTREAM}/{path}".rstrip("/")
    if request.url.query:
        upstream_url = f"{upstream_url}?{request.url.query}"

    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }
    body = await request.body()
    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=60.0) as client:
            upstream_response = await client.request(
                request.method,
                upstream_url,
                content=body if body else None,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        return JSONResponse(
            status_code=502,
            content={
                "ok": False,
                "error": {
                    "code": "upstream_unreachable",
                    "message": str(exc),
                },
            },
        )

    response_headers = {
        key: value
        for key, value in upstream_response.headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }
    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )
