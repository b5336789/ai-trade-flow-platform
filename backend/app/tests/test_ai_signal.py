"""Tests for the AI signal agent with a mocked structured-completion boundary."""
from __future__ import annotations

import pytest

from app.ai import signal_agent
from app.ai.signal_agent import AISignalResponse, generate_ai_signal
from app.ai.structured import CompletionMeta
from app.schemas import SignalAction
from app.tests.helpers import make_candles


def _patch(monkeypatch, parsed, captured=None):
    from app.ai import signal_cache

    def fake(**kwargs):
        if captured is not None:
            captured.update(kwargs)
        return parsed, CompletionMeta(model="m")

    monkeypatch.setattr(signal_agent, "structured_completion_with_meta", fake)
    # Bypass DB cache so these unit tests don't pollute state for the determinism test.
    monkeypatch.setattr(signal_cache, "lookup", lambda key: None)
    monkeypatch.setattr(signal_cache, "store", lambda key, model, response, meta: None)


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


def test_ai_signal_is_cached_and_deterministic(monkeypatch):
    from app.ai import signal_agent
    from app.ai.signal_agent import AISignalResponse, generate_ai_signal
    from app.ai.structured import CompletionMeta

    calls = {"n": 0}

    def fake(**kwargs):
        calls["n"] += 1
        return AISignalResponse(action="buy", confidence=0.6, rationale="x"), CompletionMeta(model="m")

    monkeypatch.setattr(signal_agent, "structured_completion_with_meta", fake)
    candles = make_candles([float(i) for i in range(1, 40)])
    first = generate_ai_signal("BTC/USDT", candles)
    second = generate_ai_signal("BTC/USDT", candles)
    assert calls["n"] == 1  # second call served from cache
    assert first.action == second.action == "buy"
    assert first.confidence == second.confidence
