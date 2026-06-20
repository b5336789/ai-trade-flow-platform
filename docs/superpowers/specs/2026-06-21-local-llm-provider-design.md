# Local LLM Provider (LM Studio) — Design

Date: 2026-06-21
Branch: `feature/local-llm-provider`

## Goal

Let the two AI agents (`strategy_agent`, `signal_agent`) run against a **local
LM Studio model** (e.g. `qwen3-coder-30b-a3b-instruct`) as an alternative to
Claude, selectable by config. Claude keeps its **native Anthropic SDK** path
(preserving `thinking=adaptive` and `messages.parse` strong-typed parsing); the
local path uses the OpenAI-compatible endpoint that LM Studio exposes.

Non-goals: multi-provider gateway, routing per-request from the API, changing
agent business logic, touching the workflow engine.

## Why this shape

With Claude staying native, the "other" path is a single OpenAI-compatible
endpoint, so a multi-provider library (LiteLLM) earns little. The real risk is a
small model emitting a **nested schema** (`StrategySpec` condition trees), so we
optimize for robust structured output. **Instructor** (over the OpenAI SDK)
gives Pydantic-native structured output with json_schema enforcement and
**automatic retry on validation failure** — which matches the project's
fail-loud philosophy.

## Architecture

### 1. Config (`config.py`)
New settings (env-mapped, UPPER_CASE):
- `ai_provider: str = "anthropic"` — `"anthropic"` | `"lmstudio"`
- `ai_base_url: str = "http://localhost:1234/v1"` — LM Studio OpenAI endpoint
- `ai_local_api_key: str = "lm-studio"` — OpenAI SDK requires a non-empty key; value is irrelevant for LM Studio

`ai_model` stays; its meaning depends on provider (Claude id vs local model name).

### 2. New module `ai/structured.py` — single entry point
One function, e.g.:

```python
def structured_completion(*, system: str, content: str,
                          output_model: type[BaseModelT],
                          model: str | None = None) -> BaseModelT: ...
```

Dispatches on `settings.ai_provider`:
- **anthropic** → existing `get_claude_client().messages.parse(output_format=..., thinking={"type":"adaptive"})`, returns `response.parsed_output`.
- **lmstudio** → Instructor-wrapped OpenAI client (`base_url`, `api_key` from config), `response_model=output_model`. Lazily constructed + cached, mirroring `claude_client.py`.

Returns the validated Pydantic instance. Fail loud: unreachable endpoint or
retry-exhausted validation raises `RuntimeError`/the underlying error (no silent
degrade). `None` parse result raises, same as today.

### 3. Agents
- `strategy_agent.design_strategy` — replace the inline `client.messages.parse(... output_format=StrategyDesignResponse ...)` with `structured_completion(system=_SYSTEM_PROMPT, content=content, output_model=StrategyDesignResponse)`. `prior_spec` splicing, `render_python`, return dict unchanged.
- `signal_agent.generate_ai_signal` — same swap with `AISignalResponse`. `_market_summary`, `Signal` wrapping, `source=f"ai:{model}"`, confidence clamp unchanged.

`claude_client.py` stays (used by the anthropic branch of `structured.py`).

### 4. Dependencies (`backend/pyproject.toml`)
Add to main deps: `openai>=1.0`, `instructor>=1.0`.

## Error handling
Fail-loud everywhere (mirrors `claude_client.py` and `workflow/engine.py`):
- anthropic key missing → existing RuntimeError (anthropic branch).
- lmstudio endpoint unreachable / validation retries exhausted → raise; never
  fall back to the other provider silently.
- Unknown `ai_provider` value → raise at dispatch.

## Testing
Business-logic tests, no real model calls:
- Monkeypatch `structured_completion` to assert each agent passes the right
  system/content/output_model and wraps the result correctly (Signal fields,
  rendered_python present).
- Provider dispatch: with `ai_provider="lmstudio"`, assert the OpenAI/Instructor
  branch is taken (mock the instructor client) and not the anthropic one; and
  vice versa.
- Fail-loud: parse/validation failure surfaces as an error, not a None signal.

## Out of scope / YAGNI
- No per-request provider override from the API layer.
- No LiteLLM / additional providers.
- No streaming.
- No change to `thinking` behavior on the Claude path.
