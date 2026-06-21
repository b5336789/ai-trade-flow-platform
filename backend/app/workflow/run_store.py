"""Persist workflow runs + per-signal node traces (unified across backtest and live/paper)."""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.models import WorkflowRun, WorkflowSignal
from app.workflow.engine import _summarize
from app.workflow.schema import NodeType, WorkflowGraph


def _predecessors(graph: WorkflowGraph) -> dict[str, list[str]]:
    preds: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    for e in graph.edges:
        preds[e.target].append(e.source)
    return preds


def order_node_ancestors(graph: WorkflowGraph, order_node_id: str) -> list[str]:
    """All transitive predecessors of an order node, returned in topological (source-first) order."""
    preds = _predecessors(graph)
    seen: set[str] = set()
    stack = list(preds.get(order_node_id, []))
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        stack.extend(preds.get(nid, []))
    # topological-ish: keep graph node declaration order among the ancestor set
    return [n.id for n in graph.nodes if n.id in seen]


def build_trace(graph: WorkflowGraph, order_node_id: str, node_outputs: dict[str, Any]) -> list[dict]:
    by_id = {n.id: n for n in graph.nodes}
    trace: list[dict] = []
    for nid in order_node_ancestors(graph, order_node_id):
        node = by_id[nid]
        trace.append(
            {"node_id": nid, "type": node.type.value, "summary": _summarize(node_outputs.get(nid))}
        )
    return trace


def resolve_order_symbol(graph: WorkflowGraph, order_node_id: str) -> str:
    by_id = {n.id: n for n in graph.nodes}
    own = by_id[order_node_id].params.get("symbol")
    if own:
        return str(own)
    symbols = {
        by_id[nid].params.get("symbol")
        for nid in order_node_ancestors(graph, order_node_id)
        if by_id[nid].type == NodeType.data_source and by_id[nid].params.get("symbol")
    }
    if len(symbols) != 1:
        raise ValueError(
            f"order node '{order_node_id}' must resolve to exactly one symbol "
            f"(found {sorted(s for s in symbols if s)}); set its 'symbol' param"
        )
    return str(next(iter(symbols)))


def persist_workflow_run(
    session: Session,
    *,
    run_id: str,
    kind: str,
    graph: WorkflowGraph,
    market: str,
    symbols: list[str],
    timeframe: str,
    starting_cash: float | None,
    params: dict,
    metrics: dict | None,
    equity_curve: list | None,
    trades: list | None,
    status: str,
    signals: list[dict],
) -> int:
    run = WorkflowRun(
        run_id=run_id,
        kind=kind,
        graph_json=graph.model_dump(mode="json"),
        market=market,
        symbols=symbols,
        timeframe=timeframe,
        starting_cash=starting_cash,
        params_json=params,
        metrics_json=metrics,
        equity_curve_json=equity_curve,
        trades_json=trades,
        status=status,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    for sig in signals:
        session.add(
            WorkflowSignal(
                run_id=run.id,
                order_node_id=sig["order_node_id"],
                symbol=sig["symbol"],
                timestamp=sig["timestamp"],
                bar_index=sig.get("bar_index"),
                action=sig["action"],
                confidence=sig.get("confidence", 0.5),
                price=sig.get("price", 0.0),
                trace_json=sig.get("trace", []),
            )
        )
    session.commit()
    return run.id
