#!/usr/bin/env bash
# Run backup-ec2-to-s3-and-shutdown.sh in 3 hours. Keep this process running (e.g. in tmux/screen or with nohup).
#
# Usage:
#   nohup ./scripts/schedule-backup-and-shutdown-in-3h.sh > /tmp/backup-shutdown.log 2>&1 &
#   # Or in a terminal you won't close: ./scripts/schedule-backup-and-shutdown-in-3h.sh

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/backup-ec2-to-s3-and-shutdown.sh"
DELAY=$((3 * 3600))   # 3 hours

WHEN=$(date -v+3H 2>/dev/null || date -d '+3 hours' 2>/dev/null || echo "in 3 hours")
echo "Scheduled: backup EC2 to S3 and shutdown in 3 hours ($WHEN)."
echo "Waiting ${DELAY} seconds..."
sleep "$DELAY"
echo "Running backup and shutdown..."
exec "$SCRIPT"
