#!/usr/bin/env bash
# Nightly PostgreSQL backup to S3 — backup only, NO shutdown.
#
# Runs pg_dump on the EC2 Postgres container, uploads to S3, retains last 7 days.
# Designed to run as a cron job or scheduled task.
#
# Usage:
#   ./scripts/nightly-pg-backup-to-s3.sh              # uses auto-discovered instance
#   ./scripts/nightly-pg-backup-to-s3.sh i-0dec7f1d95b252853   # explicit instance
#
# Cron (Mac/Linux, run at 2 AM daily):
#   0 2 * * * /path/to/scripts/nightly-pg-backup-to-s3.sh >> /tmp/cspulse-backup.log 2>&1
#
# Retention: Keeps last 7 backups. Older files auto-deleted from S3 prefix.

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY_FILE="${REPO_ROOT}/cspulse-v6-key.pem"
AWS_REGION="${AWS_REGION:-us-east-1}"
RETENTION_DAYS=7

# Instance discovery (same as rehydrate)
INSTANCE_ID="${1:-${CSPULSE_EC2_INSTANCE_ID:-}}"
if [[ -z "$INSTANCE_ID" ]]; then
  INSTANCE_ID=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=cspulse-v6" "Name=instance-state-name,Values=running" \
    --query 'Reservations[*].Instances[*].InstanceId' --output text --region "$AWS_REGION" 2>/dev/null | head -1)
fi
if [[ -z "$INSTANCE_ID" ]]; then
  echo "[$(date)] ERROR: No running cspulse-v6 instance found."
  exit 1
fi

# S3 bucket
S3_BUCKET="${CSPULSE_S3_BUCKET:-cspulse-container-artifacts-$(aws sts get-caller-identity --query Account --output text 2>/dev/null)}"
S3_PREFIX="backups/nightly"
DATE=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="cspulse-db-${DATE}.dump"

if [[ ! -f "$KEY_FILE" ]]; then
  echo "[$(date)] ERROR: SSH key not found: $KEY_FILE"
  exit 1
fi

PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region "$AWS_REGION" 2>/dev/null)
if [[ -z "$PUBLIC_IP" || "$PUBLIC_IP" == "None" ]]; then
  echo "[$(date)] ERROR: Could not get public IP for $INSTANCE_ID"
  exit 1
fi

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

echo "[$(date)] === Nightly PG Backup ==="
echo "  Instance: $INSTANCE_ID ($PUBLIC_IP)"
echo "  S3:       s3://${S3_BUCKET}/${S3_PREFIX}/"

# 1) pg_dump (custom format, compressed)
echo "[$(date)] 1. Running pg_dump..."
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" \
  "docker exec cspulse-postgres pg_dump -U cspulse -d cs_pulse -Fc" > "$WORKDIR/$DUMP_FILE"

if [[ ! -s "$WORKDIR/$DUMP_FILE" ]]; then
  echo "[$(date)] ERROR: Dump is empty or failed!"
  exit 1
fi
DUMP_SIZE=$(du -h "$WORKDIR/$DUMP_FILE" | cut -f1)
echo "[$(date)]    Dump size: $DUMP_SIZE"

# 2) Upload to S3
echo "[$(date)] 2. Uploading to S3..."
aws s3 cp "$WORKDIR/$DUMP_FILE" "s3://${S3_BUCKET}/${S3_PREFIX}/${DUMP_FILE}" --region "$AWS_REGION" --quiet
echo "[$(date)]    Uploaded: s3://${S3_BUCKET}/${S3_PREFIX}/${DUMP_FILE}"

# 3) Retention — delete backups older than RETENTION_DAYS
echo "[$(date)] 3. Cleaning old backups (keeping last ${RETENTION_DAYS} days)..."
CUTOFF_DATE=$(date -v-${RETENTION_DAYS}d +%Y%m%d 2>/dev/null || date -d "-${RETENTION_DAYS} days" +%Y%m%d 2>/dev/null)
if [[ -n "$CUTOFF_DATE" ]]; then
  aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" --region "$AWS_REGION" 2>/dev/null | while read -r line; do
    FILE=$(echo "$line" | awk '{print $NF}')
    # Extract date from filename: cspulse-db-YYYYMMDD_HHMMSS.dump
    FILE_DATE=$(echo "$FILE" | grep -oE '[0-9]{8}' | head -1)
    if [[ -n "$FILE_DATE" && "$FILE_DATE" < "$CUTOFF_DATE" ]]; then
      echo "  Deleting old backup: $FILE (date=$FILE_DATE < cutoff=$CUTOFF_DATE)"
      aws s3 rm "s3://${S3_BUCKET}/${S3_PREFIX}/${FILE}" --region "$AWS_REGION" --quiet
    fi
  done
fi

echo "[$(date)] === Backup complete ==="
echo "  Latest: s3://${S3_BUCKET}/${S3_PREFIX}/${DUMP_FILE} ($DUMP_SIZE)"
echo "  Restore: pg_restore -U cspulse -d cs_pulse < ${DUMP_FILE}"
