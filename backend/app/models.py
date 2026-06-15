"""SQLModel tables: persisted orders, workflows, and run logs."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import JSON, Column, Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OrderRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    broker_order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    status: str
    mode: str
    broker: str
    market: str
    created_at: datetime = Field(default_factory=_now)


class Workflow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    graph: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class RunLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    workflow_id: int | None = Field(default=None)
    status: str  # "ok" | "error"
    detail: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)
