#!/usr/bin/env bash
set -euo pipefail

REPO="devkyato/TapAuth"
TARGET_DIR="${1:-$HOME/TapAuth}"

if ! command -v gh >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y gh
fi

if gh auth status >/dev/null 2>&1; then
  if [[ -d "$TARGET_DIR/.git" ]]; then
    cd "$TARGET_DIR"
    gh repo sync "$REPO" --branch main
  else
    gh repo clone "$REPO" "$TARGET_DIR" -- --branch main
  fi
else
  echo "GitHub CLI is installed but not logged in. Run: gh auth login"
  echo "Falling back to public git access."
  if [[ -d "$TARGET_DIR/.git" ]]; then
    cd "$TARGET_DIR"
    git pull origin main
  else
    git clone "https://github.com/$REPO.git" "$TARGET_DIR"
  fi
fi

cd "$TARGET_DIR"
echo "Repository ready at $TARGET_DIR"
echo "Next: cp .env.example .env && nano .env && bash scripts/setup_raspberry_pi.sh"
