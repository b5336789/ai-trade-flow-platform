"""Workflow scheduling on top of APScheduler.

A ``Schedule`` row maps a saved workflow to an interval; an APScheduler job fires it, runs the
workflow via the shared engine, writes a RunLog and updates the schedule's last status.
"""

from __future__ import annotations

from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select

from app.db import engine
from app.models import RunLog, Schedule, Workflow
from app.workflow.engine import run_workflow
from app.workflow.schema import WorkflowGraph

_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def _job_id(schedule_id: int) -> str:
    return f"schedule-{schedule_id}"


def run_scheduled_workflow(schedule_id: int) -> None:
    """Job body: load the schedule's workflow, run it, persist results. Fail loud into RunLog."""
    with Session(engine) as session:
        schedule = session.get(Schedule, schedule_id)
        if schedule is None or not schedule.enabled:
            return
        workflow = session.get(Workflow, schedule.workflow_id)
        if workflow is None:
            schedule.last_status = "error: workflow missing"
            schedule.last_run_at = datetime.now(timezone.utc)
            session.add(schedule)
            session.commit()
            return

        graph = WorkflowGraph.model_validate(workflow.graph)
        result = run_workflow(graph, session=session)
        session.add(
            RunLog(workflow_id=workflow.id, status=result.status, detail=result.model_dump(mode="json"))
        )
        schedule.last_status = result.status if result.status == "ok" else f"error: {result.error}"
        schedule.last_run_at = datetime.now(timezone.utc)
        session.add(schedule)
        session.commit()


def add_job(schedule: Schedule) -> None:
    get_scheduler().add_job(
        run_scheduled_workflow,
        "interval",
        seconds=schedule.interval_seconds,
        args=[schedule.id],
        id=_job_id(schedule.id),
        replace_existing=True,
    )


def remove_job(schedule_id: int) -> None:
    scheduler = get_scheduler()
    if scheduler.get_job(_job_id(schedule_id)) is not None:
        scheduler.remove_job(_job_id(schedule_id))


def _restore_enabled_jobs() -> None:
    with Session(engine) as session:
        for schedule in session.exec(select(Schedule).where(Schedule.enabled == True)).all():  # noqa: E712
            add_job(schedule)


def start_scheduler() -> None:
    """Start (or restart) the scheduler and restore enabled jobs from the DB."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return
    _scheduler = BackgroundScheduler()
    _restore_enabled_jobs()
    _scheduler.start()


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
