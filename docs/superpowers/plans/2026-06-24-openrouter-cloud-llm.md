# OpenRouter free LLM for the cloud demo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the EC2 cloud demo use OpenRouter's free model router (`openrouter/free`) for AI nodes instead of the Anthropic API, with local/default behavior unchanged.

**Architecture:** OpenRouter is OpenAI-compatible, so a new `openrouter` provider branch reuses the existing Instructor-over-OpenAI seam in `structured.py` (the same one `lmstudio` uses) — pointed at `https://openrouter.ai/api/v1`, in Instructor JSON mode for max free-model compatibility with the recursive `StrategySpec`. Config gains `openrouter_api_key` / `openrouter_base_url`; the Terraform demo stack + GitHub Action wire a new `OPENROUTER_API_KEY` secret into the instance `.env`.

**Tech Stack:** Python 3.11 / FastAPI / pydantic-settings, `instructor` + `openai` SDK, pytest; Terraform + GitHub Actions for the demo deploy.

## Global Constraints

- Fail loud everywhere: missing key / unknown provider must raise, never silently degrade (`structured.py`).
- Scope is cloud-demo-only: `AI_PROVIDER` default stays `anthropic`; `ai_base_url`/`ai_local_api_key` defaults unchanged.
- Use the `ta` library convention etc. is N/A here. No new dependencies (`instructor` + `openai` already installed for the `lmstudio` path).
- Git flow: work on branch `feat/openrouter-cloud-llm` (already created); never commit to `main`.
- Commit message trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- Default cloud model slug: `openrouter/free` (OpenRouter Free Models Router; auto-selects a free model and filters for structured-output support). Env-configurable via `AI_MODEL`.

---

### Task 1: Config — add OpenRouter settings

**Files:**
- Modify: `backend/app/config.py:30-32` (add fields after the Local LLM block)
- Modify: `backend/app/tests/test_config_provider.py`
- Modify: `.env.example` (AI provider block)

**Interfaces:**
- Produces: `settings.openrouter_api_key: str` (default `""`), `settings.openrouter_base_url: str` (default `"https://openrouter.ai/api/v1"`). Consumed by Task 2.

- [ ] **Step 1: Write the failing test**

In `backend/app/tests/test_config_provider.py`, extend `test_provider_defaults`:

```python
def test_provider_defaults():
    # _env_file=None: test the code defaults, not whatever a local .env (e.g. a dev
    # machine running against LM Studio) happens to set.
    s = Settings(_env_file=None)
    assert s.ai_provider == "anthropic"
    assert s.ai_base_url == "http://localhost:1234/v1"
    assert s.ai_local_api_key == "lm-studio"
    # OpenRouter (cloud demo) defaults: key unset (fail-loud at call time), public base URL.
    assert s.openrouter_api_key == ""
    assert s.openrouter_base_url == "https://openrouter.ai/api/v1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest app/tests/test_config_provider.py::test_provider_defaults -v`
Expected: FAIL with `AttributeError: 'Settings' object has no attribute 'openrouter_api_key'`

- [ ] **Step 3: Add the config fields**

In `backend/app/config.py`, immediately after the `ai_local_api_key` line (currently line 32), add:

```python
    # OpenRouter (cloud demo, OpenAI-compatible). Used when AI_PROVIDER=openrouter.
    # AI_MODEL=openrouter/free routes to a free model and filters for structured-output support.
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest app/tests/test_config_provider.py -v`
Expected: PASS

- [ ] **Step 5: Update `.env.example`**

In `.env.example`, change the AI provider comment line to list the third value and add the OpenRouter vars. Replace:

```
# AI provider: "anthropic" (Claude) or "lmstudio" (local, OpenAI-compatible)
AI_PROVIDER=anthropic
```

with:

```
# AI provider: "anthropic" (Claude), "lmstudio" (local, OpenAI-compatible), or "openrouter" (cloud free)
AI_PROVIDER=anthropic
```

and immediately after the `AI_LOCAL_API_KEY=lm-studio` line add:

```
# OpenRouter (cloud demo). Set AI_PROVIDER=openrouter, AI_MODEL=openrouter/free (free model router).
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/app/tests/test_config_provider.py .env.example
git commit -m "feat(ai): add OpenRouter provider settings

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Provider branch — `openrouter` in `structured.py`

**Files:**
- Modify: `backend/app/ai/structured.py` (module docstring, a `_get_openrouter_client`, a third branch)
- Modify: `backend/app/tests/test_structured.py`

**Interfaces:**
- Consumes: `settings.openrouter_api_key`, `settings.openrouter_base_url` (Task 1).
- Produces: `structured._get_openrouter_client()` (lazy, cached, Instructor JSON mode); `structured_completion(..., )` dispatches `provider == "openrouter"` to it via `client.chat.completions.create(model=..., max_tokens=..., max_retries=..., messages=[system, user], response_model=...)`.

- [ ] **Step 1: Write the failing tests**

In `backend/app/tests/test_structured.py`, add three tests:

```python
def test_openrouter_branch_uses_instructor(monkeypatch):
    monkeypatch.setattr(structured.settings, "ai_provider", "openrouter")
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return Out(value="router")

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    monkeypatch.setattr(structured, "_get_openrouter_client", lambda: fake_client)

    out = structured_completion(system="S", content="C", output_model=Out, max_retries=2)
    assert out == Out(value="router")
    assert captured["response_model"] is Out
    assert captured["max_retries"] == 2
    # OpenAI-style: system prompt is the first message
    assert captured["messages"][0] == {"role": "system", "content": "S"}
    assert captured["messages"][1] == {"role": "user", "content": "C"}


def test_openrouter_client_uses_json_mode_and_base_url(monkeypatch):
    """OpenRouter client is built against the configured base URL in Instructor JSON
    mode (prompt-based + client validation) for max free-model compatibility with the
    recursive StrategySpec. Construction needs no network."""
    import instructor

    monkeypatch.setattr(structured, "_openrouter_client", None)
    monkeypatch.setattr(structured.settings, "openrouter_api_key", "or-test-key")
    monkeypatch.setattr(structured.settings, "openrouter_base_url",
                        "https://openrouter.ai/api/v1")
    client = structured._get_openrouter_client()
    assert client.mode == instructor.Mode.JSON
    assert str(client.client.base_url).rstrip("/") == "https://openrouter.ai/api/v1"


def test_openrouter_missing_key_fails_loud(monkeypatch):
    monkeypatch.setattr(structured, "_openrouter_client", None)
    monkeypatch.setattr(structured.settings, "openrouter_api_key", "")
    with pytest.raises(RuntimeError):
        structured._get_openrouter_client()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest app/tests/test_structured.py -k openrouter -v`
Expected: FAIL — `AttributeError: module 'app.ai.structured' has no attribute '_get_openrouter_client'`

- [ ] **Step 3: Implement the branch**

In `backend/app/ai/structured.py`:

(a) Add the module-level cache near `_lmstudio_client = None` / `_anthropic_client = None`:

```python
_openrouter_client = None
```

(b) Add the lazy builder after `_get_lmstudio_client`:

```python
def _get_openrouter_client():
    """Lazily build + cache the Instructor-wrapped OpenAI client for OpenRouter.

    OpenRouter is OpenAI-compatible. JSON mode (not JSON_SCHEMA): the free model
    router serves arbitrary models, and prompt-based JSON + client-side validation +
    retries handles the recursive StrategySpec most reliably. Fail loud on a missing key.
    """
    if not settings.openrouter_api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set — AI nodes require it when AI_PROVIDER=openrouter"
        )
    global _openrouter_client
    if _openrouter_client is None:
        import instructor
        from openai import OpenAI

        _openrouter_client = instructor.from_openai(
            OpenAI(
                base_url=settings.openrouter_base_url,
                api_key=settings.openrouter_api_key,
            ),
            mode=instructor.Mode.JSON,
        )
    return _openrouter_client
```

(c) Add the dispatch branch in `structured_completion`, before the final `raise RuntimeError(f"Unknown ai_provider: {provider!r}")`:

```python
    if provider == "openrouter":
        client = _get_openrouter_client()
        return client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            max_retries=max_retries,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            response_model=output_model,
        )
```

(d) Update the module docstring's first paragraph to mention OpenRouter, e.g. change
`"...either Claude or a local LM Studio model..."` to
`"...Claude, a local LM Studio model, or OpenRouter (cloud free models)..."`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest app/tests/test_structured.py -v`
Expected: PASS (all branches, including the new openrouter ones and existing anthropic/lmstudio/unknown)

- [ ] **Step 5: Commit**

```bash
git add backend/app/ai/structured.py backend/app/tests/test_structured.py
git commit -m "feat(ai): route AI_PROVIDER=openrouter through Instructor JSON mode

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Cloud wiring — Terraform + GitHub Action

**Files:**
- Modify: `infra/terraform/demo/variables.tf` (add `openrouter_api_key`; make `anthropic_api_key` optional)
- Modify: `infra/terraform/demo/user-data.sh.tftpl:33-42` (generated `.env`)
- Modify: `.github/workflows/deploy-demo.yml` (pass `TF_VAR_openrouter_api_key`)
- Modify: `infra/terraform/demo/terraform.tfvars.example` (document the new var)

**Interfaces:**
- Consumes: repo secret `OPENROUTER_API_KEY` (must be created in GitHub repo settings before `apply`).
- Produces: instance `/opt/app/.env` with `AI_PROVIDER=openrouter`, `AI_MODEL=openrouter/free`, `OPENROUTER_API_KEY=...`.

- [ ] **Step 1: Add the Terraform variable + relax the Anthropic one**

In `infra/terraform/demo/variables.tf`, change the `anthropic_api_key` block to be optional:

```hcl
variable "anthropic_api_key" {
  type        = string
  description = "Anthropic API key for AI nodes. Optional: the demo uses OpenRouter, so this may be empty."
  sensitive   = true
  default     = ""
}
```

and add after it:

```hcl
variable "openrouter_api_key" {
  type        = string
  description = "OpenRouter API key for AI nodes (cloud demo uses the free model router). Written to the instance .env."
  sensitive   = true
}
```

- [ ] **Step 2: Update the generated `.env` in user-data**

In `infra/terraform/demo/user-data.sh.tftpl`, replace the AI lines in the `.env` heredoc (currently lines 35-37):

```
AI_PROVIDER=anthropic
AI_MODEL=claude-opus-4-8
ANTHROPIC_API_KEY=${anthropic_api_key}
```

with:

```
AI_PROVIDER=openrouter
AI_MODEL=openrouter/free
OPENROUTER_API_KEY=${openrouter_api_key}
```

- [ ] **Step 3: Pass the secret in the GitHub Action**

In `.github/workflows/deploy-demo.yml`, in the `"Terraform ${{ github.event.inputs.action }}"` step `env:` block (currently lines 75-77), add the OpenRouter var. Result:

```yaml
        env:
          TF_VAR_anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          TF_VAR_openrouter_api_key: ${{ secrets.OPENROUTER_API_KEY }}
          TF_VAR_api_token: ${{ secrets.API_TOKEN }}
```

(`TF_VAR_anthropic_api_key` is now optional; leaving it is harmless if the secret is unset since the var defaults to `""`.)

- [ ] **Step 4: Document the var in the tfvars example**

In `infra/terraform/demo/terraform.tfvars.example`, add a line (match existing formatting):

```hcl
openrouter_api_key = "sk-or-..."  # OpenRouter API key; cloud demo uses the free model router
```

- [ ] **Step 5: Validate Terraform formatting + syntax**

Run: `cd infra/terraform/demo && terraform fmt -check && terraform validate`
Expected: `terraform fmt -check` exits 0 (no diff); `terraform validate` prints `Success! The configuration is valid.`
(If `terraform` is unavailable locally, instead confirm the templated `.env` heredoc and tfvars edits by re-reading the files; note in the commit that validation was deferred to CI.)

- [ ] **Step 6: Commit**

```bash
git add infra/terraform/demo/variables.tf infra/terraform/demo/user-data.sh.tftpl \
        infra/terraform/demo/terraform.tfvars.example .github/workflows/deploy-demo.yml
git commit -m "feat(deploy): wire OpenRouter free LLM into the demo stack

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Final verification

- [ ] Run the full backend suite: `cd backend && pytest -q` → all pass.
- [ ] Grep for leftover demo Anthropic wiring: `grep -rn "claude-opus-4-8\|ANTHROPIC_API_KEY" infra/terraform/demo` → only the optional, now-empty-default var remains; the generated `.env` no longer sets them.
- [ ] Manual deploy step (out of band, by the user): create the `OPENROUTER_API_KEY` GitHub repo secret, then run the **Deploy Demo** workflow (`apply` with `replace_instance=true` to regenerate `.env`).

## Self-Review notes

- **Spec coverage:** structured.py branch (Task 2), config + .env.example (Task 1), Terraform/user-data/Action (Task 3), tests for branch + fail-loud (Task 2). All spec sections mapped.
- **Type consistency:** `_get_openrouter_client` / `_openrouter_client` / `settings.openrouter_api_key` / `settings.openrouter_base_url` used identically across config, code, and tests.
- **Out of scope confirmed:** no ranking headers, no default-provider change, no prod stack edits.
