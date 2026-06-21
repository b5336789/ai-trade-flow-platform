"""Workflow CRUD + execution endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import settings
from app.db import get_session
from app.models import RunLog, Workflow, WorkflowRun, WorkflowSignal
from app.schemas import SignalAction
from app.workflow.engine import run_workflow
from app.workflow.nodes import RunContext
from app.workflow.run_store import build_trace, persist_workflow_run, resolve_order_symbol
from app.workflow.schema import NodeType, RunResult, WorkflowGraph

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


@router.get("/runs", response_model=list[WorkflowRun])
def list_runs(kind: str | None = None, limit: int = 50, session: Session = Depends(get_session)) -> list[WorkflowRun]:
    q = select(WorkflowRun).order_by(WorkflowRun.id.desc()).limit(limit)
    if kind:
        q = q.where(WorkflowRun.kind == kind)
    return list(session.exec(q).all())


@router.get("/runs/{run_id}", response_model=WorkflowRun)
def get_run(run_id: int, session: Session = Depends(get_session)) -> WorkflowRun:
    run = session.get(WorkflowRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/runs/{run_id}/signals", response_model=list[WorkflowSignal])
def get_run_signals(run_id: int, symbol: str | None = None, session: Session = Depends(get_session)) -> list[WorkflowSignal]:
    q = select(WorkflowSignal).where(WorkflowSignal.run_id == run_id).order_by(WorkflowSignal.bar_index)
    if symbol:
        q = q.where(WorkflowSignal.symbol == symbol)
    return list(session.exec(q).all())


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


def _persist_live_run(session, graph, workflow_id, ctx, result):
    """Record a live/paper workflow execution as a WorkflowRun + per-order-node signals."""
    order_nodes = [n for n in graph.nodes if n.type == NodeType.order]
    signals = []
    symbols = []
    for n in order_nodes:
        try:
            sym = resolve_order_symbol(graph, n.id)
        except ValueError:
            sym = n.params.get("symbol", "")
        symbols.append(sym)
        out = ctx.node_outputs.get(n.id)
        # out is an OrderResult when an order was placed, else None
        action = "hold"
        price = 0.0
        if out is not None and hasattr(out, "side"):
            action = SignalAction.buy.value if out.side.value == "buy" else SignalAction.sell.value
            price = out.price
        signals.append(
            {
                "order_node_id": n.id,
                "symbol": sym,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "bar_index": None,
                "action": action,
                "confidence": 0.5,
                "price": price,
                "trace_json": build_trace(graph, n.id, ctx.node_outputs),
            }
        )
    persist_workflow_run(
        session,
        run_id=ctx.run_id,
        kind=settings.trading_mode.value if hasattr(settings.trading_mode, "value") else str(settings.trading_mode),
        graph=graph,
        market="crypto",
        symbols=sorted(set(s for s in symbols if s)),
        timeframe="",
        starting_cash=None,
        params={},
        metrics=None,
        equity_curve=None,
        trades=None,
        status=result.status,
        signals=signals,
    )


@router.post("/run", response_model=RunResult)
def run_ad_hoc(graph: WorkflowGraph, session: Session = Depends(get_session)) -> RunResult:
    """Run a graph without persisting the workflow (handy for the editor's 'Run' button)."""
    ctx = RunContext(session=session)
    result = run_workflow(graph, session=session, ctx=ctx)
    session.add(RunLog(workflow_id=None, status=result.status, detail=result.model_dump(mode="json")))
    session.commit()
    if result.status == "ok":
        try:
            _persist_live_run(session, graph, None, ctx, result)
        except Exception:
            session.rollback()
            logging.getLogger(__name__).exception(
                "workflow run executed and logged, but history persistence failed"
            )
    return result


@router.post("/{workflow_id}/run", response_model=RunResult)
def run_saved(workflow_id: int, session: Session = Depends(get_session)) -> RunResult:
    wf = session.get(Workflow, workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="workflow not found")
    graph = WorkflowGraph.model_validate(wf.graph)
    ctx = RunContext(session=session)
    result = run_workflow(graph, session=session, ctx=ctx)
    session.add(
        RunLog(workflow_id=workflow_id, status=result.status, detail=result.model_dump(mode="json"))
    )
    session.commit()
    if result.status == "ok":
        try:
            _persist_live_run(session, graph, workflow_id, ctx, result)
        except Exception:
            session.rollback()
            logging.getLogger(__name__).exception(
                "workflow run executed and logged, but history persistence failed"
            )
    return result
