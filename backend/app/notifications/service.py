"""Notifications: persist an in-app feed and (optionally) POST to an outbound webhook.

Used to alert on order fills and signals. Webhook delivery is best-effort — a failed external
POST must never break trading — but the in-app record is always written.
"""

from __future__ import annotations

import httpx
from sqlmodel import Session

from app.config import settings
from app.models import Notification


def record_notification(
    session: Session,
    title: str,
    message: str = "",
    level: str = "info",
    meta: dict | None = None,
) -> Notification:
    notification = Notification(title=title, message=message, level=level, meta=meta or {})
    session.add(notification)
    session.commit()
    session.refresh(notification)
    return notification


def dispatch_webhook(title: str, message: str, level: str = "info", meta: dict | None = None) -> bool:
    """POST to the configured webhook. Returns True on success, False if unset or it failed."""
    url = settings.notify_webhook_url
    if not url:
        return False
    try:
        httpx.post(
            url,
            json={"title": title, "message": message, "level": level, "meta": meta or {}},
            timeout=5.0,
        )
        return True
    except Exception:
        # Best-effort: external delivery failures don't propagate into trading flow.
        return False


def notify(
    session: Session,
    title: str,
    message: str = "",
    level: str = "info",
    meta: dict | None = None,
) -> Notification:
    notification = record_notification(session, title, message, level, meta)
    dispatch_webhook(title, message, level, meta)
    return notification
