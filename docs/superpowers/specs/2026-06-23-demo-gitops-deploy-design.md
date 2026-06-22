# 設計:Demo 模組的 GitOps(GitHub Actions)部署

> 日期:2026-06-23 · 分支:`feat/demo-ec2-deploy`(疊在 PR #44 的 demo 模組上)
> 來源:使用者要透過 GitHub Actions(GitOps)把 demo 部署上 AWS,而非只手動 `terraform apply`。

## 目標與成功標準
- 在 GitHub Actions 以**手動按鈕**(`workflow_dispatch`)對 demo 模組執行 `plan` / `apply` / `destroy`,透過既有 OIDC role 部署到 AWS。
- demo 模組改用 **S3 remote state**(GitOps 必要),沿用既有 prod 的 state bucket + lock table(不同 key)。
- 拿掉 SSH,改用 SSM 進機;CI 部署不需任何人為 SSH。

成功標準:
- `terraform fmt -check` + `terraform validate`(demo 模組,含 S3 backend 的 `init -backend-config`)通過。
- workflow YAML 經 `actionlint`(或等價靜態檢查)無誤。
- 合併到 main 後,在 Actions 按 `apply` 能實際開出 demo;按 `destroy` 能歸零。(實際 apply 由使用者執行——需其 AWS 帳號 + 既有 GH secrets。)

## 決策(使用者已確認)
| 項目 | 決定 |
|------|------|
| 觸發 | `workflow_dispatch`,輸入 `action` = plan/apply/destroy(預設 plan) |
| SSH | **移除**(無 key pair、無 22 埠);改 **SSM Session Manager** 進機 |
| Plan | 手動 plan 按鈕(同一 workflow 的 plan action);**不**做 PR 自動 plan、**不**動 bootstrap/OIDC |
| State | local → **S3 backend**(key `demo/terraform.tfstate`),沿用 prod 的 bucket + DynamoDB lock |
| 機密 | 沿用既有 GH secrets(`ANTHROPIC_API_KEY`/`API_TOKEN`)→ `TF_VAR_*`;拿掉 SSH 後**不需新增 secret** |

## 既有可重用基礎(來自 `infra/terraform/bootstrap` 與 `deploy.yml`)
- S3 state bucket `ai-trade-flow-tfstate-<account>-<region>`、DynamoDB lock `ai-trade-flow-tf-locks`(GH secrets `TF_STATE_BUCKET`/`TF_LOCK_TABLE`)。
- OIDC provider + `github_deploy` role(AdministratorAccess),GH secret `AWS_DEPLOY_ROLE_ARN`。
- **OIDC trust 限制(關鍵)**:role 只可被 `ref = refs/heads/main` 且 `environment = production` 的 job assume。故 demo workflow 必須在 main + `environment: production` 執行 → **本分支需先合併到 main**。

## 範圍
### 做(In scope)
- `infra/terraform/demo/`:移除 SSH(key pair / 22 埠 / 2 個 ssh 變數 / ssh_command output / instance key_name);加 SSM IAM instance profile;`versions.tf` 加 `backend "s3"`。
- `infra/terraform/demo/variables.tf`、`terraform.tfvars.example`:移除 ssh 變數。
- `.github/workflows/deploy-demo.yml`:新 workflow(dispatch plan/apply/destroy)。
- `docs/deploy-demo.md`:加 GitOps 段、改 S3 backend init、SSH→SSM。

### 不做(Out of scope,YAGNI)
- 不動 `infra/terraform/bootstrap`/OIDC;不做 PR 自動 plan;不接 RDS/ECR(demo 仍 build-on-box);不做 HTTPS/網域。

## 架構與單元

### 1. demo 模組變更(`infra/terraform/demo/`)
- **`versions.tf`**:在 `terraform {}` 內加
  ```hcl
  backend "s3" {
    key     = "demo/terraform.tfstate"
    encrypt = true
  }
  ```
  bucket/region/dynamodb_table 由 `init -backend-config` 注入(同 prod)。
- **`main.tf`**:
  - 刪 `aws_key_pair.demo`;刪 SG 的 22 埠 ingress block;刪 instance 的 `key_name`。
  - 加 SSM:`data aws_iam_policy_document`(assume ec2.amazonaws.com)、`aws_iam_role.ssm`、attach `arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore`、`aws_iam_instance_profile.ssm`;instance 設 `iam_instance_profile = aws_iam_instance_profile.ssm.name`。
- **`variables.tf`**:刪 `ssh_ingress_cidr`、`ssh_public_key`。
- **`outputs.tf`**:刪 `ssh_command`;`eip`/`demo_url`/`api_health_url`/`instance_id` 保留。新增 `ssm_command = "aws ssm start-session --target ${aws_instance.demo.id}"`。
- **`terraform.tfvars.example`**:刪 ssh 兩行(本地手動路徑仍可用 tfvars 帶 anthropic_api_key/api_token;GitOps 則由 TF_VAR_* 注入)。

### 2. Workflow(`.github/workflows/deploy-demo.yml`)
- `on: workflow_dispatch`,inputs:`action`(type choice:`plan`/`apply`/`destroy`,default `plan`)。
- `permissions: { contents: read, id-token: write }`;`concurrency: demo-deploy`。
- `env`:`AWS_REGION: ap-east-2`、`TF_VAR_aws_region: ap-east-2`。
- job `demo`:`runs-on: ubuntu-latest`、`environment: production`。
  1. checkout。
  2. `aws-actions/configure-aws-credentials@v4`(role `AWS_DEPLOY_ROLE_ARN`、region)。
  3. `hashicorp/setup-terraform@v3`(1.15.6,`terraform_wrapper: false`)。
  4. 驗證 `API_TOKEN` secret 非空(fail-loud)。
  5. `terraform init`(working-dir `infra/terraform/demo`,`-backend-config` bucket/region/dynamodb_table 來自 secrets)。
  6. 依 `action` 執行:
     - plan → `terraform plan -input=false`
     - apply → `terraform apply -input=false -auto-approve` → 印 `demo_url`/`api_health_url`
     - destroy → `terraform destroy -input=false -auto-approve`
     - `TF_VAR_anthropic_api_key`/`TF_VAR_api_token` 由 secrets 注入(destroy 也帶,避免 var 缺失;Terraform 需要 var 值才能規劃刪除)。

### 3. 文件(`docs/deploy-demo.md`)
- 新段「GitOps 部署(GitHub Actions)」:先決條件(bootstrap 已 apply、GH secrets 已設、分支合併到 main)、操作(Actions → Run workflow → 選 plan/apply/destroy)。
- 手動路徑:`terraform init` 改帶 `-backend-config`(或 `-backend-config=backend.hcl`);移除 SSH 段,改 SSM(`aws ssm start-session --target <id>`)。

## 資料流
GH Actions(main, environment=production)→ OIDC assume `github_deploy` role → `terraform -chdir=infra/terraform/demo`(S3 state)→ 建/改/刪 demo 資源。Secrets(anthropic/api_token)以 `TF_VAR_*` 注入 → 由 user-data 寫進 EC2 `.env`。

## 錯誤處理(fail loud)
- workflow 早期驗 `API_TOKEN` 非空,缺則 `exit 1`。
- 所有 step `set -euo pipefail`;`-input=false` 避免卡互動。
- OIDC/ secrets 缺失 → configure-aws-credentials 或 init 直接失敗並顯示原因。

## 測試/驗證
- 本地:`terraform fmt -check` + `terraform validate`(demo,需 `terraform init -backend=false` 略過 backend 後 validate;或 `-backend-config` 帶假值僅供 validate)。workflow YAML 以 `actionlint`(若可裝)或人工 + `python -c "import yaml"` 結構檢查。
- 端到端 apply/destroy 需 AWS 憑證 + 合併到 main,**由使用者在 Actions 執行**;runbook 記載。

## 風險與邊界
- **OIDC 鎖 main+production**:本分支未合併到 main 前 workflow 無法成功(會在 assume-role 失敗)。spec/runbook 明示。
- **state 遷移**:demo 之前無 remote state(PR #44 是 local);改 S3 後第一次 `init` 是全新 state(沒有既有資源被 import)——乾淨起步,無遷移問題。
- **destroy 誤觸**:destroy 是 dispatch 選項,需人為選擇 + 在 production environment(可設 reviewers 加保護);列為已知,demo 可接受。
- 我(助理)**無法執行實際 apply**:需使用者 AWS 帳號、既有 GH secrets、合併到 main。交付物為可運作的 pipeline + runbook。
