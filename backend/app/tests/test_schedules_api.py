"""HTTP test for the schedule endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_schedule_lifecycle(client):
    wf = client.post(
        "/api/workflows",
        json={"name": "sched-api", "graph": {"nodes": [{"id": "l", "type": "logger"}], "edges": []}},
    ).json()

    created = client.post(
        "/api/schedules", json={"workflow_id": wf["id"], "interval_seconds": 3600}
    )
    assert created.status_code == 200, created.text
    sched = created.json()
    assert sched["enabled"] is True

    listed = client.get("/api/schedules").json()
    assert any(s["id"] == sched["id"] for s in listed)

    toggled = client.post(f"/api/schedules/{sched['id']}/toggle").json()
    assert toggled["enabled"] is False

    deleted = client.delete(f"/api/schedules/{sched['id']}")
    assert deleted.status_code == 200


def test_schedule_rejects_unknown_workflow(client):
    resp = client.post("/api/schedules", json={"workflow_id": 999999, "interval_seconds": 3600})
    assert resp.status_code == 404


def test_schedule_rejects_too_short_interval(client):
    wf = client.post(
        "/api/workflows",
        json={"name": "sched-api2", "graph": {"nodes": [{"id": "l", "type": "logger"}], "edges": []}},
    ).json()
    resp = client.post("/api/schedules", json={"workflow_id": wf["id"], "interval_seconds": 1})
    assert resp.status_code == 422
