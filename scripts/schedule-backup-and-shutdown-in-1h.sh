#!/usr/bin/env bash
# Run backup-ec2-to-s3-and-shutdown.sh in 1 hour. Same backup + shutdown as the 3h script.
#
# Usage:
#   nohup ./scripts/schedule-backup-and-shutdown-in-1h.sh > /tmp/backup-shutdown.log 2>&1 &

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/backup-ec2-to-s3-and-shutdown.sh"
DELAY=$((1 * 3600))   # 1 hour

WHEN=$(date -v+1H 2>/dev/null || date -d '+1 hour' 2>/dev/null || echo "in 1 hour")
echo "Scheduled: backup EC2 to S3 and shutdown in 1 hour ($WHEN)."
echo "Waiting ${DELAY} seconds..."
sleep "$DELAY"
echo "Running backup and shutdown..."
exec "$SCRIPT"
