"""Shared FastAPI dependencies (M0.7 — API bearer-token auth).

Auth model: clients send ``Authorization: Bearer <token>`` where ``<token>`` must equal
``settings.api_token``. Missing or mismatched tokens raise HTTP 401.

Empty-token behaviour (deliberate, documented): if ``settings.api_token`` is the empty string,
auth is DISABLED (every request is allowed) so local development and the existing test suite work
without configuration. This is a SAFE-for-dev / UNSAFE-for-prod default, so we log a loud warning
on every unauthenticated request. Real deployments MUST set ``API_TOKEN``.
"""

from __future__ import annotations

import logging

from fastapi import Header, HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Missing or invalid bearer token",
    headers={"WWW-Authenticate": "Bearer"},
)


def require_api_token(authorization: str | None = Header(default=None)) -> None:
    """Require a valid ``Authorization: Bearer <api_token>`` header on protected routes.

    Raises 401 on a missing/malformed/incorrect token when ``settings.api_token`` is set.
    When ``settings.api_token`` is empty, auth is disabled (open) but a loud warning is logged.
    """
    if not settings.api_token:
        logger.warning(
            "API_TOKEN is not set — auth is DISABLED and all /api endpoints are OPEN. "
            "Set API_TOKEN before any real/networked deployment."
        )
        return

    if not authorization:
        raise _UNAUTHORIZED

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != settings.api_token:
        raise _UNAUTHORIZED
