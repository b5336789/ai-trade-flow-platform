# ai-trade-flow-platform

AI 驅動的自動交易平台 — supports crypto / 台股 / 美股 programmatic trading behind a single
broker abstraction, with technical-indicator strategies, LLM (Claude) signal generation, a
strategy backtester, scheduled (auto-running) workflows, and a workflow-based web UI.

> Development is governed by [`CLAUDE.md`](./CLAUDE.md). Read it before contributing.

## Status

This is an in-progress build. The **first fully-working end-to-end slice is crypto + paper
trading** (Binance via `ccxt`). The architecture is designed so additional markets/brokers plug
in behind the common `Broker` interface:

| Market | Broker target            | Status                                            |
| ------ | ------------------------ | ------------------------------------------------- |
| Crypto | Binance (`ccxt`)         | ✅ market data + paper trading (live opt-in)      |
| 台股   | 元大證券 (Yuanta)        | ⏳ interface ready, implementation later          |
| 美股   | 元大複委託 + Firstrade   | ⏳ interface ready, later (Firstrade = unofficial API) |

## Architecture

```
backend/   FastAPI + ccxt + ta + anthropic + SQLModel
frontend/  Next.js (App Router) + TypeScript + React Flow + lightweight-charts
```

See the approved plan and `CLAUDE.md` for conventions. Key seam: `backend/app/brokers/base.py`
(`Broker` ABC) is the single boundary between paper and live, and between markets.

## Quick start

### 1. Configure secrets

```bash
cp .env.example .env
# edit .env — set ANTHROPIC_API_KEY for AI nodes; TRADING_MODE defaults to "paper" (safe).
```

### 2. Run with Docker

```bash
docker compose up --build
# backend  -> http://localhost:8000  (docs at /docs)
# frontend -> http://localhost:3000
```

### 3. Run locally (without Docker)

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
pytest            # business-logic tests
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Safety

- `TRADING_MODE=paper` is the default. Live crypto trading requires `TRADING_MODE=live` **and**
  valid exchange API keys; `risk.py` enforces position-size / max-loss guards before any live
  order is sent.
- Secrets are read only from `.env` (git-ignored). Never hardcode keys.

## Documentation

- **Developer docs** (architecture, API, modules, dev log): [`docs/`](./docs/README.md) — diagrams
  render on GitHub.
- **End-user manual** (illustrated, 圖文並茂): run the frontend and open
  [`/manual`](http://localhost:3000/manual).

## Notes

- Technical indicators use the [`ta`](https://github.com/bukosabino/ta) library (stable under
  NumPy 2.x) rather than `pandas-ta`, to keep a fresh install reliable.
