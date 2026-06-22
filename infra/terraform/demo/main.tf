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

resource "aws_key_pair" "demo" {
  key_name   = "${local.name}-key"
  public_key = var.ssh_public_key
  tags       = local.common_tags
}

resource "aws_security_group" "demo" {
  name        = "${local.name}-sg"
  description = "Demo: SSH from operator, HTTP app ports public"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_ingress_cidr]
  }

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

  egress {
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
  key_name                    = aws_key_pair.demo.key_name
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
    eip               = aws_eip.demo.public_ip
  })

  tags = merge(local.common_tags, { Name = "${local.name}-ec2" })
}

resource "aws_eip_association" "demo" {
  instance_id   = aws_instance.demo.id
  allocation_id = aws_eip.demo.id
}
