#!/bin/bash
# Transcribe Studio - Free tier EC2 deploy (git clone + uv + pm2 + nginx)
# No PyPI package install on the server - pure source + uv
set -euo pipefail

GIT_REPO="${git_repo}"
GIT_BRANCH="${git_branch}"
APP_PORT="${app_port}"
LISTENER_PORT="${listener_port}"

echo "==> Updating system and installing base tools"
yum update -y
yum install -y git python3 python3-pip nginx curl tar

# --- uv (fast Python tooling) ---
echo "==> Installing uv for ec2-user (preferred)"
sudo -u ec2-user bash -c 'curl -LsSf https://astral.sh/uv/install.sh | sh'
export PATH="/home/ec2-user/.local/bin:/root/.local/bin:$PATH"

# --- Node.js + pm2 ---
echo "==> Installing Node.js + pm2"
curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
yum install -y nodejs
npm install -g pm2

# --- Clone source (git version) ---
echo "==> Cloning repo: $GIT_REPO ($GIT_BRANCH)"
rm -rf /opt/transcribe-studio
git clone --depth 1 --branch "$GIT_BRANCH" "$GIT_REPO" /opt/transcribe-studio
chown -R ec2-user:ec2-user /opt/transcribe-studio

# Data dir (persistent)
mkdir -p /var/lib/transcribe-studio
chown -R ec2-user:ec2-user /var/lib/transcribe-studio

# --- Install with uv (in venv for cleanliness) ---
echo "==> Installing dependencies with uv (editable)"
sudo -u ec2-user bash -c '
  export PATH="$HOME/.local/bin:$PATH"
  cd /opt/transcribe-studio
  uv venv --python python3 .venv
  source .venv/bin/activate
  uv pip install -e .
'

# --- pm2 ecosystem (runs uvicorn directly via source) ---
echo "==> Configuring pm2"
cat > /opt/transcribe-studio/ecosystem.config.js <<'PM2EOF'
module.exports = {
  apps: [{
    name: "transcribe",
    cwd: "/opt/transcribe-studio",
    script: "./.venv/bin/uvicorn",
    args: "app.main:app --host 0.0.0.0 --port 8082",
    interpreter: "none",
    env: {
      TRANSCRIBE_STUDIO_DATA: "/var/lib/transcribe-studio",
      TRANSCRIBE_STUDIO_HOST: "0.0.0.0",
      TRANSCRIBE_STUDIO_PORT: "8082"
    },
    instances: 1,
    exec_mode: "fork",
    autorestart: true,
    watch: false,
    max_memory_restart: "700M"
  }]
};
PM2EOF

chown ec2-user:ec2-user /opt/transcribe-studio/ecosystem.config.js

# Start pm2 as ec2-user + make it survive reboots
sudo -u ec2-user bash -c '
  export PATH="$HOME/.local/bin:/usr/bin:$PATH"
  cd /opt/transcribe-studio
  pm2 start ecosystem.config.js
  pm2 save
  pm2 startup systemd -u ec2-user --hp /home/ec2-user | bash
'

# --- Nginx reverse proxy (port 80 -> app) ---
cat > /etc/nginx/conf.d/transcribe-studio.conf <<NGINX
server {
    listen ${LISTENER_PORT} default_server;
    listen [::]:${LISTENER_PORT} default_server;
    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}
NGINX

systemctl daemon-reload
systemctl enable nginx
systemctl restart nginx

echo "==> Deployment complete. App managed by pm2."
echo "==> Check: sudo -u ec2-user pm2 status"
echo "==> Logs:  sudo -u ec2-user pm2 logs transcribe"
echo "==> Public URL will be on port ${LISTENER_PORT}"