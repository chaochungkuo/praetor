from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status


def require_bearer_token(authorization: str | None, expected_token: str) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Missing Authorization header."},
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Invalid auth scheme."},
        )
    token = authorization.split(" ", 1)[1]
    if not secrets.compare_digest(token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Invalid token."},
        )


def authorization_header(
    authorization: str | None = Header(default=None),
) -> str | None:
    return authorization
