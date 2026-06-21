# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Part 1: Core Coding Rules

- **Think Before Coding**: State your assumptions clearly. Discuss trade-offs and ask clarifying questions instead of guessing.
- **Simplicity First**: Write the minimum code required to solve the immediate problem. Avoid speculative features or premature abstractions.
- **Surgical Changes**: Only modify code directly relevant to the task. Do not "clean up" adjacent code, styling, or comments.
- **Goal-Driven Execution**: Define what success looks like (e.g., write a test and make it pass). Let the AI iterate until verification.

## Part 2: Agent Orchestration Rules

- **Keep Deterministic Work out of AI**: Do not make Claude handle raw string formatting or mechanical tasks; delegate these to standard code tools.
- **Manage Token Budgets**: Enforce strict limits on context usage (e.g., 4k per message, 30k per session) to prevent token bloat.
- **Resolve Style Conflicts**: If formatting or lint rules conflict, prioritize a single unified configuration and discard the rest.
- **Verify Context Before Editing**: Always read the surrounding code and imports before writing a single line to ensure compatibility.
- **Use Business-Logic Tests**: Write meaningful tests that validate actual intent and business outcomes, not just empty code coverage.
- **Create Step-by-Step Checkpoints**: For multi-step long tasks, halt at milestones to log what was done, what was verified, and what remains.
- **Match Existing Codebase Style**: Strictly follow established code conventions (e.g., snake_case or class components) even if you disagree.
- **Explicitly Fail Loud (Fail Loud)**: If a step fails, skips data, or cannot be fully verified, report the error immediately. Never hide uncertainties.

## Commands

### Backend (`backend/`, Python 3.11+, FastAPI)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # install (editable) + dev deps
uvicorn app.main:app --reload    # run API at http://localhost:8000 (docs at /docs)
pytest                           # run all business-logic tests (config: pyproject.toml, -q)
pytest app/tests/test_workflow.py            # single file
pytest app/tests/test_workflow.py::test_name # single test
```

### Frontend (`frontend/`, Next.js 14 App Router + TypeScript)
```bash
cd frontend
npm install
npm run dev      # http://localhost:3000 — predev hook runs sync-docs first
npm run build    # prebuild hook runs sync-docs first
npm run lint     # next lint
```
There is no frontend test runner; CI only does `npm ci` + `npm run build`.

### Full stack
```bash
cp .env.example .env   # set ANTHROPIC_API_KEY for AI nodes; TRADING_MODE defaults to "paper"
docker compose up --build
```

CI (`.github/workflows/ci.yml`) runs `pytest` (backend) and `npm run build` (frontend) on PRs and pushes to `main`/`claude/**`/`deploy/**`.

## Architecture

AI-driven auto-trading platform for crypto / 台股 (TW stocks) / 美股 (US stocks). Users design strategies by talking to an AI, then run them backtested or live via a node-based workflow. **First working end-to-end slice is crypto + paper trading** (Binance via `ccxt`); other markets are fail-loud scaffolds with offline CSV paper/backtest.

### Backend (`backend/app/`)
- **`main.py`** — FastAPI entrypoint. Lifespan starts the DB (`init_db`) and APScheduler. Bearer-token auth (`api/deps.py:require_api_token`) is applied **globally** to every `/api/*` router; `GET /health` is public. Empty `API_TOKEN` disables auth (local/test) with a loud warning.
- **`config.py`** — All settings come from env (pydantic-settings), mapped from UPPER_CASE vars (see `.env.example`). Comma-separated env strings (CORS origins, FX rates, "CCY:rate") are parsed by field validators.
- **`brokers/`** — **The single core seam.** `base.py:Broker` (ABC) is the only boundary between paper/live and across markets. Add a market or switch modes by subclassing `Broker` and registering in `registry.py` — nothing else changes. `registry.get_broker(market, mode)` returns `PaperBroker` (cached per-market, persists state) or a live broker (`CcxtBroker`, `YuantaBroker`, `FirstradeBroker` scaffolds). Stock markets paper/backtest through `CsvDataBroker` over user-imported OHLCV.
- **`strategies/`** — `base.py:Strategy` (ABC) turns OHLCV → one `Signal`. Built-ins (`ma_cross`/`rsi`/`macd`/`bollinger`) are in `registry.py:STRATEGIES`. **AI agents emit the same `Signal` type**, so indicator strategies and LLM agents are interchangeable in workflows. `spec.py` is a declarative, **never-executed** whitelisted-indicator DSL (`StrategySpec`) — the safe representation for AI-generated strategies; `library.py` persists them as `StrategyDef`.
- **`workflow/`** — `engine.py:run_workflow` topologically sorts a `WorkflowGraph` (detects cycles/dupes), executes node runners in order, and **fails loud** on any node error (stops, reports which node and why). Node types in `schema.py:NodeType` (data_source, strategy, ai_signal, risk_exit, order, logger, condition, combine, branch). A `run_id` makes order nodes idempotent.
- **`trading/`** — `execution.py:execute_order` is the **single order path** shared by the orders API and the workflow engine (resolves fill price → `RiskGuard`/`PortfolioGuard` → broker → persist `OrderRecord`). `costs.py` applies transaction costs to every paper + backtest fill (ON by default). `risk.py` enforces per-order and portfolio-level (base-currency) limits. `paper_store.py` persists paper account state across restarts.
- **`backtest/`** — `engine.py` (single backtest), `metrics.py`, `optimize.py` (parameter grid search), `validation.py`.
- **`ai/`** — `claude_client.py` wraps the Anthropic SDK; `signal_agent.py` (AI buy/sell/hold signal) and `strategy_agent.py` (NL → `StrategySpec`). Default model in `config.py:ai_model`.
- **`api/`** — One router per domain (markets, orders, ai, workflows, backtest, schedules, notifications, risk, ledger, strategies). **`models.py`** = SQLModel tables (SQLite by default); **`schemas.py`** = shared enums/DTOs (`MarketKind`, `TradingMode`, `Signal`, `OrderRequest/Result`, `Candle`, …).

### Frontend (`frontend/`)
- App Router with two route groups mirroring the **two-room IA** (see DESIGN.md): `app/(rooms)/` (策略室 strategy-lab, 交易室 trading-room with backtest/workflow, market, portfolio, schedules, notifications, data-import) and `app/(handbook)/` (standalone light-themed `/docs`). Nav is centralized in `lib/nav.ts`.
- `lib/api.ts` — typed backend client. Base URL is same-origin in prod else `http://localhost:8000`; bearer token from `NEXT_PUBLIC_API_TOKEN` (intentionally browser-exposed, not a server secret).
- Workflow editor uses React Flow (`@xyflow/react`); charts use `lightweight-charts`.
- **Docs sync**: repo-root `docs/*.md` are copied into `frontend/content/docs/` by `scripts/sync-docs.mjs` (runs on predev/prebuild). The file list derives from `lib/docs-manifest.ts` — the single source of truth; don't hand-edit the synced copies.

## Design System

Always read [`DESIGN.md`](./DESIGN.md) before making any visual or UI decision.
All fonts, colors, spacing, aesthetic direction, and the two-room IA (策略室 / 交易室)
are defined there. Do not deviate without explicit user approval.

- The electric-cyan accent (`--accent`) is reserved for AI / automation only.
- Drive price up/down through `--up` / `--down` tokens — never hardcode green-as-gain
  (台股 inverts the convention via `data-market="tw"`).
- In QA / review, flag any code that does not match DESIGN.md.

## Conventions

- **Fail loud everywhere**: missing data, external errors, and risk violations must be reported explicitly, never silently skipped (mirrored in `workflow/engine.py` and `RiskGuard`).
- **Paper is the safe default** (`TRADING_MODE=paper`). Live trading requires `TRADING_MODE=live` + valid keys and passes `risk.py` guards first.
- Secrets only from `.env` (git-ignored). Never hardcode keys.
- Technical indicators use the `ta` library (not `pandas-ta`) for NumPy 2.x stability.
- Git flow: never commit directly to `main` — branch, open a PR, then merge.
