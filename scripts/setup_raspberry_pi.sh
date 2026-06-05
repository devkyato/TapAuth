#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
SERVICE_NAME="airhub.service"
RUN_USER="${SUDO_USER:-$USER}"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
  cat <<EOF
Created $ENV_FILE.
Edit it first, then rerun this setup script:
  nano $ENV_FILE
  bash scripts/setup_raspberry_pi.sh
EOF
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

DB_NAME="${AIRHUB_DB_NAME:-airhub_db}"
DB_USER="${AIRHUB_DB_USER:-}"
DB_PASSWORD="${AIRHUB_DB_PASSWORD:-}"

if [[ -z "$DB_USER" || -z "$DB_PASSWORD" || "$DB_USER" == "your_mysql_user" || "$DB_PASSWORD" == "your_mysql_password" ]]; then
  cat <<EOF
Please set real MySQL credentials in $ENV_FILE before setup.
Required:
  AIRHUB_DB_USER=...
  AIRHUB_DB_PASSWORD=...
EOF
  exit 1
fi

if [[ "$DB_USER" == *"'"* || "$DB_PASSWORD" == *"'"* || "$DB_NAME" == *"'"* ]]; then
  echo "For automated setup, AIRHUB_DB_USER, AIRHUB_DB_PASSWORD, and AIRHUB_DB_NAME must not contain single quotes."
  exit 1
fi

sudo apt-get update
sudo apt-get install -y \
  git \
  python3 \
  python3-venv \
  python3-pip \
  mariadb-server \
  mariadb-client \
  libnfc-bin \
  libnfc-dev \
  libfreefare-bin \
  libfreefare-dev \
  pcscd \
  pcsc-tools

python3 -m venv "$PROJECT_DIR/.venv"
"$PROJECT_DIR/.venv/bin/pip" install --upgrade pip
"$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

sudo systemctl enable --now mariadb

sudo mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
SQL

MYSQL_PWD="$DB_PASSWORD" mysql -u "$DB_USER" "$DB_NAME" < "$PROJECT_DIR/schema.sql"

sudo usermod -aG plugdev "$RUN_USER" || true
cat <<'EOF' | sudo tee /etc/udev/rules.d/99-acr122u.rules >/dev/null
SUBSYSTEM=="usb", ATTR{idVendor}=="072f", ATTR{idProduct}=="2200", MODE="0666", GROUP="plugdev"
EOF
sudo udevadm control --reload-rules || true
sudo udevadm trigger || true

# pcscd often claims the ACR122U before libnfc can use it.
sudo systemctl stop pcscd || true
sudo systemctl disable pcscd || true

sudo tee "/etc/systemd/system/$SERVICE_NAME" >/dev/null <<EOF
[Unit]
Description=APC Airhub NFC Flask App
After=network-online.target mariadb.service
Wants=network-online.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$PROJECT_DIR/.venv/bin/python $PROJECT_DIR/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

cat <<EOF
APC Airhub setup complete.

Service status:
  sudo systemctl status $SERVICE_NAME

Logs:
  journalctl -u $SERVICE_NAME -f

Open:
  http://$(hostname -I | awk '{print $1}'):5000/

Hidden registration:
  http://$(hostname -I | awk '{print $1}'):5000/airhub-register

If the ACR122U still shows USB busy, unplug it, wait 5 seconds, plug it back in, then run:
  sudo systemctl restart $SERVICE_NAME
EOF