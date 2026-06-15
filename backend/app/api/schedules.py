"""Schedule CRUD — attach intervals to saved workflows so they run automatically."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.db import get_session
from app.models import Schedule, Workflow
from app.scheduler.service import add_job, remove_job

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


class ScheduleCreate(BaseModel):
    workflow_id: int
    interval_seconds: int = Field(ge=5)  # floor to avoid hammering exchanges
    enabled: bool = True


@router.post("", response_model=Schedule)
def create_schedule(payload: ScheduleCreate, session: Session = Depends(get_session)) -> Schedule:
    if session.get(Workflow, payload.workflow_id) is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    schedule = Schedule(
        workflow_id=payload.workflow_id,
        interval_seconds=payload.interval_seconds,
        enabled=payload.enabled,
    )
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    if schedule.enabled:
        add_job(schedule)
    return schedule


@router.get("", response_model=list[Schedule])
def list_schedules(session: Session = Depends(get_session)) -> list[Schedule]:
    return list(session.exec(select(Schedule).order_by(Schedule.id.desc())).all())


@router.post("/{schedule_id}/toggle", response_model=Schedule)
def toggle_schedule(schedule_id: int, session: Session = Depends(get_session)) -> Schedule:
    schedule = session.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="schedule not found")
    schedule.enabled = not schedule.enabled
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    if schedule.enabled:
        add_job(schedule)
    else:
        remove_job(schedule_id)
    return schedule


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, session: Session = Depends(get_session)) -> dict[str, bool]:
    schedule = session.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="schedule not found")
    remove_job(schedule_id)
    session.delete(schedule)
    session.commit()
    return {"deleted": True}
