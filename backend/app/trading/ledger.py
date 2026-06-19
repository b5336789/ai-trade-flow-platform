"""FIFO realized-P&L ledger (M1.3).

Maintains purchase lots per ``(market, symbol)`` and computes realized P&L on disposals using
First-In-First-Out matching — the convention used for 台股 / 美股 tax reporting and the cleanest
audit trail for a real-money platform.

- A BUY opens a :class:`~app.models.Lot` (quantity, price, and the buy-side ``fee`` from the
  M0.1 ``CostModel`` as part of the cost basis).
- A SELL consumes the oldest open lots FIFO. For each consumed slice it emits a
  :class:`~app.models.RealizedPnL` row:

      gross_pnl    = (sell_price - buy_price) * qty
      cost_basis   = buy_price * qty + apportioned buy fee
      fee          = apportioned buy fee + apportioned sell fee
      tax          = apportioned sell tax (證交稅, tw_stock only — reuses CostModel)
      realized_net = gross_pnl - fee - tax

The buy fee is apportioned across a lot's disposals by consumed fraction; the sell fee and tax
(computed once for the whole sell via ``CostModel.fill_cost``) are apportioned across the lots the
sell touches by disposed quantity. This keeps the totals exactly equal to the per-fill costs the
broker actually charged (no rounding drift, fail-loud on oversell).

Persistence uses the caller's SQLModel ``Session``; the ledger ``add``s rows but does NOT commit —
the caller (``execute_order``) owns the transaction so the OrderRecord and ledger rows commit
atomically.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.models import Lot, RealizedPnL
from app.notifications.service import notify
from app.schemas import MarketKind, OrderSide
from app.trading.costs import CostModel

_EPS = 1e-9


class FifoLedger:
    """FIFO lot tracker bound to a DB session. One per logical accounting operation."""

    def __init__(self, session: Session, cost_model: CostModel | None = None) -> None:
        self._session = session
        self._cost = cost_model or CostModel.from_settings()

    def record_buy(
        self, market: MarketKind, symbol: str, quantity: float, price: float, fee: float
    ) -> Lot:
        """Open a new lot. ``fee`` is the buy-side commission (cost-basis component)."""
        if quantity <= 0 or price < 0 or fee < 0:
            raise ValueError("buy quantity must be > 0; price and fee must be >= 0")
        lot = Lot(
            market=market.value,
            symbol=symbol,
            quantity=quantity,
            remaining_quantity=quantity,
            price=price,
            fee=fee,
        )
        self._session.add(lot)
        # Flush so the lot gets an id/opened_at and is visible to subsequent FIFO queries
        # within this same session before commit.
        self._session.flush()
        return lot

    def record_sell(
        self,
        market: MarketKind,
        symbol: str,
        quantity: float,
        price: float,
        *,
        allow_partial: bool = False,
    ) -> list[RealizedPnL]:
        """Consume the oldest open lots FIFO, emitting one RealizedPnL per consumed slice.

        ``allow_partial=False`` (default, used by unit tests) fails loud if the sell exceeds the
        open lots. ``allow_partial=True`` (used by the ``record_fill`` wiring) consumes only what
        the lots can cover and returns; the caller is responsible for surfacing any shortfall —
        a safety-critical exit must never be blocked by ledger bookkeeping.
        """
        if quantity <= 0 or price < 0:
            raise ValueError("sell quantity must be > 0; price must be >= 0")

        open_lots = list(
            self._session.exec(
                select(Lot)
                .where(Lot.market == market.value)
                .where(Lot.symbol == symbol)
                .where(Lot.remaining_quantity > _EPS)
                .order_by(Lot.opened_at, Lot.id)
            ).all()
        )
        available = sum(lot.remaining_quantity for lot in open_lots)
        if quantity > available + _EPS:
            if not allow_partial:
                raise ValueError(
                    f"sell {quantity} {symbol} exceeds open lots (have {available})"
                )
            quantity = available  # consume everything available; shortfall handled by caller
        if quantity <= _EPS:
            return []

        # Sell-side fee + tax for the whole sell, apportioned across touched lots by quantity.
        sell_cost = self._cost.fill_cost(market, OrderSide.sell, price, quantity)

        disposals: list[RealizedPnL] = []
        remaining_to_sell = quantity
        for lot in open_lots:
            if remaining_to_sell <= _EPS:
                break
            take = min(lot.remaining_quantity, remaining_to_sell)
            frac_of_sell = take / quantity
            frac_of_lot = take / lot.quantity

            proceeds = price * take
            price_cost = lot.price * take
            buy_fee_portion = lot.fee * frac_of_lot
            sell_fee_portion = sell_cost.fee * frac_of_sell
            tax_portion = sell_cost.tax * frac_of_sell
            gross = proceeds - price_cost
            fee_total = buy_fee_portion + sell_fee_portion

            disposal = RealizedPnL(
                market=market.value,
                symbol=symbol,
                quantity=take,
                proceeds=proceeds,
                cost_basis=price_cost + buy_fee_portion,
                fee=fee_total,
                tax=tax_portion,
                gross_pnl=gross,
                realized_net=gross - fee_total - tax_portion,
                lot_id=lot.id,
            )
            self._session.add(disposal)
            disposals.append(disposal)

            lot.remaining_quantity -= take
            self._session.add(lot)
            remaining_to_sell -= take

        self._session.flush()
        return disposals


def record_fill(
    session: Session,
    market: MarketKind,
    symbol: str,
    side: OrderSide,
    price: float,
    quantity: float,
    *,
    fee: float | None = None,
    cost_model: CostModel | None = None,
) -> None:
    """Record a single filled order into the FIFO ledger.

    Buys open a lot (``fee`` from the broker's fill, or computed from the CostModel if omitted);
    sells consume lots FIFO. Called by ``execute_order`` only when a session is present and the
    order was actually placed (never on an idempotent skip).
    """
    cost = cost_model or CostModel.from_settings()
    ledger = FifoLedger(session, cost_model=cost)
    if side == OrderSide.buy:
        buy_fee = fee if fee is not None else cost.fill_cost(market, side, price, quantity).fee
        ledger.record_buy(market, symbol, quantity=quantity, price=price, fee=buy_fee)
        return

    # Sell: match against open lots FIFO. A position can legitimately exceed the tracked lots
    # (e.g. opened before the ledger existed, or synthesised from a live balance snapshot), so we
    # consume what we can and FAIL LOUD via a notification on any unmatched quantity rather than
    # blocking the exit. The broker already validated the position has enough to sell.
    disposed = sum(
        d.quantity
        for d in ledger.record_sell(market, symbol, quantity=quantity, price=price, allow_partial=True)
    )
    shortfall = quantity - disposed
    if shortfall > _EPS:
        notify(
            session,
            title=f"Ledger: untracked disposal {shortfall:g} {symbol}",
            message=(
                f"Sold {quantity:g} {symbol} but only {disposed:g} matched open FIFO lots; "
                f"{shortfall:g} had no recorded cost basis (realized P&L for that portion omitted)."
            ),
            level="warning",
            meta={"market": market.value, "symbol": symbol, "shortfall": shortfall},
        )
