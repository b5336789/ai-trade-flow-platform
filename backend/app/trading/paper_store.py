"""Persistence for paper-trading state so cash/positions survive process restarts.

Important for an auto-trading bot: scheduled workflows run continuously, and an in-memory paper
account would silently reset on every redeploy. The store loads on PaperBroker construction and
saves after each fill.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.db import engine
from app.models import PaperAccount, PaperPosition
from app.schemas import MarketKind, Position


class PaperStore:
    def __init__(self, market: MarketKind) -> None:
        self.market = market.value

    def load(self) -> tuple[float | None, dict[str, Position]]:
        """Return (cash, positions). cash is None when no account exists yet."""
        with Session(engine) as session:
            account = session.exec(
                select(PaperAccount).where(PaperAccount.market == self.market)
            ).first()
            if account is None:
                return None, {}
            positions: dict[str, Position] = {}
            for row in session.exec(
                select(PaperPosition).where(PaperPosition.market == self.market)
            ).all():
                positions[row.symbol] = Position(
                    symbol=row.symbol, quantity=row.quantity, avg_price=row.avg_price
                )
            return account.cash, positions

    def save(self, cash: float, quote_asset: str, positions: dict[str, Position]) -> None:
        with Session(engine) as session:
            account = session.exec(
                select(PaperAccount).where(PaperAccount.market == self.market)
            ).first()
            if account is None:
                account = PaperAccount(market=self.market, cash=cash, quote_asset=quote_asset)
            else:
                account.cash = cash
                account.quote_asset = quote_asset
                account.updated_at = datetime.now(timezone.utc)
            session.add(account)

            existing = session.exec(
                select(PaperPosition).where(PaperPosition.market == self.market)
            ).all()
            for row in existing:
                session.delete(row)
            for pos in positions.values():
                session.add(
                    PaperPosition(
                        market=self.market,
                        symbol=pos.symbol,
                        quantity=pos.quantity,
                        avg_price=pos.avg_price,
                    )
                )
            session.commit()

    def reset(self) -> None:
        with Session(engine) as session:
            for model in (PaperAccount, PaperPosition):
                for row in session.exec(select(model).where(model.market == self.market)).all():
                    session.delete(row)
            session.commit()
