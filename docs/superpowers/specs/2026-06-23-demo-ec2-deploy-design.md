# 設計:Demo 用單台 EC2 + docker compose 部署

> 日期:2026-06-23 · 分支:`feat/demo-ec2-deploy`
> 來源:使用者要把專案以最低成本部署上 AWS 供 demo(低流量、非高可用),取代現行 ECS+RDS+NAT+ALB 的 always-on 架構。

## 目標與成功標準
- 一個 `terraform apply` 即可開出可公開存取的 demo 站(前端 + 後端 + SQLite),開機自動起服務。
- 成本遠低於現行架構。**搭配排程(每天只開 9.5 小時)實際約 US$0.3/天**(運算 ~$0.16 + EBS ~$0.08 + 停機 EIP ~$0.07);若 24h 全開 ~$0.5/天。
- 每天台灣時間 08:30 自動開、18:00 自動關(EventBridge Scheduler);也可手動 stop/start;`terraform destroy` 可歸零。
- 完全不更動現有 `infra/terraform/prod`。

成功標準:
- `terraform fmt -check` + `terraform validate` + `terraform plan` 乾淨。
- `apply` 後,瀏覽器開 `http://<EIP>:3000` 可看到 app;`http://<EIP>:8000/health` 回 `{"status":"ok"}`;AI 設計策略可運作(已填 Anthropic key)。

## 決策(使用者已確認)
| 項目 | 決定 |
|------|------|
| 運算 | 單台 **EC2 `t4g.small`**(arm64, 2vCPU/2GB)+ 2GB swap;build 較穩的替代是 t4g.medium(變數可調) |
| 網路 | **default VPC** + default subnet;免自建 VPC/NAT/subnet |
| 固定 IP | **Elastic IP**(stop/start 不變,解決前端 build 時需知 IP) |
| AI | **接 Anthropic API key**(`AI_PROVIDER=anthropic`,key 由 sensitive 變數寫入 `.env`) |
| 供置 | **全自動 user-data**:裝 docker → clone repo → 寫 `.env` → `docker compose up -d --build` |
| DB | 容器內 **SQLite**(不接 RDS;demo 重啟資料可重置) |
| 對外埠 | `3000`(前端)、`8000`(後端)對 **0.0.0.0/0** 開放 |
| SSH | `22` 限 **使用者本機 IP**(變數 `ssh_ingress_cidr`;runbook 教 `curl ifconfig.me` 取得) |
| TLS/網域 | 不做,純 HTTP + 公有 IP |
| Terraform state | **local state**(demo 用,免依賴 bootstrap S3 backend) |
| Region | 預設 `ap-east-2`(台北,沿用專案慣例;變數可改 us-east-1 更便宜) |
| 排程 | **EventBridge Scheduler** 每天台灣時間 **08:30 開機、18:00 關機**(timezone `Asia/Taipei`);cron 變數化 |
| 開機自動起服務 | user-data 裝 **systemd unit**,每次 EC2 啟動跑 `docker compose up -d`(首次才 `--build`)——因 user-data 只在首次開機執行 |

## 範圍
### 做(In scope)
- 新目錄 `infra/terraform/demo/`:`versions.tf`、`variables.tf`、`main.tf`、`outputs.tf`、`user-data.sh.tftpl`、`terraform.tfvars.example`。
- `docs/deploy-demo.md` runbook(apply / 取 URL / 手動 stop-start / **暫停或改排程時段** / destroy / 取本機 IP / 看 log / 首次 build 等待說明)。
- `.gitignore` 追加忽略 demo 的 local state 與 `terraform.tfvars`。

### 不做(Out of scope,YAGNI)
- HTTPS/網域/憑證、反向代理、ECR/CI 映像流程、RDS、Auto Scaling、多 AZ、CloudWatch 告警、變更現有 prod 模組。

## 架構與單元

### Terraform resources(`infra/terraform/demo/main.tf`)
- `data aws_ssm_parameter` → 最新 Amazon Linux 2023 **arm64** AMI id(`/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-arm64`)。
- `data aws_vpc default = true`;`data aws_subnets`(default VPC)→ 取一個 subnet。
- `aws_key_pair`:由變數 `ssh_public_key` 建。
- `aws_security_group`:ingress 22 ← `var.ssh_ingress_cidr`;ingress 3000、8000 ← `0.0.0.0/0`;egress all。
- `aws_instance`:`t4g.small`(`var.instance_type`)、上述 AMI/subnet/SG/key、`root_block_device` gp3 30GB、`user_data`=templatefile(帶入 secrets + EIP 佔位)。
- `aws_eip` + `aws_eip_association`:固定公有 IP 綁到 instance。
- **排程(每日自動開關機)**:
  - `aws_iam_role` + inline policy:EventBridge Scheduler 可 assume,允許 `ec2:StartInstances`/`ec2:StopInstances`(限本 instance ARN)。
  - `aws_scheduler_schedule "start"`:`cron(30 8 * * ? *)`、`schedule_expression_timezone = "Asia/Taipei"`、target = `arn:aws:scheduler:::aws-sdk:ec2:startInstances`、input = `{"InstanceIds":["<id>"]}`、`flexible_time_window { mode = "OFF" }`。
  - `aws_scheduler_schedule "stop"`:`cron(0 18 * * ? *)`、同 timezone、target = `...:stopInstances`。
  - cron 兩條以變數 `start_cron`/`stop_cron` 帶入(預設每天;改 `cron(... ? * MON-FRI *)` 即只平日)。EIP 在停機期間維持綁定,start 後 IP 不變。

> EIP 與 user-data 的相依:user-data 需要 EIP 位址寫進 `NEXT_PUBLIC_API_BASE_URL`。以 `aws_eip` 先配置 → 用其 `public_ip` 算 `user_data`;EIP 與 instance 用 `aws_eip_association` 綁定(避免 instance↔eip 循環相依;`user_data` 變更會觸發 instance 重建,可接受)。

### 開機腳本(`user-data.sh.tftpl`)
以 `templatefile()` 帶入:`anthropic_api_key`、`api_token`、`eip`、`repo_url`、`branch`。步驟:
1. `dnf install -y docker git` → 啟用 docker;裝 compose plugin(`/usr/libexec/docker/cli-plugins/docker-compose`)。
2. 建 2GB swap(`/swapfile`)→ 確保 `next build` 不 OOM。
3. `git clone <repo_url>` 到 `/opt/app`、`git checkout <branch>`。
4. 寫 `/opt/app/.env`:`TRADING_MODE=paper`、`AI_PROVIDER=anthropic`、`ANTHROPIC_API_KEY=...`、`AI_MODEL=claude-opus-4-8`、`API_TOKEN=...`、`NEXT_PUBLIC_API_TOKEN=...`、`NEXT_PUBLIC_API_BASE_URL=http://<eip>:8000`、`API_CORS_ORIGINS=http://<eip>:3000`。
5. 寫 systemd unit `/etc/systemd/system/atf-demo.service`(`Type=oneshot`、`RemainAfterExit=yes`、`WorkingDirectory=/opt/app`、`ExecStart=/usr/bin/docker compose up -d`、`After=docker.service`、`Requires=docker.service`、`WantedBy=multi-user.target`)→ `systemctl enable atf-demo`。讓**每次 EC2 啟動**(排程開機)都自動把容器拉起。
6. 首次:`cd /opt/app && docker compose up -d --build`(建映像);其後開機由 systemd unit 跑 `up -d`(重用映像,不重 build)。
7. 全程輸出到 `/var/log/user-data.log`(`exec > >(tee ...)`),失敗保留 log 供 SSH 排查(fail-loud:不靜默)。

### 變數(`variables.tf`)
`aws_region`(default `ap-east-2`)、`instance_type`(default `t4g.small`)、`ssh_ingress_cidr`(必填,如 `1.2.3.4/32`)、`ssh_public_key`(必填)、`anthropic_api_key`(sensitive)、`api_token`(sensitive;由使用者自訂任一字串,`NEXT_PUBLIC_API_TOKEN` 用相同值)、`repo_url`(default 公開 GitHub)、`branch`(default `main`)、`start_cron`(default `cron(30 8 * * ? *)`)、`stop_cron`(default `cron(0 18 * * ? *)`)、`schedule_timezone`(default `Asia/Taipei`)。

### 輸出(`outputs.tf`)
`demo_url` = `http://<eip>:3000`、`api_health_url`、`ssh_command` = `ssh ec2-user@<eip>`、`eip`。

### 機密與 git 衛生
`ANTHROPIC_API_KEY`、`API_TOKEN` 走 sensitive 變數,放 **gitignored** `infra/terraform/demo/terraform.tfvars`。`terraform.tfvars.example` 提供範本(不含真值)。`.gitignore` 追加:`infra/terraform/demo/terraform.tfvars`、`infra/terraform/demo/*.tfstate*`、`infra/terraform/demo/.terraform/`。

## 資料流
瀏覽器 → `http://<EIP>:3000`(Next.js 容器)→ 前端以 `NEXT_PUBLIC_API_BASE_URL=http://<EIP>:8000` 打後端容器 → 後端 SQLite + ccxt(Binance 公開行情)+ Anthropic API。EIP 固定使前端 build 時即可寫死正確後端位址。

## 錯誤處理(fail loud)
- user-data 全程 log 到 `/var/log/user-data.log`;任一步失敗不靜默(`set -euo pipefail`),box 仍在、可 SSH 進去看 log 與 `docker compose logs`。
- runbook 明列「apply 後等 N 分鐘(首次 build 較久)再開 URL;若白頁則 SSH 看 user-data.log」。

## 測試/驗證
- 本地:`terraform fmt -check`、`terraform validate`、`terraform plan`(帶 example tfvars 的假值或 `-var` 假值)為硬性關卡。**無法替使用者 `apply`**(需其 AWS 憑證)。
- 上線驗證(寫進 runbook,由使用者執行):`apply` → 等 build → `curl http://<EIP>:8000/health` 回 ok → 瀏覽器開 `http://<EIP>:3000` 確認 app 與 AI 功能。

## 風險
- **t4g.small 2GB build OOM**:以 2GB swap 緩解;備案改 `instance_type=t4g.medium`(runbook 註明)。
- **user_data 變更觸發 instance 重建**:可接受(demo);EIP 不變,重建後 IP 不動。
- **SQLite 不持久**:容器/實例重建資料歸零——demo 可接受,runbook 說明。
- **ap-east-2 機型/AMI 可用性**:若 t4g 或 AL2023 arm64 在該區不可用,改 region 或機型(變數化)。
