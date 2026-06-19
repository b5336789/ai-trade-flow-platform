output "terraform_state_bucket" {
  description = "Name of the S3 bucket for Terraform remote state."
  value       = aws_s3_bucket.terraform_state.bucket
}

output "terraform_lock_table" {
  description = "Name of the DynamoDB table for Terraform state locking."
  value       = aws_dynamodb_table.terraform_locks.name
}

output "github_deploy_role_arn" {
  description = "ARN of the GitHub Actions deploy role."
  value       = aws_iam_role.github_deploy.arn
}
