"""Workflow CRUD + execution endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.db import get_session
from app.models import RunLog, Workflow
from app.workflow.engine import run_workflow
from app.workflow.schema import RunResult, WorkflowGraph

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class WorkflowCreate(BaseModel):
    name: str
    graph: WorkflowGraph


@router.post("", response_model=Workflow)
def create_workflow(payload: WorkflowCreate, session: Session = Depends(get_session)) -> Workflow:
    wf = Workflow(name=payload.name, graph=payload.graph.model_dump(mode="json"))
    session.add(wf)
    session.commit()
    session.refresh(wf)
    return wf


@router.get("", response_model=list[Workflow])
def list_workflows(session: Session = Depends(get_session)) -> list[Workflow]:
    return list(session.exec(select(Workflow).order_by(Workflow.id.desc())).all())


@router.get("/{workflow_id}", response_model=Workflow)
def get_workflow(workflow_id: int, session: Session = Depends(get_session)) -> Workflow:
    wf = session.get(Workflow, workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    return wf


@router.put("/{workflow_id}", response_model=Workflow)
def update_workflow(
    workflow_id: int, payload: WorkflowCreate, session: Session = Depends(get_session)
) -> Workflow:
    wf = session.get(Workflow, workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    wf.name = payload.name
    wf.graph = payload.graph.model_dump(mode="json")
    wf.updated_at = datetime.now(timezone.utc)
    session.add(wf)
    session.commit()
    session.refresh(wf)
    return wf


@router.post("/run", response_model=RunResult)
def run_ad_hoc(graph: WorkflowGraph, session: Session = Depends(get_session)) -> RunResult:
    """Run a graph without persisting the workflow (handy for the editor's 'Run' button)."""
    result = run_workflow(graph, session=session)
    session.add(RunLog(workflow_id=None, status=result.status, detail=result.model_dump(mode="json")))
    session.commit()
    return result


@router.post("/{workflow_id}/run", response_model=RunResult)
def run_saved(workflow_id: int, session: Session = Depends(get_session)) -> RunResult:
    wf = session.get(Workflow, workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    graph = WorkflowGraph.model_validate(wf.graph)
    result = run_workflow(graph, session=session)
    session.add(
        RunLog(workflow_id=workflow_id, status=result.status, detail=result.model_dump(mode="json"))
    )
    session.commit()
    return result
