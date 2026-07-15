# Transcribe Studio — AWS Terraform (free tier + pm2)

Deploys a **t2.micro** (or t3.micro) EC2 instance on **Amazon Linux 2** with optional **S3** storage and **Supabase** cloud database.

**Deployment style:**
- Git clone (source, not PyPI package)
- `uv pip install -e .`
- FastAPI served by **uvicorn** managed by **pm2**
- nginx reverse proxy on port 80
- IAM role for EC2 → S3 access (no API keys on server)

## Prerequisites

- Terraform >= 1.5
- AWS CLI configured
- Free tier account (t2.micro = 750 hrs/month free)
- (Optional) Supabase project — [supabase.com](https://supabase.com)

## Deploy

If you hit provider checksum / cache errors (common on Windows or after previous runs):

```powershell
cd infra
Remove-Item -Recurse -Force .terraform -ErrorAction SilentlyContinue
Remove-Item -Force .terraform.lock.hcl -ErrorAction SilentlyContinue
```

Then:

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your Supabase + S3 settings
terraform init
terraform plan
terraform apply
```

**Get your EC2 link:**

```bash
terraform output app_url
```

## Variables

| Variable | Default | Notes |
|----------|---------|-------|
| `instance_type` | `t2.micro` | Free tier |
| `git_repo` | the public repo | Change for your fork |
| `git_branch` | `main` | |
| `app_port` | 8082 | Internal (behind nginx) |
| `listener_port` | 80 | Public |
| `supabase_url` | `""` | Supabase project URL |
| `supabase_anon_key` | `""` | Supabase anon key |
| `supabase_db_url` | `""` | Direct Postgres URL for table creation |
| `s3_bucket_name` | `""` | Creates bucket + IAM policy if set |
| `s3_prefix` | `transcribe-studio` | Object key prefix |

## Architecture

```
┌─────────────┐      ┌──────────────────────────────┐
│   Browser   │─────▶│  EC2 (nginx:80 → uvicorn:8082)│
└─────────────┘      └──────────┬───────────────────┘
                                │
                     ┌──────────┼──────────────┐
                     ▼          ▼              ▼
              ┌──────────┐ ┌────────┐  ┌─────────────┐
              │  SQLite  │ │   S3   │  │  Supabase   │
              │  (local) │ │ (audio │  │ (cloud DB   │
              │          │ │  files)│  │  backup)    │
              └──────────┘ └────────┘  └─────────────┘
```

## Supabase Setup

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **Project Settings → API** — copy the URL and anon key
3. Go to **Project Settings → Database** — copy the connection string
4. Add these to your `terraform.tfvars`:

```hcl
supabase_url      = "https://xxx.supabase.co"
supabase_anon_key = "eyJ..."
supabase_db_url   = "postgresql://postgres.xxx:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
```

Tables (projects, recordings, segments) are **auto-created** on first app startup.

## S3 Setup

Set `s3_bucket_name` in your tfvars and Terraform will:
- Create the S3 bucket (private, encrypted, versioned)
- Create an IAM role with least-privilege S3 access
- Attach the role to your EC2 instance (no API keys needed)

Audio files and LLM transcripts are automatically uploaded to S3. The app falls back to local disk if S3 is unavailable.

```hcl
s3_bucket_name = "my-transcribe-studio-files"
s3_prefix      = "transcribe-studio"
```

## SSH Access

```bash
ssh -i your-key.pem ec2-user@<public-ip>
sudo -u ec2-user pm2 status
sudo -u ec2-user pm2 logs transcribe
```

## After Deploy

1. Open the public URL
2. Upload audio and transcribe
3. Check integrations: `GET /api/settings/status`

## Destroy

```bash
terraform destroy
```

## Security Notes

- Never commit `terraform.tfvars` or state files (gitignored)
- S3 bucket has public access blocked + server-side encryption
- EC2 uses IAM role for S3 (no long-lived API keys)
- Supabase credentials are passed as env vars (not stored in git)
