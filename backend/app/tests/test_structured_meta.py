from __future__ import annotations

from types import SimpleNamespace

from pydantic import BaseModel

import app.ai.structured as structured


class _Out(BaseModel):
    value: int


def test_with_meta_returns_tokens_and_latency(monkeypatch):
    out = _Out(value=7)
    completion = SimpleNamespace(usage=SimpleNamespace(input_tokens=11, output_tokens=5))

    class _FakeMessages:
        def create_with_completion(self, **kwargs):
            return out, completion

    monkeypatch.setattr(structured, "_client_and_mode",
                        lambda provider: (SimpleNamespace(messages=_FakeMessages()), "messages"))
    obj, meta = structured.structured_completion_with_meta(
        system="s", content="c", output_model=_Out, model="claude-test"
    )
    assert obj.value == 7
    assert meta.prompt_tokens == 11
    assert meta.completion_tokens == 5
    assert meta.model == "claude-test"
    assert meta.latency_ms >= 0.0
