#!/usr/bin/env bash
set -euo pipefail
APP_DIR=/home/probotix/resource_management
VENV=/home/probotix/venvs/resource_venv
cd "$APP_DIR"

git fetch --all
# Use your correct branch name here (main or master)
git reset --hard origin/main

REQ=requirements-linux-py312.txt
[ -f "$REQ" ] || REQ=requirements.txt

"$VENV/bin/pip" install -U pip
"$VENV/bin/pip" install -r "$REQ"

"$VENV/bin/python" manage.py migrate --noinput
"$VENV/bin/python" manage.py collectstatic --noinput

# Try graceful reload; if it fails, restart
if ! sudo systemctl reload gunicorn.resource; then
  sudo systemctl restart gunicorn.resource
fi

echo "Deployed at $(date)"
