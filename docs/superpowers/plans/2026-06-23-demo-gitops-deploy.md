# Demo GitOps (GitHub Actions) 部署 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 demo 模組可由 GitHub Actions 手動觸發(plan/apply/destroy)部署到 AWS:改用 S3 remote state、移除 SSH 改 SSM、新增一個 `workflow_dispatch` workflow,沿用既有 OIDC role 與 GH secrets。

**Architecture:** 改 `infra/terraform/demo/` 為 S3 backend(沿用 prod 的 bucket/lock,key `demo/terraform.tfstate`),拿掉 key pair 與 22 埠、加 SSM instance profile;新增 `.github/workflows/deploy-demo.yml`(`environment: production` + OIDC,依輸入跑 plan/apply/destroy)。

**Tech Stack:** Terraform ≥1.6 (v1.15.6) · AWS provider ~>5.0 · GitHub Actions (OIDC, aws-actions/configure-aws-credentials@v4, hashicorp/setup-terraform@v3) · AWS SSM Session Manager。

## Global Constraints

- 只動 `infra/terraform/demo/`、`.github/workflows/deploy-demo.yml`、`docs/deploy-demo.md`。**不動** `infra/terraform/bootstrap/`、`infra/terraform/prod/`、`.github/workflows/deploy.yml`、app code。
- demo state = S3 backend,`key = "demo/terraform.tfstate"`、`encrypt = true`;bucket/region/dynamodb_table 由 `init -backend-config` 注入(同 prod 模式)。
- 無 SSH(無 key pair、無 22 埠);改 SSM(IAM instance profile `AmazonSSMManagedInstanceCore`)。3000/8000 仍對 0.0.0.0/0。
- workflow:`workflow_dispatch` 輸入 `action`∈{plan,apply,destroy}(default plan);`environment: production`;`permissions: id-token: write, contents: read`;OIDC role = `secrets.AWS_DEPLOY_ROLE_ARN`;terraform 1.15.6;`set -euo pipefail` + `-input=false`。
- 機密:`TF_VAR_anthropic_api_key` ← `secrets.ANTHROPIC_API_KEY`、`TF_VAR_api_token` ← `secrets.API_TOKEN`(沿用既有 secrets,不新增)。
- 區域 `ap-east-2`(`env.AWS_REGION` 與 `TF_VAR_aws_region`)。
- **OIDC 限制**:role 僅信任 `main` + `environment=production` → workflow 只有合併到 main 後跑得起來(runbook 註明)。
- 每個 task 結束 commit。分支:`feat/demo-ec2-deploy`(併入 PR #44)。

---

## File Structure

| 檔案 | 動作 | 責任 |
|------|------|------|
| `infra/terraform/demo/versions.tf` | Modify | 加 `backend "s3"` 區塊 |
| `infra/terraform/demo/main.tf` | Modify | 移除 key pair / 22 埠 / instance key_name;加 SSM role + instance profile |
| `infra/terraform/demo/variables.tf` | Modify | 移除 `ssh_ingress_cidr`、`ssh_public_key` |
| `infra/terraform/demo/outputs.tf` | Modify | 移除 `ssh_command`;加 `ssm_command` |
| `infra/terraform/demo/terraform.tfvars.example` | Modify | 移除 ssh 兩行 |
| `.github/workflows/deploy-demo.yml` | Create | dispatch plan/apply/destroy workflow |
| `docs/deploy-demo.md` | Modify | 加 GitOps 段;手動 init 改 backend-config;SSH→SSM |

---

### Task 1: demo 模組改造(remove SSH + add SSM + S3 backend)

**Files:**
- Modify: `infra/terraform/demo/versions.tf`
- Modify: `infra/terraform/demo/main.tf`
- Modify: `infra/terraform/demo/variables.tf`
- Modify: `infra/terraform/demo/outputs.tf`
- Modify: `infra/terraform/demo/terraform.tfvars.example`

**Interfaces:**
- Produces:`aws_instance.demo`(無 key_name、帶 `iam_instance_profile`)、`output.ssm_command`、S3 backend。後續 workflow 以 `terraform -chdir`/working-dir 操作。

- [ ] **Step 1: `versions.tf` 加 S3 backend**

把 `terraform { ... }` 區塊改成(在 `required_providers` 之後、`}` 之前加 backend):
```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    key     = "demo/terraform.tfstate"
    encrypt = true
  }
}

provider "aws" {
  region = var.aws_region
}
```

- [ ] **Step 2: `main.tf` — 移除 key pair 區塊**

刪除整個 `aws_key_pair.demo` 資源(目前的):
```hcl
resource "aws_key_pair" "demo" {
  key_name   = "${local.name}-key"
  public_key = var.ssh_public_key
  tags       = local.common_tags
}
```

- [ ] **Step 3: `main.tf` — 移除 SSH ingress、改 SG 描述**

在 `aws_security_group.demo`:把 description 從 `"Demo: SSH from operator, HTTP app ports public"` 改為 `"Demo: public HTTP app ports (SSM for shell, no SSH)"`,並刪除整個 SSH ingress block:
```hcl
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_ingress_cidr]
  }
```
(保留 Frontend 3000、Backend API 8000、egress 三個 block。)

- [ ] **Step 4: `main.tf` — instance 移除 key_name、加 instance profile**

在 `aws_instance.demo` 中刪除這行:
```hcl
  key_name                    = aws_key_pair.demo.key_name
```
並在 `vpc_security_group_ids` 那組屬性內新增一行(緊接其後):
```hcl
  iam_instance_profile        = aws_iam_instance_profile.ssm.name
```

- [ ] **Step 5: `main.tf` — 新增 SSM role + instance profile**

在 `aws_eip_association.demo` 之後(scheduler 區塊之前或檔尾任一處)新增:
```hcl
# SSM Session Manager access (replaces SSH; needs no inbound port).
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ssm" {
  name               = "${local.name}-ssm"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ssm" {
  name = "${local.name}-ssm"
  role = aws_iam_role.ssm.name
  tags = local.common_tags
}
```

- [ ] **Step 6: `variables.tf` — 移除 ssh 變數**

刪除整個 `ssh_ingress_cidr` 與 `ssh_public_key` 兩個 variable 區塊(含其 description/type)。

- [ ] **Step 7: `outputs.tf` — 移除 ssh_command、加 ssm_command**

刪除:
```hcl
output "ssh_command" {
  description = "SSH into the instance (use the private key matching ssh_public_key)."
  value       = "ssh ec2-user@${aws_eip.demo.public_ip}"
}
```
新增:
```hcl
output "ssm_command" {
  description = "Open a shell on the instance via SSM (no SSH needed)."
  value       = "aws ssm start-session --target ${aws_instance.demo.id}"
}
```

- [ ] **Step 8: `terraform.tfvars.example` — 移除 ssh 兩行**

刪除這兩行:
```hcl
ssh_ingress_cidr  = "1.2.3.4/32" # your IP/32 — run: curl -s ifconfig.me
ssh_public_key    = "ssh-ed25519 AAAA... you@host"
```
(保留 `anthropic_api_key`、`api_token`,以及註解的 overrides。)

- [ ] **Step 9: fmt + validate**

Run(於 `infra/terraform/demo/`):
```bash
rm -rf .terraform
terraform fmt -check
terraform init -backend=false
terraform validate
```
Expected: `fmt` 無輸出;`init -backend=false` 成功(略過 S3 backend,僅初始化 provider);`validate` → `Success! The configuration is valid.`(確認無殘留 `var.ssh_*` 參照、無 `aws_key_pair` 參照)。

- [ ] **Step 10: 確認無殘留 ssh 參照**

Run(於 `infra/terraform/demo/`):
```bash
grep -rn "ssh_public_key\|ssh_ingress_cidr\|aws_key_pair\|key_name" *.tf || echo "NO SSH REFS"
```
Expected: 印出 `NO SSH REFS`(完全無殘留)。

- [ ] **Step 11: Commit**

```bash
git add infra/terraform/demo/versions.tf infra/terraform/demo/main.tf infra/terraform/demo/variables.tf infra/terraform/demo/outputs.tf infra/terraform/demo/terraform.tfvars.example
git commit -m "feat(infra): demo module to S3 backend + SSM (drop SSH) for GitOps"
```

---

### Task 2: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/deploy-demo.yml`

**Interfaces:**
- Consumes: GH secrets `AWS_DEPLOY_ROLE_ARN`、`TF_STATE_BUCKET`、`TF_LOCK_TABLE`、`ANTHROPIC_API_KEY`、`API_TOKEN`;demo 模組(Task 1)的 S3 backend + outputs。

- [ ] **Step 1: 建 `.github/workflows/deploy-demo.yml`**

```yaml
name: Deploy Demo

on:
  workflow_dispatch:
    inputs:
      action:
        description: "Terraform action to run"
        type: choice
        required: true
        default: plan
        options:
          - plan
          - apply
          - destroy

permissions:
  contents: read
  id-token: write

concurrency:
  group: demo-deploy
  cancel-in-progress: false

env:
  AWS_REGION: ap-east-2
  TF_VAR_aws_region: ap-east-2

jobs:
  demo:
    name: "Demo ${{ github.event.inputs.action }}"
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-region: ${{ env.AWS_REGION }}
          role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}

      - name: Set up Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.15.6
          terraform_wrapper: false

      - name: Validate required secrets
        env:
          API_TOKEN: ${{ secrets.API_TOKEN }}
        run: |
          set -euo pipefail
          if [ -z "$API_TOKEN" ]; then
            printf '%s\n' 'API_TOKEN secret is required for the demo deploy' >&2
            exit 1
          fi

      - name: Terraform init
        working-directory: infra/terraform/demo
        run: |
          set -euo pipefail
          terraform init -input=false \
            -backend-config="bucket=${{ secrets.TF_STATE_BUCKET }}" \
            -backend-config="region=${{ env.AWS_REGION }}" \
            -backend-config="dynamodb_table=${{ secrets.TF_LOCK_TABLE }}"

      - name: "Terraform ${{ github.event.inputs.action }}"
        working-directory: infra/terraform/demo
        env:
          TF_VAR_anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          TF_VAR_api_token: ${{ secrets.API_TOKEN }}
        run: |
          set -euo pipefail
          case "${{ github.event.inputs.action }}" in
            plan)
              terraform plan -input=false
              ;;
            apply)
              terraform apply -input=false -auto-approve
              ;;
            destroy)
              terraform destroy -input=false -auto-approve
              ;;
            *)
              printf 'unknown action: %s\n' "${{ github.event.inputs.action }}" >&2
              exit 1
              ;;
          esac

      - name: Print URLs
        if: ${{ github.event.inputs.action == 'apply' }}
        working-directory: infra/terraform/demo
        run: |
          set -euo pipefail
          printf 'Demo URL: %s\n' "$(terraform output -raw demo_url)"
          printf 'Health:   %s\n' "$(terraform output -raw api_health_url)"
          printf 'SSM:      %s\n' "$(terraform output -raw ssm_command)"
```

- [ ] **Step 2: 用 actionlint 檢查 workflow**

Run(於 repo 根):
```bash
brew list actionlint >/dev/null 2>&1 || brew install actionlint
actionlint .github/workflows/deploy-demo.yml
```
Expected: actionlint 無輸出(零問題)。若 brew 無法安裝 actionlint,改用 `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/deploy-demo.yml')); print('YAML OK')"`(必要時先 `python3 -m pip install --quiet pyyaml`),並在 report 說明改用 YAML-only 檢查。

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/deploy-demo.yml
git commit -m "feat(ci): GitOps workflow for demo (dispatch plan/apply/destroy)"
```

---

### Task 3: runbook 更新(GitOps + S3 backend + SSM)

**Files:**
- Modify: `docs/deploy-demo.md`

**Interfaces:**
- Consumes: Task 1(S3 backend、ssm_command)、Task 2(workflow)。

- [ ] **Step 1: 在 `docs/deploy-demo.md` 開頭加「GitOps 部署(GitHub Actions)」段**

在文件第一段(`最低成本...`)之後插入:
```markdown
## GitOps 部署(GitHub Actions,推薦)

一鍵在 Actions 上 plan / apply / destroy,透過既有 OIDC role 部署。

**先決條件(一次性,需你做):**
- `infra/terraform/bootstrap` 已 `apply`(OIDC provider + S3 state bucket + deploy role)。
- GitHub repo 已設這些 secrets(prod deploy 若可跑即已存在):`AWS_DEPLOY_ROLE_ARN`、`TF_STATE_BUCKET`、`TF_LOCK_TABLE`、`ANTHROPIC_API_KEY`、`API_TOKEN`。
- **這個 workflow 只在 `main` 分支可用**(OIDC role 只信任 `main` + `production` environment),所以本功能的分支要先合併到 `main`。

**操作:**
1. GitHub → Actions → **Deploy Demo** → **Run workflow**。
2. 選 `action`:
   - `plan` — 預覽變更(部署前先看)。
   - `apply` — 建立/更新 demo;完成後 log 會印出 `Demo URL` / `Health` / `SSM`。
   - `destroy` — 拆除歸零。
3. 開印出的 `Demo URL`(`http://<EIP>:3000`)。首次 apply 後 EC2 仍需 ~3–5 分鐘 build 映像才會服務。

> state 存於既有 S3 bucket 的 `demo/terraform.tfstate`,與 prod 隔離。
```

- [ ] **Step 2: 手動路徑的 `terraform init` 改成 backend-config**

把現有手動「## 部署」段的
```bash
terraform init
```
改為:
```bash
# demo 現在用 S3 remote state(沿用 prod 的 bucket/lock)。帶入 backend 設定:
terraform init \
  -backend-config="bucket=<你的 TF_STATE_BUCKET,如 ai-trade-flow-tfstate-<account>-ap-east-2>" \
  -backend-config="region=ap-east-2" \
  -backend-config="dynamodb_table=ai-trade-flow-tf-locks"
```
並在該段註明:手動路徑的 `terraform.tfvars` 仍需 `anthropic_api_key` 與 `api_token`(已不需 ssh 變數)。

- [ ] **Step 3: 把「## 排錯」段的 SSH 改成 SSM**

把現有以 `ssh ec2-user@...` 進機的指令改為:
```bash
# 用 SSM 進機(無需 SSH;需本機裝 AWS CLI + session-manager-plugin)
aws ssm start-session --target "$(terraform output -raw instance_id)"
sudo cat /var/log/user-data.log
cd /opt/app && sudo docker compose -f docker-compose.demo.yml ps
sudo docker compose -f docker-compose.demo.yml logs --tail=100
```
並移除任何要求 `ssh_ingress_cidr`/`ssh_public_key`/`curl ifconfig.me` 的前置步驟(改述:GitOps 走 secrets,手動走 tfvars,皆不再需要 SSH 金鑰)。

- [ ] **Step 4: Commit**

```bash
git add docs/deploy-demo.md
git commit -m "docs(demo): GitOps workflow usage + S3 backend init + SSM access"
```

---

## Self-Review

**1. Spec coverage(逐項對照 spec)**
- 移除 SSH(key pair / 22 埠 / 2 變數 / ssh_command / key_name)→ Task 1 Step 2-4,6,7 ✅
- 加 SSM instance profile → Task 1 Step 5(+ Step 4 掛上 instance)✅
- S3 backend → Task 1 Step 1(+ workflow/ runbook 的 backend-config)✅
- workflow dispatch plan/apply/destroy、environment production、OIDC、TF_VAR secrets、印 URL → Task 2 ✅
- 沿用既有 secrets、不新增 → Task 2(只引用既有 5 個)✅
- runbook:GitOps 段 + backend-config init + SSH→SSM → Task 3 ✅
- 不動 bootstrap/prod/deploy.yml/app → 範圍限定於 3 處 ✅
- OIDC main+production 限制 → Global Constraints + runbook Task 3 Step 1 ✅

**2. Placeholder scan:** 無 TBD/TODO;每個程式碼步驟含完整內容。runbook 內 `<你的 TF_STATE_BUCKET...>` 是使用者需填的真實佔位(說明用),非計畫 placeholder。

**3. Type/名稱一致性:**
- `aws_iam_instance_profile.ssm.name`(Task1 Step5 定義)= instance 的 `iam_instance_profile`(Step4 引用)✅
- `output.ssm_command` / `instance_id` / `demo_url` / `api_health_url`(Task1 outputs)= workflow Print URLs(Task2)與 runbook 引用 ✅
- backend key `demo/terraform.tfstate`(Task1)+ `-backend-config` bucket/region/dynamodb_table(Task2 workflow / Task3 runbook)一致 ✅
- secrets 名稱 `AWS_DEPLOY_ROLE_ARN`/`TF_STATE_BUCKET`/`TF_LOCK_TABLE`/`ANTHROPIC_API_KEY`/`API_TOKEN` 與既有 `deploy.yml` 一致 ✅

**4. 注意事項(實作者必讀)**
- `terraform validate` 在加了 `backend "s3"` 後需先 `terraform init -backend=false`(略過 backend);否則 validate 會要求 backend 設定。Task 1 Step 9 已含。
- workflow 內 `${{ github.event.inputs.action }}` 出現在 step name 與 shell `case` 皆正確;`case` 有 `*)` 防呆。
- `.terraform/` 與 `.terraform.lock.hcl`:Task 1 Step 9 `rm -rf .terraform` 後重新 `init -backend=false` 會重建 lock;`.terraform/` 已 gitignored,`.terraform.lock.hcl` 已於 PR #44 提交(若 provider 未變則不變)。不要提交 `.terraform/`。
