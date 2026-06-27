"""DB-backed cache for AI signal responses (deterministic, metered)."""
from __future__ import annotations

import hashlib

from pydantic import BaseModel
from sqlmodel import Session

from app.db import engine
from app.models import AiSignalCache


def cache_key(model: str, system: str, summary: str) -> str:
    raw = f"{model}\x00{system}\x00{summary}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def lookup(key: str) -> dict | None:
    with Session(engine) as session:
        row = session.get(AiSignalCache, key)
        return dict(row.response_json) if row is not None else None


def store(key: str, model: str, response: BaseModel, meta) -> None:
    with Session(engine) as session:
        if session.get(AiSignalCache, key) is not None:
            return
        session.add(
            AiSignalCache(
                cache_key=key,
                model=model,
                response_json=response.model_dump(mode="json"),
                prompt_tokens=getattr(meta, "prompt_tokens", 0),
                completion_tokens=getattr(meta, "completion_tokens", 0),
                latency_ms=getattr(meta, "latency_ms", 0.0),
            )
        )
        session.commit()
