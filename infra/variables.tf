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

variable "git_repo" {
  description = "Git repository to clone (for source-based deploy, no PyPI)"
  type        = string
  default     = "https://github.com/Mishkat-Quantum-Labs/transcribe-studio.git"
}

variable "git_branch" {
  description = "Branch to checkout"
  type        = string
  default     = "main"
}

# Deprecated: use git clone + uv instead of PyPI package on server
variable "app_package" {
  description = "(deprecated) kept for compatibility"
  type        = string
  default     = ""
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

# --- Supabase (passed to app via env vars) ---
variable "supabase_url" {
  description = "Supabase project URL (e.g. https://xxx.supabase.co)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "supabase_anon_key" {
  description = "Supabase anon/public key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "supabase_db_url" {
  description = "Supabase direct database connection URL"
  type        = string
  default     = ""
  sensitive   = true
}

# --- S3 ---
variable "s3_bucket_name" {
  description = "S3 bucket for audio and transcript storage (created if set)"
  type        = string
  default     = ""
}

variable "s3_prefix" {
  description = "Object key prefix inside the bucket"
  type        = string
  default     = "transcribe-studio"
}