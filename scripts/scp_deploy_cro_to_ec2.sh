#!/usr/bin/env bash
# SCP changed CRO phase files to EC2 and rebuild cs-pulse (native amd64).
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY="${CSPULSE_SSH_KEY_FILE:-$REPO_ROOT/cspulse-v6-key.pem}"
HOST="${CSPULSE_EC2_HOST:-ec2-user@3.94.106.197}"
REMOTE_DIR="${CSPULSE_REPO_DIR:-/home/ec2-user/CustomerSuccessAI-DataCenter}"

FILES=(
  kpi-dashboard/src/components/dashboard/CRODashboard.tsx
  kpi-dashboard/src/components/dashboard/CROOverviewHonesty.tsx
  kpi-dashboard/backend/executive_dashboard_api.py
  kpi-dashboard/backend/ask_ai_endpoint.py
  scripts/verify_cro_phases_ec2.py
)

echo "=== SCP ${#FILES[@]} files to $HOST ==="
for f in "${FILES[@]}"; do
  dest="$REMOTE_DIR/$f"
  ssh -o StrictHostKeyChecking=no -i "$KEY" "$HOST" "mkdir -p $(dirname "$dest")"
  scp -o StrictHostKeyChecking=no -i "$KEY" "$REPO_ROOT/$f" "$HOST:$dest"
  echo "  $f"
done

echo "=== Rebuild cs-pulse on EC2 ==="
ssh -o StrictHostKeyChecking=no -i "$KEY" "$HOST" "cd $REMOTE_DIR/kpi-dashboard && \
  chmod +x ../scripts/ensure-ec2-docker-buildx.sh && \
  ../scripts/ensure-ec2-docker-buildx.sh && \
  sudo docker compose -p cspulse -f docker-compose.ec2-build.yml build cs-pulse && \
  sudo docker compose -p cspulse -f docker-compose.ec2-build.yml up -d cs-pulse"

echo "=== Done ==="
