"""Tests for the AI signal agent with a mocked Claude client (no network/key needed)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.ai import signal_agent
from app.ai.signal_agent import AISignalResponse, generate_ai_signal
from app.schemas import SignalAction
from app.tests.helpers import make_candles


class FakeMessages:
    def __init__(self, parsed: AISignalResponse):
        self._parsed = parsed
        self.last_kwargs: dict | None = None

    def parse(self, **kwargs):
        self.last_kwargs = kwargs
        return SimpleNamespace(parsed_output=self._parsed)


class FakeClient:
    def __init__(self, parsed: AISignalResponse):
        self.messages = FakeMessages(parsed)


def test_maps_model_output_to_signal(monkeypatch):
    parsed = AISignalResponse(action=SignalAction.buy, confidence=0.8, rationale="uptrend + low RSI")
    fake = FakeClient(parsed)
    monkeypatch.setattr(signal_agent, "get_claude_client", lambda: fake)

    signal = generate_ai_signal("BTC/USDT", make_candles([float(i) for i in range(1, 40)]))

    assert signal.action == SignalAction.buy
    assert signal.confidence == pytest.approx(0.8)
    assert signal.reason == "uptrend + low RSI"
    assert signal.source.startswith("ai:")
    # the model received a compact summary string, not raw candle objects
    assert "Recent closes" in fake.messages.last_kwargs["messages"][0]["content"]


def test_confidence_is_clamped(monkeypatch):
    parsed = AISignalResponse(action=SignalAction.hold, confidence=1.0, rationale="ambiguous")
    monkeypatch.setattr(signal_agent, "get_claude_client", lambda: FakeClient(parsed))
    signal = generate_ai_signal("BTC/USDT", make_candles([100.0] * 30))
    assert 0.0 <= signal.confidence <= 1.0


def test_empty_candles_fails_loud():
    with pytest.raises(ValueError):
        generate_ai_signal("BTC/USDT", [])
