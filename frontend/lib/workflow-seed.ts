import type { WorkflowGraph } from "@/lib/api";

export interface SeedStrategyInput {
  /** Saved-library strategy id, or null/undefined for a built-in by name. */
  strategyId?: number | null;
  /** Built-in strategy name (e.g. "ma_cross") when strategyId is absent. */
  strategyName?: string;
  symbol: string;
  market: string;
  timeframe: string;
  /** Order size; defaults to the order node's catalog default. */
  quantity?: number;
}

/**
 * Build a minimal runnable workflow: data_source -> strategy -> order.
 * Node `type`/`params` mirror backend app/workflow/schema.py + nodes.py so the
 * persisted graph runs without further editing. No global store: the caller
 * persists this via api.createWorkflow and navigates with the returned id.
 */
export function seedGraphFromStrategy(input: SeedStrategyInput): WorkflowGraph {
  const { strategyId, strategyName, symbol, market, timeframe, quantity } = input;

  const strategyParams: Record<string, unknown> =
    strategyId != null
      ? { strategy_id: strategyId }
      : { name: strategyName ?? "ma_cross" };

  return {
    nodes: [
      {
        id: "data",
        type: "data_source",
        params: { symbol, market, timeframe, limit: 500 },
      },
      { id: "strat", type: "strategy", params: strategyParams },
      { id: "order", type: "order", params: { quantity: quantity ?? 0.01 } },
    ],
    edges: [
      { source: "data", target: "strat" },
      { source: "strat", target: "order" },
    ],
  };
}
