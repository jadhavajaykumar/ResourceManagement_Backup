#!/usr/bin/env bash
set -e
echo "== Service =="
systemctl is-active --quiet gunicorn.resource && echo "gunicorn: active" || (echo "gunicorn: NOT active"; exit 1)
echo "== HTTP =="
curl -sSI http://127.0.0.1:8000/ | head -n1
curl -sSI http://127.0.0.1:8000/accounts/login/ | grep -i '^set-cookie' || echo "No Set-Cookie seen"
echo "== Static =="
curl -sSI http://127.0.0.1:8000/static/images/logo.png | head -n1
echo "== Done =="
