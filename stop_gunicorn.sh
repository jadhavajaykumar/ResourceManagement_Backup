PIDFILE=/run/gunicorn.resource/gunicorn.pid
[ -f "$PIDFILE" ] && kill -TERM "$(cat "$PIDFILE")" || true
sleep 2
pgrep -f "gunicorn.*ResourceManagement.wsgi" >/dev/null && pkill -f "gunicorn.*ResourceManagement.wsgi" || true
