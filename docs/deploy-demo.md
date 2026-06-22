# Demo 部署(單台 EC2 + docker compose)

最低成本的 demo 部署:一台 `t4g.small` 跑 `docker-compose.yml`,每天台灣時間
08:30 自動開、18:00 自動關。成本約 US$0.3/天。**不影響** `infra/terraform/prod`。

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

## 前置
- 已安裝 Terraform ≥ 1.6、AWS CLI,且本機有可部署的 AWS 憑證(`aws sts get-caller-identity` 可通)。

## 設定(手動部署)
```bash
cd infra/terraform/demo
cp terraform.tfvars.example terraform.tfvars
# 編輯 terraform.tfvars:
#   anthropic_api_key = 你的 Anthropic key
#   api_token         = 自訂一串隨機字串
```

## 部署(手動路徑)
```bash
# demo 現在用 S3 remote state(沿用 prod 的 bucket/lock)。帶入 backend 設定:
terraform init \
  -backend-config="bucket=<你的 TF_STATE_BUCKET,如 ai-trade-flow-tfstate-<account>-ap-east-2>" \
  -backend-config="region=ap-east-2" \
  -backend-config="dynamodb_table=ai-trade-flow-tf-locks"
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
# 用 SSM 進機(無需 SSH;需本機裝 AWS CLI + session-manager-plugin)
aws ssm start-session --target "$(terraform output -raw instance_id)"
sudo cat /var/log/user-data.log     # 開機腳本輸出
cd /opt/app && sudo docker compose -f docker-compose.demo.yml ps
sudo docker compose -f docker-compose.demo.yml logs --tail=100
```
資料庫是容器內 SQLite,實例重建會歸零(demo 可接受)。

## 拆除(歸零成本)
```bash
terraform destroy     # 輸入 yes
```
