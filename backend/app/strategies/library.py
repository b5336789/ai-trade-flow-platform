"""Persistence for saved strategies (StrategyDef <-> StrategySpec)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models import StrategyDef
from app.strategies.spec import StrategySpec


def save_strategy(session: Session, name: str, spec: StrategySpec,
                  description: str = "", source: str = "manual") -> StrategyDef:
    row = StrategyDef(name=name, description=description,
                      spec_json=spec.model_dump(mode="json"), source=source)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_strategies(session: Session) -> list[StrategyDef]:
    return list(session.exec(select(StrategyDef)).all())


def get_strategy(session: Session, sid: int) -> StrategyDef | None:
    return session.get(StrategyDef, sid)


def update_strategy(session: Session, sid: int, *, name: str | None = None,
                    description: str | None = None, spec: StrategySpec | None = None) -> StrategyDef:
    row = session.get(StrategyDef, sid)
    if row is None:
        raise ValueError(f"strategy {sid} not found")
    if name is not None:
        row.name = name
    if description is not None:
        row.description = description
    if spec is not None:
        row.spec_json = spec.model_dump(mode="json")
    row.updated_at = datetime.now(timezone.utc)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def delete_strategy(session: Session, sid: int) -> bool:
    row = session.get(StrategyDef, sid)
    if row is None:
        return False
    session.delete(row)
    session.commit()
    return True


def load_spec(session: Session, sid: int) -> StrategySpec:
    row = session.get(StrategyDef, sid)
    if row is None:
        raise ValueError(f"strategy {sid} not found")
    return StrategySpec.model_validate(row.spec_json)
