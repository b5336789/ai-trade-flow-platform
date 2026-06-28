"""Cross-market portfolio summary aggregates each market's equity into the base currency."""
from __future__ import annotations

import pytest

import app.api.portfolio as pf
from app.schemas import MarketKind


class _Bal:
    def __init__(self, free): self.free = free

class _Pos:
    def __init__(self, symbol, quantity, avg_price):
        self.symbol, self.quantity, self.avg_price = symbol, quantity, avg_price

class _Tick:
    def __init__(self, price): self.price = price

class _CryptoBroker:
    def get_balance(self): return [_Bal(1000.0)]
    def get_positions(self): return [_Pos("BTC/USDT", 1.0, 50.0)]
    def get_ticker(self, symbol): return _Tick(60.0)


def test_summary_aggregates_to_base_and_skips_unavailable(monkeypatch):
    def fake_get_broker(market):
        if market == MarketKind.crypto:
            return _CryptoBroker()
        raise NotImplementedError(f"{market.value}: live brokers not implemented yet")
    monkeypatch.setattr(pf, "get_broker", fake_get_broker)

    out = pf.portfolio_summary()

    assert out.base_currency == "TWD"
    crypto = next(m for m in out.markets if m.market == "crypto")
    # equity_native = 1000 cash + 60 (1 * 60 ticker) = 1060 USDT
    assert crypto.available is True
    assert crypto.quote_currency == "USDT"
    assert crypto.equity_native == pytest.approx(1060.0)
    # USDT->TWD via default static fx_rates (USDT: 31.5)
    assert crypto.equity_base == pytest.approx(1060.0 * 31.5)
    assert out.total_equity_base == pytest.approx(1060.0 * 31.5)
    # tw/us unavailable, contribute 0 and carry the loud error
    tw = next(m for m in out.markets if m.market == "tw_stock")
    assert tw.available is False and tw.error and "not implemented" in tw.error
    assert tw.equity_base == 0.0
