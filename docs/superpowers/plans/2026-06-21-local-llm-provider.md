# Local LLM Provider (LM Studio) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `strategy_agent` and `signal_agent` run against a local LM Studio model (OpenAI-compatible) as an alternative to Claude, selectable by config, without touching agent business logic.

**Architecture:** Add a provider-agnostic `ai/structured.py` with a single `structured_completion()` entry point that dispatches on `settings.ai_provider`: the `anthropic` branch keeps the native Anthropic SDK (`messages.parse` + `thinking=adaptive`); the `lmstudio` branch uses Instructor over the OpenAI SDK pointed at LM Studio. Both agents call this one function. Fail loud everywhere.

**Tech Stack:** Python 3.11+, FastAPI, pydantic-settings, anthropic SDK, openai SDK, instructor, pytest.

## Global Constraints

- Fail loud everywhere: missing key, unreachable endpoint, unparseable/validation-exhausted output must raise — never silently degrade or fall back to another provider (CLAUDE.md; mirrors `claude_client.py`).
- Surgical changes only: do not alter agent business logic (market summary, prior_spec splicing, `render_python`, `Signal` wrapping, confidence clamp).
- Settings come from env, UPPER_CASE mapping (`config.py`); add new vars to `.env.example`.
- Tests are business-logic, no real network/model calls (mock the boundary). Run with `cd backend && pytest`.
- Git flow: work on branch `feature/local-llm-provider`; never commit to `main`. End commit messages with the Co-Authored-By trailer.
- Indicators/`ta` etc. unaffected.

---

### Task 1: Config settings + dependencies

**Files:**
- Modify: `backend/app/config.py:23-25` (Anthropic / Claude block)
- Modify: `backend/pyproject.toml:6-19` (dependencies)
- Modify: `.env.example` (repo root)
- Modify: `docs/configuration.md`
- Test: `backend/app/tests/test_config_provider.py` (create)

**Interfaces:**
- Produces: `settings.ai_provider: str` (`"anthropic"` default), `settings.ai_base_url: str` (default `"http://localhost:1234/v1"`), `settings.ai_local_api_key: str` (default `"lm-studio"`). Existing `settings.ai_model` unchanged.

- [ ] **Step 1: Write the failing test**

Create `backend/app/tests/test_config_provider.py`:

```python
"""Defaults for the AI provider settings."""
from __future__ import annotations

from app.config import Settings


def test_provider_defaults():
    s = Settings()
    assert s.ai_provider == "anthropic"
    assert s.ai_base_url == "http://localhost:1234/v1"
    assert s.ai_local_api_key == "lm-studio"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_config_provider.py -v`
Expected: FAIL (AttributeError — `ai_provider` not defined)

- [ ] **Step 3: Add the settings**

In `backend/app/config.py`, replace the Anthropic block (lines 23-25):

```python
    # Anthropic / Claude
    anthropic_api_key: str = ""
    ai_model: str = "claude-opus-4-8"
```

with:

```python
    # AI provider selection: "anthropic" (Claude, native SDK) or "lmstudio" (local, OpenAI-compatible)
    ai_provider: str = "anthropic"

    # Anthropic / Claude
    anthropic_api_key: str = ""
    ai_model: str = "claude-opus-4-8"

    # Local LLM (LM Studio, OpenAI-compatible). api_key is required-non-empty by the OpenAI SDK but unused by LM Studio.
    ai_base_url: str = "http://localhost:1234/v1"
    ai_local_api_key: str = "lm-studio"
```

- [ ] **Step 4: Add dependencies**

In `backend/pyproject.toml`, inside `dependencies = [ ... ]` add after the `"anthropic>=0.40",` line:

```toml
    "openai>=1.0",
    "instructor>=1.0",
```

- [ ] **Step 5: Install the new deps**

Run: `cd backend && pip install -e ".[dev]"`
Expected: installs `openai` and `instructor` without error.

- [ ] **Step 6: Document the new env vars**

In `.env.example`, near the `ANTHROPIC_API_KEY` / `AI_MODEL` lines, add:

```bash
# AI provider: "anthropic" (Claude) or "lmstudio" (local, OpenAI-compatible)
AI_PROVIDER=anthropic
# Local LLM endpoint + key (only used when AI_PROVIDER=lmstudio). For LM Studio the key is a non-empty placeholder.
AI_BASE_URL=http://localhost:1234/v1
AI_LOCAL_API_KEY=lm-studio
```

In `docs/configuration.md`, add a short row/paragraph (match the file's existing format) documenting `AI_PROVIDER`, `AI_BASE_URL`, `AI_LOCAL_API_KEY`: when `AI_PROVIDER=lmstudio`, AI nodes call the local OpenAI-compatible endpoint instead of Claude; `AI_MODEL` then holds the local model name (e.g. `qwen3-coder-30b-a3b-instruct`).

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_config_provider.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/config.py backend/pyproject.toml .env.example docs/configuration.md backend/app/tests/test_config_provider.py
git commit -m "feat(ai): add ai_provider/local-LLM settings + openai+instructor deps

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: `ai/structured.py` provider-agnostic entry point

**Files:**
- Create: `backend/app/ai/structured.py`
- Test: `backend/app/tests/test_structured.py` (create)

**Interfaces:**
- Consumes: `settings.ai_provider`, `settings.ai_model`, `settings.ai_base_url`, `settings.ai_local_api_key` (Task 1); `app.ai.claude_client.get_claude_client`.
- Produces: `structured_completion(*, system: str, content: str, output_model: type[T], model: str | None = None, max_tokens: int = 2048) -> T` where `T` is a `pydantic.BaseModel` subclass. Returns a validated instance of `output_model`. Raises `RuntimeError` on unparseable anthropic output or unknown provider.

- [ ] **Step 1: Write the failing test**

Create `backend/app/tests/test_structured.py`:

```python
"""Provider dispatch + fail-loud for structured_completion (no network)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.ai import structured
from app.ai.structured import structured_completion


class Out(BaseModel):
    value: str


def test_anthropic_branch_returns_parsed(monkeypatch):
    monkeypatch.setattr(structured.settings, "ai_provider", "anthropic")
    captured = {}

    class FakeMessages:
        def parse(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(parsed_output=Out(value="ok"))

    monkeypatch.setattr(structured, "get_claude_client",
                        lambda: SimpleNamespace(messages=FakeMessages()))

    out = structured_completion(system="S", content="C", output_model=Out)
    assert out == Out(value="ok")
    assert captured["thinking"] == {"type": "adaptive"}
    assert captured["output_format"] is Out


def test_anthropic_none_fails_loud(monkeypatch):
    monkeypatch.setattr(structured.settings, "ai_provider", "anthropic")

    class FakeMessages:
        def parse(self, **kwargs):
            return SimpleNamespace(parsed_output=None)

    monkeypatch.setattr(structured, "get_claude_client",
                        lambda: SimpleNamespace(messages=FakeMessages()))

    with pytest.raises(RuntimeError):
        structured_completion(system="S", content="C", output_model=Out)


def test_lmstudio_branch_uses_instructor(monkeypatch):
    monkeypatch.setattr(structured.settings, "ai_provider", "lmstudio")
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return Out(value="local")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    monkeypatch.setattr(structured, "_get_lmstudio_client", lambda: fake_client)

    out = structured_completion(system="S", content="C", output_model=Out)
    assert out == Out(value="local")
    assert captured["response_model"] is Out
    # system prompt is delivered as the first message for the OpenAI-style API
    assert captured["messages"][0] == {"role": "system", "content": "S"}
    assert captured["messages"][1] == {"role": "user", "content": "C"}


def test_unknown_provider_fails_loud(monkeypatch):
    monkeypatch.setattr(structured.settings, "ai_provider", "bogus")
    with pytest.raises(RuntimeError):
        structured_completion(system="S", content="C", output_model=Out)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_structured.py -v`
Expected: FAIL (ModuleNotFoundError: `app.ai.structured`)

- [ ] **Step 3: Write the implementation**

Create `backend/app/ai/structured.py`:

```python
"""Provider-agnostic structured completion.

Routes a (system, content, output_model) request to either Claude (native
Anthropic SDK, preserving adaptive thinking + messages.parse) or a local
LM Studio model (OpenAI-compatible endpoint via Instructor), selected by
``settings.ai_provider``. Fail loud: a missing key, unreachable endpoint,
unparseable output, or unknown provider raises — never silently degrade.
"""
from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.ai.claude_client import get_claude_client
from app.config import settings

T = TypeVar("T", bound=BaseModel)

_lmstudio_client = None


def _get_lmstudio_client():
    """Lazily build + cache the Instructor-wrapped OpenAI client (mirrors claude_client)."""
    global _lmstudio_client
    if _lmstudio_client is None:
        import instructor
        from openai import OpenAI

        _lmstudio_client = instructor.from_openai(
            OpenAI(base_url=settings.ai_base_url, api_key=settings.ai_local_api_key)
        )
    return _lmstudio_client


def structured_completion(
    *,
    system: str,
    content: str,
    output_model: type[T],
    model: str | None = None,
    max_tokens: int = 2048,
) -> T:
    model = model or settings.ai_model
    provider = settings.ai_provider

    if provider == "anthropic":
        client = get_claude_client()
        response = client.messages.parse(
            model=model,
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": content}],
            output_format=output_model,
        )
        out = response.parsed_output
        if out is None:
            raise RuntimeError("AI response could not be parsed from the model")
        return out

    if provider == "lmstudio":
        client = _get_lmstudio_client()
        return client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            response_model=output_model,
        )

    raise RuntimeError(f"Unknown ai_provider: {provider!r}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_structured.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/ai/structured.py backend/app/tests/test_structured.py
git commit -m "feat(ai): provider-agnostic structured_completion (anthropic | lmstudio)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Route `strategy_agent` through `structured_completion`

**Files:**
- Modify: `backend/app/ai/strategy_agent.py:29-54`
- Test: `backend/app/tests/test_strategy_agent.py` (rewrite mocks)

**Interfaces:**
- Consumes: `structured_completion` (Task 2).
- Produces: `design_strategy(message, prior_spec=None, model=None) -> dict` — unchanged signature and return shape (`spec`, `rendered_python`, `explanation`).

- [ ] **Step 1: Update the test to mock the new boundary**

Replace the body of `backend/app/tests/test_strategy_agent.py` (keep `_SPEC_DICT` and imports of `StrategyDesignResponse`, `design_strategy`, `StrategySpec`) with mocks on `structured_completion`:

```python
# backend/app/tests/test_strategy_agent.py
"""AI strategy agent with a mocked structured-completion boundary (no key/network)."""
from __future__ import annotations

import pytest

from app.ai import strategy_agent
from app.ai.strategy_agent import StrategyDesignResponse, design_strategy
from app.strategies.spec import StrategySpec

_SPEC_DICT = {
    "indicators": [{"id": "r", "kind": "rsi", "args": {"window": {"type": "param", "ref": "win"}}}],
    "entry": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
              "op": "lt", "right": {"type": "param", "ref": "th"}},
    "exit": {"kind": "cmp", "left": {"type": "indicator", "ref": "r"},
             "op": "gt", "right": {"type": "literal", "value": 70}},
    "params": [{"name": "win", "type": "int", "default": 14},
               {"name": "th", "type": "float", "default": 28}],
}


def _patch(monkeypatch, parsed, captured=None):
    def fake(**kwargs):
        if captured is not None:
            captured.update(kwargs)
        return parsed
    monkeypatch.setattr(strategy_agent, "structured_completion", fake)


def test_design_returns_spec_python_and_explanation(monkeypatch):
    parsed = StrategyDesignResponse(spec=StrategySpec.model_validate(_SPEC_DICT), explanation="RSI reversion")
    _patch(monkeypatch, parsed)
    out = design_strategy("make an RSI strategy")
    assert isinstance(out["spec"], StrategySpec)
    assert out["explanation"] == "RSI reversion"
    assert "def generate_signal" in out["rendered_python"]


def test_prior_spec_is_sent_to_model(monkeypatch):
    parsed = StrategyDesignResponse(spec=StrategySpec.model_validate(_SPEC_DICT), explanation="updated")
    captured = {}
    _patch(monkeypatch, parsed, captured)
    prior = StrategySpec.model_validate(_SPEC_DICT)
    design_strategy("change threshold to 28", prior_spec=prior)
    assert "change threshold" in captured["content"]
    assert captured["output_model"] is StrategyDesignResponse
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_strategy_agent.py -v`
Expected: FAIL (`strategy_agent` has no attribute `structured_completion`)

- [ ] **Step 3: Update the agent**

In `backend/app/ai/strategy_agent.py`, change the import (line 11):

```python
from app.ai.structured import structured_completion
```

(remove the `from app.ai.claude_client import get_claude_client` import) and replace the body of `design_strategy` (lines 29-54) with:

```python
def design_strategy(message: str, prior_spec: StrategySpec | None = None,
                    model: str | None = None) -> dict:
    content = message
    if prior_spec is not None:
        content = (
            f"Current strategy spec (JSON):\n{prior_spec.model_dump_json()}\n\n"
            f"Requested change: {message}"
        )
    out = structured_completion(
        system=_SYSTEM_PROMPT,
        content=content,
        output_model=StrategyDesignResponse,
        model=model,
        max_tokens=2048,
    )
    return {
        "spec": out.spec,
        "rendered_python": render_python(out.spec),
        "explanation": out.explanation,
    }
```

(The `settings` import is now unused in this file — remove `from app.config import settings`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_strategy_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/ai/strategy_agent.py backend/app/tests/test_strategy_agent.py
git commit -m "refactor(ai): route strategy_agent through structured_completion

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Route `signal_agent` through `structured_completion`

**Files:**
- Modify: `backend/app/ai/signal_agent.py:47-79`
- Test: `backend/app/tests/test_ai_signal.py` (rewrite mocks)

**Interfaces:**
- Consumes: `structured_completion` (Task 2).
- Produces: `generate_ai_signal(symbol, candles, model=None, extra_context="") -> Signal` — unchanged signature, `source=f"ai:{model}"`, confidence clamped to [0,1].

- [ ] **Step 1: Update the test to mock the new boundary**

Replace `backend/app/tests/test_ai_signal.py` with:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_ai_signal.py -v`
Expected: FAIL (`signal_agent` has no attribute `structured_completion`)

- [ ] **Step 3: Update the agent**

In `backend/app/ai/signal_agent.py`, change the import (line 12) from `from app.ai.claude_client import get_claude_client` to:

```python
from app.ai.structured import structured_completion
```

Replace the body of `generate_ai_signal` (lines 47-79) with:

```python
def generate_ai_signal(
    symbol: str,
    candles: list[Candle],
    model: str | None = None,
    extra_context: str = "",
) -> Signal:
    if not candles:
        raise ValueError("generate_ai_signal requires candle data")

    model = model or settings.ai_model
    summary = _market_summary(symbol, candles)
    if extra_context:
        summary += f"\nAdditional context: {extra_context}"

    out = structured_completion(
        system=_SYSTEM_PROMPT,
        content=summary,
        output_model=AISignalResponse,
        model=model,
        max_tokens=1024,
    )

    return Signal(
        action=out.action,
        confidence=max(0.0, min(1.0, out.confidence)),
        reason=out.rationale,
        source=f"ai:{model}",
    )
```

(Keep `from app.config import settings` — still used for `model` resolution / the `source` label.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_ai_signal.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite (regression check)**

Run: `cd backend && pytest`
Expected: all tests pass (no regressions in workflow/spec-strategy tests that exercise these agents).

- [ ] **Step 6: Commit**

```bash
git add backend/app/ai/signal_agent.py backend/app/tests/test_ai_signal.py
git commit -m "refactor(ai): route signal_agent through structured_completion

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage:**
- Config (`ai_provider`/`ai_base_url`/`ai_local_api_key`) → Task 1. ✓
- `ai/structured.py` single entry, anthropic + lmstudio dispatch → Task 2. ✓
- Agents swapped, business logic untouched → Tasks 3, 4. ✓
- Dependencies (`openai`, `instructor`) → Task 1. ✓
- Fail-loud (None parse, unknown provider, propagation) → Task 2 tests; ValueError on empty candles preserved → Task 4. ✓
- Testing strategy (mock boundary, no network) → all tasks. ✓
- `.env.example` + docs → Task 1. ✓

**Placeholder scan:** none — all steps contain concrete code/commands.

**Type consistency:** `structured_completion(*, system, content, output_model, model=None, max_tokens=2048)` is defined in Task 2 and called with exactly these kwargs in Tasks 3 (`max_tokens=2048`) and 4 (`max_tokens=1024`). Test mocks accept `**kwargs` and assert `output_model`/`content`/`messages`, matching the signature. `parsed_output` (anthropic) vs `response_model` return (lmstudio) both yield an `output_model` instance.

**Note on removed coverage:** the old `test_unparseable_output_fails_loud` (agent-level None check) is replaced by `test_anthropic_none_fails_loud` in Task 2, since the None check moved into `structured_completion`.
