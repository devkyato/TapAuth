#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
SERVICE_NAME="airhub.service"
RUN_USER="${SUDO_USER:-$USER}"
RUN_HOME="$(getent passwd "$RUN_USER" | cut -d: -f6)"

if [[ ! -f "$ENV_FILE" && ! -f "$PROJECT_DIR/data/settings.json" ]]; then
  python3 "$PROJECT_DIR/scripts/configure.py"
fi
cd "$PROJECT_DIR"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

DB_NAME="${AIRHUB_DB_NAME:-$(python3 -c 'from config import MYSQL_CONFIG; print(MYSQL_CONFIG["database"])')}"
DB_USER="${AIRHUB_DB_USER:-$(python3 -c 'from config import MYSQL_CONFIG; print(MYSQL_CONFIG["user"])')}"
DB_PASSWORD="${AIRHUB_DB_PASSWORD:-$(python3 -c 'from config import MYSQL_CONFIG; print(MYSQL_CONFIG["password"])')}"
ADMIN_CODE="${TAPAUTH_ADMIN_CODE:-$(python3 -c 'from config import ACCESS_CONFIG; print(ACCESS_CONFIG["admin_code"])')}"
STORAGE="${AIRHUB_STORAGE:-$(python3 -c 'from config import APP_CONFIG; print(APP_CONFIG["active_storage"])')}"

if [[ "$STORAGE" == "mysql" && ( -z "$DB_USER" || -z "$DB_PASSWORD" || "$DB_USER" == "your_mysql_user" || "$DB_PASSWORD" == "your_mysql_password" ) ]]; then
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

if [[ "$STORAGE" == "mysql" ]]; then
  sudo apt-get install -y mariadb-server mariadb-client
  "$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements-mysql.txt"
  sudo systemctl enable --now mariadb
  sudo mysql <<SQL
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'localhost';
FLUSH PRIVILEGES;
SQL
  MYSQL_PWD="$DB_PASSWORD" mysql -u "$DB_USER" "$DB_NAME" < "$PROJECT_DIR/schema.sql"
fi
"$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/scripts/sync_local_registry.py" || echo "Warning: registry reconciliation failed; TapAuth can retry after startup."

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
After=local-fs.target

[Service]
Type=simple
User=$RUN_USER
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=-$ENV_FILE
Environment=PYTHONUNBUFFERED=1
ExecStart=$PROJECT_DIR/.venv/bin/python $PROJECT_DIR/app.py
Restart=always
RestartSec=5
TimeoutStopSec=15

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
sudo systemctl disable --now airhub-update.service 2>/dev/null || true
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

cat <<EOF
TapAuth setup complete.

Storage backend:
  $STORAGE

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

Updates are intentionally manual so a network outage cannot delay kiosk startup:
  bash scripts/update_pi_from_github.sh
EOF
