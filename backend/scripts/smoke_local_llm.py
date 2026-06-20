#!/usr/bin/env python
"""Smoke-test the local LM Studio provider end-to-end (REAL network).

Exercises both AI agents against a running LM Studio server, exactly the way
the app would when ``AI_PROVIDER=lmstudio``:

  1. strategy_agent.design_strategy   (NL -> StrategySpec, nested schema)
  2. signal_agent.generate_ai_signal  (market summary -> buy/sell/hold)

This is intentionally NOT a pytest test: the offline suite mocks the model
boundary, while this hits a real local server. Run it by hand once LM Studio
has the model loaded and its server started.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/smoke_local_llm.py
    python scripts/smoke_local_llm.py --model qwen3-coder-30b-a3b-instruct
    python scripts/smoke_local_llm.py --base-url http://localhost:1234/v1

Fails loud: any unreachable endpoint, unparseable output, or schema-validation
failure raises and exits non-zero — no silent degradation.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

import httpx

from app.config import settings


def _check_server(base_url: str) -> None:
    """Fail loud early if the LM Studio server / model isn't reachable."""
    url = base_url.rstrip("/") + "/models"
    try:
        resp = httpx.get(url, timeout=5.0)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - smoke script: surface the raw cause
        raise SystemExit(
            f"❌ Cannot reach LM Studio at {url}: {exc}\n"
            "   Start LM Studio, load the model, and enable the local server."
        ) from exc
    ids = [m.get("id") for m in resp.json().get("data", [])]
    print(f"✅ Server reachable. Loaded models: {ids or '(none reported)'}")
    if settings.ai_model not in ids:
        print(
            f"⚠️  Configured model '{settings.ai_model}' is not in the loaded list; "
            "the request may fail or LM Studio may route to its default."
        )


def _make_candles(closes: list[float]):
    from app.schemas import Candle

    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [
        Candle(timestamp=base + timedelta(hours=i), open=c, high=c, low=c, close=c, volume=1.0)
        for i, c in enumerate(closes)
    ]


def _test_strategy() -> None:
    from app.ai.strategy_agent import design_strategy

    print("\n── 1/2  strategy_agent.design_strategy ─────────────────────")
    out = design_strategy("Buy when RSI drops below 30, sell when it goes above 70.")
    print("  spec indicators:", [i.kind for i in out["spec"].indicators])
    print("  explanation:", out["explanation"][:200])
    assert "def generate_signal" in out["rendered_python"], "render_python produced no function"
    print("✅ strategy generated + rendered to Python")


def _test_signal() -> None:
    from app.ai.signal_agent import generate_ai_signal

    print("\n── 2/2  signal_agent.generate_ai_signal ────────────────────")
    closes = [100.0 + (i % 5) - 2 for i in range(40)]  # mild oscillation
    signal = generate_ai_signal("BTC/USDT", _make_candles(closes))
    print(f"  action={signal.action}  confidence={signal.confidence:.2f}")
    print("  reason:", signal.reason[:200])
    print("  source:", signal.source)
    print("✅ signal produced")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen3-coder-30b-a3b-instruct",
                        help="LM Studio model id (default: qwen3-coder-30b-a3b-instruct)")
    parser.add_argument("--base-url", default="http://localhost:1234/v1",
                        help="LM Studio OpenAI-compatible base URL")
    parser.add_argument("--api-key", default="lm-studio",
                        help="Placeholder key (LM Studio does not validate it)")
    args = parser.parse_args()

    # Drive the real provider path by overriding the settings singleton at runtime.
    settings.ai_provider = "lmstudio"
    settings.ai_model = args.model
    settings.ai_base_url = args.base_url
    settings.ai_local_api_key = args.api_key

    print(f"Provider=lmstudio  model={args.model}  base_url={args.base_url}")
    _check_server(args.base_url)
    _test_strategy()
    _test_signal()
    print("\n🎉 Both paths OK against local LM Studio.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
