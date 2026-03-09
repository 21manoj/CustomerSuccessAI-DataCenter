#!/bin/bash
set -e

echo "=== CS Pulse Platform Starting ==="

# Run database migrations if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
    echo "Running database migrations..."
    cd /app/backend
    flask db upgrade 2>/dev/null || echo "Note: Migrations skipped (run manually if needed)"

    # Ensure UUID columns exist (idempotent ALTER TABLE IF NOT EXISTS)
    echo "Ensuring UUID columns exist..."
    python -c "
from app_v3_minimal import app
from extensions import db
with app.app_context():
    with db.engine.connect() as conn:
        conn.execute(db.text(\"ALTER TABLE customers ADD COLUMN IF NOT EXISTS uuid VARCHAR(60) UNIQUE\"))
        conn.execute(db.text(\"ALTER TABLE customers ADD COLUMN IF NOT EXISTS vertical VARCHAR(20)\"))
        conn.execute(db.text(\"ALTER TABLE accounts ADD COLUMN IF NOT EXISTS uuid VARCHAR(60) UNIQUE\"))
        conn.execute(db.text(\"ALTER TABLE accounts ADD COLUMN IF NOT EXISTS customer_uuid VARCHAR(60)\"))
        conn.execute(db.text(\"ALTER TABLE users ADD COLUMN IF NOT EXISTS uuid VARCHAR(60) UNIQUE\"))
        conn.execute(db.text(\"ALTER TABLE users ADD COLUMN IF NOT EXISTS customer_uuid VARCHAR(60)\"))
        conn.commit()
    print('UUID columns ensured.')
" 2>/dev/null || echo "Note: UUID column check skipped"

    # Backfill UUIDs for existing records (idempotent)
    echo "Running UUID backfill..."
    python -c "
from app_v3_minimal import app
with app.app_context():
    from uuid_backfill import backfill_uuids_safe
    stats = backfill_uuids_safe()
    total = stats.get('customers_updated', 0) + stats.get('accounts_updated', 0) + stats.get('users_updated', 0)
    print(f'UUID backfill: {total} records updated')
" 2>/dev/null || echo "Note: UUID backfill skipped"
fi

# Start MCP server in background when enabled (port 8001)
if [ "${FEATURE_MCP_SERVER}" = "true" ]; then
    echo "Starting MCP server on port 8001..."
    (cd /app/backend && FEATURE_MCP_SERVER=true python3 mcp_server/cs_pulse_mcp_server.py http) &
fi

# Start Nginx in background (serves React frontend + proxies /api/)
echo "Starting Nginx..."
nginx -g "daemon on;"

# Start Flask backend with Gunicorn
echo "Starting Gunicorn (workers=${GUNICORN_WORKERS:-4}, timeout=${GUNICORN_TIMEOUT:-120})..."
cd /app/backend
exec gunicorn \
    --bind 0.0.0.0:5059 \
    --workers "${GUNICORN_WORKERS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "app_v3_minimal:app"
