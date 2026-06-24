"""Tests for notifications: in-app feed, webhook dispatch, and order-fill alerts."""

from __future__ import annotations

from sqlmodel import Session, select

from app.brokers import registry
from app.brokers.paper import PaperBroker
from app.db import engine
from app.models import Notification
from app.notifications import service
from app.schemas import MarketKind, OrderRequest, OrderSide
from app.tests.helpers import StubBroker
from app.trading.execution import execute_order


def test_record_notification_persists():
    with Session(engine) as session:
        before = len(session.exec(select(Notification)).all())
        service.record_notification(session, "hello", "world", level="info")
        after = session.exec(select(Notification)).all()
        assert len(after) == before + 1
        assert after[-1].title == "hello"


def test_dispatch_webhook_noop_without_url(monkeypatch):
    monkeypatch.setattr(service.settings, "notify_webhook_url", "")
    assert service.dispatch_webhook("t", "m") is False


def test_dispatch_webhook_noop_when_disabled_sentinel(monkeypatch):
    monkeypatch.setattr(service.settings, "notify_webhook_url", "__disabled__")
    assert service.dispatch_webhook("t", "m") is False


def test_dispatch_webhook_posts_when_configured(monkeypatch):
    calls = {}
    monkeypatch.setattr(service.settings, "notify_webhook_url", "http://example.test/hook")
    monkeypatch.setattr(service.httpx, "post", lambda url, **kw: calls.update(url=url, kw=kw))
    assert service.dispatch_webhook("t", "m", meta={"a": 1}) is True
    assert calls["url"] == "http://example.test/hook"
    assert calls["kw"]["json"]["title"] == "t"


def test_dispatch_webhook_swallows_errors(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(service.settings, "notify_webhook_url", "http://example.test/hook")
    monkeypatch.setattr(service.httpx, "post", boom)
    assert service.dispatch_webhook("t", "m") is False  # does not raise


def test_notify_logs_event_for_cloudwatch(caplog):
    with Session(engine) as session:
        service.notify(
            session,
            "Max daily loss breached - trading halted",
            "Entries blocked; exits allowed.",
            level="error",
            meta={"gate": "max_daily_loss"},
        )

    assert "notification_event" in caplog.text
    assert "Max daily loss breached - trading halted" in caplog.text
    assert "max_daily_loss" in caplog.text


def test_order_fill_creates_notification():
    registry.reset_paper_brokers()
    registry._paper_cache[MarketKind.crypto] = PaperBroker(
        data_provider=StubBroker({"BTC/USDT": 100.0}), starting_cash=10_000.0
    )
    with Session(engine) as session:
        before = len(session.exec(select(Notification)).all())
        execute_order(
            OrderRequest(symbol="BTC/USDT", side=OrderSide.buy, quantity=2),
            market=MarketKind.crypto,
            session=session,
        )
        rows = session.exec(select(Notification).order_by(Notification.id.desc())).all()
        assert len(rows) == before + 1
        assert "BTC/USDT" in rows[0].title
        assert rows[0].level == "success"
    registry.reset_paper_brokers()
