variable "aws_region" {
  description = "AWS region (us-east-1 recommended for free tier)"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type (t2.micro is free-tier eligible)"
  type        = string
  default     = "t2.micro"
}

variable "app_port" {
  description = "Port Transcribe Studio listens on (proxied by nginx)"
  type        = number
  default     = 8082
}

variable "listener_port" {
  description = "Public HTTP port (80 for standard web)"
  type        = number
  default     = 80
}

variable "app_package" {
  description = "PyPI package spec to install on the instance"
  type        = string
  default     = "transcribe-studio>=0.2.6"
}

variable "key_name" {
  description = "Optional EC2 key pair name for SSH"
  type        = string
  default     = ""
}

variable "ssh_cidr" {
  description = "CIDR allowed for SSH (empty disables SSH ingress)"
  type        = string
  default     = ""
}

variable "project_name" {
  description = "Name prefix for AWS resources"
  type        = string
  default     = "transcribe-studio"
}