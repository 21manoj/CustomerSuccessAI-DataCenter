#!/bin/bash
# Zero-downtime Gunicorn reload — sends HUP to master process.
# Workers gracefully finish in-flight requests (30s timeout), then restart.
#
# Usage (on EC2):
#   docker exec cspulse-platform /app/scripts/gunicorn-reload.sh
#
# What HUP does:
#   1. Master forks new workers with fresh code
#   2. Old workers finish current requests (up to --graceful-timeout 30s)
#   3. Old workers are replaced by new ones
#   4. Zero dropped connections
#
# When to use:
#   - After docker cp of Python files into container
#   - After config JSON changes (health_thresholds.json, etc.)
#   - NOT needed after full docker compose up -d (that restarts everything)

PID_FILE="/tmp/gunicorn.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "ERROR: $PID_FILE not found — is Gunicorn running?"
    exit 1
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    echo "Sending HUP to Gunicorn master (PID=$PID)..."
    kill -HUP "$PID"
    echo "Reload signal sent. Workers will gracefully restart within 30s."
else
    echo "ERROR: Gunicorn process $PID is not running."
    exit 1
fi
