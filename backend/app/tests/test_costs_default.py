"""The default cost model must apply non-zero slippage (zero is dishonest)."""
from __future__ import annotations

from app.config import Settings
from app.trading.costs import CostModel


def test_default_slippage_is_nonzero():
    assert Settings().cost_slippage_bps == 5.0


def test_cost_model_from_settings_carries_slippage():
    model = CostModel.from_settings(Settings())
    assert model.slippage_bps == 5.0
