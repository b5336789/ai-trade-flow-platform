"""Market-hours calendar (M1.4).

``is_market_open(market, dt)`` answers whether a market accepts orders at ``dt`` so the scheduler
can SKIP (not error) ticks that fire while a market is closed.

DATETIME CONTRACT
-----------------
``dt`` may be timezone-aware OR naive. A naive ``dt`` is interpreted as UTC (the scheduler passes
``datetime.now(timezone.utc)``). Aware datetimes are honoured as-is. Either way ``dt`` is converted
to the market's local timezone internally before the session/holiday checks, so callers never have
to reason about local time.

The function is pure and deterministic: pass an explicit ``dt`` and you get a reproducible answer,
which is how the tests freeze time (no freezegun dependency).

EXTENDING HOLIDAYS
------------------
``TW_STOCK_HOLIDAYS`` / ``US_STOCK_HOLIDAYS`` are module-level sets of ``date`` objects holding a
small built-in list. They are importable and mutable; ``add_holidays(market, dates)`` is provided
for callers that want to extend a market's holiday set (e.g. loading a yearly calendar) without
reaching into the module internals.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from app.schemas import MarketKind

TW_TZ = ZoneInfo("Asia/Taipei")
US_TZ = ZoneInfo("America/New_York")

# Regular cash-session hours in each market's local timezone.
TW_OPEN, TW_CLOSE = time(9, 0), time(13, 30)
US_OPEN, US_CLOSE = time(9, 30), time(16, 0)

# Built-in (non-exhaustive) holiday seeds. Extend via add_holidays() or by importing these sets.
TW_STOCK_HOLIDAYS: set[date] = {
    date(2026, 1, 1),    # New Year's Day
    date(2026, 2, 16),   # Lunar New Year (representative day)
    date(2026, 2, 17),   # Lunar New Year
    date(2026, 2, 18),   # Lunar New Year
    date(2026, 2, 28),   # Peace Memorial Day
    date(2026, 4, 4),    # Children's / Tomb-Sweeping Day
    date(2026, 5, 1),    # Labour Day
    date(2026, 10, 10),  # National Day
}

US_STOCK_HOLIDAYS: set[date] = {
    date(2026, 1, 1),    # New Year's Day
    date(2026, 1, 19),   # Martin Luther King Jr. Day
    date(2026, 2, 16),   # Washington's Birthday
    date(2026, 4, 3),    # Good Friday
    date(2026, 5, 25),   # Memorial Day
    date(2026, 6, 19),   # Juneteenth
    date(2026, 7, 3),    # Independence Day (observed)
    date(2026, 9, 7),    # Labor Day
    date(2026, 11, 26),  # Thanksgiving
    date(2026, 12, 25),  # Christmas Day
}

_HOLIDAYS: dict[MarketKind, set[date]] = {
    MarketKind.tw_stock: TW_STOCK_HOLIDAYS,
    MarketKind.us_stock: US_STOCK_HOLIDAYS,
}


def add_holidays(market: MarketKind, dates: "set[date] | list[date]") -> None:
    """Extend a market's holiday set in place (no-op for markets with no holiday calendar)."""
    holidays = _HOLIDAYS.get(market)
    if holidays is not None:
        holidays.update(dates)


def _as_aware_utc(dt: datetime) -> datetime:
    """Naive ``dt`` is treated as UTC (the contract); aware ``dt`` is returned unchanged."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _is_session_open(local_dt: datetime, open_t: time, close_t: time, holidays: set[date]) -> bool:
    if local_dt.weekday() >= 5:  # Saturday/Sunday
        return False
    if local_dt.date() in holidays:
        return False
    return open_t <= local_dt.time() < close_t


def is_market_open(market: MarketKind, dt: datetime) -> bool:
    """Whether ``market`` is in its regular session at ``dt`` (see module docstring for contract)."""
    if market == MarketKind.crypto:
        return True  # crypto trades 24/7

    aware = _as_aware_utc(dt)
    if market == MarketKind.tw_stock:
        return _is_session_open(aware.astimezone(TW_TZ), TW_OPEN, TW_CLOSE, TW_STOCK_HOLIDAYS)
    if market == MarketKind.us_stock:
        return _is_session_open(aware.astimezone(US_TZ), US_OPEN, US_CLOSE, US_STOCK_HOLIDAYS)

    raise ValueError(f"no market calendar for market '{market}'")  # fail loud on unknown market
