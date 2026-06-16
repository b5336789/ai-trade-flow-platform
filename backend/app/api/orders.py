"""Order placement, listing, portfolio, and positions endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.brokers.registry import get_broker, reset_paper_account
from app.db import get_session
from app.models import OrderRecord
from app.schemas import MarketKind, OrderRequest, OrderResult
from app.trading.execution import execute_order
from app.trading.portfolio import PortfolioView, build_portfolio
from app.trading.risk import RiskError

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderResult)
def place_order(
    request: OrderRequest,
    market: MarketKind = MarketKind.crypto,
    session: Session = Depends(get_session),
) -> OrderResult:
    try:
        return execute_order(request, market=market, session=session)
    except RiskError as exc:
        raise HTTPException(status_code=422, detail=f"Risk check failed: {exc}")
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"{type(exc).__name__}: {exc}")


@router.get("", response_model=list[OrderRecord])
def list_orders(session: Session = Depends(get_session)) -> list[OrderRecord]:
    return list(session.exec(select(OrderRecord).order_by(OrderRecord.id.desc())).all())


@router.get("/portfolio", response_model=PortfolioView)
def portfolio(market: MarketKind = MarketKind.crypto) -> PortfolioView:
    try:
        return build_portfolio(get_broker(market))
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))


@router.post("/paper/reset")
def reset_paper(market: MarketKind = MarketKind.crypto) -> dict[str, bool]:
    """Wipe the persisted paper-trading account/positions for a market."""
    reset_paper_account(market)
    return {"reset": True}
