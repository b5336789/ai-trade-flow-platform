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

variable "api_token" {
  type        = string
  description = "Bearer token required by backend /api routes."
  sensitive   = true
}

variable "anthropic_api_key" {
  type        = string
  description = "Anthropic API key. Empty string disables AI calls that require it."
  sensitive   = true
  default     = ""
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
