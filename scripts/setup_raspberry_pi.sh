#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
SERVICE_NAME="airhub.service"
UPDATE_SERVICE_NAME="airhub-update.service"
RUN_USER="${SUDO_USER:-$USER}"
RUN_HOME="$(getent passwd "$RUN_USER" | cut -d: -f6)"

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
ADMIN_CODE="${TAPAUTH_ADMIN_CODE:-${AIRHUB_REGISTRATION_CODE:-}}"

if [[ -z "$DB_USER" || -z "$DB_PASSWORD" || "$DB_USER" == "your_mysql_user" || "$DB_PASSWORD" == "your_mysql_password" || "$DB_PASSWORD" == "replace-with-a-strong-password" ]]; then
  cat <<EOF
Please set real MySQL credentials in $ENV_FILE before setup.
Required:
  AIRHUB_DB_USER=...
  AIRHUB_DB_PASSWORD=...
EOF
  exit 1
fi

if [[ -z "$ADMIN_CODE" || "$ADMIN_CODE" == "replace-with-a-private-admin-code" ]]; then
  echo "Set a private TAPAUTH_ADMIN_CODE in $ENV_FILE before setup."
  exit 1
fi

if [[ "$DB_USER" == *"'"* || "$DB_PASSWORD" == *"'"* || "$DB_NAME" == *"'"* ]]; then
  echo "For automated setup, AIRHUB_DB_USER, AIRHUB_DB_PASSWORD, and AIRHUB_DB_NAME must not contain single quotes."
  exit 1
fi

sudo apt-get update
sudo apt-get install -y \
  git \
  gh \
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

sudo timedatectl set-ntp true || true
sudo systemctl restart systemd-timesyncd || true

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
"$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/scripts/sync_local_registry.py" || echo "Warning: MySQL registry import failed; TapAuth will create the local registry on first registration."

sudo usermod -aG plugdev "$RUN_USER" || true
cat <<'EOF' | sudo tee /etc/udev/rules.d/99-acr122u.rules >/dev/null
SUBSYSTEM=="usb", ATTR{idVendor}=="072f", ATTR{idProduct}=="2200", MODE="0666", GROUP="plugdev"
EOF
sudo udevadm control --reload-rules || true
sudo udevadm trigger || true

# pcscd often claims the ACR122U before libnfc can use it.
sudo systemctl stop pcscd || true
sudo systemctl disable pcscd || true
echo "blacklist pn533_usb" | sudo tee /etc/modprobe.d/blacklist-libnfc.conf >/dev/null || true

sudo tee "/etc/systemd/system/$SERVICE_NAME" >/dev/null <<EOF
[Unit]
Description=TapAuth NFC Flask App
After=network-online.target mariadb.service $UPDATE_SERVICE_NAME
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

sudo tee "/etc/systemd/system/$UPDATE_SERVICE_NAME" >/dev/null <<EOF
[Unit]
Description=Update TapAuth from GitHub on boot
After=network-online.target mariadb.service
Wants=network-online.target

[Service]
Type=oneshot
User=$RUN_USER
WorkingDirectory=$PROJECT_DIR
Environment=AIRHUB_SKIP_SERVICE_RESTART=1
ExecStart=/usr/bin/bash $PROJECT_DIR/scripts/update_pi_from_github.sh
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

if [[ -n "$RUN_HOME" && -d "$RUN_HOME" ]]; then
  AUTOSTART_DIR="$RUN_HOME/.config/autostart"
  sudo -u "$RUN_USER" mkdir -p "$AUTOSTART_DIR"
  sudo -u "$RUN_USER" tee "$AUTOSTART_DIR/airhub-kiosk.desktop" >/dev/null <<EOF
[Desktop Entry]
Type=Application
Name=TapAuth Kiosk
Exec=sh -c 'sleep 8; BROWSER=$(command -v chromium-browser || command -v chromium || command -v chromium/chromium); exec "$BROWSER" --kiosk --disable-extensions --disable-background-networking --disable-sync --disable-gpu --noerrdialogs --disable-infobars http://127.0.0.1:5000/'
X-GNOME-Autostart-enabled=true
EOF
fi

sudo systemctl daemon-reload
sudo systemctl enable "$UPDATE_SERVICE_NAME"
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

cat <<EOF
TapAuth setup complete.

Service status:
  sudo systemctl status $SERVICE_NAME

Logs:
  journalctl -u $SERVICE_NAME -f

Open:
  http://$(hostname -I | awk '{print $1}'):5000/

Hidden registration:
  http://$(hostname -I | awk '{print $1}'):5000/airhub-register?code=$ADMIN_CODE

iPhone registration on the same Wi-Fi:
  http://$(hostname -I | awk '{print $1}'):5000/airhub-register?code=$ADMIN_CODE

Chromium kiosk autostart:
  $RUN_HOME/.config/autostart/airhub-kiosk.desktop

If the ACR122U still shows USB busy, unplug it, wait 5 seconds, plug it back in, then run:
  sudo systemctl restart $SERVICE_NAME
EOF
