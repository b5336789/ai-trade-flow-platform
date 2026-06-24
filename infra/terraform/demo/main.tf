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

resource "aws_security_group" "demo" {
  name        = "${local.name}-sg"
  description = "Demo: public HTTP app ports (SSM for shell, no SSH)"
  vpc_id      = data.aws_vpc.default.id

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

  ingress {
    description = "HTTP (Caddy / ACME challenge)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS (Caddy)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_eip" "demo" {
  domain = "vpc"
  tags   = merge(local.common_tags, { Name = "${local.name}-eip" })
}

resource "aws_instance" "demo" {
  ami                         = data.aws_ssm_parameter.al2023.value
  instance_type               = var.instance_type
  subnet_id                   = data.aws_subnets.default.ids[0]
  vpc_security_group_ids      = [aws_security_group.demo.id]
  iam_instance_profile        = aws_iam_instance_profile.ssm.name
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
    domain            = var.domain_name
  })

  tags = merge(local.common_tags, { Name = "${local.name}-ec2" })
}

resource "aws_eip_association" "demo" {
  instance_id   = aws_instance.demo.id
  allocation_id = aws_eip.demo.id
}

# DNS: point the demo subdomain at the stable EIP (Route 53 hosted zone for the
# parent domain must already exist). Caddy uses this to obtain a TLS cert.
data "aws_route53_zone" "main" {
  name = var.route53_zone_name
}

resource "aws_route53_record" "demo" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = 300
  records = [aws_eip.demo.public_ip]
}

# SSM Session Manager access (replaces SSH; needs no inbound port).
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ssm" {
  name               = "${local.name}-ssm"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ssm" {
  name = "${local.name}-ssm"
  role = aws_iam_role.ssm.name
  tags = local.common_tags
}

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
