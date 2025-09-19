cd ~/resource_management
exec /home/probotix/venvs/resource_venv/bin/gunicorn \
  --workers 3 --timeout 120 --bind 0.0.0.0:8000 \
  --pid /run/gunicorn.resource/gunicorn.pid \
  ResourceManagement.wsgi:application
