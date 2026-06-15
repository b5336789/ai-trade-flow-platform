"""Tests for workflow scheduling (no real timing — job body + registration tested directly)."""

from __future__ import annotations

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
