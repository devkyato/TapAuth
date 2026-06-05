#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

sudo apt-get update
sudo apt-get install -y \
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
sudo systemctl enable --now pcscd

mysql -u root < "$PROJECT_DIR/schema.sql"

cat <<'EOF'
Raspberry Pi setup complete.

Start the app with:
  source .venv/bin/activate
  python app.py

Then open:
  http://<raspberry-pi-ip>:5000
EOF
