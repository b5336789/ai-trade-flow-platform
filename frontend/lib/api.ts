// Typed client for the backend API. Base URL from env (defaults to local backend).

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type SignalAction = "buy" | "sell" | "hold";

export interface Signal {
  action: SignalAction;
  confidence: number;
  reason: string;
  source: string;
}

export interface OrderResult {
  id: string;
  symbol: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  status: string;
  mode: string;
  broker: string;
  timestamp: string;
}

export interface PositionView {
  symbol: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  price_source: string;
}

export interface PortfolioView {
  cash: number;
  positions: PositionView[];
  positions_value: number;
  equity: number;
}

export interface AppConfig {
  trading_mode: string;
  markets: string[];
  implemented_markets: string[];
  ai_model: string;
}

// Workflow graph types (mirror backend app/workflow/schema.py)
export type NodeType = "data_source" | "strategy" | "ai_signal" | "order" | "logger";

export interface GraphNode {
  id: string;
  type: NodeType;
  params: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
}

export interface WorkflowGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface RunResult {
  status: string;
  steps: { node_id: string; type: NodeType; summary: Record<string, unknown> }[];
  orders: OrderResult[];
  error: string | null;
}

export interface Workflow {
  id: number;
  name: string;
  graph: WorkflowGraph;
  created_at: string;
  updated_at: string;
}

export interface Schedule {
  id: number;
  workflow_id: number;
  interval_seconds: number;
  enabled: boolean;
  last_run_at: string | null;
  last_status: string | null;
  created_at: string;
}

export interface EquityPoint {
  timestamp: string;
  equity: number;
}

export interface BacktestResult {
  starting_cash: number;
  final_equity: number;
  total_return_pct: number;
  buy_hold_return_pct: number;
  num_trades: number;
  wins: number;
  win_rate: number;
  max_drawdown_pct: number;
  equity_curve: EquityPoint[];
}

export interface BacktestRequest {
  symbol: string;
  market?: string;
  timeframe?: string;
  limit?: number;
  strategy: string;
  params?: Record<string, unknown>;
  starting_cash?: number;
  position_fraction?: number;
}

export interface CompareRow {
  strategy: string;
  total_return_pct: number;
  buy_hold_return_pct: number;
  num_trades: number;
  win_rate: number;
  max_drawdown_pct: number;
  error: string | null;
}

export interface CompareRequest {
  symbol: string;
  market?: string;
  timeframe?: string;
  limit?: number;
  strategies?: string[];
  starting_cash?: number;
  position_fraction?: number;
}

export interface OptimizeRow {
  params: Record<string, number>;
  total_return_pct: number;
  num_trades: number;
  win_rate: number;
  max_drawdown_pct: number;
  error: string | null;
}

export interface OptimizeRequest {
  symbol: string;
  market?: string;
  timeframe?: string;
  limit?: number;
  strategy: string;
  param_grid: Record<string, number[]>;
  metric?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* keep statusText */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  config: () => request<AppConfig>("/api/config"),
  ohlcv: (symbol: string, timeframe = "1h", limit = 100, market = "crypto") =>
    request<Candle[]>(
      `/api/markets/ohlcv?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&limit=${limit}&market=${market}`,
    ),
  aiSignal: (symbol: string, market = "crypto", timeframe = "1h", limit = 100) =>
    request<Signal>("/api/ai/signal", {
      method: "POST",
      body: JSON.stringify({ symbol, market, timeframe, limit }),
    }),
  portfolio: (market = "crypto") => request<PortfolioView>(`/api/orders/portfolio?market=${market}`),
  orders: () => request<OrderResult[]>("/api/orders"),
  runWorkflow: (graph: WorkflowGraph) =>
    request<RunResult>("/api/workflows/run", {
      method: "POST",
      body: JSON.stringify(graph),
    }),
  strategies: () => request<{ strategies: string[] }>("/api/backtest/strategies"),
  backtest: (req: BacktestRequest) =>
    request<BacktestResult>("/api/backtest", { method: "POST", body: JSON.stringify(req) }),
  compareStrategies: (req: CompareRequest) =>
    request<CompareRow[]>("/api/backtest/compare", { method: "POST", body: JSON.stringify(req) }),
  optimize: (req: OptimizeRequest) =>
    request<OptimizeRow[]>("/api/backtest/optimize", { method: "POST", body: JSON.stringify(req) }),
  createWorkflow: (name: string, graph: WorkflowGraph) =>
    request<Workflow>("/api/workflows", { method: "POST", body: JSON.stringify({ name, graph }) }),
  listWorkflows: () => request<Workflow[]>("/api/workflows"),
  listSchedules: () => request<Schedule[]>("/api/schedules"),
  createSchedule: (workflow_id: number, interval_seconds: number) =>
    request<Schedule>("/api/schedules", {
      method: "POST",
      body: JSON.stringify({ workflow_id, interval_seconds }),
    }),
  toggleSchedule: (id: number) =>
    request<Schedule>(`/api/schedules/${id}/toggle`, { method: "POST" }),
  deleteSchedule: (id: number) =>
    request<{ deleted: boolean }>(`/api/schedules/${id}`, { method: "DELETE" }),
};
