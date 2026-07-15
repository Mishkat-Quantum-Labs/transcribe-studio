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

output "s3_bucket" {
  description = "S3 bucket for storage (empty if not configured)"
  value       = var.s3_bucket_name != "" ? aws_s3_bucket.storage[0].bucket : ""
}

output "iam_role" {
  description = "IAM role attached to EC2 instance"
  value       = aws_iam_role.app.name
}
