# AWS GitHub Actions Deployment Design

Date: 2026-06-19

## Summary

Set up production-only deployment for this repository on AWS using Terraform, GitHub Actions OIDC, ECR, ECS Fargate, an Application Load Balancer, and RDS PostgreSQL.

The first deployment target is `ap-east-2`. The project already has the domain `bwtseng.com`, but the initial release will use the ALB default DNS name so deployment is not blocked by domain propagation, Route 53 records, or ACM validation.

## Goals

- Run backend tests and frontend build in GitHub Actions.
- Build production Docker images for both services.
- Push images to ECR with immutable commit-SHA tags.
- Provision AWS infrastructure with Terraform.
- Deploy the FastAPI backend and Next.js frontend to ECS Fargate.
- Store application data in RDS PostgreSQL, not container-local SQLite.
- Use GitHub Actions OIDC instead of long-lived AWS access keys.
- Keep the first release in `TRADING_MODE=paper`.
- Output the ALB DNS name after deployment for manual verification.

## Non-Goals

- No Route 53, ACM, HTTPS, or `bwtseng.com` routing in the first release.
- No staging environment in the first release.
- No live trading credentials in the first release.
- No database migration framework in the first release. A fresh RDS database can use the current `SQLModel.metadata.create_all` startup behavior.
- No broader application refactor outside deployment requirements.

## AWS Architecture

Terraform will create a production stack in `ap-east-2`:

- VPC with two public subnets and two private subnets across availability zones.
- Internet gateway and NAT access for private ECS tasks that need outbound package/API access.
- Public Application Load Balancer listening on HTTP port `80`.
- One ECS cluster with two Fargate services:
  - `frontend`, running Next.js on port `3000`.
  - `backend`, running FastAPI/Uvicorn on port `8000`.
- Two ECR repositories:
  - backend image repository.
  - frontend image repository.
- RDS PostgreSQL in private subnets.
- CloudWatch log groups for frontend and backend containers.
- IAM roles:
  - GitHub OIDC deploy role.
  - ECS task execution role.
  - ECS task role.

The ALB will use path-based routing:

- `/api/*` routes to the backend target group.
- `/health` routes to the backend target group.
- all other paths route to the frontend target group.

This keeps the first release on one ALB and avoids needing separate frontend/backend public endpoints.

## Security Groups

- ALB security group accepts inbound HTTP `80` from the internet.
- Frontend ECS service accepts inbound `3000` only from the ALB security group.
- Backend ECS service accepts inbound `8000` only from the ALB security group.
- RDS accepts inbound PostgreSQL `5432` only from the backend ECS service security group.
- ECS tasks can make outbound requests for APIs and package/runtime network needs.

## GitHub Actions

### CI Workflow

`ci.yml` should run on pull requests and pushes:

- Backend:
  - install Python dependencies with `pip install -e ".[dev]"`.
  - run `pytest`.
- Frontend:
  - run `npm ci`.
  - run `npm run build`.
- Optional later step:
  - Docker build smoke test for both images.

### Deploy Workflow

`deploy.yml` should run on `main` and support manual `workflow_dispatch`:

1. Configure AWS credentials with GitHub OIDC.
2. Run Terraform init/plan/apply for production infrastructure.
3. Build backend and frontend Docker images.
4. Push images to ECR using the current commit SHA tag.
5. Render ECS task definitions with the new image tags.
6. Deploy both ECS services.
7. Wait for services to become stable.
8. Print the ALB DNS output.

The deployment workflow should use the GitHub `production` environment so repository maintainers can add approval gates later without changing the workflow shape.

## Terraform Layout

Add Terraform under `infra/terraform` with a production root module. The implementation can start with local state, then move to S3 and DynamoDB remote state once bootstrap is complete.

Expected areas:

- provider and backend config.
- network resources.
- security groups.
- ECR repositories.
- ECS cluster, task definitions, and services.
- ALB listeners, target groups, and listener rules.
- RDS PostgreSQL subnet group, instance, and credentials.
- IAM roles and policies for GitHub OIDC and ECS.
- outputs for ALB DNS name, ECR repository URLs, ECS cluster/service names, and role ARNs.

## Application Changes Required

The deployment requires a small set of project changes:

- Update `frontend/Dockerfile` to build and run a production Next.js server instead of `npm run dev`.
- Consider `output: "standalone"` in `frontend/next.config.mjs` to keep the production image smaller and more reliable.
- Add a PostgreSQL driver to `backend/pyproject.toml`, for example `psycopg[binary]`.
- Document AWS deployment variables in `.env.example` and deployment docs.

These are deployment-enabling changes only. They should not alter trading behavior or UI features.

## Runtime Configuration

Backend environment:

- `DATABASE_URL`, pointing to RDS PostgreSQL.
- `TRADING_MODE=paper`.
- `API_TOKEN`.
- `API_CORS_ORIGINS`, initially the ALB frontend origin.
- `ANTHROPIC_API_KEY`, optional for AI features.
- existing risk and cost environment variables as needed.

Frontend environment:

- `NEXT_PUBLIC_API_BASE_URL`, initially the same ALB origin because path routing sends `/api/*` to the backend.
- `NEXT_PUBLIC_API_TOKEN`, matching `API_TOKEN`.

Secrets:

- RDS credentials should be generated by Terraform and stored in AWS Secrets Manager or injected securely into ECS.
- GitHub should store non-AWS application secrets such as `API_TOKEN` and optional `ANTHROPIC_API_KEY`.
- Do not store Binance live keys for the first release.

## GitHub Secrets And Variables

GitHub repository or environment configuration should include:

- `AWS_ACCOUNT_ID`
- `AWS_REGION=ap-east-2`
- `API_TOKEN`
- `NEXT_PUBLIC_API_TOKEN`
- `ANTHROPIC_API_KEY`, if AI features are enabled

The AWS deploy role should be assumed via OIDC and restricted to this repository and the production branch/environment.

## Data And Migration Strategy

The current backend uses SQLModel and calls `SQLModel.metadata.create_all` on startup. That is acceptable for the first clean RDS deployment because it can create missing tables.

This does not handle schema migrations for existing databases. Before meaningful production data accumulates, add Alembic or another migration process.

## Domain And HTTPS Follow-Up

`bwtseng.com` is already registered, but the first release will not depend on it.

Follow-up work:

- create or connect the Route 53 hosted zone.
- request an ACM certificate.
- add HTTPS listener on the ALB.
- redirect HTTP to HTTPS.
- add DNS record such as `app.bwtseng.com`.
- update `API_CORS_ORIGINS` and `NEXT_PUBLIC_API_BASE_URL` to use the HTTPS domain.

## Validation

The first deployment is complete when:

- CI passes backend tests and frontend build.
- Terraform apply completes in `ap-east-2`.
- ECR contains backend and frontend images tagged with the deployed commit SHA.
- ECS services are stable.
- ALB DNS opens the frontend.
- `GET /health` through the ALB returns `{"status":"ok"}`.
- Frontend API calls reach backend `/api/*` through the same ALB origin.
- RDS contains created application tables after backend startup.
- Deployment remains in `TRADING_MODE=paper`.

## Concurrency Note

Other agents may be developing this repository concurrently. Implementation should re-check `git status` before each edit and keep deployment work scoped to:

- `.github/workflows/*`
- `infra/terraform/*`
- frontend Docker/Next production build settings
- backend PostgreSQL dependency
- deployment documentation

Unrelated application changes must not be reverted or bundled into deployment commits.
