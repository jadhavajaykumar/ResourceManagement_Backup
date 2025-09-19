PIDFILE=/run/gunicorn.resource/gunicorn.pid
[ -f "$PIDFILE" ] && kill -HUP "$(cat "$PIDFILE")" || true
