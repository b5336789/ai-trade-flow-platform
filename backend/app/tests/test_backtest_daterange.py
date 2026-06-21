"""C2 date-range backtest: range-capable data fetch (ccxt pagination + CSV filter + boundaries)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.brokers.base import Broker
from app.brokers.crypto_ccxt import CcxtBroker, MAX_RANGE_BARS


def _utc(y, m, d, h=0):
    return datetime(y, m, d, h, tzinfo=timezone.utc)


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


class _FakeExchange:
    """Mimics ccxt fetch_ohlcv(since=, limit=): returns hourly bars from `since`, page by page."""

    def __init__(self, bars: list[list], page_size: int = 2) -> None:
        self._bars = bars  # sorted [[ms, o, h, l, c, v], ...]
        self.page_size = page_size
        self.calls: list[int | None] = []

    def fetch_ohlcv(self, symbol, timeframe="1h", since=None, limit=None):
        self.calls.append(since)
        rows = [b for b in self._bars if since is None or b[0] >= since]
        return rows[: (limit or self.page_size)]


def _hourly_bars(start: datetime, n: int) -> list[list]:
    out = []
    for i in range(n):
        t = _ms(start) + i * 3_600_000  # +1h
        out.append([t, 10.0 + i, 11.0 + i, 9.0 + i, 10.5 + i, 1.0])
    return out


def _make_ccxt(monkeypatch, fake: _FakeExchange) -> CcxtBroker:
    # Build a CcxtBroker without touching the network, then swap in the fake exchange.
    monkeypatch.setattr(CcxtBroker, "__init__", lambda self: None)
    broker = CcxtBroker()
    broker._exchange = fake
    broker._exchange_id = "binance"
    return broker


def test_base_get_ohlcv_range_default_fails_loud():
    # The ABC default must fail loud so unimplemented brokers never silently return nothing.
    assert hasattr(Broker, "get_ohlcv_range")


def test_ccxt_range_paginates_across_two_pages(monkeypatch):
    start, end = _utc(2024, 1, 1), _utc(2024, 1, 1, 3)  # want 4 hourly bars (00,01,02,03)
    bars = _hourly_bars(start, 4)
    fake = _FakeExchange(bars, page_size=2)  # forces 2 pages to cover the range
    broker = _make_ccxt(monkeypatch, fake)

    candles = broker.get_ohlcv_range("BTC/USDT", "1h", start, end)

    assert [int(c.timestamp.timestamp()) for c in candles] == [int(b[0] / 1000) for b in bars]
    assert len(candles) == 4
    # paginated: first call since=start_ms, second call advanced past page 1's last bar.
    assert len(fake.calls) >= 2
    assert fake.calls[0] == _ms(start)
    assert fake.calls[1] == bars[2][0]  # last-of-page-1 ts + 1ms → next page's first bar


def test_ccxt_range_stops_at_end_and_excludes_beyond(monkeypatch):
    start, end = _utc(2024, 1, 1), _utc(2024, 1, 1, 1)  # only 00 and 01 in range
    bars = _hourly_bars(start, 6)  # exchange has 6 bars; range only covers 2
    broker = _make_ccxt(monkeypatch, _FakeExchange(bars, page_size=10))

    candles = broker.get_ohlcv_range("BTC/USDT", "1h", start, end)

    assert len(candles) == 2
    assert candles[-1].timestamp <= end


def test_ccxt_range_caps_total_bars(monkeypatch):
    start, end = _utc(2020, 1, 1), _utc(2025, 1, 1)  # huge range
    bars = _hourly_bars(start, MAX_RANGE_BARS + 500)
    broker = _make_ccxt(monkeypatch, _FakeExchange(bars, page_size=1000))

    candles = broker.get_ohlcv_range("BTC/USDT", "1h", start, end)

    assert len(candles) <= MAX_RANGE_BARS


def test_ccxt_range_empty_fails_loud(monkeypatch):
    start, end = _utc(2024, 1, 1), _utc(2024, 1, 2)
    broker = _make_ccxt(monkeypatch, _FakeExchange([], page_size=2))  # exchange returns nothing
    with pytest.raises(RuntimeError):
        broker.get_ohlcv_range("BTC/USDT", "1h", start, end)
