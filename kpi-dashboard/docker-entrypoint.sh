#!/bin/bash
set -e

echo "=== CS Pulse Platform Starting ==="

# Run database migrations if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
    echo "Running database schema sync..."
    cd /app/backend
    python3 scripts/migrate_schema_sync.py 2>&1 || echo "Note: Schema sync completed with warnings (non-fatal)"

    # Named migrations (idempotent, safe to re-run)
    echo "Running named migrations..."
    python3 migrations/add_customer_id_to_wizard_learnings.py 2>&1 || echo "Note: wizard_learnings migration skipped (non-fatal)"

    # Legacy: flask db upgrade for Alembic migrations (if any)
    flask db upgrade 2>/dev/null || true

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

    echo "Starting Partner MCP server on port 8002..."
    (cd /app/backend && FEATURE_MCP_SERVER=true python3 mcp_server/partner_mcp_server.py http) &
fi

# Start Nginx in background (serves React frontend + proxies /api/)
echo "Starting Nginx..."
nginx -g "daemon on;"

# Start Flask backend with Gunicorn
# PID file enables zero-downtime reload via: kill -HUP $(cat /tmp/gunicorn.pid)
# Graceful timeout gives in-flight requests 30s to finish before worker kill
echo "Starting Gunicorn (workers=${GUNICORN_WORKERS:-4}, timeout=${GUNICORN_TIMEOUT:-120})..."
cd /app/backend
exec gunicorn \
    --bind 0.0.0.0:5059 \
    --workers "${GUNICORN_WORKERS:-4}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --graceful-timeout 30 \
    --pid /tmp/gunicorn.pid \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    "app_v3_minimal:app"
