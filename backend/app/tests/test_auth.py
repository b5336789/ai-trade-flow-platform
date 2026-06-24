"""HTTP-level tests for M0.7 bearer-token auth on /api routes.

``require_api_token`` reads ``settings.api_token`` at request time, so each test sets the token
via monkeypatch — no app rebuild needed. ``/api/config`` is used as a representative protected
endpoint because it has no external dependencies.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_health_open_without_token(client, monkeypatch):
    """GET /health is public even when a token is configured."""
    monkeypatch.setattr(settings, "api_token", "secret-token")
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_api_requires_token_when_set(client, monkeypatch):
    monkeypatch.setattr(settings, "api_token", "secret-token")
    resp = client.get("/api/config")
    assert resp.status_code == 401


def test_api_accepts_correct_token(client, monkeypatch):
    monkeypatch.setattr(settings, "api_token", "secret-token")
    resp = client.get("/api/config", headers={"Authorization": "Bearer secret-token"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["trading_mode"]


def test_api_rejects_wrong_token(client, monkeypatch):
    monkeypatch.setattr(settings, "api_token", "secret-token")
    resp = client.get("/api/config", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


def test_api_rejects_non_bearer_scheme(client, monkeypatch):
    monkeypatch.setattr(settings, "api_token", "secret-token")
    resp = client.get("/api/config", headers={"Authorization": "Basic secret-token"})
    assert resp.status_code == 401


def test_non_ascii_token_rejected_not_crash(monkeypatch):
    """A non-ASCII bearer token must raise 401, not crash.

    The constant-time check compares UTF-8 bytes; a str-level ``hmac.compare_digest`` would raise
    TypeError on non-ASCII input. Asserted at the dependency level because the HTTP transport
    rejects non-ASCII header bytes before they ever reach the app.
    """
    from fastapi import HTTPException

    from app.api.deps import require_api_token

    monkeypatch.setattr(settings, "api_token", "secret-token")
    with pytest.raises(HTTPException) as exc:
        require_api_token(authorization="Bearer ☃-not-the-token")
    assert exc.value.status_code == 401


def test_empty_token_leaves_api_open(client, monkeypatch):
    """Empty api_token => auth DISABLED so local dev + existing tests work without a token."""
    monkeypatch.setattr(settings, "api_token", "")
    resp = client.get("/api/config")
    assert resp.status_code == 200, resp.text
