from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field

from fastapi import HTTPException, Request, status

from .config import (
    get_bridge_token,
    get_login_max_attempts,
    get_login_window_seconds,
    get_rate_limit_enabled,
    get_session_secret,
    get_setup_token,
    is_production,
)


WEAK_SECRET_VALUES = {
    "",
    "change-me",
    "change-this",
    "change-this-in-real-use",
    "change-this-too",
    "praetor-dev-session-secret",
    "praetor-dev-bridge-token",
}


def validate_runtime_security() -> None:
    if not is_production():
        return
    session_secret = get_session_secret()
    bridge_token = get_bridge_token()
    setup_token = get_setup_token()
    weak = []
    if session_secret in WEAK_SECRET_VALUES or len(session_secret) < 32:
        weak.append("PRAETOR_SESSION_SECRET")
    if bridge_token and (bridge_token in WEAK_SECRET_VALUES or len(bridge_token) < 32):
        weak.append("PRAETOR_BRIDGE_TOKEN")
    if not setup_token or setup_token in WEAK_SECRET_VALUES or len(setup_token) < 24:
        weak.append("PRAETOR_SETUP_TOKEN")
    if weak:
        names = ", ".join(weak)
        raise RuntimeError(f"Refusing production startup with weak security setting(s): {names}.")


def csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def require_csrf(request: Request, token: str | None = None) -> None:
    expected = request.session.get("csrf_token")
    supplied = token or request.headers.get("x-csrf-token")
    if not expected or not supplied or not secrets.compare_digest(str(expected), str(supplied)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "csrf_failed", "message": "Invalid CSRF token."},
        )


def require_setup_token(request: Request, supplied_token: str | None = None) -> None:
    expected = get_setup_token()
    if not expected:
        return
    supplied = supplied_token or request.headers.get("x-praetor-setup-token") or request.query_params.get("setup_token")
    if not supplied or not secrets.compare_digest(expected, supplied):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "setup_token_required", "message": "Valid setup token required."},
        )


@dataclass
class LoginRateLimiter:
    attempts: dict[str, list[float]] = field(default_factory=dict)

    def check(self, key: str) -> None:
        if not get_rate_limit_enabled():
            return
        now = time.monotonic()
        window = get_login_window_seconds()
        max_attempts = get_login_max_attempts()
        recent = [stamp for stamp in self.attempts.get(key, []) if now - stamp < window]
        self.attempts[key] = recent
        if len(recent) >= max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "rate_limited", "message": "Too many login attempts. Try again later."},
            )

    def record_failure(self, key: str) -> None:
        if get_rate_limit_enabled():
            self.attempts.setdefault(key, []).append(time.monotonic())

    def reset(self, key: str) -> None:
        self.attempts.pop(key, None)


login_rate_limiter = LoginRateLimiter()
