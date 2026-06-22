# Demo 單台 EC2 + docker compose 部署 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增一個獨立的 Terraform 模組 `infra/terraform/demo/`,以單台 EC2 跑現有 `docker-compose.yml`,開機自動起服務,並以 EventBridge Scheduler 每天台灣時間 08:30 開、18:00 關,供低流量 demo。

**Architecture:** default VPC 內一台 `t4g.small`(+2GB swap)+ Elastic IP;user-data 裝 docker、clone 公開 repo、寫 `.env`(含 Anthropic key 與 EIP)、`docker compose up -d --build`,並裝 systemd unit 讓每次開機自動 `docker compose up -d`。EventBridge Scheduler 兩條(Asia/Taipei cron)透過 IAM role 對該 instance start/stop。Local state、純 HTTP。

**Tech Stack:** Terraform ≥1.6 · AWS provider ~>5.0 · Amazon Linux 2023 (arm64) · Docker + docker compose · EventBridge Scheduler。

## Global Constraints

- 完全不更動 `infra/terraform/prod/`。所有檔案都在 `infra/terraform/demo/`(+ repo 根 `.gitignore`、`docs/deploy-demo.md`)。
- Terraform `required_version = ">= 1.6.0"`、provider `hashicorp/aws ~> 5.0`(對齊 prod)。
- **Local state**(無 `backend` 區塊)。
- 機密(`anthropic_api_key`、`api_token`)只走 sensitive 變數 + gitignored `terraform.tfvars`;**絕不寫進 git**。
- 對外埠:`3000`、`8000` → `0.0.0.0/0`;`22` → `var.ssh_ingress_cidr`。
- Region 預設 `ap-east-2`;排程預設 `Asia/Taipei`、開 `cron(30 8 * * ? *)`、關 `cron(0 18 * * ? *)`。
- AI 用 Anthropic(`AI_PROVIDER=anthropic`)。DB 用容器內 SQLite。
- **每個 task 的關卡**(在 `infra/terraform/demo/` 執行):`terraform fmt -check`、`terraform init -backend=false`(首次)、`terraform validate` 必須通過。`terraform plan`/`apply` 需 AWS 憑證,**不在本計畫執行**——寫進 runbook 由使用者執行。
- 分支:`feat/demo-ec2-deploy`。每個 task 結束即 commit。

---

## File Structure

| 檔案 | 動作 | 責任 |
|------|------|------|
| `infra/terraform/demo/versions.tf` | Create | terraform/provider 版本 + provider 設定(無 backend) |
| `infra/terraform/demo/variables.tf` | Create | 所有輸入變數(region/instance/ssh/secrets/cron…) |
| `infra/terraform/demo/terraform.tfvars.example` | Create | 變數範本(不含真值) |
| `infra/terraform/demo/main.tf` | Create | data sources、key pair、SG、EC2、EIP、scheduler(IAM+2 schedules) |
| `infra/terraform/demo/user-data.sh.tftpl` | Create | 開機腳本(docker/swap/clone/.env/systemd/compose up) |
| `infra/terraform/demo/outputs.tf` | Create | demo_url / api_health_url / ssh_command / eip |
| `.gitignore` | Modify | 追加忽略 `*.tfvars`(保留 `*.tfvars.example`) |
| `docs/deploy-demo.md` | Create | runbook:apply / URL / 排程 / stop-start / destroy / 排錯 |

---

### Task 1: 模組骨架(versions / variables / tfvars 範本 / gitignore)

**Files:**
- Create: `infra/terraform/demo/versions.tf`
- Create: `infra/terraform/demo/variables.tf`
- Create: `infra/terraform/demo/terraform.tfvars.example`
- Modify: `.gitignore`

**Interfaces:**
- Produces 變數(後續 task 引用):`aws_region`、`instance_type`、`ssh_ingress_cidr`、`ssh_public_key`、`anthropic_api_key`、`api_token`、`repo_url`、`branch`、`start_cron`、`stop_cron`、`schedule_timezone`、`project_name`。

- [ ] **Step 1: 建 `versions.tf`**

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
```

- [ ] **Step 2: 建 `variables.tf`**

```hcl
variable "project_name" {
  type        = string
  description = "Short project name (used in resource names)."
  default     = "ai-trade-flow-demo"
}

variable "aws_region" {
  type        = string
  description = "AWS region."
  default     = "ap-east-2"
}

variable "instance_type" {
  type        = string
  description = "EC2 instance type (arm64). t4g.small=2GB; t4g.medium=4GB if builds OOM."
  default     = "t4g.small"
}

variable "ssh_ingress_cidr" {
  type        = string
  description = "CIDR allowed to SSH (port 22), e.g. \"1.2.3.4/32\". Get yours with: curl -s ifconfig.me"
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key material (contents of e.g. ~/.ssh/id_ed25519.pub) for EC2 login."
}

variable "anthropic_api_key" {
  type        = string
  description = "Anthropic API key for AI nodes. Written to the instance .env."
  sensitive   = true
}

variable "api_token" {
  type        = string
  description = "Shared bearer token for /api/* (also used as NEXT_PUBLIC_API_TOKEN). Any non-trivial string."
  sensitive   = true
}

variable "repo_url" {
  type        = string
  description = "Public git repo to clone on the instance."
  default     = "https://github.com/b5336789/ai-trade-flow-platform.git"
}

variable "branch" {
  type        = string
  description = "Git branch to deploy."
  default     = "main"
}

variable "start_cron" {
  type        = string
  description = "EventBridge Scheduler cron to START the instance. Default 08:30 daily."
  default     = "cron(30 8 * * ? *)"
}

variable "stop_cron" {
  type        = string
  description = "EventBridge Scheduler cron to STOP the instance. Default 18:00 daily."
  default     = "cron(0 18 * * ? *)"
}

variable "schedule_timezone" {
  type        = string
  description = "IANA timezone for the schedules."
  default     = "Asia/Taipei"
}
```

- [ ] **Step 3: 建 `terraform.tfvars.example`**

```hcl
# Copy to terraform.tfvars (gitignored) and fill in. NEVER commit terraform.tfvars.
ssh_ingress_cidr  = "1.2.3.4/32" # your IP/32 — run: curl -s ifconfig.me
ssh_public_key    = "ssh-ed25519 AAAA... you@host"
anthropic_api_key = "sk-ant-..."
api_token         = "pick-a-long-random-string"

# Optional overrides:
# aws_region        = "ap-east-2"
# instance_type     = "t4g.medium"
# start_cron        = "cron(30 8 ? * MON-FRI *)" # weekdays only
# stop_cron         = "cron(0 18 ? * MON-FRI *)"
```

- [ ] **Step 4: 更新 `.gitignore`(在 `# Terraform` 區塊末追加)**

在 `.gitignore` 的 Terraform 區塊(`*_override.tf.json` 之後)追加:
```
# Terraform variable files may contain secrets (keep examples tracked)
*.tfvars
```

- [ ] **Step 5: fmt + init + validate**

Run(於 `infra/terraform/demo/`):
```bash
terraform fmt -check
terraform init -backend=false
terraform validate
```
Expected: `fmt` 無輸出(已格式化);`init` 成功下載 aws provider;`validate` 印 `Success! The configuration is valid.`

- [ ] **Step 6: 確認 secrets 不會進 git**

Run(於 repo 根):
```bash
git check-ignore infra/terraform/demo/terraform.tfvars && echo "IGNORED OK"
```
Expected: 印出該路徑 + `IGNORED OK`(被忽略)。

- [ ] **Step 7: Commit**

```bash
git add infra/terraform/demo/versions.tf infra/terraform/demo/variables.tf infra/terraform/demo/terraform.tfvars.example .gitignore
git commit -m "feat(infra): scaffold demo terraform module (versions, vars, gitignore)"
```

---

### Task 2: 資料源 + key pair + security group(`main.tf`)

**Files:**
- Create: `infra/terraform/demo/main.tf`

**Interfaces:**
- Consumes: 變數(Task 1)。
- Produces(後續 task 引用):`local.name`、`data.aws_ssm_parameter.al2023.value`(AMI id)、`data.aws_subnets.default.ids`、`aws_key_pair.demo.key_name`、`aws_security_group.demo.id`。

- [ ] **Step 1: 建 `main.tf` — locals、data sources、key pair、SG**

```hcl
locals {
  name = var.project_name

  common_tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
    Stack     = "demo"
  }
}

# Latest Amazon Linux 2023 arm64 AMI
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64"
}

# Use the account's default VPC + its subnets (no custom VPC/NAT)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_key_pair" "demo" {
  key_name   = "${local.name}-key"
  public_key = var.ssh_public_key
  tags       = local.common_tags
}

resource "aws_security_group" "demo" {
  name        = "${local.name}-sg"
  description = "Demo: SSH from operator, HTTP app ports public"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_ingress_cidr]
  }

  ingress {
    description = "Frontend"
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Backend API"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}
```

- [ ] **Step 2: fmt + validate**

Run(於 `infra/terraform/demo/`):
```bash
terraform fmt -check
terraform validate
```
Expected: `fmt` 無輸出;`validate` → `Success! The configuration is valid.`

- [ ] **Step 3: Commit**

```bash
git add infra/terraform/demo/main.tf
git commit -m "feat(infra): demo data sources, key pair, security group"
```

---

### Task 3: user-data 範本 + EC2 + Elastic IP

**Files:**
- Create: `infra/terraform/demo/user-data.sh.tftpl`
- Modify: `infra/terraform/demo/main.tf`(append)

**Interfaces:**
- Consumes: `local.name`、`data.aws_ssm_parameter.al2023.value`、`data.aws_subnets.default.ids`、`aws_key_pair.demo.key_name`、`aws_security_group.demo.id`(Task 2)、變數(Task 1)。
- Produces:`aws_instance.demo.id`、`aws_instance.demo.arn`、`aws_eip.demo.public_ip`。

- [ ] **Step 1: 建 `user-data.sh.tftpl`**

> 注意:`${...}` 為 templatefile 變數插值;此腳本刻意不使用任何 shell `${var}` 展開,避免衝突。

```bash
#!/bin/bash
set -euo pipefail
exec > >(tee /var/log/user-data.log) 2>&1
echo "=== user-data start: $(date -u) ==="

# Docker + git
dnf install -y docker git
systemctl enable --now docker

# docker compose v2 plugin (arm64)
mkdir -p /usr/libexec/docker/cli-plugins
curl -fSL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-aarch64 \
  -o /usr/libexec/docker/cli-plugins/docker-compose
chmod +x /usr/libexec/docker/cli-plugins/docker-compose

# 2GB swap so frontend image build does not OOM on a 2GB box
if [ ! -f /swapfile ]; then
  dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# App source
git clone ${repo_url} /opt/app
cd /opt/app
git checkout ${branch}

# Environment for docker compose (env_file: .env)
cat > /opt/app/.env <<ENV
TRADING_MODE=paper
AI_PROVIDER=anthropic
AI_MODEL=claude-opus-4-8
ANTHROPIC_API_KEY=${anthropic_api_key}
API_TOKEN=${api_token}
NEXT_PUBLIC_API_TOKEN=${api_token}
NEXT_PUBLIC_API_BASE_URL=http://${eip}:8000
API_CORS_ORIGINS=http://${eip}:3000
ENV

# systemd unit: bring containers up on EVERY boot (user-data only runs once).
cat > /etc/systemd/system/atf-demo.service <<UNIT
[Unit]
Description=AI Trade Flow demo (docker compose)
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/app
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable atf-demo

# First boot: build images + start
docker compose up -d --build
echo "=== user-data done: $(date -u) ==="
```

- [ ] **Step 2: append EC2 + EIP 到 `main.tf`**

```hcl
resource "aws_eip" "demo" {
  domain = "vpc"
  tags   = merge(local.common_tags, { Name = "${local.name}-eip" })
}

resource "aws_instance" "demo" {
  ami                         = data.aws_ssm_parameter.al2023.value
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnets.default.ids[0]
  vpc_security_group_ids      = [aws_security_group.demo.id]
  key_name                    = aws_key_pair.demo.key_name
  associate_public_ip_address = true

  root_block_device {
    volume_type = "gp3"
    volume_size = 30
  }

  user_data = templatefile("${path.module}/user-data.sh.tftpl", {
    repo_url          = var.repo_url
    branch            = var.branch
    anthropic_api_key = var.anthropic_api_key
    api_token         = var.api_token
    eip               = aws_eip.demo.public_ip
  })

  tags = merge(local.common_tags, { Name = "${local.name}-ec2" })
}

resource "aws_eip_association" "demo" {
  instance_id   = aws_instance.demo.id
  allocation_id = aws_eip.demo.id
}
```

- [ ] **Step 3: fmt + validate**

Run(於 `infra/terraform/demo/`):
```bash
terraform fmt -check
terraform validate
```
Expected: `validate` → `Success! The configuration is valid.`(確認 `templatefile` 變數集合與 `.tftpl` 內 `${...}` 完全一致:repo_url/branch/anthropic_api_key/api_token/eip)

- [ ] **Step 4: Commit**

```bash
git add infra/terraform/demo/user-data.sh.tftpl infra/terraform/demo/main.tf
git commit -m "feat(infra): demo EC2 instance + Elastic IP + cloud-init (docker compose, systemd autostart)"
```

---

### Task 4: EventBridge Scheduler 每日開/關機(IAM + 2 schedules)

**Files:**
- Modify: `infra/terraform/demo/main.tf`(append)

**Interfaces:**
- Consumes: `aws_instance.demo.id`、`aws_instance.demo.arn`(Task 3)、`local.name`、`var.start_cron`/`var.stop_cron`/`var.schedule_timezone`(Task 1)。
- Produces:`aws_scheduler_schedule.start`、`aws_scheduler_schedule.stop`。

- [ ] **Step 1: append scheduler IAM role + policy + 兩條 schedule 到 `main.tf`**

```hcl
# IAM role assumed by EventBridge Scheduler to start/stop this instance
data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${local.name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy" "scheduler" {
  name = "${local.name}-scheduler-ec2"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ec2:StartInstances", "ec2:StopInstances"]
        Resource = aws_instance.demo.arn
      },
    ]
  })
}

resource "aws_scheduler_schedule" "start" {
  name = "${local.name}-start"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = var.start_cron
  schedule_expression_timezone = var.schedule_timezone

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ec2:startInstances"
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ InstanceIds = [aws_instance.demo.id] })
  }
}

resource "aws_scheduler_schedule" "stop" {
  name = "${local.name}-stop"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = var.stop_cron
  schedule_expression_timezone = var.schedule_timezone

  target {
    arn      = "arn:aws:scheduler:::aws-sdk:ec2:stopInstances"
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ InstanceIds = [aws_instance.demo.id] })
  }
}
```

- [ ] **Step 2: fmt + validate**

Run(於 `infra/terraform/demo/`):
```bash
terraform fmt -check
terraform validate
```
Expected: `Success! The configuration is valid.`

- [ ] **Step 3: Commit**

```bash
git add infra/terraform/demo/main.tf
git commit -m "feat(infra): daily 08:30-18:00 TWT auto start/stop via EventBridge Scheduler"
```

---

### Task 5: outputs + runbook + 最終驗證

**Files:**
- Create: `infra/terraform/demo/outputs.tf`
- Create: `docs/deploy-demo.md`

**Interfaces:**
- Consumes: `aws_eip.demo.public_ip`、`aws_instance.demo.id`(Task 3)。

- [ ] **Step 1: 建 `outputs.tf`**

```hcl
output "demo_url" {
  description = "Open this in a browser to use the demo."
  value       = "http://${aws_eip.demo.public_ip}:3000"
}

output "api_health_url" {
  description = "Backend health check."
  value       = "http://${aws_eip.demo.public_ip}:8000/health"
}

output "ssh_command" {
  description = "SSH into the instance (use the private key matching ssh_public_key)."
  value       = "ssh ec2-user@${aws_eip.demo.public_ip}"
}

output "instance_id" {
  description = "EC2 instance id (for manual start/stop)."
  value       = aws_instance.demo.id
}

output "eip" {
  description = "Stable public IP."
  value       = aws_eip.demo.public_ip
}
```

- [ ] **Step 2: 建 `docs/deploy-demo.md`(runbook)**

```markdown
# Demo 部署(單台 EC2 + docker compose)

最低成本的 demo 部署:一台 `t4g.small` 跑 `docker-compose.yml`,每天台灣時間
08:30 自動開、18:00 自動關。成本約 US$0.3/天。**不影響** `infra/terraform/prod`。

## 前置
- 已安裝 Terraform ≥ 1.6、AWS CLI,且本機有可部署的 AWS 憑證(`aws sts get-caller-identity` 可通)。
- 一把 SSH 金鑰:`ssh-keygen -t ed25519 -f ~/.ssh/atf-demo`(公鑰內容填入 tfvars)。

## 設定
```bash
cd infra/terraform/demo
cp terraform.tfvars.example terraform.tfvars
# 編輯 terraform.tfvars:
#   ssh_ingress_cidr  = "$(curl -s ifconfig.me)/32"
#   ssh_public_key    = 貼上 ~/.ssh/atf-demo.pub 內容
#   anthropic_api_key = 你的 Anthropic key
#   api_token         = 自訂一串隨機字串
```

## 部署
```bash
terraform init
terraform plan
terraform apply        # 輸入 yes
```
`apply` 後會輸出 `demo_url`。**首次開機要等 ~3–5 分鐘**(裝 docker + build 映像);
太早開會白頁。可先確認後端:
```bash
curl "$(terraform output -raw api_health_url)"   # 期望 {"status":"ok"}
```
再開 `terraform output -raw demo_url`。

## 每日排程
- 已自動建立:每天 08:30(台北)開機、18:00 關機。
- 改時段:編輯 `terraform.tfvars` 的 `start_cron`/`stop_cron`(EventBridge cron,
  格式 `cron(分 時 日 月 週 年)`,週用 `?`),`terraform apply`。
  - 只平日:`start_cron = "cron(30 8 ? * MON-FRI *)"`、`stop_cron = "cron(0 18 ? * MON-FRI *)"`。
- 暫停排程(不刪資源):AWS Console → EventBridge Scheduler → 對 `*-start`/`*-stop` 選 Disable。

## 手動開關機
```bash
ID=$(terraform output -raw instance_id)
aws ec2 stop-instances  --instance-ids "$ID"
aws ec2 start-instances --instance-ids "$ID"
```
EIP 固定,開機後網址不變。

## 排錯
```bash
ssh ec2-user@$(terraform output -raw eip)
sudo cat /var/log/user-data.log     # 開機腳本輸出
cd /opt/app && sudo docker compose ps
sudo docker compose logs --tail=100
```
資料庫是容器內 SQLite,實例重建會歸零(demo 可接受)。

## 拆除(歸零成本)
```bash
terraform destroy     # 輸入 yes
```
```

- [ ] **Step 3: 最終 fmt + validate + (離線可行的) plan 檢查**

Run(於 `infra/terraform/demo/`):
```bash
terraform fmt -check
terraform validate
```
Expected: 兩者皆通過(`validate` → Success)。
> `terraform plan`/`apply` 需 AWS 憑證,不在此執行;由使用者依 runbook 跑。

- [ ] **Step 4: Commit**

```bash
git add infra/terraform/demo/outputs.tf docs/deploy-demo.md
git commit -m "feat(infra): demo outputs + deploy runbook"
```

---

## Self-Review

**1. Spec coverage（逐項對照 spec)**
- default VPC + t4g.small + swap + EIP → Task 2/3 ✅
- AMI AL2023 arm64(SSM)→ Task 2 ✅
- SG:22 限 IP、3000/8000 對外 → Task 2 ✅
- user-data:docker/git/swap/clone/.env/compose up + **systemd 開機自起** → Task 3 ✅
- AI=Anthropic、SQLite、HTTP、NEXT_PUBLIC_API_BASE_URL=http://EIP:8000、CORS → Task 3 .env ✅
- EventBridge Scheduler 08:30/18:00 Asia/Taipei + IAM role(限本 instance ARN)+ cron 變數化 → Task 4 ✅
- 機密走 sensitive 變數 + gitignored tfvars → Task 1(變數 sensitive + `.gitignore *.tfvars` + check-ignore 驗證)✅
- local state(無 backend)→ Task 1 versions.tf ✅
- outputs(demo_url/health/ssh/eip/instance_id)+ runbook(apply/URL/排程/stop-start/destroy/排錯)→ Task 5 ✅
- 不動 prod → 全部檔案在 demo/ 與根層 gitignore/docs ✅
- 不做 HTTPS/ECR/RDS/反向代理 → 未出現 ✅

**2. Placeholder scan:** 無 TBD/TODO;每個建立檔案步驟皆含完整內容。

**3. Type/名稱一致性:**
- `templatefile` 傳入鍵 `{repo_url, branch, anthropic_api_key, api_token, eip}`(Task 3 Step 2)與 `.tftpl` 內 `${...}`(Task 3 Step 1)完全對應——Task 3 Step 3 明列此檢查。
- 變數名在 Task 1 定義,Task 2/3/4 一致引用(`var.ssh_ingress_cidr`、`var.start_cron`…)。
- 資源參照鏈:`aws_eip.demo.public_ip`(Task 3)→ user_data/outputs;`aws_instance.demo.id`/`.arn`(Task 3)→ scheduler(Task 4)/outputs(Task 5)。皆一致。
- EIP↔instance 無循環:`aws_eip.demo` 獨立配置(無 instance 參數)→ 其 `public_ip` 餵 instance user_data;`aws_eip_association` 綁定兩者,無反向相依。

**4. 注意事項(實作者必讀)**
- `terraform validate` 不需 AWS 憑證(不執行 data sources);`init` 用 `-backend=false`(local state 模式)。`plan`/`apply` 需憑證,不在本計畫範圍。
- docker compose v2 plugin 版本字串 `v2.29.7` 為固定下載;若該版不存在改用當時最新的 `docker-compose-linux-aarch64` release。
- 現有 `docker-compose.yml` 是 dev 模式(`npm run dev` / `--reload`),前端在 runtime 讀 `NEXT_PUBLIC_*`,故 `.env` 寫入即生效,無 build-time bake 問題。
