#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$HOME/resource_management"
VENV="/home/probotix/venvs/resource_venv/bin/activate"
PIDFILE="/run/gunicorn.resource/gunicorn.pid"
BACKUP_REMOTE="backup"
MAIN_REMOTE="origin"
MAIN_BRANCH="main"
BACKUP_DIR="$HOME/rm_backups"

cd "$APP_DIR"

TS=$(date +"%Y%m%d-%H%M%S")
SNAP_BRANCH="server-snapshot/$TS"
SNAP_TAG="pre-deploy-$TS"

echo "==> Backing up current code to $BACKUP_REMOTE as $SNAP_BRANCH + tag $SNAP_TAG"
git checkout -B "$SNAP_BRANCH"
git add -A
git commit -m "Server snapshot at $TS (pre-deploy)" || true
git tag -a "$SNAP_TAG" -m "Snapshot before deploy at $TS"
git push "$BACKUP_REMOTE" "$SNAP_BRANCH"
git push "$BACKUP_REMOTE" "$SNAP_TAG"

echo "==> Backing up DB/media locally to $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"
[ -f db.sqlite3 ] && cp db.sqlite3 "$BACKUP_DIR/db-$TS.sqlite3"
[ -d media ] && tar -czf "$BACKUP_DIR/media-$TS.tgz" media/ 2>/dev/null || true

echo "==> Pulling latest code from $MAIN_REMOTE/$MAIN_BRANCH"
git fetch "$MAIN_REMOTE"
git checkout -B "$MAIN_BRANCH" "$MAIN_REMOTE/$MAIN_BRANCH"
git reset --hard "$MAIN_REMOTE/$MAIN_BRANCH"

echo "==> Rebuilding and migrating"
source "$VENV"
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput

echo '==> Reloading gunicorn'
if [ -f "$PIDFILE" ]; then
  kill -HUP "$(cat "$PIDFILE")" || true
else
  echo "No PID file; starting gunicorn..."
  "$APP_DIR/start_gunicorn.sh"
fi

echo "==> Smoke test"
if curl -fsS http://127.0.0.1:8000/ >/dev/null; then
  echo "✅ Deploy OK"
else
  echo "❌ Deploy looks broken — rolling back to $SNAP_TAG"
  git reset --hard "$SNAP_TAG"
  source "$VENV"
  pip install -r requirements.txt
  python manage.py collectstatic --noinput
  "$APP_DIR/stop_gunicorn.sh" || true
  "$APP_DIR/start_gunicorn.sh"
  curl -fsS http://127.0.0.1:8000/ >/dev/null && echo "✅ Rolled back" || echo "❌ Rollback failed"
fi
