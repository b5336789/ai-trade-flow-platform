"""HTTP-level tests for risk operator controls."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db import engine
from app.main import app
from app.models import Notification
from app.trading import runtime_state


@pytest.fixture(autouse=True)
def _reset_runtime_flags():
    with Session(engine) as session:
        runtime_state.set_kill_switch(session, False)
        runtime_state.set_halted(session, False)
    yield
    with Session(engine) as session:
        runtime_state.set_kill_switch(session, False)
        runtime_state.set_halted(session, False)


def test_kill_switch_accepts_json_body_and_notifies():
    with TestClient(app) as client:
        resp = client.post("/api/risk/kill-switch", json={"engaged": True})

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"kill_switch": True}

    with Session(engine) as session:
        assert runtime_state.get_kill_switch(session) is True
        notification = session.exec(
            select(Notification).order_by(Notification.id.desc())
        ).first()

    assert notification is not None
    assert notification.level == "warning"
    assert "Kill switch engaged" in notification.title


def test_resume_clears_halt_and_notifies():
    with Session(engine) as session:
        runtime_state.set_halted(session, True)

    with TestClient(app) as client:
        resp = client.post("/api/risk/resume")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"halted": False}

    with Session(engine) as session:
        assert runtime_state.get_halted(session) is False
        notification = session.exec(
            select(Notification).order_by(Notification.id.desc())
        ).first()

    assert notification is not None
    assert notification.level == "info"
    assert "Trading resumed" in notification.title
