"""HTTP tests for saved workflow CRUD."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def _graph_with_position() -> dict:
    return {
        "nodes": [
            {
                "id": "l",
                "type": "logger",
                "position": {"x": 120.5, "y": -32.25},
            }
        ],
        "edges": [],
    }


def test_workflow_crud_roundtrip_preserves_position_and_deletes():
    with _client() as client:
        created_resp = client.post(
            "/api/workflows",
            json={"name": "crud-position", "graph": _graph_with_position()},
        )
        assert created_resp.status_code == 200, created_resp.text
        created = created_resp.json()
        workflow_id = created["id"]
        assert created["graph"]["nodes"][0]["position"] == {"x": 120.5, "y": -32.25}

        fetched = client.get(f"/api/workflows/{workflow_id}")
        assert fetched.status_code == 200, fetched.text
        assert fetched.json()["graph"]["nodes"][0]["position"] == {"x": 120.5, "y": -32.25}

        updated_graph = {
            "nodes": [
                {
                    "id": "l",
                    "type": "logger",
                    "position": {"x": 8.0, "y": 13.0},
                }
            ],
            "edges": [],
        }
        updated_resp = client.put(
            f"/api/workflows/{workflow_id}",
            json={"name": "crud-position-updated", "graph": updated_graph},
        )
        assert updated_resp.status_code == 200, updated_resp.text
        updated = updated_resp.json()
        assert updated["name"] == "crud-position-updated"
        assert updated["graph"]["nodes"][0]["position"] == {"x": 8.0, "y": 13.0}
        assert updated["updated_at"] != created["updated_at"]

        run_resp = client.post(f"/api/workflows/{workflow_id}/run")
        assert run_resp.status_code == 200, run_resp.text
        assert run_resp.json()["status"] == "ok"

        deleted = client.delete(f"/api/workflows/{workflow_id}")
        assert deleted.status_code == 204, deleted.text
        assert client.get(f"/api/workflows/{workflow_id}").status_code == 404


def test_workflow_delete_missing_returns_404():
    with _client() as client:
        resp = client.delete("/api/workflows/999999")
    assert resp.status_code == 404


def test_workflow_delete_rejects_scheduled_workflow():
    with _client() as client:
        wf = client.post(
            "/api/workflows",
            json={
                "name": "scheduled-workflow",
                "graph": {"nodes": [{"id": "l", "type": "logger"}], "edges": []},
            },
        ).json()
        schedule_resp = client.post(
            "/api/schedules",
            json={"workflow_id": wf["id"], "interval_seconds": 3600, "enabled": False},
        )
        assert schedule_resp.status_code == 200, schedule_resp.text

        delete_resp = client.delete(f"/api/workflows/{wf['id']}")
        assert delete_resp.status_code == 409
        assert "schedule" in delete_resp.json()["detail"]

        assert client.get(f"/api/workflows/{wf['id']}").status_code == 200

