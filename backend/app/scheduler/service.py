"""Workflow scheduling on top of APScheduler.

A ``Schedule`` row maps a saved workflow to an interval; an APScheduler job fires it, runs the
workflow via the shared engine, writes a RunLog and updates the schedule's last status.
"""

from __future__ import annotations

from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlmodel import Session, select

from app.db import engine
from app.marketdata.calendar import is_market_open
from app.models import RunLog, Schedule, Workflow
from app.schemas import MarketKind
from app.workflow.engine import run_workflow
from app.workflow.schema import NodeType, WorkflowGraph

_scheduler: BackgroundScheduler | None = None

# Don't let a slow/blocked tick fire stale instances: collapse missed runs into one and tolerate a
# small dispatch delay before declaring a misfire (M1.4).
_MISFIRE_GRACE_TIME = 30


def _market_for_graph(graph: WorkflowGraph) -> MarketKind:
    """A schedule's market = the market of its workflow's first data_source node.

    Chosen because the data_source node already carries ``params["market"]`` (defaulting to
    crypto, matching the workflow engine), so no new schedule field is needed and the gate
    follows whatever market the workflow actually trades.
    """
    for node in graph.nodes:
        if node.type == NodeType.data_source:
            return MarketKind(node.params.get("market", "crypto"))
    return MarketKind.crypto  # no data_source (e.g. logger-only) => treat as always-open


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def _job_id(schedule_id: int) -> str:
    return f"schedule-{schedule_id}"


def run_scheduled_workflow(schedule_id: int) -> None:
    """Job body: load the schedule's workflow, run it, persist results. Fail loud into RunLog."""
    now = datetime.now(timezone.utc)
    with Session(engine) as session:
        schedule = session.get(Schedule, schedule_id)
        if schedule is None or not schedule.enabled:
            return
        workflow = session.get(Workflow, schedule.workflow_id)
        if workflow is None:
            schedule.last_status = "error: workflow missing"
            schedule.last_run_at = now
            session.add(schedule)
            session.commit()
            return

        graph = WorkflowGraph.model_validate(workflow.graph)
        # Market-hours gate (M1.4): SKIP (not error) when the workflow's market is closed.
        if schedule.respect_market_hours and not is_market_open(_market_for_graph(graph), now):
            schedule.last_status = "skipped: market closed"
            schedule.last_run_at = now
            session.add(schedule)
            session.commit()
            return
        # Deterministic per scheduled tick: a misfire/retry of the SAME tick re-uses this run_id
        # (so order nodes' client_order_ids match and the duplicate fill is skipped), while the
        # next tick gets a fresh one. (M0.5)
        run_id = f"schedule-{schedule_id}-{int(now.timestamp())}"
        result = run_workflow(graph, session=session, run_id=run_id)
        session.add(
            RunLog(workflow_id=workflow.id, status=result.status, detail=result.model_dump(mode="json"))
        )
        schedule.last_status = result.status if result.status == "ok" else f"error: {result.error}"
        schedule.last_run_at = now
        session.add(schedule)
        session.commit()


def add_job(schedule: Schedule) -> None:
    # A cron expression (when set) overrides the interval trigger (M1.4).
    if schedule.cron:
        trigger, trigger_kwargs = CronTrigger.from_crontab(schedule.cron), {}
    else:
        trigger, trigger_kwargs = "interval", {"seconds": schedule.interval_seconds}
    get_scheduler().add_job(
        run_scheduled_workflow,
        trigger,
        args=[schedule.id],
        id=_job_id(schedule.id),
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=_MISFIRE_GRACE_TIME,
        **trigger_kwargs,
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
