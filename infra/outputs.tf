output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.app.id
}

output "public_ip" {
  description = "Public IPv4 address"
  value       = aws_instance.app.public_ip
}

output "app_url" {
  description = "URL to open in browser"
  value       = "http://${aws_instance.app.public_ip}:${var.listener_port}"
}

output "ami_id" {
  description = "Amazon Linux 2 AMI used"
  value       = data.aws_ami.amazon_linux_2.id
}