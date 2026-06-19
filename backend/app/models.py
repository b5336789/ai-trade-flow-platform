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


class Schedule(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    workflow_id: int
    interval_seconds: int
    enabled: bool = True
    last_run_at: datetime | None = Field(default=None)
    last_status: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=_now)


class Notification(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    level: str = "info"  # info | success | warning | error
    title: str
    message: str = ""
    meta: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_now)


class PaperAccount(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    market: str = Field(unique=True, index=True)
    cash: float
    quote_asset: str
    updated_at: datetime = Field(default_factory=_now)


class PaperPosition(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    market: str = Field(index=True)
    symbol: str
    quantity: float
    avg_price: float


class StrategyDef(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    spec_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    source: str = "manual"  # "ai" | "manual"
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)
