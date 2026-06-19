data "aws_caller_identity" "current" {}

locals {
  name_prefix                = "${var.project_name}-prod"
  state_bucket_name          = "${var.project_name}-tfstate-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
  lock_table_name            = "${var.project_name}-tf-locks"
  github_repository          = "${var.github_owner}/${var.github_repo}"
  github_branch_ref          = "refs/heads/${var.github_branch}"
  github_environment         = "production"
  github_subject_legacy      = "repo:${local.github_repository}:*"
  github_subject_immutable   = "repo:${var.github_owner}@*/${var.github_repo}@*:*"
  oidc_provider_url          = "https://token.actions.githubusercontent.com"
  oidc_provider_host         = "token.actions.githubusercontent.com"
}

resource "aws_s3_bucket" "terraform_state" {
  bucket = local.state_bucket_name
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket                  = aws_s3_bucket.terraform_state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_dynamodb_table" "terraform_locks" {
  name         = local.lock_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}

resource "aws_iam_openid_connect_provider" "github" {
  url            = local.oidc_provider_url
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd",
  ]
}

data "aws_iam_policy_document" "github_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_host}:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "${local.oidc_provider_host}:sub"
      values = [
        local.github_subject_legacy,
        local.github_subject_immutable,
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_host}:repository"
      values   = [local.github_repository]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_host}:ref"
      values   = [local.github_branch_ref]
    }

    condition {
      test     = "StringEquals"
      variable = "${local.oidc_provider_host}:environment"
      values   = [local.github_environment]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name               = "${local.name_prefix}-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_assume_role.json
}

resource "aws_iam_role_policy_attachment" "github_deploy_admin" {
  role       = aws_iam_role.github_deploy.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
