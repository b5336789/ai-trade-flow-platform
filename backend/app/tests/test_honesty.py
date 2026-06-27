from __future__ import annotations

from app.backtest.honesty import assess, representative_cost_bps
from app.config import Settings
from app.schemas import MarketKind


def test_warns_on_zero_slippage_low_trades_few_bars():
    a = assess(slippage_bps=0.0, cost_taker_bps=7.5, bars=50, num_trades=3,
               timeframe="1h", market="crypto")
    joined = " ".join(a.warnings)
    assert "零滑價" in joined
    assert "樣本過少" in joined
    assert "K 線過少" in joined
    assert a.annualization_basis.startswith("365.25")


def test_clean_run_has_no_warnings():
    a = assess(slippage_bps=5.0, cost_taker_bps=7.5, bars=500, num_trades=40,
               timeframe="1d", market="us_stock")
    assert a.warnings == []
    assert "252" in a.annualization_basis


def test_oos_selected_flag_warns():
    a = assess(slippage_bps=5.0, cost_taker_bps=7.5, bars=500, num_trades=40,
               timeframe="1d", market="crypto", oos_selected=True)
    assert any("OOS" in w for w in a.warnings)


def test_representative_cost_bps_per_market():
    s = Settings()
    assert representative_cost_bps(MarketKind.crypto, s) == s.cost_crypto_taker_bps
    assert representative_cost_bps(MarketKind.tw_stock, s) == s.cost_tw_fee_rate * s.cost_tw_fee_discount * 10_000
