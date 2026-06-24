# Production Ops Runbook

This runbook is for Stage 1 crypto production readiness. It prepares the ECS/Fargate stack,
monitoring, and emergency controls, but it does not authorize a production apply or live trading.
Final production release remains a human decision.

## Current Guardrails

- `infra/terraform/prod` is the production runtime stack: ECR, ECS Fargate, ALB, RDS PostgreSQL,
  Secrets Manager, CloudWatch logs, SNS alerts, and EventBridge task-stop alerts.
- The production task definition pins `TRADING_MODE=paper`. Switching to `live` is a separate
  change and must pass the go-live checklist.
- RDS has `prevent_destroy = true`; do not disable it in routine deploys.
- App secret values are written to Secrets Manager outside Terraform state by GitHub Actions.
- Required production approval gates: no real `terraform apply`, live trading, or secret creation
  without human approval.

## Terraform Plan and Blast Radius

Run from a credentialed operator shell after confirming the AWS account and region:

```bash
aws sts get-caller-identity
cd infra/terraform/prod
terraform init \
  -input=false \
  -backend-config="bucket=$TF_STATE_BUCKET" \
  -backend-config="region=ap-east-2" \
  -backend-config="dynamodb_table=$TF_LOCK_TABLE"
terraform plan -out=plan.out \
  -var="backend_image=<backend-ecr-uri>:<tag>" \
  -var="frontend_image=<frontend-ecr-uri>:<tag>" \
  -var="app_secrets_revision=<non-secret-revision>"
terraform show -no-color plan.out > plan.txt
terraform show -json plan.out > plan.json
```

Expected blast radius when the stack is currently destroyed for cost control:

- Creates runtime networking: VPC, two public subnets, two private subnets, internet gateway,
  one NAT gateway/EIP, route tables, and security groups.
- Creates runtime compute: ECS cluster, task definitions, backend/frontend Fargate services,
  ALB, listener, listener rule, and target groups.
- Creates data plane: one encrypted private PostgreSQL RDS instance and DB subnet group.
- Creates deployment/support resources: ECR repos, CloudWatch log groups, Secrets Manager secret
  containers, SNS topic/subscription, CloudWatch alarms, log metric filters, and EventBridge rule.
- Does not create real broker/API keys in Terraform state.
- Does not intentionally destroy RDS; `prevent_destroy` should make any destructive DB plan fail.

Rollback path:

- Application-only rollback: redeploy the previous immutable image tags with a new
  `app_secrets_revision`.
- Infrastructure rollback: revert the Terraform change and run a fresh plan for human review.
- Emergency cost rollback before live data exists: human-approved `terraform destroy` can tear down
  runtime resources, but RDS `prevent_destroy` requires an explicit, reviewed decision.

## Monitoring and Alerts

Production Terraform creates an SNS topic output as `ops_alerts_topic_arn`.
Set `alarm_email` to subscribe an email endpoint; the recipient must confirm the SNS subscription.

Alert sources:

- ALB generated 5xx responses: `ai-trade-flow-prod-alb-5xx`.
- Backend target 5xx responses: `ai-trade-flow-prod-backend-target-5xx`.
- Backend/frontend unhealthy targets: target group `UnHealthyHostCount`.
- ECS stopped tasks: EventBridge `ECS Task State Change` with `lastStatus=STOPPED`.
- Risk halt events: backend log metric filter for notification events with `max_daily_loss`.
- Kill-switch operator events: backend log metric filter for notification events with `kill_switch`.

App notifications:

- Every fill and risk gate emits an in-app `Notification`.
- If `NOTIFY_WEBHOOK_URL` is set in the GitHub production environment, the deploy workflow writes
  it to Secrets Manager and the backend also posts outbound webhook notifications.
- If unset, the workflow writes `__disabled__`; the app normalizes that to an empty URL.

## Kill Switch

Engage the runtime kill switch:

```bash
curl -X POST "http://<alb-dns-name>/api/risk/kill-switch" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"engaged": true}'
```

Verify:

```bash
curl "http://<alb-dns-name>/api/risk/status?market=crypto" \
  -H "Authorization: Bearer $API_TOKEN"
```

Expected behavior:

- `kill_switch` and `kill_switch_runtime` are `true`.
- New entries are rejected.
- Position-reducing sells still pass so the operator can de-risk.
- An in-app notification, optional webhook, backend log event, and CloudWatch kill-switch alarm are
  emitted.

Release:

```bash
curl -X POST "http://<alb-dns-name>/api/risk/kill-switch" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"engaged": false}'
```

## Daily Loss Halt

`MAX_DAILY_LOSS` is measured in `BASE_CURRENCY` from the first UTC equity snapshot of the day.
When breached, the backend persists `halted=true`.

Expected behavior:

- Entries are rejected.
- Exits remain allowed.
- An in-app notification, optional webhook, backend log event, and CloudWatch risk-halt alarm are
  emitted.

Dry-run on paper/testnet before live:

1. Keep `TRADING_MODE=paper` and `BINANCE_TESTNET=true`.
2. Set a deliberately small `MAX_DAILY_LOSS` in a non-production environment.
3. Establish a position, move the stub/testnet mark or risk inputs to breach the limit, then submit
   a new buy.
4. Confirm the buy is rejected, `GET /api/risk/status` reports `halted=true`, notifications appear,
   and an exit sell still succeeds.
5. Resume only after the cause is understood:

```bash
curl -X POST "http://<alb-dns-name>/api/risk/resume" \
  -H "Authorization: Bearer $API_TOKEN"
```

## Emergency Full Stop

Use the least destructive control that stops new risk quickly:

1. Engage the runtime kill switch.
2. Disable schedules or stop external workflow triggers.
3. If app traffic must stop, set ECS service desired counts to 0 through a reviewed Terraform
   change or an explicitly approved AWS console/CLI emergency action.
4. Keep exits available unless a human explicitly decides the broker connection itself must be
   disabled.

## Testnet to Production Cutover

1. Confirm the go-live checklist is fully checked.
2. Run the production Terraform plan and review `plan.txt` plus `plan.json`.
3. Confirm alarms, SNS subscription, and webhook destination.
4. Confirm DB path: clean RDS database or an Alembic migration applied before app startup.
5. Run paper mode through the ALB and verify `/health`, `/api/risk/status`, notifications, and
   kill switch.
6. Run broker testnet with tiny limits and verify one entry, one exit, and daily-loss halt dry-run.
7. Only after human approval, change live-trading settings and start with a small amount well below
   all configured caps.
8. Monitor fills, risk-trigger notifications, ALB/ECS alarms, and database health during the first
   sessions.

## Database Migration Plan

Do not rely on `SQLModel.metadata.create_all()` for existing production tables. It creates missing
tables but does not add columns to existing tables.

Current schema requirements before production data exists:

- `OrderRecord.client_order_id` from M0.5.
- `RuntimeFlag` table from M0.6.

Accepted paths:

- Clean DB path: for first production launch, start with an empty RDS database and let startup create
  the current schema. This is acceptable only before durable production data exists.
- Migration path: add Alembic, generate an initial baseline from current SQLModel metadata, and add
  explicit migrations for `OrderRecord.client_order_id` and `RuntimeFlag`. Run migrations before
  starting the ECS backend task.

Once production data exists, all schema changes must go through Alembic or an equivalent reviewed
migration process. `init_db()` is not a migration mechanism.
