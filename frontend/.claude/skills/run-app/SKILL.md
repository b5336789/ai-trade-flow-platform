---
name: run-app
description: Run/launch/start the full AI-Trade-Flow stack — FastAPI backend + SQLite database + Next.js frontend — and drive/screenshot the UI (especially the trading-room workflow builder) in a real browser. Use to bring up the whole app, verify an end-to-end flow, or take screenshots, not just build.
---

# Run the full stack (backend + database + frontend)

Three tiers: a **FastAPI backend** (`backend/`, port 8000), its **SQLite database**
(`backend/trade_flow.db`, created automatically by the lifespan `init_db`), and a
**Next.js frontend** (`frontend/`, port 3000). "Running" means starting all three
and driving the UI in a **real browser** via Playwright against the **system Google
Chrome** — the screenshots are the proof. The driver is
`frontend/.claude/skills/run-app/driver.mjs`.

Paths below are relative to the **repo root** unless a `cd` says otherwise.

> Verified on **macOS** with Google Chrome at `/Applications/Google Chrome.app`.
> The driver uses Playwright `channel: "chrome"` — no chromium download. (On
> headless Linux: `npx playwright install chromium` and drop the `channel`.)

## Prerequisites

- Backend venv prepared: `cd backend && python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"` (already done in this repo).
- Frontend deps installed (`cd frontend && npm install`), plus Playwright module (no browser), not saved:

```bash
cd frontend && npm i -D playwright --no-save
```

- Google Chrome installed.

## Run (agent path) — full stack, then drive

### 1. Backend + database

The lifespan runs `init_db` (creates/opens the SQLite DB) and starts the scheduler.
Config comes from `backend/.env` (e.g. `AI_PROVIDER=lmstudio`, `API_TOKEN=` → auth open for local). Start it and poll health:

```bash
cd backend && source .venv/bin/activate
pkill -f "uvicorn app.main:app" 2>/dev/null
uvicorn app.main:app --port 8000 >/tmp/atf-api.log 2>&1 &
until curl -sf http://127.0.0.1:8000/health >/dev/null; do sleep 1; done
ls -la trade_flow.db                 # SQLite DB exists (created on startup)
curl -s http://127.0.0.1:8000/api/config        # {"trading_mode":"paper", ...}
curl -s http://127.0.0.1:8000/api/strategies    # DB-backed saved strategies (may be [])
```

### 2. Frontend (fresh — see gotcha #1)

```bash
cd frontend
pkill -f "next dev" 2>/dev/null; rm -rf .next/cache
npm run dev >/tmp/atf-dev.log 2>&1 &
until curl -sf http://127.0.0.1:3000/ >/dev/null; do sleep 1; done
# force the workflow route to compile, then confirm the CSS bundle is real (~400KB), not a stale 8KB stub:
curl -s http://localhost:3000/trading-room/workflow >/dev/null; sleep 3
CSS=$(curl -s http://localhost:3000/trading-room/workflow | grep -o '/_next/static/css/[^"?]*' | head -1)
curl -s "http://localhost:3000$CSS" | wc -c            # expect ~400000, NOT ~8000
```

### 3. Drive the UI (run from `frontend/` so ESM resolves `./node_modules`)

```bash
cd frontend
node .claude/skills/run-app/driver.mjs
```

Screenshots land in `frontend/.claude/skills/run-app/screenshots/`
(`desktop.png`, `node-selected.png`, `after-run.png`, `tablet.png`). **Open
desktop.png and look at it.**

Expected stdout with the full stack up:
```
canvas: 4 nodes, 2 edges
inspector: "資料 DATA\nData Source\nsymbol\ntimeframe\nlimit\n複製\n刪除"
validation before: ✓ 有效 · 4 nodes · 3 edges
validation after edge delete: ✗ 節點 strat (Strategy) 缺少輸入
validation after undo: ✓ 有效 · 4 nodes · 3 edges
run result: "Status: ok"
console errors: ["Failed to load resource: ...404..."]
```

`run result: "Status: ok"` proves the end-to-end path: frontend → backend → live
OHLCV → strategy → paper order → logger → result panel. With the backend **down**
you instead get `ERR_CONNECTION_REFUSED` in console, the mode chip falls back to
PAPER, and the palette shows `無法載入已存策略` (graceful — built-ins still work).

Drive any other page: `node .claude/skills/run-app/driver.mjs http://localhost:3000/`

## Run (human path)

`docker compose up --build` (repo root) brings up the whole stack per
`docker-compose.yml`; or run the two `npm run dev` / `uvicorn` commands above and
open `http://localhost:3000/trading-room/workflow`. Useless headless — that's what
the driver is for.

## Gotchas (battle scars)

- **A long-running `npm run dev` serves a STALE CSS bundle.** A dev server left up
  for hours served an 8KB `layout.css` missing all Tailwind + React Flow styles, so
  the page rendered fully **unstyled** and the React Flow canvas collapsed to 0
  height (0 nodes) — even though `npm run build` was clean. Always start fresh
  (`pkill -f "next dev"; rm -rf .next/cache`) and verify the ~400KB CSS.
- **Headless Chrome's `--screenshot` renders Next App Router pages unstyled.** Next
  injects CSS via `data-precedence` `<link>`s that `chrome --headless --screenshot`
  captures before applying. Use Playwright `waitUntil:"networkidle"` (the driver
  does); don't trust raw `chrome --headless --screenshot` here.
- **Run the driver from `frontend/`.** ESM ignores `NODE_PATH`; `import "playwright"`
  only resolves with `frontend/node_modules` as CWD. From `/tmp` it throws
  `ERR_MODULE_NOT_FOUND`.
- **`channel: "chrome"`** drives the installed Chrome — no `npx playwright install`.
- **Database is SQLite, auto-created** at `backend/trade_flow.db` by the backend
  lifespan; no separate DB server. Delete that file to reset state. (Set
  `DATABASE_URL` in `backend/.env` for Postgres instead.)
- Run fetches **live** BTC/USDT OHLCV via ccxt, so step 3's Run needs network and
  takes a few seconds (the driver waits 8s).

## Troubleshooting

- `TypeError: URL is not a constructor` → don't shadow the global `URL`; the target
  arg variable in driver.mjs is `TARGET`.
- Driver finds 0 nodes / unstyled screenshot → stale dev server (gotcha #1). Restart it.
- `ERR_MODULE_NOT_FOUND: playwright` → run from `frontend/`; ensure `npm i -D playwright --no-save` ran.
- `run result: "no result panel"` or `Status` error → backend down or no network for OHLCV; start the backend (step 1) and retry.
