from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.ai import strategy_agent
from app.ai.strategy_agent import StrategyDesignResponse
from app.brokers.base import Broker
from app.main import app
from app.schemas import Balance, Candle, MarketKind, Position, Ticker, TradingMode
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


class _RangeStubBroker(Broker):
    """Stub with get_ohlcv_range for date-windowed strategy backtest tests."""

    market = MarketKind.crypto
    mode = TradingMode.live

    def __init__(self, closes: list[float]) -> None:
        base = datetime(2024, 1, 1, tzinfo=timezone.utc)
        self._series = [
            Candle(timestamp=base + timedelta(days=i), open=c, high=c, low=c, close=c, volume=1.0)
            for i, c in enumerate(closes)
        ]

    @property
    def name(self) -> str:
        return "range-stub-strategies"

    def get_ticker(self, symbol: str) -> Ticker:
        return Ticker(symbol=symbol, price=self._series[-1].close, timestamp=self._series[-1].timestamp)

    def get_ohlcv(self, symbol, timeframe="1h", limit=100):
        return self._series[-limit:]

    def get_ohlcv_range(self, symbol, timeframe, start, end):
        if start > end:
            raise ValueError("start must be before end")
        return [c for c in self._series if start <= c.timestamp <= end]

    def create_order(self, request):  # pragma: no cover
        raise NotImplementedError

    def get_balance(self) -> list[Balance]:
        return []

    def get_positions(self) -> list[Position]:
        return []


def _stub_strategies_range_broker(monkeypatch, closes):
    monkeypatch.setattr("app.api.strategies.get_data_broker", lambda market: _RangeStubBroker(closes))


def test_strategy_backtest_reversed_range_is_422(monkeypatch):
    """start after end on /{sid}/backtest must return 422 (proves date range is wired through)."""
    _stub_strategies_range_broker(monkeypatch, [100.0] * 60)
    # create a saved strategy first
    created = client.post("/api/strategies", json={"name": "rsi-range-test", "spec": _SPEC})
    assert created.status_code == 200
    sid = created.json()["id"]
    resp = client.post(
        f"/api/strategies/{sid}/backtest",
        json={
            "symbol": "BTC/USDT",
            "start": "2024-02-01T00:00:00Z",
            "end": "2024-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 422, resp.text


def test_design_maps_agent_output(monkeypatch):
    parsed = StrategyDesignResponse(spec=StrategySpec.model_validate(_SPEC), explanation="ok")
    monkeypatch.setattr(strategy_agent, "structured_completion", lambda **k: parsed)
    r = client.post("/api/strategies/design", json={"message": "rsi please"})
    assert r.status_code == 200
    assert r.json()["explanation"] == "ok"
    assert "rendered_python" in r.json()
    assert r.json()["spec"]["indicators"][0]["kind"] == "rsi"
