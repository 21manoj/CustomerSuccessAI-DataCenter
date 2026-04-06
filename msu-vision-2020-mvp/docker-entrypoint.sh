#!/bin/sh
set -e
python manage.py migrate --noinput
# Fresh SQLite (e.g. new EB container) has no users — seed so demo/demo works. Idempotent if data exists.
if ! python manage.py shell -c "from django.contrib.auth import get_user_model; import sys; sys.exit(0 if get_user_model().objects.filter(username='demo').exists() else 1)"; then
  python manage.py load_demo_data
fi
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
