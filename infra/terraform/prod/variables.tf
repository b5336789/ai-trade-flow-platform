variable "aws_region" {
  type        = string
  description = "AWS region."
  default     = "ap-southeast-2"
}

variable "project_name" {
  type        = string
  description = "Short project name."
  default     = "ai-trade-flow"
}

variable "environment" {
  type        = string
  description = "Deployment environment."
  default     = "prod"
}

variable "backend_image" {
  type        = string
  description = "Full backend image URI including tag."
}

variable "frontend_image" {
  type        = string
  description = "Full frontend image URI including tag."
}

variable "app_secrets_revision" {
  type        = string
  description = "Non-secret marker that changes when app-level Secrets Manager values are updated outside Terraform."
  default     = "initial"
}

variable "database_name" {
  type        = string
  description = "RDS database name."
  default     = "tradeflow"
}

variable "database_username" {
  type        = string
  description = "RDS master username."
  default     = "tradeflow"
}
