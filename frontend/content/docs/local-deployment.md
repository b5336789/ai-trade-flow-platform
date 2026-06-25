# Local Deployment Runbook

This is the first deployment path for MYM-12: run the platform locally with Docker Compose only.
It does not use AWS, Terraform, ECS, ALB, RDS, or cloud secrets.

Use this path to dry-run the app, risk controls, notifications, and operator procedures before any
cloud deployment is considered.

## Scope

- Backend: FastAPI container on `http://localhost:8000`.
- Frontend: production Next.js container on `http://localhost:3000`.
- Database: local SQLite file stored in Docker volume `local_backend_data`.
- Trading mode: `.env` defaults to `TRADING_MODE=paper`; keep it there unless a human explicitly
  approves testnet/live changes.
- Notifications: in-app feed always works; optional outbound webhook uses `NOTIFY_WEBHOOK_URL`.

## Prerequisites

- Docker Desktop or Docker Engine with Compose v2.
- No AWS credentials are needed.
- Do not put real exchange keys into `.env` until the go-live checklist is complete.

## Configure

```bash
cp .env.example .env
```

Edit `.env` for local deployment:

```bash
TRADING_MODE=paper
BINANCE_TESTNET=true
API_TOKEN=<strong-local-token>
NEXT_PUBLIC_API_TOKEN=<same-value-as-API_TOKEN>
API_CORS_ORIGINS=http://localhost:3000
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NOTIFY_WEBHOOK_URL=
```

If ports `3000` or `8000` are already used, change the local published ports and keep the frontend
API URL aligned:

```bash
LOCAL_FRONTEND_PORT=3100
LOCAL_BACKEND_PORT=8100
API_CORS_ORIGINS=http://localhost:3100
NEXT_PUBLIC_API_BASE_URL=http://localhost:8100
```

If you leave `API_TOKEN` blank, local APIs are open. That is acceptable only for isolated local
development, not for any shared machine or networked deployment.

## Start

```bash
docker compose -f docker-compose.local.yml up -d --build
```

Verify containers:

```bash
docker compose -f docker-compose.local.yml ps
curl http://localhost:${LOCAL_BACKEND_PORT:-8000}/health
open http://localhost:${LOCAL_FRONTEND_PORT:-3000}
```

Expected:

- Backend health returns `{"status":"ok"}`.
- Frontend opens at `http://localhost:${LOCAL_FRONTEND_PORT:-3000}`.
- `docker compose ... ps` shows backend and frontend as healthy after startup.

## Risk Status

```bash
curl "http://localhost:${LOCAL_BACKEND_PORT:-8000}/api/risk/status?market=crypto" \
  -H "Authorization: Bearer $API_TOKEN"
```

Check:

- `kill_switch` is `false`.
- `halted` is `false`.
- `base_currency` is `TWD`.
- Limits match `.env`: `MAX_TOTAL_EXPOSURE_VALUE`, `MAX_DAILY_LOSS`, `MAX_ORDERS_PER_DAY`.

## Kill Switch Dry Run

Engage:

```bash
curl -X POST "http://localhost:${LOCAL_BACKEND_PORT:-8000}/api/risk/kill-switch?engaged=true" \
  -H "Authorization: Bearer $API_TOKEN"
```

Verify:

```bash
curl "http://localhost:${LOCAL_BACKEND_PORT:-8000}/api/risk/status?market=crypto" \
  -H "Authorization: Bearer $API_TOKEN"
```

Expected:

- `kill_switch_runtime` becomes `true`.
- New buy entries are blocked.
- Position-reducing sells still pass if a position exists.

Release:

```bash
curl -X POST "http://localhost:${LOCAL_BACKEND_PORT:-8000}/api/risk/kill-switch?engaged=false" \
  -H "Authorization: Bearer $API_TOKEN"
```

## Daily Loss Halt Dry Run

Use paper mode only.

1. Stop the stack:

```bash
docker compose -f docker-compose.local.yml down
```

2. In `.env`, temporarily set a very small limit:

```bash
MAX_DAILY_LOSS=1
```

3. Start again:

```bash
docker compose -f docker-compose.local.yml up -d --build
```

4. Use the UI or order/workflow API to create a small paper position, then submit another entry
   after paper equity falls below the UTC day-start baseline.

Expected:

- The entry is rejected.
- `GET /api/risk/status` reports `halted=true`.
- In-app notifications show the risk halt.
- Exits remain allowed.

Resume after investigation:

```bash
curl -X POST "http://localhost:${LOCAL_BACKEND_PORT:-8000}/api/risk/resume" \
  -H "Authorization: Bearer $API_TOKEN"
```

Then restore the real `MAX_DAILY_LOSS` value in `.env` and restart.

## Notifications

Open the UI notifications page:

```text
http://localhost:${LOCAL_FRONTEND_PORT:-3000}/notifications
```

Optional webhook dry-run:

1. Set `NOTIFY_WEBHOOK_URL` in `.env`.
2. Restart the stack.
3. Send a test notification:

```bash
curl -X POST "http://localhost:${LOCAL_BACKEND_PORT:-8000}/api/notifications/test" \
  -H "Authorization: Bearer $API_TOKEN"
```

## Logs

```bash
docker compose -f docker-compose.local.yml logs -f backend
docker compose -f docker-compose.local.yml logs -f frontend
```

Use backend logs for API errors, scheduler issues, risk rejection traces, and notification delivery
failures.

## Stop and Roll Back

Stop containers but keep SQLite data:

```bash
docker compose -f docker-compose.local.yml down
```

Full local reset, including SQLite data:

```bash
docker compose -f docker-compose.local.yml down -v
```

Rollback application code:

```bash
git checkout main
docker compose -f docker-compose.local.yml up -d --build
```

## Migration Discipline

Local SQLite startup still uses `SQLModel.metadata.create_all()`. That is fine for a disposable local
database, but it is not a migration system.

Before preserving production data anywhere, add Alembic or another reviewed migration path for:

- `OrderRecord.client_order_id`.
- `RuntimeFlag`.

For local testing, use `docker compose -f docker-compose.local.yml down -v` to recreate a clean DB
when schema drift is suspected.
