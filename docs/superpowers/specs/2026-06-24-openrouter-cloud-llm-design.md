# OpenRouter free LLM for the cloud demo — design

**Date:** 2026-06-24
**Status:** Approved (brainstorming)
**Scope:** Cloud demo (EC2) only. Local dev and the repo default stay `AI_PROVIDER=anthropic`.

## Goal

Make the cloud demo deployment use OpenRouter's **free** models for all AI nodes
(signal + strategy designer) instead of the Anthropic API, so the live demo costs
nothing to run. Local development, the test suite, and the repo defaults are
unchanged — only the EC2 demo's generated `.env` switches providers.

## Why OpenRouter `openrouter/free`

`openrouter/free` is OpenRouter's Free Models Router: it auto-selects a free model
per request and **filters for the features the request needs (structured outputs /
tool calling)**. This matches our structured-output requirement and removes the
need to hand-pick / maintain a specific free model slug. It stays env-configurable
via `AI_MODEL`, so the model can be swapped without a code change.

OpenRouter is OpenAI-compatible, so it slots into the existing Instructor-over-OpenAI
seam already used by the `lmstudio` provider — no new SDK.

## Components & changes

### 1. Provider branch — `backend/app/ai/structured.py`
Add a third provider branch `openrouter`, mirroring `_get_lmstudio_client` but:
- `base_url = settings.openrouter_base_url` (default `https://openrouter.ai/api/v1`)
- `api_key = settings.openrouter_api_key`
- `mode = instructor.Mode.JSON` — **JSON mode, not JSON_SCHEMA**. The recursive
  `StrategySpec` (Combinator → Combinator) plus arbitrary free models behind the
  router are most reliably handled by prompt-based JSON + client-side validation +
  the existing retry budget. (Same reasoning that drove Anthropic to JSON mode.)
- Calls `client.chat.completions.create(model, max_tokens, max_retries, messages,
  response_model)` exactly like the `lmstudio` branch (system+user messages).

Fail loud: building the client raises `RuntimeError` if `openrouter_api_key` is
empty (mirrors the Anthropic key guard). The final `raise RuntimeError(f"Unknown
ai_provider: {provider!r}")` stays.

### 2. Config — `backend/app/config.py` + `.env.example`
Add:
- `openrouter_api_key: str = ""`
- `openrouter_base_url: str = "https://openrouter.ai/api/v1"`

`.env.example`: document `AI_PROVIDER=openrouter`, `AI_MODEL=openrouter/free`,
`OPENROUTER_API_KEY=`, and the base URL. Note that `AI_MAX_RETRIES` (default 5)
also covers the OpenRouter path. Update the `AI_PROVIDER` comment to list the third
value: `anthropic` | `lmstudio` | `openrouter`.

### 3. Cloud wiring
- `infra/terraform/demo/variables.tf`: add `openrouter_api_key` (string, sensitive).
  Make `anthropic_api_key` optional (`default = ""`) — the demo no longer requires it.
- `infra/terraform/demo/user-data.sh.tftpl`: the generated `/opt/app/.env` sets
  `AI_PROVIDER=openrouter`, `AI_MODEL=openrouter/free`,
  `OPENROUTER_API_KEY=${openrouter_api_key}`. Drop the `ANTHROPIC_API_KEY` line
  (or leave it blank) and the `AI_MODEL=claude-opus-4-8` line.
- `.github/workflows/deploy-demo.yml`: pass `TF_VAR_openrouter_api_key` from a new
  repo secret `OPENROUTER_API_KEY` in the Terraform step env. `TF_VAR_anthropic_api_key`
  may be dropped or kept (now optional).

### 4. Tests — `backend/app/tests/`
Following the existing structured-output test style (mock the Instructor client):
- `openrouter` branch builds an OpenAI-compatible client against
  `https://openrouter.ai/api/v1` and calls `chat.completions.create` with the
  given `response_model` / model.
- Fail-loud when `OPENROUTER_API_KEY` is empty.

## Out of scope (YAGNI)
- OpenRouter ranking headers (`HTTP-Referer` / `X-Title`).
- Changing the local/default provider or the prod Terraform stack.
- Per-model fallback lists (the router already handles selection).

## Success criteria
- With `AI_PROVIDER=openrouter` + a valid `OPENROUTER_API_KEY`, signal and strategy
  AI nodes return validated structured output via `openrouter/free`.
- Missing key fails loud.
- `pytest` passes; local/default behavior (anthropic) unchanged.
- Demo deploy provisions with the OpenRouter secret and no Anthropic key.

## References
- Free Models Router: https://openrouter.ai/openrouter/free
- Auto Router docs: https://openrouter.ai/docs/guides/routing/routers/auto-router
