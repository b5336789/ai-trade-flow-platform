// Typed client for the backend API. Base URL uses same-origin in production builds
// unless NEXT_PUBLIC_API_BASE_URL is explicitly set.
const DEFAULT_BASE = process.env.NODE_ENV === "production" ? "" : "http://localhost:8000";
const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? DEFAULT_BASE;
// M0.7: bearer token is intentionally exposed to the browser via NEXT_PUBLIC_*
// and is not a private server-side secret.
const API_TOKEN = process.env.NEXT_PUBLIC_API_TOKEN ?? "";

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Ticker {
  symbol: string;
  price: number;
  timestamp: string;
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
export type NodeType =
  | "data_source"
  | "strategy"
  | "ai_signal"
  | "risk_exit"
  | "order"
  | "logger"
  | "condition"
  | "combine"
  | "branch";

export interface GraphNode {
  id: string;
  type: NodeType;
  params: Record<string, unknown>;
  position?: { x: number; y: number } | null;
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

export interface Notification {
  id: number;
  level: string;
  title: string;
  message: string;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface EquityPoint {
  timestamp: string;
  equity: number;
}

export interface Trade {
  entry_time: string;
  exit_time: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  pnl: number; // net of costs
  gross_pnl: number;
  cost: number;
  return_pct: number;
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
  cagr: number;
  annualized_volatility: number;
  sharpe: number;
  sortino: number;
  calmar: number;
  profit_factor: number | null;
  avg_win: number;
  avg_loss: number;
  exposure_pct: number;
  max_consecutive_losses: number;
  turnover: number;
  trades: Trade[];
  equity_curve: EquityPoint[];
  assumptions: BacktestAssumptions | null;
}

export interface BacktestAssumptions {
  slippage_bps: number;
  cost_taker_bps: number;
  bars: number;
  num_trades: number;
  timeframe: string;
  market: string;
  annualization_basis: string;
  oos_selected: boolean;
  warnings: string[];
}

export interface BacktestRunDTO {
  id: number;
  symbol: string;
  market: string;
  timeframe: string;
  strategy: string;
  starting_cash: number;
  slippage_bps: number;
  bars: number;
  range_start: string;
  range_end: string;
  metrics_json: Record<string, number> | null;
  assumptions_json: BacktestAssumptions | null;
  created_at: string;
}

export interface BacktestRequest {
  symbol: string;
  market?: string;
  timeframe?: string;
  limit?: number;
  start?: string;
  end?: string;
  strategy: string;
  params?: Record<string, unknown>;
  starting_cash?: number;
  position_fraction?: number;
}

export interface CompareRow {
  strategy: string;
  total_return_pct: number;
  sharpe: number;
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
  start?: string;
  end?: string;
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
  // M0.4 split mode: in-sample vs out-of-sample, surfaced so overfitting is visible.
  is_return_pct?: number | null;
  oos_return_pct?: number | null;
  is_oos_gap_pct?: number | null;
  oos_sharpe?: number | null;
  oos_max_drawdown_pct?: number | null;
  oos_return_over_maxdd?: number | null;
  rank_score?: number | null;
}

export interface OptimizeRequest {
  symbol: string;
  market?: string;
  timeframe?: string;
  limit?: number;
  start?: string;
  end?: string;
  strategy: string;
  param_grid: Record<string, number[]>;
  metric?: string;
  // M0.4: rank by out-of-sample risk-adjusted metric instead of raw in-sample return.
  split?: boolean;
  oos_fraction?: number;
  rank_metric?: string;
}

export interface WalkForwardRequest {
  symbol: string;
  market?: string;
  timeframe?: string;
  limit?: number;
  start?: string;
  end?: string;
  strategy: string;
  param_grid: Record<string, number[]>;
  n_folds?: number;
  metric?: string; // "sharpe" | "sortino" | "calmar" | "return_over_maxdd"
  anchored?: boolean;
  max_combinations?: number;
}

export interface FoldResult {
  fold: number;
  best_params: Record<string, number>;
  train_start: number;
  train_end: number;
  test_start: number;
  test_end: number;
  train_size: number;
  test_size: number;
  is_metric: number;
  oos_metric: number;
  is_return_pct: number;
  oos_return_pct: number;
  oos_max_drawdown_pct: number;
  error: string | null;
}

export interface WalkForwardReport {
  strategy: string;
  metric: string;
  n_folds: number;
  anchored: boolean;
  folds: FoldResult[];
  aggregate_oos_metric: number;
  aggregate_oos_return_pct: number;
}

// Strategy Lab (策略室) — declarative StrategySpec mirrors backend app/strategies/spec.py.
// The condition trees (entry/exit) and indicators are passed through opaquely; the
// frontend only edits param defaults and displays the rendered Python.
export interface SpecParamDef {
  name: string;
  type: "int" | "float";
  default: number;
  min?: number | null;
  max?: number | null;
  step?: number | null;
}

export interface StrategySpec {
  indicators: unknown[];
  entry: unknown;
  exit: unknown;
  params: SpecParamDef[];
}

export interface DesignResponse {
  spec: StrategySpec;
  rendered_python: string;
  explanation: string;
}

export interface StrategyListItem {
  id: number;
  name: string;
  description: string;
  source: string;
  num_params: number;
}

export interface StrategyOut {
  id: number;
  name: string;
  description: string;
  source: string;
  spec: StrategySpec;
  rendered_python: string;
}

export interface SavedBacktestRequest {
  symbol: string;
  market?: string;
  timeframe?: string;
  limit?: number;
  start?: string;
  end?: string;
  param_overrides?: Record<string, number>;
  starting_cash?: number;
  position_fraction?: number;
}

export interface WorkflowSignalDTO {
  id: number;
  run_id: number;
  order_node_id: string;
  symbol: string;
  timestamp: string;
  bar_index: number | null;
  action: "buy" | "sell" | "hold";
  confidence: number;
  price: number;
  trace_json: { node_id: string; type: string; summary: Record<string, unknown> }[];
}

export interface WorkflowRunDTO {
  id: number;
  run_id: string;
  kind: "backtest" | "live" | "paper";
  workflow_id: number | null;
  market: string;
  symbols: string[];
  timeframe: string;
  starting_cash: number | null;
  metrics_json: Record<string, number> | null;
  equity_curve_json: { timestamp: string; equity: number }[] | null;
  trades_json: unknown[] | null;
  status: string;
  created_at: string;
}

export type WorkflowBacktestResponse = BacktestResult & {
  run_id: number;
  symbols: string[];
  signals: WorkflowSignalDTO[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (API_TOKEN) {
    headers.Authorization = `Bearer ${API_TOKEN}`;
  }
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string> | undefined) },
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
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export const api = {
  config: () => request<AppConfig>("/api/config"),
  ohlcv: (symbol: string, timeframe = "1h", limit = 100, market = "crypto", start?: string, end?: string) => {
    let url = `/api/markets/ohlcv?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}&limit=${limit}&market=${market}`;
    if (start && end) url += `&start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`;
    return request<Candle[]>(url);
  },
  ticker: (symbol: string, market = "crypto") =>
    request<Ticker>(
      `/api/markets/ticker?symbol=${encodeURIComponent(symbol)}&market=${market}`,
    ),
  aiSignal: (symbol: string, market = "crypto", timeframe = "1h", limit = 100) =>
    request<Signal>("/api/ai/signal", {
      method: "POST",
      body: JSON.stringify({ symbol, market, timeframe, limit }),
    }),
  portfolio: (market = "crypto") => request<PortfolioView>(`/api/orders/portfolio?market=${market}`),
  resetPaper: (market = "crypto") =>
    request<{ reset: boolean }>(`/api/orders/paper/reset?market=${market}`, { method: "POST" }),
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
  walkForward: (req: WalkForwardRequest) =>
    request<WalkForwardReport>("/api/backtest/walk-forward", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  listBacktestRuns: (limit = 50) =>
    request<BacktestRunDTO[]>(`/api/backtest/runs?limit=${limit}`),
  getBacktestRun: (id: number) => request<BacktestRunDTO>(`/api/backtest/runs/${id}`),
  createWorkflow: (name: string, graph: WorkflowGraph) =>
    request<Workflow>("/api/workflows", { method: "POST", body: JSON.stringify({ name, graph }) }),
  updateWorkflow: (id: number, name: string, graph: WorkflowGraph) =>
    request<Workflow>(`/api/workflows/${id}`, { method: "PUT", body: JSON.stringify({ name, graph }) }),
  getWorkflow: (id: number) => request<Workflow>(`/api/workflows/${id}`),
  listWorkflows: () => request<Workflow[]>("/api/workflows"),
  deleteWorkflow: (id: number) => request<void>(`/api/workflows/${id}`, { method: "DELETE" }),
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
  listNotifications: () => request<Notification[]>("/api/notifications"),
  testNotification: () => request<Notification>("/api/notifications/test", { method: "POST" }),
  importHistory: (market: string, symbol: string, csv: string) =>
    request<{ market: string; symbol: string; imported: number }>("/api/markets/import", {
      method: "POST",
      body: JSON.stringify({ market, symbol, csv }),
    }),
  // 策略室 — AI design + strategy library CRUD + per-strategy backtest.
  designStrategy: (message: string, prior_spec?: StrategySpec, model?: string) =>
    request<DesignResponse>("/api/strategies/design", {
      method: "POST",
      body: JSON.stringify({ message, prior_spec, model }),
    }),
  listSavedStrategies: () => request<StrategyListItem[]>("/api/strategies"),
  getSavedStrategy: (id: number) => request<StrategyOut>(`/api/strategies/${id}`),
  saveStrategy: (name: string, spec: StrategySpec, description = "") =>
    request<StrategyOut>("/api/strategies", {
      method: "POST",
      body: JSON.stringify({ name, description, spec }),
    }),
  deleteStrategy: (id: number) =>
    request<{ deleted: number }>(`/api/strategies/${id}`, { method: "DELETE" }),
  backtestSavedStrategy: (id: number, req: SavedBacktestRequest) =>
    request<BacktestResult>(`/api/strategies/${id}/backtest`, {
      method: "POST",
      body: JSON.stringify(req),
    }),
  runWorkflowBacktest: (body: {
    graph?: WorkflowGraph;
    workflow_id?: number;
    market?: string;
    timeframe?: string;
    limit?: number;
    starting_cash?: number;
  }) =>
    request<WorkflowBacktestResponse>("/api/backtest/workflow", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listWorkflowRuns: (params?: { kind?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.kind) q.set("kind", params.kind);
    if (params?.limit) q.set("limit", String(params.limit));
    return request<WorkflowRunDTO[]>(`/api/workflows/runs?${q.toString()}`);
  },
  getWorkflowRun: (runId: number) => request<WorkflowRunDTO>(`/api/workflows/runs/${runId}`),
  getWorkflowRunSignals: (runId: number, symbol?: string) =>
    request<WorkflowSignalDTO[]>(
      `/api/workflows/runs/${runId}/signals${symbol ? `?symbol=${encodeURIComponent(symbol)}` : ""}`,
    ),
};

export const MARKETS = [
  { value: "crypto", label: "加密貨幣 (Binance)" },
  { value: "tw_stock", label: "台股 (元大)" },
  { value: "us_stock", label: "美股 (元大複委託 / Firstrade)" },
];
