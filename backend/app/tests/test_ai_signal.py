"""Tests for the AI signal agent with a mocked structured-completion boundary."""
from __future__ import annotations

import pytest

from app.ai import signal_agent
from app.ai.signal_agent import AISignalResponse, generate_ai_signal
from app.schemas import SignalAction
from app.tests.helpers import make_candles


def _patch(monkeypatch, parsed, captured=None):
    def fake(**kwargs):
        if captured is not None:
            captured.update(kwargs)
        return parsed
    monkeypatch.setattr(signal_agent, "structured_completion", fake)


def test_maps_model_output_to_signal(monkeypatch):
    parsed = AISignalResponse(action=SignalAction.buy, confidence=0.8, rationale="uptrend + low RSI")
    captured = {}
    _patch(monkeypatch, parsed, captured)

    signal = generate_ai_signal("BTC/USDT", make_candles([float(i) for i in range(1, 40)]))

    assert signal.action == SignalAction.buy
    assert signal.confidence == pytest.approx(0.8)
    assert signal.reason == "uptrend + low RSI"
    assert signal.source.startswith("ai:")
    # the model received a compact summary string, not raw candle objects
    assert "Recent closes" in captured["content"]
    assert captured["output_model"] is AISignalResponse


def test_confidence_is_clamped(monkeypatch):
    parsed = AISignalResponse(action=SignalAction.hold, confidence=1.0, rationale="ambiguous")
    _patch(monkeypatch, parsed)
    signal = generate_ai_signal("BTC/USDT", make_candles([100.0] * 30))
    assert 0.0 <= signal.confidence <= 1.0


def test_empty_candles_fails_loud():
    with pytest.raises(ValueError):
        generate_ai_signal("BTC/USDT", [])
