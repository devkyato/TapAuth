#!/usr/bin/env bash
set -euo pipefail

echo "== USB readers =="
lsusb || true

echo
echo "== libnfc scan =="
nfc-scan-device -v || true

echo
echo "== pcscd status =="
systemctl status pcscd --no-pager || true

echo
echo "== Airhub service last logs =="
journalctl -u airhub.service -n 80 --no-pager || true

echo
echo "If ACR122U is USB busy, run:"
echo "  sudo systemctl stop pcscd"
echo "  sudo systemctl disable pcscd"
echo "  sudo systemctl restart airhub.service"
echo "Then unplug/replug the reader."