import type { NodeType } from "@/lib/api";

export type NodeCategory = "data" | "strategy" | "logic" | "order" | "output";

export interface ParamField {
  key: string;
  label: string;
  kind: "number" | "text" | "select";
  options?: string[];
  default: unknown;
}

export interface NodeMeta {
  category: NodeCategory;
  colorVar: string;
  title: string;
  hasInput: boolean;
  hasOutput: boolean;
  params: ParamField[];
  summaryKeys: string[];
}

export const CATEGORY_COLOR: Record<NodeCategory, string> = {
  data: "var(--c-data)",
  strategy: "var(--c-strat)",
  logic: "var(--c-logic)",
  order: "var(--c-order)",
  output: "var(--c-out)",
};

export const CATEGORY_LABEL: Record<NodeCategory, string> = {
  data: "資料 Data",
  strategy: "策略 Strategy",
  logic: "邏輯 Logic",
  order: "下單 Order",
  output: "輸出 Output",
};

const OPERATORS = [">", ">=", "<", "<=", "==", "!="];

export const NODE_CATALOG: Record<NodeType, NodeMeta> = {
  data_source: {
    category: "data", colorVar: CATEGORY_COLOR.data, title: "Data Source",
    hasInput: false, hasOutput: true,
    params: [
      { key: "symbol", label: "symbol", kind: "text", default: "BTC/USDT" },
      { key: "timeframe", label: "timeframe", kind: "text", default: "1h" },
      { key: "limit", label: "limit", kind: "number", default: 100 },
    ],
    summaryKeys: ["symbol", "timeframe"],
  },
  strategy: {
    category: "strategy", colorVar: CATEGORY_COLOR.strategy, title: "Strategy",
    hasInput: true, hasOutput: true,
    // strategy params beyond `name` are appended dynamically by the Inspector from STRATEGY_PARAMS[name].
    params: [{ key: "name", label: "name", kind: "select", options: [], default: "ma_cross" }],
    summaryKeys: ["name"],
  },
  ai_signal: {
    category: "strategy", colorVar: CATEGORY_COLOR.strategy, title: "AI Signal",
    hasInput: true, hasOutput: true,
    params: [{ key: "model", label: "model (optional)", kind: "text", default: "" }],
    summaryKeys: [],
  },
  risk_exit: {
    category: "order", colorVar: CATEGORY_COLOR.order, title: "Risk Exit (SL/TP)",
    hasInput: true, hasOutput: true,
    params: [
      { key: "stop_loss_pct", label: "stop_loss_pct", kind: "number", default: 5 },
      { key: "take_profit_pct", label: "take_profit_pct", kind: "number", default: 10 },
    ],
    summaryKeys: ["stop_loss_pct", "take_profit_pct"],
  },
  order: {
    category: "order", colorVar: CATEGORY_COLOR.order, title: "Order",
    hasInput: true, hasOutput: false,
    params: [{ key: "quantity", label: "quantity", kind: "number", default: 0.01 }],
    summaryKeys: ["quantity"],
  },
  logger: {
    category: "output", colorVar: CATEGORY_COLOR.output, title: "Logger",
    hasInput: true, hasOutput: false,
    params: [],
    summaryKeys: [],
  },
  condition: {
    category: "logic", colorVar: CATEGORY_COLOR.logic, title: "Condition",
    hasInput: true, hasOutput: true,
    params: [
      { key: "source", label: "source", kind: "text", default: "close" },
      { key: "operator", label: "operator", kind: "select", options: OPERATORS, default: ">" },
      { key: "value", label: "value", kind: "number", default: 0 },
    ],
    summaryKeys: ["source", "operator", "value"],
  },
  combine: {
    category: "logic", colorVar: CATEGORY_COLOR.logic, title: "Combine",
    hasInput: true, hasOutput: true,
    params: [{ key: "mode", label: "mode", kind: "select", options: ["AND", "OR", "weighted"], default: "AND" }],
    summaryKeys: ["mode"],
  },
  branch: {
    category: "logic", colorVar: CATEGORY_COLOR.logic, title: "Branch",
    hasInput: true, hasOutput: true,
    params: [
      { key: "source", label: "source", kind: "text", default: "close" },
      { key: "operator", label: "operator", kind: "select", options: OPERATORS, default: ">" },
      { key: "value", label: "value", kind: "number", default: 0 },
    ],
    summaryKeys: ["source", "operator", "value"],
  },
};

export function defaultParams(t: NodeType): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const f of NODE_CATALOG[t].params) out[f.key] = f.default;
  return out;
}

export function summaryText(t: NodeType, params: Record<string, unknown>): string {
  const keys = NODE_CATALOG[t].summaryKeys;
  if (keys.length === 0) return "";
  return keys.map((k) => params[k]).filter((v) => v !== undefined && v !== "").join(" ");
}
