# AWS Deployment Guide

## 1. Overview

This project ships an AWS production path on branch `deploy/aws-github-actions`:

- `infra/terraform/bootstrap` bootstraps remote Terraform state (S3), lock table (DynamoDB), and GitHub OIDC deploy role.
- `infra/terraform/prod` deploys ECS Fargate frontend/backend, ALB, RDS PostgreSQL, ECR repos, logging, and Secrets Manager secret containers.
- GitHub Actions deploy workflow is `/.github/workflows/deploy.yml`.
- Region is fixed to `ap-southeast-2`.
- First release exposes the app on ALB HTTP DNS only (no custom domain, Route 53, or ACM HTTPS yet).

Image tags are immutable and include GitHub metadata:

`<sha>-<run_id>-<run_attempt>` (for example `f4b7c1a-123456789-2`).

## 2. First-time bootstrap commands

Run these once from a machine with AWS credentials and Terraform installed:

```bash
cd infra/terraform/bootstrap
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
```

Then capture bootstrap outputs:

```bash
terraform output terraform_state_bucket
terraform output terraform_lock_table
terraform output github_deploy_role_arn
```

Record these values for GitHub configuration.

## 3. GitHub Environment and secrets setup

Create a `production` environment in the repository settings.

Set these as repository or Environment secrets:

- `AWS_ACCOUNT_ID` (for operator notes and verification; not currently consumed by workflow logic).
- `AWS_DEPLOY_ROLE_ARN` (from `github_deploy_role_arn` output).
- `TF_STATE_BUCKET` (from `terraform_state_bucket` output).
- `TF_LOCK_TABLE` (from `terraform_lock_table` output).
- `API_TOKEN` (required; must be non-empty).
- `NEXT_PUBLIC_API_TOKEN` (required; must be non-empty and identical to `API_TOKEN`).
- `ANTHROPIC_API_KEY` (optional).

`API_TOKEN` and `NEXT_PUBLIC_API_TOKEN` are required by the workflow and must match before any Secrets Manager writes.
`NEXT_PUBLIC_API_TOKEN` is passed into the frontend build as a `NEXT_PUBLIC_*` value, so it is embedded into the browser bundle and visible to end users. It is therefore only a coarse shared API token, not a private server-side secret.

## 4. Deploy

Deployment runs when:

- pushing to `main`, or
- dispatching `.github/workflows/deploy.yml` via `workflow_dispatch`.

No extra local `.env` is needed once workflow secrets are set.

## 5. Verification

After deploy, open the ALB DNS or query health directly:

```bash
curl http://<alb-dns-name>/health
```

Replace `<alb-dns-name>` with the output from the deploy logs or:

```bash
terraform -chdir=infra/terraform/prod output -raw alb_dns_name
```

Also open:

```bash
http://<alb-dns-name>
```

in a browser.

## 6. Secrets behavior

- `API_TOKEN` and `NEXT_PUBLIC_API_TOKEN` are validated in workflow and must be both set and identical for production deploy.
- Terraform only creates Secrets Manager secret objects; app secret values are intentionally written outside Terraform state using AWS CLI in the deploy job.
- If `ANTHROPIC_API_KEY` is omitted, workflow writes `__disabled__` and backend normalizes it to an empty string so Anthropic features are disabled.

## 7. Current limits / follow-ups

- Deployment exposes HTTP only through ALB DNS (`http://...`).
- `bwtseng.com`, Route 53 DNS records, and ACM HTTPS are pending follow-up.
- `TRADING_MODE` is pinned to `paper` in `prod` task definition.
- Database schema is currently initialized via SQLModel `create_all` at startup; Alembic-based migrations are not yet wired.
- RDS `prevent_destroy` is enabled, so Terraform plans that destroy DB must be handled carefully.
- Terraform lockfiles (`.terraform.lock.hcl`) are committed for reproducible runs.
