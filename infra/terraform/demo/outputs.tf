output "demo_url" {
  description = "Primary HTTPS URL (Caddy + Let's Encrypt at the domain)."
  value       = "https://${var.domain_name}"
}

output "demo_url_ip" {
  description = "Direct IP fallback (HTTP) for debugging before the TLS cert is issued."
  value       = "http://${aws_eip.demo.public_ip}:3000"
}

output "api_health_url" {
  description = "Backend health check."
  value       = "http://${aws_eip.demo.public_ip}:8000/health"
}

output "ssm_command" {
  description = "Open a shell on the instance via SSM (no SSH needed)."
  value       = "aws ssm start-session --target ${aws_instance.demo.id}"
}

output "instance_id" {
  description = "EC2 instance id (for manual start/stop)."
  value       = aws_instance.demo.id
}

output "eip" {
  description = "Stable public IP."
  value       = aws_eip.demo.public_ip
}
