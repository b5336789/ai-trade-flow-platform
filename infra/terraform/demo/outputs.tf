output "demo_url" {
  description = "Open this in a browser to use the demo."
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
