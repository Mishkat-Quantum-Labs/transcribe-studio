# Transcribe Studio — AWS Terraform (free tier + pm2)

Deploys a **t2.micro** (or t3.micro) EC2 instance on **Amazon Linux 2**.

**Deployment style (as requested):**
- Git clone (source, not PyPI package)
- `uv pip install -e .`
- FastAPI served by **uvicorn** managed by **pm2**
- nginx reverse proxy on port 80

This is a classic "old school" deploy — no fancy pipx on the server.

## Prerequisites

- Terraform >= 1.5
- AWS CLI configured
- Free tier account (t2.micro = 750 hrs/month free)

## Deploy

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars   # at minimum set ssh_cidr if you want SSH
terraform init
terraform plan
terraform apply
```

Get the URL:
```bash
terraform output app_url
```

SSH (if you set key + ssh_cidr):
```bash
ssh -i your-key.pem ec2-user@<public-ip>
sudo -u ec2-user pm2 status
sudo -u ec2-user pm2 logs transcribe
```

## Variables (important)

| Variable     | Default | Notes |
|--------------|---------|-------|
| `instance_type` | `t2.micro` | Free tier |
| `git_repo`   | the public repo | Change for your fork |
| `git_branch` | `main` | |
| `app_port`   | 8082 | Internal |
| `listener_port` | 80 | Public via nginx |

## After deploy

1. Open the public URL.
2. Go to **Settings** and connect your Supabase project (the app will auto-create tables).
3. Upload audio and have fun.

## Destroy

```bash
terraform destroy
```

## Notes

- Everything is installed from git source using `uv`.
- pm2 manages the uvicorn process (autorestart, memory limit).
- Data lives at `/var/lib/transcribe-studio` (owned by ec2-user).
- Never commit `terraform.tfvars` or state files.