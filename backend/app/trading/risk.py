"""Pre-trade risk guards. Every order passes through here before reaching a broker."""

from __future__ import annotations

from dataclasses import dataclass

from sqlmodel import Session

from app.brokers.base import Broker
from app.marketdata.fx import FxConverter, quote_currency_for
from app.notifications.service import notify
from app.schemas import MarketKind, OrderRequest, OrderSide
from app.trading import runtime_state
from app.trading.portfolio import build_portfolio


class RiskError(Exception):
    """Raised when an order violates a risk limit (CLAUDE.md: fail loud)."""


@dataclass
class RiskGuard:
    max_order_value: float = 50_000.0
    max_position_value: float = 100_000.0

    def check(
        self,
        request: OrderRequest,
        fill_price: float,
        current_position_qty: float = 0.0,
        current_price: float | None = None,
    ) -> None:
        if fill_price <= 0:
            raise RiskError(f"non-positive fill price {fill_price}")
        order_value = fill_price * request.quantity
        if order_value > self.max_order_value:
            raise RiskError(
                f"order value {order_value:.2f} exceeds max_order_value {self.max_order_value:.2f}"
            )
        if request.side == OrderSide.buy:
            # Judge the position cap by CURRENT MARKET VALUE (M0.5): the existing holding is marked
            # at the live price (spot avg_price is often unknown / synthesised as 0), and the new
            # slice at its fill price. Falls back to fill_price when no separate mark is supplied.
            mark_price = current_price if current_price is not None else fill_price
            projected_value = current_position_qty * mark_price + request.quantity * fill_price
            if projected_value > self.max_position_value:
                raise RiskError(
                    f"projected position value {projected_value:.2f} exceeds "
                    f"max_position_value {self.max_position_value:.2f}"
                )


def _is_exit(request: OrderRequest, broker: Broker) -> bool:
    """An EXIT reduces (or closes) an existing long position. Sells of a held symbol are exits.

    Exits must ALWAYS be allowed through the portfolio gates so the operator can de-risk / stop-loss
    even while halted or kill-switched. Buys (and sells with no position to reduce) are ENTRIES.
    """
    if request.side != OrderSide.sell:
        return False
    held = next((p.quantity for p in broker.get_positions() if p.symbol == request.symbol), 0.0)
    return held > 0.0


@dataclass
class PortfolioGuard:
    """Portfolio-level, base-currency (TWD) risk gates evaluated on the order about to be placed.

    Semantics (M0.6, SAFETY-CRITICAL): any trigger (kill switch, halt, or a breached cap) REJECTS
    NEW ENTRIES (buys) but ALWAYS ALLOWS EXITS (position-reducing sells), so trading can still be
    wound down while halted. ``max_daily_loss`` breach also SETS the persistent ``halted`` flag.

    All monetary comparisons are in the base currency: position market values and equity (computed
    via ``build_portfolio``) are converted from the broker's single quote currency with ``fx``.
    """

    max_total_exposure_value: float = 1_000_000.0
    max_daily_loss: float = 100_000.0
    max_orders_per_day: int = 50
    kill_switch: bool = False
    fx: FxConverter | None = None

    @classmethod
    def from_settings(cls) -> "PortfolioGuard":
        from app.config import settings

        return cls(
            max_total_exposure_value=settings.max_total_exposure_value,
            max_daily_loss=settings.max_daily_loss,
            max_orders_per_day=settings.max_orders_per_day,
            kill_switch=settings.kill_switch,
            fx=FxConverter.from_settings(),
        )

    def check(
        self,
        request: OrderRequest,
        fill_price: float,
        market: MarketKind,
        broker: Broker,
        session: Session,
    ) -> None:
        fx = self.fx or FxConverter.from_settings()
        quote_ccy = quote_currency_for(market)

        # Exits are never blocked by portfolio gates — they only reduce risk.
        if _is_exit(request, broker):
            return

        # Single, market-priced portfolio snapshot reused across all gates (base currency).
        view = build_portfolio(broker)
        equity_base = fx.to_base(view.equity, quote_ccy)
        exposure_base = fx.to_base(view.positions_value, quote_ccy)

        # --- Kill switch (config OR persisted runtime flag) ---
        if self.kill_switch or runtime_state.get_kill_switch(session):
            notify(
                session,
                title="Kill switch active — entry blocked",
                message=f"Rejected {request.side.value} {request.quantity} {request.symbol} (entry).",
                level="warning",
                meta={"symbol": request.symbol, "gate": "kill_switch"},
            )
            raise RiskError("kill switch is active: new entries are blocked (exits still allowed)")

        # --- Already halted (e.g. a prior daily-loss breach) ---
        if runtime_state.get_halted(session):
            notify(
                session,
                title="Trading halted — entry blocked",
                message=f"Rejected {request.side.value} {request.quantity} {request.symbol} (entry).",
                level="warning",
                meta={"symbol": request.symbol, "gate": "halted"},
            )
            raise RiskError("trading is halted: new entries are blocked (exits still allowed)")

        # --- Daily loss (intraday drawdown from the day-start equity baseline) ---
        day_start_equity = runtime_state.get_or_snapshot_day_start_equity(session, equity_base)
        daily_loss = day_start_equity - equity_base
        if daily_loss > self.max_daily_loss:
            runtime_state.set_halted(session, True)
            notify(
                session,
                title="Max daily loss breached — trading halted",
                message=(
                    f"Daily loss {daily_loss:.2f} {fx.base_currency} exceeds "
                    f"max_daily_loss {self.max_daily_loss:.2f}. Entries blocked; exits allowed."
                ),
                level="error",
                meta={"daily_loss": daily_loss, "gate": "max_daily_loss"},
            )
            raise RiskError(
                f"daily loss {daily_loss:.2f} {fx.base_currency} exceeds "
                f"max_daily_loss {self.max_daily_loss:.2f}: trading halted"
            )

        # --- Orders per day ---
        orders_today = runtime_state.count_orders_today(session)
        if orders_today >= self.max_orders_per_day:
            notify(
                session,
                title="Max orders per day reached — entry blocked",
                message=f"{orders_today} orders already placed today (cap {self.max_orders_per_day}).",
                level="warning",
                meta={"orders_today": orders_today, "gate": "max_orders_per_day"},
            )
            raise RiskError(
                f"orders today {orders_today} reached max_orders_per_day {self.max_orders_per_day}"
            )

        # --- Total exposure (projected position market value AFTER this entry) ---
        projected_exposure = exposure_base + fx.to_base(fill_price * request.quantity, quote_ccy)
        if projected_exposure > self.max_total_exposure_value:
            notify(
                session,
                title="Max total exposure breached — entry blocked",
                message=(
                    f"Projected exposure {projected_exposure:.2f} {fx.base_currency} exceeds "
                    f"max_total_exposure_value {self.max_total_exposure_value:.2f}."
                ),
                level="warning",
                meta={"projected_exposure": projected_exposure, "gate": "max_total_exposure_value"},
            )
            raise RiskError(
                f"projected total exposure {projected_exposure:.2f} {fx.base_currency} exceeds "
                f"max_total_exposure_value {self.max_total_exposure_value:.2f}"
            )
