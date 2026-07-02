#!/bin/bash
set -euxo pipefail

APP_PORT="${app_port}"
LISTENER_PORT="${listener_port}"
APP_PACKAGE="${app_package}"

yum update -y
yum install -y python3 python3-pip nginx

python3 -m pip install --upgrade pip
python3 -m pip install "$APP_PACKAGE"

mkdir -p /var/lib/transcribe-studio
chown -R ec2-user:ec2-user /var/lib/transcribe-studio

cat > /etc/systemd/system/transcribe-studio.service <<UNIT
[Unit]
Description=Transcribe Studio
After=network.target

[Service]
Type=simple
User=ec2-user
Environment=TRANSCRIBE_STUDIO_DATA=/var/lib/transcribe-studio
Environment=TRANSCRIBE_STUDIO_HOST=127.0.0.1
Environment=TRANSCRIBE_STUDIO_PORT=$APP_PORT
ExecStart=/usr/local/bin/transcribe-studio --host 127.0.0.1 --port $APP_PORT
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

# Fallback if console script is not on PATH
if [ ! -x /usr/local/bin/transcribe-studio ]; then
  sed -i 's|ExecStart=.*|ExecStart=/usr/bin/python3 -m app --host 127.0.0.1 --port '"$APP_PORT"'|' /etc/systemd/system/transcribe-studio.service
fi

cat > /etc/nginx/conf.d/transcribe-studio.conf <<NGINX
server {
    listen $LISTENER_PORT default_server;
    listen [::]:$LISTENER_PORT default_server;
    server_name _;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
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
systemctl enable nginx transcribe-studio
systemctl restart nginx
systemctl restart transcribe-studio