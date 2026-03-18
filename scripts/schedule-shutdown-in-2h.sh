#!/usr/bin/env bash
# Run shutdown-ec2-containers-and-instance.sh in 2 hours.
# Keep this process running (e.g. nohup or in tmux/screen).
#
# Usage:
#   nohup ./scripts/schedule-shutdown-in-2h.sh > /tmp/ec2-shutdown.log 2>&1 &

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="${REPO_ROOT}/scripts/shutdown-ec2-containers-and-instance.sh"
DELAY=$((2 * 3600))   # 2 hours

WHEN=$(date -v+2H 2>/dev/null || date -d '+2 hours' 2>/dev/null || echo "in 2 hours")
echo "Scheduled: clean shutdown (containers + EC2) in 2 hours ($WHEN)."
echo "Waiting ${DELAY} seconds..."
sleep "$DELAY"
echo "Running shutdown..."
exec "$SCRIPT"
