#!/usr/bin/env bash
# Clean shutdown: stop all containers on EC2, then stop the EC2 instance.
# No backup. To backup first, use scripts/backup-ec2-to-s3-and-shutdown.sh
#
# Usage:
#   ./scripts/shutdown-ec2-containers-and-instance.sh [INSTANCE_ID]

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY_FILE="${REPO_ROOT}/cspulse-v6-key.pem"
AWS_REGION="${AWS_REGION:-us-east-1}"

INSTANCE_ID="${1:-${CSPULSE_EC2_INSTANCE_ID}}"
if [[ -z "$INSTANCE_ID" ]]; then
  INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=cspulse-v6" "Name=instance-state-name,Values=running" \
    --query 'Reservations[*].Instances[*].InstanceId' --output text --region "$AWS_REGION" 2>/dev/null | head -1)
fi
if [[ -z "$INSTANCE_ID" ]]; then
  echo "No running cspulse-v6 instance found."
  exit 1
fi

if [[ ! -f "$KEY_FILE" ]]; then
  echo "SSH key not found: $KEY_FILE"
  exit 1
fi

PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region "$AWS_REGION" 2>/dev/null)
if [[ -z "$PUBLIC_IP" || "$PUBLIC_IP" == "None" ]]; then
  echo "Could not get public IP for $INSTANCE_ID"
  exit 1
fi

echo "=== Clean shutdown EC2 ==="
echo "  Instance:  $INSTANCE_ID"
echo "  Public IP: $PUBLIC_IP"
echo ""
echo "1. Stopping containers on EC2..."
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" \
  "cd ~/cspulse && docker compose -f docker-compose.ec2-registry.yml -f docker-compose.ec2-loaddriver.yml down --remove-orphans 2>/dev/null || true"
echo "   Containers stopped."
echo "2. Stopping EC2 instance..."
aws ec2 stop-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" --output text
echo "   Instance stop requested."
echo "Done. Rehydrate later with: ./scripts/rehydrate-ec2-ecr.sh"
