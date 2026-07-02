# Transcribe Studio — AWS Terraform (free tier)

Deploys a **t2.micro** EC2 instance on **Amazon Linux 2** with nginx on port **80** proxying to the app.

## Prerequisites

- [Terraform](https://www.terraform.io/downloads) >= 1.5
- AWS CLI configured (`aws configure`)
- Free-tier eligible account (first 12 months)

## Deploy

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars   # edit if needed
terraform init
terraform plan
terraform apply
```

Open the URL from `terraform output app_url`.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `app_port` | `8082` | Internal app port |
| `listener_port` | `80` | Public HTTP port (nginx) |
| `instance_type` | `t2.micro` | EC2 size |
| `app_package` | `transcribe-studio>=0.2.1` | pip package on instance |

Change app port:

```hcl
app_port = 9000
listener_port = 80
```

## Destroy

```bash
terraform destroy
```

## Notes

- Data persists on the instance at `/var/lib/transcribe-studio`
- Configure **Supabase** in the app UI under **Settings** after deploy (URL, anon key, database URL for auto table creation)
- Supabase credentials stay on the instance only — never committed to git
- CLI on the instance: `transcribe` or `transcribe-studio` (after pip install)
- Never commit `terraform.tfvars`, `.terraform/`, or `*.tfstate`