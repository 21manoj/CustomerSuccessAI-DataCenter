#!/usr/bin/env bash
# ============================================================
# CS Pulse — PostgreSQL Backup to S3
# ============================================================
#
# Nightly pg_dump → gzip → upload to S3 bucket.
# Retains 30 days of daily backups.
#
# Usage:
#   # Manual run:
#   bash scripts/pg_backup_s3.sh
#
#   # Install as daily cron (run on EC2):
#   bash scripts/pg_backup_s3.sh --install-cron
#
#   # Restore from backup:
#   bash scripts/pg_backup_s3.sh --restore 2026-04-17
#
#   # List available backups:
#   bash scripts/pg_backup_s3.sh --list
#
# Environment:
#   PGBACKUP_S3_BUCKET  — S3 bucket (default: cspulse-backups)
#   PGBACKUP_S3_PREFIX  — S3 key prefix (default: pg-backups/)
#   PGBACKUP_CONTAINER  — postgres container name (default: cspulse-postgres)
#   PGBACKUP_DB         — database name (default: cs_pulse)
#   PGBACKUP_USER       — postgres user (default: cspulse)
#   PGBACKUP_RETAIN     — days to retain (default: 30)
#   AWS_REGION          — AWS region (default: us-east-1)
#
# ============================================================

set -euo pipefail

# Defaults
S3_BUCKET="${PGBACKUP_S3_BUCKET:-cspulse-backups}"
S3_PREFIX="${PGBACKUP_S3_PREFIX:-pg-backups/}"
CONTAINER="${PGBACKUP_CONTAINER:-cspulse-postgres}"
DB_NAME="${PGBACKUP_DB:-cs_pulse}"
DB_USER="${PGBACKUP_USER:-cspulse}"
RETAIN_DAYS="${PGBACKUP_RETAIN:-30}"
REGION="${AWS_REGION:-us-east-1}"

DATE=$(date -u +%Y-%m-%d)
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_FILE="cs_pulse_${DATE}.sql.gz"
S3_KEY="${S3_PREFIX}${BACKUP_FILE}"
LOCAL_TMP="/tmp/${BACKUP_FILE}"

ACTION="${1:-backup}"

# ── List available backups ──
if [[ "$ACTION" == "--list" ]]; then
    echo "=== Available backups in s3://${S3_BUCKET}/${S3_PREFIX} ==="
    aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}" --region "$REGION" 2>/dev/null | sort -r | head -30
    exit 0
fi

# ── Install cron ──
if [[ "$ACTION" == "--install-cron" ]]; then
    SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
    CRON_LINE="0 3 * * * /bin/bash ${SCRIPT_PATH} >> /var/log/cspulse-backup.log 2>&1"

    # Check if already installed
    if crontab -l 2>/dev/null | grep -q "pg_backup_s3"; then
        echo "Cron already installed:"
        crontab -l | grep "pg_backup_s3"
    else
        (crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
        echo "Cron installed: daily at 03:00 UTC"
        echo "  $CRON_LINE"
    fi
    exit 0
fi

# ── Restore from backup ──
if [[ "$ACTION" == "--restore" ]]; then
    RESTORE_DATE="${2:-}"
    if [[ -z "$RESTORE_DATE" ]]; then
        echo "Usage: $0 --restore YYYY-MM-DD"
        echo "Available backups:"
        aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}" --region "$REGION" 2>/dev/null | sort -r | head -10
        exit 1
    fi

    RESTORE_FILE="cs_pulse_${RESTORE_DATE}.sql.gz"
    RESTORE_KEY="${S3_PREFIX}${RESTORE_FILE}"
    RESTORE_LOCAL="/tmp/${RESTORE_FILE}"

    echo "=== Restoring from s3://${S3_BUCKET}/${RESTORE_KEY} ==="

    # Download
    aws s3 cp "s3://${S3_BUCKET}/${RESTORE_KEY}" "$RESTORE_LOCAL" --region "$REGION"

    # Confirm
    echo ""
    echo "WARNING: This will DROP and recreate the ${DB_NAME} database."
    echo "Press Ctrl+C to cancel, or Enter to continue..."
    read -r

    # Stop platform containers (keep postgres running)
    echo "Stopping platform containers..."
    sudo docker stop cspulse-platform cspulse-platform-b 2>/dev/null || true

    # Restore
    echo "Restoring database..."
    gunzip -c "$RESTORE_LOCAL" | sudo docker exec -i "$CONTAINER" psql -U "$DB_USER" -d postgres -c "
        SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DB_NAME}' AND pid <> pg_backend_pid();
        DROP DATABASE IF EXISTS ${DB_NAME};
        CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};
    " 2>/dev/null
    gunzip -c "$RESTORE_LOCAL" | sudo docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME"

    # Restart platform
    echo "Restarting platform containers..."
    cd ~/cspulse
    sudo docker compose -f docker-compose.ec2-registry.yml -f docker-compose.ec2-platform-replica.yml up -d cs-pulse cs-pulse-b

    echo "=== Restore complete from ${RESTORE_DATE} ==="
    rm -f "$RESTORE_LOCAL"
    exit 0
fi

# ── Backup ──
echo "=== CS Pulse PostgreSQL Backup ==="
echo "  Date:      ${DATE}"
echo "  Database:  ${DB_NAME}"
echo "  Container: ${CONTAINER}"
echo "  Dest:      s3://${S3_BUCKET}/${S3_KEY}"

# Check container is running
if ! sudo docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "ERROR: Container ${CONTAINER} is not running"
    exit 1
fi

# pg_dump → gzip → local temp file
echo "  Dumping..."
sudo docker exec "$CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl | gzip > "$LOCAL_TMP"

SIZE=$(ls -lh "$LOCAL_TMP" | awk '{print $5}')
echo "  Dump size: ${SIZE}"

# Upload to S3
echo "  Uploading to S3..."
aws s3 cp "$LOCAL_TMP" "s3://${S3_BUCKET}/${S3_KEY}" --region "$REGION" --storage-class STANDARD_IA

# Verify upload
if aws s3 ls "s3://${S3_BUCKET}/${S3_KEY}" --region "$REGION" >/dev/null 2>&1; then
    echo "  ✅ Upload verified"
else
    echo "  ❌ Upload verification failed!"
    exit 1
fi

# Cleanup local temp
rm -f "$LOCAL_TMP"

# Prune old backups (retain N days)
echo "  Pruning backups older than ${RETAIN_DAYS} days..."
CUTOFF=$(date -u -d "-${RETAIN_DAYS} days" +%Y-%m-%d 2>/dev/null || date -u -v-${RETAIN_DAYS}d +%Y-%m-%d)
aws s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}" --region "$REGION" 2>/dev/null | while read -r line; do
    FILE=$(echo "$line" | awk '{print $4}')
    # Extract date from filename: cs_pulse_YYYY-MM-DD.sql.gz
    FILE_DATE=$(echo "$FILE" | grep -oP '\d{4}-\d{2}-\d{2}' || true)
    if [[ -n "$FILE_DATE" && "$FILE_DATE" < "$CUTOFF" ]]; then
        echo "    Deleting old backup: ${FILE}"
        aws s3 rm "s3://${S3_BUCKET}/${S3_PREFIX}${FILE}" --region "$REGION"
    fi
done

echo "  ✅ Backup complete: ${BACKUP_FILE} (${SIZE})"
echo "  Timestamp: ${TIMESTAMP}"
