"""Workflow graph schema (node-based, mirrors the React Flow editor on the frontend)."""

from __future__ import annotations

import enum

from pydantic import BaseModel, Field


class NodeType(str, enum.Enum):
    data_source = "data_source"  # fetch OHLCV -> candles
    strategy = "strategy"        # indicator strategy -> Signal
    ai_signal = "ai_signal"      # LLM -> Signal
    order = "order"              # Signal -> OrderResult (paper/live)
    logger = "logger"            # pass-through, records to run log


class NodeConfig(BaseModel):
    id: str
    type: NodeType
    params: dict = Field(default_factory=dict)


class Edge(BaseModel):
    source: str  # source node id
    target: str  # target node id


class WorkflowGraph(BaseModel):
    nodes: list[NodeConfig]
    edges: list[Edge] = Field(default_factory=list)


class StepResult(BaseModel):
    node_id: str
    type: NodeType
    summary: dict


class RunResult(BaseModel):
    status: str  # "ok" | "error"
    steps: list[StepResult] = Field(default_factory=list)
    orders: list[dict] = Field(default_factory=list)
    error: str | None = None
