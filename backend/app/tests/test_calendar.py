"""Unit tests for the market-hours calendar (M1.4).

Time is "frozen" by passing explicit datetimes (no freezegun dependency). The dt-timezone
contract is exercised directly: naive => UTC, aware => honoured as-is.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from app.marketdata.calendar import add_holidays, is_market_open
from app.schemas import MarketKind

TW = ZoneInfo("Asia/Taipei")
NY = ZoneInfo("America/New_York")


def test_crypto_is_always_open():
    # Sunday 03:00 UTC — closed for any equity market, open for crypto.
    assert is_market_open(MarketKind.crypto, datetime(2026, 6, 21, 3, 0, tzinfo=timezone.utc))


def test_tw_stock_open_during_session():
    # Tue 10:30 Asia/Taipei is inside 09:00-13:30.
    dt = datetime(2026, 6, 16, 10, 30, tzinfo=TW)
    assert is_market_open(MarketKind.tw_stock, dt)


def test_tw_stock_closed_before_open_and_after_close():
    # 08:30 (before open) and 14:00 (after 13:30 close), same weekday.
    assert not is_market_open(MarketKind.tw_stock, datetime(2026, 6, 16, 8, 30, tzinfo=TW))
    assert not is_market_open(MarketKind.tw_stock, datetime(2026, 6, 16, 14, 0, tzinfo=TW))


def test_tw_stock_closed_at_0300_taipei():
    # 03:00 Taipei == 19:00 prior-day UTC; verify the naive-UTC contract resolves the same.
    aware = datetime(2026, 6, 16, 3, 0, tzinfo=TW)
    naive_utc = datetime(2026, 6, 15, 19, 0)  # naive => interpreted as UTC
    assert not is_market_open(MarketKind.tw_stock, aware)
    assert not is_market_open(MarketKind.tw_stock, naive_utc)


def test_us_stock_open_during_regular_session():
    # Wed 10:00 America/New_York is inside 09:30-16:00.
    dt = datetime(2026, 6, 17, 10, 0, tzinfo=NY)
    assert is_market_open(MarketKind.us_stock, dt)


def test_us_stock_closed_after_close():
    assert not is_market_open(MarketKind.us_stock, datetime(2026, 6, 17, 16, 30, tzinfo=NY))


def test_weekend_closed_for_equities():
    # Saturday during what would be session hours.
    assert not is_market_open(MarketKind.tw_stock, datetime(2026, 6, 20, 11, 0, tzinfo=TW))
    assert not is_market_open(MarketKind.us_stock, datetime(2026, 6, 20, 11, 0, tzinfo=NY))


def test_us_holiday_closed():
    # Independence Day (observed) 2026-07-03 is a Friday in the built-in holiday set.
    assert not is_market_open(MarketKind.us_stock, datetime(2026, 7, 3, 11, 0, tzinfo=NY))


def test_tw_holiday_closed():
    # National Day 2026-10-10 (Saturday anyway, but listed) — use a weekday holiday.
    assert not is_market_open(MarketKind.tw_stock, datetime(2026, 2, 17, 11, 0, tzinfo=TW))


def test_add_holidays_extends_calendar():
    custom = date(2026, 6, 16)  # a normally-open Tuesday
    assert is_market_open(MarketKind.tw_stock, datetime(2026, 6, 16, 11, 0, tzinfo=TW))
    add_holidays(MarketKind.tw_stock, {custom})
    try:
        assert not is_market_open(MarketKind.tw_stock, datetime(2026, 6, 16, 11, 0, tzinfo=TW))
    finally:
        # Keep the module-level set clean for other tests.
        from app.marketdata.calendar import TW_STOCK_HOLIDAYS

        TW_STOCK_HOLIDAYS.discard(custom)
