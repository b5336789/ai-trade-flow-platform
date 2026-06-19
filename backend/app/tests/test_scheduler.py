"""Tests for workflow scheduling (no real timing — job body + registration tested directly)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.db import engine
from app.models import RunLog, Schedule, Workflow
from app.scheduler import service
from app.workflow.schema import NodeConfig, NodeType, WorkflowGraph


def _make_logger_workflow(session: Session) -> Workflow:
    graph = WorkflowGraph(nodes=[NodeConfig(id="l", type=NodeType.logger)], edges=[])
    wf = Workflow(name="sched-test", graph=graph.model_dump(mode="json"))
    session.add(wf)
    session.commit()
    session.refresh(wf)
    return wf


def _make_tw_stock_workflow(session: Session) -> Workflow:
    graph = WorkflowGraph(
        nodes=[NodeConfig(id="ds", type=NodeType.data_source, params={"symbol": "2330", "market": "tw_stock"})],
        edges=[],
    )
    wf = Workflow(name="sched-tw", graph=graph.model_dump(mode="json"))
    session.add(wf)
    session.commit()
    session.refresh(wf)
    return wf


def _freeze_clock(monkeypatch, frozen: datetime) -> None:
    """Pin ``service``'s wall clock so triggers fire at an explicit time (no freezegun)."""

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen if tz is None else frozen.astimezone(tz)

    monkeypatch.setattr(service, "datetime", _FrozenDatetime)


def test_run_scheduled_workflow_writes_runlog_and_status():
    with Session(engine) as session:
        wf = _make_logger_workflow(session)
        schedule = Schedule(workflow_id=wf.id, interval_seconds=3600)
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
        schedule_id = schedule.id
        before = len(session.exec(select(RunLog).where(RunLog.workflow_id == wf.id)).all())

    service.run_scheduled_workflow(schedule_id)

    with Session(engine) as session:
        after = session.exec(select(RunLog).where(RunLog.workflow_id == wf.id)).all()
        assert len(after) == before + 1
        assert after[-1].status == "ok"
        refreshed = session.get(Schedule, schedule_id)
        assert refreshed.last_status == "ok"
        assert refreshed.last_run_at is not None


def test_disabled_schedule_is_skipped():
    with Session(engine) as session:
        wf = _make_logger_workflow(session)
        schedule = Schedule(workflow_id=wf.id, interval_seconds=3600, enabled=False)
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
        sid = schedule.id

    service.run_scheduled_workflow(sid)  # should no-op

    with Session(engine) as session:
        assert session.get(Schedule, sid).last_run_at is None


def test_add_and_remove_job():
    with Session(engine) as session:
        wf = _make_logger_workflow(session)
        schedule = Schedule(workflow_id=wf.id, interval_seconds=3600)
        session.add(schedule)
        session.commit()
        session.refresh(schedule)

    service.add_job(schedule)
    assert service.get_scheduler().get_job(service._job_id(schedule.id)) is not None
    service.remove_job(schedule.id)
    assert service.get_scheduler().get_job(service._job_id(schedule.id)) is None


def test_tw_schedule_skipped_when_market_closed(monkeypatch):
    # 03:00 Asia/Taipei == 19:00 prior-day UTC: 台股 is closed -> SKIP, not error (M1.4).
    frozen = datetime(2026, 6, 15, 19, 0, tzinfo=timezone.utc)  # Mon 03:00 Taipei
    _freeze_clock(monkeypatch, frozen)
    with Session(engine) as session:
        wf = _make_tw_stock_workflow(session)
        schedule = Schedule(workflow_id=wf.id, interval_seconds=3600, respect_market_hours=True)
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
        sid = schedule.id
        before = len(session.exec(select(RunLog).where(RunLog.workflow_id == wf.id)).all())

    service.run_scheduled_workflow(sid)

    with Session(engine) as session:
        refreshed = session.get(Schedule, sid)
        assert refreshed.last_status == "skipped: market closed"
        assert refreshed.last_run_at is not None
        after = len(session.exec(select(RunLog).where(RunLog.workflow_id == wf.id)).all())
        assert after == before  # skipped runs write no RunLog


def test_tw_schedule_runs_during_open_hours(monkeypatch):
    # 10:30 Asia/Taipei == 02:30 UTC, a weekday inside the session -> runs normally.
    frozen = datetime(2026, 6, 16, 2, 30, tzinfo=timezone.utc)  # Tue 10:30 Taipei
    _freeze_clock(monkeypatch, frozen)
    with Session(engine) as session:
        wf = _make_tw_stock_workflow(session)
        schedule = Schedule(workflow_id=wf.id, interval_seconds=3600, respect_market_hours=True)
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
        sid = schedule.id

    service.run_scheduled_workflow(sid)

    with Session(engine) as session:
        # Market is open so the gate passes; status reflects the actual workflow run (not skipped).
        assert session.get(Schedule, sid).last_status != "skipped: market closed"


def test_market_hours_gate_disabled_runs_anytime(monkeypatch):
    # Same closed-market time, but respect_market_hours=False -> the gate is bypassed.
    frozen = datetime(2026, 6, 15, 19, 0, tzinfo=timezone.utc)  # Mon 03:00 Taipei
    _freeze_clock(monkeypatch, frozen)
    with Session(engine) as session:
        wf = _make_tw_stock_workflow(session)
        schedule = Schedule(workflow_id=wf.id, interval_seconds=3600, respect_market_hours=False)
        session.add(schedule)
        session.commit()
        session.refresh(schedule)
        sid = schedule.id

    service.run_scheduled_workflow(sid)

    with Session(engine) as session:
        assert session.get(Schedule, sid).last_status != "skipped: market closed"


def test_add_job_uses_cron_trigger_when_provided():
    from apscheduler.triggers.cron import CronTrigger

    with Session(engine) as session:
        wf = _make_logger_workflow(session)
        schedule = Schedule(workflow_id=wf.id, interval_seconds=3600, cron="0 9 * * 1-5")
        session.add(schedule)
        session.commit()
        session.refresh(schedule)

    service.add_job(schedule)
    job = service.get_scheduler().get_job(service._job_id(schedule.id))
    assert isinstance(job.trigger, CronTrigger)
    service.remove_job(schedule.id)
