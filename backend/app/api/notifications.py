"""Notification feed endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models import Notification
from app.notifications.service import notify

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[Notification])
def list_notifications(
    limit: int = Query(20, ge=1, le=100), session: Session = Depends(get_session)
) -> list[Notification]:
    return list(
        session.exec(select(Notification).order_by(Notification.id.desc()).limit(limit)).all()
    )


@router.post("/test", response_model=Notification)
def test_notification(session: Session = Depends(get_session)) -> Notification:
    return notify(session, "Test notification", "Notifications are working.", level="info")
