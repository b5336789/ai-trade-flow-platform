"""Provider dispatch + fail-loud for structured_completion (no network)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.ai import structured
from app.ai.structured import structured_completion


class Out(BaseModel):
    value: str


def test_anthropic_branch_uses_instructor(monkeypatch):
    monkeypatch.setattr(structured.settings, "ai_provider", "anthropic")
    captured = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return Out(value="ok")

    monkeypatch.setattr(structured, "_get_anthropic_client",
                        lambda: SimpleNamespace(messages=FakeMessages()))

    out = structured_completion(system="S", content="C", output_model=Out, max_retries=4)
    assert out == Out(value="ok")
    # Instructor JSON mode: client-side response_model + retries (handles the
    # recursive StrategySpec schema that Anthropic's native output_format rejects).
    assert captured["response_model"] is Out
    assert captured["max_retries"] == 4
    assert captured["system"] == "S"
    assert captured["messages"] == [{"role": "user", "content": "C"}]


def test_anthropic_client_uses_json_mode(monkeypatch):
    """Anthropic path must use Instructor ANTHROPIC_JSON (not native output_format),
    because StrategySpec's condition tree is self-referencing and the native
    structured-output validator rejects recursive schemas. No network at build."""
    import anthropic
    import instructor

    monkeypatch.setattr(structured, "_anthropic_client", None)
    monkeypatch.setattr(structured, "get_claude_client",
                        lambda: anthropic.Anthropic(api_key="test-key"))
    client = structured._get_anthropic_client()
    assert client.mode == instructor.Mode.JSON


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

    out = structured_completion(system="S", content="C", output_model=Out, max_retries=3)
    assert out == Out(value="local")
    assert captured["response_model"] is Out
    # weak local models intermittently violate the schema; retries let Instructor reprompt
    assert captured["max_retries"] == 3
    # system prompt is delivered as the first message for the OpenAI-style API
    assert captured["messages"][0] == {"role": "system", "content": "S"}
    assert captured["messages"][1] == {"role": "user", "content": "C"}


def test_unknown_provider_fails_loud(monkeypatch):
    monkeypatch.setattr(structured.settings, "ai_provider", "bogus")
    with pytest.raises(RuntimeError):
        structured_completion(system="S", content="C", output_model=Out)


def test_lmstudio_client_uses_json_schema_mode(monkeypatch):
    """LM Studio rejects Instructor's default TOOLS mode (object tool_choice);
    the client must be built in JSON_SCHEMA mode. Construction needs no network."""
    import instructor

    monkeypatch.setattr(structured, "_lmstudio_client", None)
    client = structured._get_lmstudio_client()
    assert client.mode == instructor.Mode.JSON_SCHEMA
