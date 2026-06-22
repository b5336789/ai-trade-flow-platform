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
