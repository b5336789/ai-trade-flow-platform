"""Topological execution of a workflow graph."""

from __future__ import annotations

from typing import Any

from app.schemas import Candle, OrderResult, Signal
from app.workflow.nodes import RunContext, get_runner
from app.workflow.schema import (
    NodeConfig,
    NodeType,
    RunResult,
    StepResult,
    WorkflowGraph,
)


def _topological_order(graph: WorkflowGraph) -> list[NodeConfig]:
    by_id = {n.id: n for n in graph.nodes}
    if len(by_id) != len(graph.nodes):
        raise ValueError("workflow has duplicate node ids")

    indegree = {nid: 0 for nid in by_id}
    adjacency: dict[str, list[str]] = {nid: [] for nid in by_id}
    for edge in graph.edges:
        if edge.source not in by_id or edge.target not in by_id:
            raise ValueError(f"edge references unknown node: {edge.source}->{edge.target}")
        adjacency[edge.source].append(edge.target)
        indegree[edge.target] += 1

    queue = [nid for nid, d in indegree.items() if d == 0]
    order: list[str] = []
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for nxt in adjacency[nid]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if len(order) != len(by_id):
        raise ValueError("workflow graph has a cycle")
    return [by_id[nid] for nid in order]


def _summarize(output: Any) -> dict:
    if output is None:
        return {"output": None}
    if isinstance(output, list) and output and isinstance(output[0], Candle):
        return {"candles": len(output), "last_close": output[-1].close}
    if isinstance(output, Signal):
        return {"signal": output.model_dump(mode="json")}
    if isinstance(output, OrderResult):
        return {"order": output.model_dump(mode="json")}
    return {"output": str(output)}


def run_workflow(
    graph: WorkflowGraph, session=None, run_id: str | None = None, ctx: RunContext | None = None
) -> RunResult:
    """Execute a graph; on any node failure the run stops and reports the error (fail loud).

    ``run_id`` identifies this logical run; order nodes fold it into a deterministic
    client_order_id, so re-running with the SAME run_id is idempotent (M0.5). Defaults to a
    fresh id per call.
    """
    if ctx is None:
        ctx = RunContext(session=session, run_id=run_id)
    outputs: dict[str, Any] = {}
    steps: list[StepResult] = []
    orders: list[dict] = []

    try:
        order = _topological_order(graph)
    except ValueError as exc:
        return RunResult(status="error", error=str(exc))

    predecessors: dict[str, list[str]] = {n.id: [] for n in graph.nodes}
    for edge in graph.edges:
        predecessors[edge.target].append(edge.source)

    for node in order:
        inputs = [outputs[src] for src in predecessors[node.id]]
        try:
            result = get_runner(node.type)(node, inputs, ctx)
        except Exception as exc:  # fail loud: capture which node broke and why
            steps.append(
                StepResult(node_id=node.id, type=node.type, summary={"error": f"{type(exc).__name__}: {exc}"})
            )
            return RunResult(
                status="error",
                steps=steps,
                orders=orders,
                error=f"node '{node.id}' ({node.type.value}) failed: {exc}",
            )
        outputs[node.id] = result
        ctx.node_outputs[node.id] = result
        summary = _summarize(result)
        steps.append(StepResult(node_id=node.id, type=node.type, summary=summary))
        # Collect orders only from order nodes (logger/pass-through can re-surface the same result).
        if node.type == NodeType.order and isinstance(result, OrderResult):
            orders.append(result.model_dump(mode="json"))

    return RunResult(status="ok", steps=steps, orders=orders)
