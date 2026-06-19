variable "aws_region" {
  type        = string
  description = "AWS region for bootstrap resources."
  default     = "ap-east-2"
}

variable "project_name" {
  type        = string
  description = "Short project name used in resource names."
  default     = "ai-trade-flow"
}

variable "github_owner" {
  type        = string
  description = "GitHub repository owner."
  default     = "b5336789"
}

variable "github_repo" {
  type        = string
  description = "GitHub repository name."
  default     = "ai-trade-flow-platform"
}

variable "github_branch" {
  type        = string
  description = "Branch allowed to assume the deploy role."
  default     = "main"
}
