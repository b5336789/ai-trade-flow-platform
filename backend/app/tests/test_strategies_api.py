from __future__ import annotations

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.ai import strategy_agent
from app.ai.strategy_agent import StrategyDesignResponse
from app.main import app
from app.strategies.spec import StrategySpec

client = TestClient(app)

_SPEC = {
    "indicators": [{"id": "r", "kind": "rsi", "args": {"window": 14}}],
    "entry": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
              "op": "le", "right": {"type": "literal", "value": 30}},
    "exit": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
             "op": "ge", "right": {"type": "literal", "value": 70}},
    "params": [],
}


def test_crud_and_validation():
    created = client.post("/api/strategies", json={"name": "rsi-lib", "spec": _SPEC})
    assert created.status_code == 200
    sid = created.json()["id"]
    assert any(s["id"] == sid for s in client.get("/api/strategies").json())
    assert client.get(f"/api/strategies/{sid}").json()["rendered_python"].startswith("def generate_signal")
    assert client.delete(f"/api/strategies/{sid}").status_code == 200
    assert client.get(f"/api/strategies/{sid}").status_code == 404
    # invalid spec rejected
    bad = {"name": "x", "spec": {**_SPEC, "indicators": [{"id": "r", "kind": "nope", "args": {}}]}}
    assert client.post("/api/strategies", json=bad).status_code == 422


def test_design_maps_agent_output(monkeypatch):
    parsed = StrategyDesignResponse(spec=StrategySpec.model_validate(_SPEC), explanation="ok")
    fake = SimpleNamespace(messages=SimpleNamespace(parse=lambda **k: SimpleNamespace(parsed_output=parsed)))
    monkeypatch.setattr(strategy_agent, "get_claude_client", lambda: fake)
    r = client.post("/api/strategies/design", json={"message": "rsi please"})
    assert r.status_code == 200
    assert r.json()["explanation"] == "ok"
    assert "rendered_python" in r.json()
    assert r.json()["spec"]["indicators"][0]["kind"] == "rsi"
