#!/usr/bin/env bash
# Backup EC2 (Postgres + app volumes) to S3, then stop all containers and the EC2 instance.
# Use for overnight/weekend shutdown; rehydrate tomorrow with ./scripts/rehydrate-ec2-ecr.sh
#
# Requires: AWS CLI, SSH key (cspulse-v6-key.pem). Optional: CSPULSE_S3_BUCKET, CSPULSE_EC2_INSTANCE_ID.
#
# Usage:
#   ./scripts/backup-ec2-to-s3-and-shutdown.sh [INSTANCE_ID]
#   CSPULSE_S3_BUCKET=my-bucket ./scripts/backup-ec2-to-s3-and-shutdown.sh

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY_FILE="${REPO_ROOT}/cspulse-v6-key.pem"
AWS_REGION="${AWS_REGION:-us-east-1}"

# Instance (same discovery as rehydrate)
INSTANCE_ID="${1:-${CSPULSE_EC2_INSTANCE_ID}}"
if [[ -z "$INSTANCE_ID" ]]; then
  INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=cspulse-v6" "Name=instance-state-name,Values=running" \
    --query 'Reservations[*].Instances[*].InstanceId' --output text --region "$AWS_REGION" 2>/dev/null | head -1)
fi
if [[ -z "$INSTANCE_ID" ]]; then
  echo "No running cspulse-v6 instance found. Set CSPULSE_EC2_INSTANCE_ID or pass instance ID."
  exit 1
fi

# S3 bucket (same default as upload-docker-images-to-s3.sh)
S3_BUCKET="${CSPULSE_S3_BUCKET:-cspulse-container-artifacts-$(aws sts get-caller-identity --query Account --output text 2>/dev/null)}"
S3_PREFIX="backups"
DATE=$(date +%Y%m%d_%H%M%S)

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

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

echo "=== Backup EC2 to S3 and shutdown ==="
echo "  Instance:   $INSTANCE_ID"
echo "  Public IP:  $PUBLIC_IP"
echo "  S3:         s3://${S3_BUCKET}/${S3_PREFIX}/"
echo "  Date:       $DATE"
echo ""

# 1) Postgres dump (stream from EC2 to local)
echo "1. Creating Postgres dump..."
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" \
  "docker exec cspulse-postgres pg_dump -U cspulse -d cs_pulse -Fc" > "$WORKDIR/cspulse-db-${DATE}.dump"

if [[ ! -s "$WORKDIR/cspulse-db-${DATE}.dump" ]]; then
  echo "   Warning: dump is empty or failed; continuing."
else
  echo "   Dump size: $(du -h "$WORKDIR/cspulse-db-${DATE}.dump" | cut -f1)"
fi

# 2) App volumes (uploads, verticals, instance) from platform container
echo "2. Archiving app volumes (uploads, verticals, instance)..."
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" \
  "docker exec cspulse-platform tar czf - -C /app/backend uploads verticals instance 2>/dev/null || true" \
  > "$WORKDIR/cspulse-volumes-${DATE}.tar.gz" || true
if [[ -s "$WORKDIR/cspulse-volumes-${DATE}.tar.gz" ]]; then
  echo "   Volumes size: $(du -h "$WORKDIR/cspulse-volumes-${DATE}.tar.gz" | cut -f1)"
else
  echo "   No volume archive (container may be down or empty); skipping."
  rm -f "$WORKDIR/cspulse-volumes-${DATE}.tar.gz"
fi

# 3) Upload to S3
echo "3. Uploading to S3..."
aws s3 cp "$WORKDIR/cspulse-db-${DATE}.dump" "s3://${S3_BUCKET}/${S3_PREFIX}/cspulse-db-${DATE}.dump" --region "$AWS_REGION"
[[ -f "$WORKDIR/cspulse-volumes-${DATE}.tar.gz" ]] && [[ -s "$WORKDIR/cspulse-volumes-${DATE}.tar.gz" ]] && \
  aws s3 cp "$WORKDIR/cspulse-volumes-${DATE}.tar.gz" "s3://${S3_BUCKET}/${S3_PREFIX}/cspulse-volumes-${DATE}.tar.gz" --region "$AWS_REGION"
echo "   Done: s3://${S3_BUCKET}/${S3_PREFIX}/cspulse-db-${DATE}.dump"

# 4) Stop all containers on EC2
echo "4. Stopping containers on EC2..."
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" \
  "cd ~/cspulse && docker compose -f docker-compose.ec2-registry.yml -f docker-compose.ec2-loaddriver.yml down --remove-orphans 2>/dev/null || true"
echo "   Containers stopped."

# 5) Stop EC2 instance
echo "5. Stopping EC2 instance..."
aws ec2 stop-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" --output text
echo "   Instance stop requested."

echo ""
echo "=== Done ==="
echo "  Backup: s3://${S3_BUCKET}/${S3_PREFIX}/cspulse-db-${DATE}.dump (and volumes if present)"
echo "  Instance $INSTANCE_ID is stopping. Rehydrate tomorrow with:"
echo "    ./scripts/rehydrate-ec2-ecr.sh $INSTANCE_ID"
echo "  Then update CloudFront origin if the public IP changed (see docs/EC2_STOP_START_SAVE_COST.md)."
