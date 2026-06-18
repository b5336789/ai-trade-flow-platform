"""SQLModel tables: persisted orders, workflows, and run logs."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import JSON, Column, Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OrderRecord(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    # Idempotency key (M0.5): deterministic per (scheduled-run × order node). Nullable so manual
    # orders (which have no logical re-run identity) keep working unchanged; indexed for the
    # duplicate lookup performed before every workflow-driven order.
    client_order_id: str | None = Field(default=None, index=True)
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


class RuntimeFlag(SQLModel, table=True):
    """Persistent key/value runtime state (M0.6).

    Holds the kill switch, the ``halted`` flag, and the per-day equity baseline (keyed by
    ``equity_baseline:<YYYY-MM-DD>``) so portfolio-level risk survives restarts and is toggleable
    via the DB/API. Values are stored as strings; helpers in trading/runtime_state.py coerce them.
    """

    key: str = Field(primary_key=True)
    value: str = ""
    updated_at: datetime = Field(default_factory=_now)
