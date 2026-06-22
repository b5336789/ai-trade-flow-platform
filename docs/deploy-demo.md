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
