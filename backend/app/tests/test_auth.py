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


def test_empty_token_leaves_api_open(client, monkeypatch):
    """Empty api_token => auth DISABLED so local dev + existing tests work without a token."""
    monkeypatch.setattr(settings, "api_token", "")
    resp = client.get("/api/config")
    assert resp.status_code == 200, resp.text
