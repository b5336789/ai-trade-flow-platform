"""Persistent runtime state for portfolio-level risk (M0.6).

Isolates all DB persistence for the kill switch, the ``halted`` flag, and the per-day equity
baseline behind small helpers backed by the ``RuntimeFlag`` table. Keeping this in one module
means the PortfolioGuard and the risk API never touch SQL directly.

"Today" is the UTC calendar day. The equity baseline is snapshotted once per day on first read and
reused for the rest of that day, so ``max_daily_loss`` measures intraday drawdown deterministically.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, func, select

from app.models import OrderRecord, RuntimeFlag

KILL_SWITCH_KEY = "kill_switch"
HALTED_KEY = "halted"
_EQUITY_BASELINE_PREFIX = "equity_baseline:"


def _today_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _start_of_today_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)


def _get(session: Session, key: str) -> str | None:
    flag = session.get(RuntimeFlag, key)
    return flag.value if flag is not None else None


def _set(session: Session, key: str, value: str) -> None:
    flag = session.get(RuntimeFlag, key)
    if flag is None:
        flag = RuntimeFlag(key=key, value=value)
    else:
        flag.value = value
        flag.updated_at = datetime.now(timezone.utc)
    session.add(flag)
    session.commit()


def get_kill_switch(session: Session) -> bool:
    return _get(session, KILL_SWITCH_KEY) == "true"


def set_kill_switch(session: Session, engaged: bool) -> None:
    _set(session, KILL_SWITCH_KEY, "true" if engaged else "false")


def get_halted(session: Session) -> bool:
    return _get(session, HALTED_KEY) == "true"


def set_halted(session: Session, halted: bool) -> None:
    _set(session, HALTED_KEY, "true" if halted else "false")


def get_or_snapshot_day_start_equity(session: Session, current_equity: float) -> float:
    """Return today's day-start equity baseline, snapshotting ``current_equity`` on first read.

    The baseline is keyed by the UTC date, so the first risk check of a new day captures that
    day's opening equity and every subsequent check reuses it.
    """
    key = f"{_EQUITY_BASELINE_PREFIX}{_today_utc()}"
    existing = _get(session, key)
    if existing is not None:
        return float(existing)
    _set(session, key, repr(current_equity))
    return current_equity


def count_orders_today(session: Session) -> int:
    """Number of OrderRecords created since the start of the current UTC day."""
    stmt = select(func.count()).select_from(OrderRecord).where(
        OrderRecord.created_at >= _start_of_today_utc()
    )
    return int(session.exec(stmt).one())
