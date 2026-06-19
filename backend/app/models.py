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
    # Optional cron expression (5-field, APScheduler CronTrigger) as an alternative to the interval
    # trigger; when set it takes precedence over interval_seconds (M1.4).
    cron: str | None = Field(default=None)
    # When True (default), skip ticks that fire while the workflow's market is closed (M1.4).
    respect_market_hours: bool = True
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


class Lot(SQLModel, table=True):
    """An open (or partially consumed) purchase lot for FIFO realized-P&L (M1.3).

    A BUY opens one Lot; SELLs consume the oldest open lots first, decrementing
    ``remaining_quantity``. ``fee`` is the buy-side commission from the CostModel and is part of
    the cost basis (apportioned across disposals by consumed fraction).
    """

    id: int | None = Field(default=None, primary_key=True)
    market: str = Field(index=True)
    symbol: str = Field(index=True)
    quantity: float  # original lot size
    remaining_quantity: float  # unconsumed quantity (0 == fully closed)
    price: float  # buy fill price (before fee)
    fee: float = 0.0  # buy-side commission for the whole lot (cost-basis component)
    opened_at: datetime = Field(default_factory=_now, index=True)


class RealizedPnL(SQLModel, table=True):
    """One FIFO disposal: proceeds vs cost basis, net of fees + tax (M1.3).

    Emitted per consumed lot on a SELL. ``gross_pnl`` = proceeds − price-only cost basis;
    ``realized_net`` = gross − apportioned buy fee − sell fee − sell tax (證交稅, tw_stock only).
    """

    id: int | None = Field(default=None, primary_key=True)
    market: str = Field(index=True)
    symbol: str = Field(index=True)
    quantity: float  # disposed quantity from this lot
    proceeds: float  # sell price * quantity
    cost_basis: float  # buy price * quantity (+ apportioned buy fee)
    fee: float = 0.0  # apportioned buy fee + sell fee
    tax: float = 0.0  # 證交稅 on this disposal's proceeds (tw_stock only)
    gross_pnl: float = 0.0  # proceeds - (price-only cost basis)
    realized_net: float = 0.0  # gross_pnl - fee - tax
    lot_id: int | None = Field(default=None, index=True)
    closed_at: datetime = Field(default_factory=_now, index=True)


class RuntimeFlag(SQLModel, table=True):
    """Persistent key/value runtime state (M0.6).

    Holds the kill switch, the ``halted`` flag, and the per-day equity baseline (keyed by
    ``equity_baseline:<YYYY-MM-DD>``) so portfolio-level risk survives restarts and is toggleable
    via the DB/API. Values are stored as strings; helpers in trading/runtime_state.py coerce them.
    """

    key: str = Field(primary_key=True)
    value: str = ""
    updated_at: datetime = Field(default_factory=_now)
