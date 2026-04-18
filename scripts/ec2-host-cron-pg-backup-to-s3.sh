#!/usr/bin/env bash
# Run ON the EC2 host (cron). No SSH from laptop.
#
#   docker exec cspulse-postgres pg_dump … | aws s3 cp - s3://…/backups/nightly/…
#
# Requires:
#   - Instance IAM role with s3:PutObject, s3:ListBucket, s3:DeleteObject on the backup prefix
#   - aws CLI v2, docker, cspulse-postgres container running
#
# Env (optional):
#   CSPULSE_S3_BUCKET   — default: cspulse-container-artifacts-<accountId from IMDS>
#   AWS_REGION          — default: us-east-1
#   S3_PREFIX           — default: backups/nightly
#   RETENTION_DAYS      — default: 7 (deletes older objects under S3_PREFIX by date in filename)
#
# Cron example (3:15 UTC daily, log append):
#   15 3 * * * CSPULSE_S3_BUCKET=cspulse-container-artifacts-822824391150 AWS_DEFAULT_REGION=us-east-1 /home/ec2-user/CustomerSuccessAI-DataCenter/scripts/ec2-host-cron-pg-backup-to-s3.sh >>/var/log/cspulse-pg-backup.log 2>&1
#
# Install once on host:
#   sudo cp scripts/ec2-host-cron-pg-backup-to-s3.sh /usr/local/bin/ && sudo chmod +x /usr/local/bin/ec2-host-cron-pg-backup-to-s3.sh
#   (then point cron at /usr/local/bin/ec2-host-cron-pg-backup-to-s3.sh)

set -euo pipefail

CONTAINER_NAME="${POSTGRES_CONTAINER:-cspulse-postgres}"
PG_USER="${POSTGRES_USER:-cspulse}"
PG_DB="${POSTGRES_DB:-cs_pulse}"
AWS_REGION="${AWS_DEFAULT_REGION:-${AWS_REGION:-us-east-1}}"
S3_PREFIX="${S3_PREFIX:-backups/nightly}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

log() { echo "[$(date -Is)] $*"; }

_imds_account_id() {
  local token
  token="$(curl -fsS -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null)" || return 1
  curl -fsS -H "X-aws-ec2-metadata-token: $token" \
    "http://169.254.169.254/latest/dynamic/instance-identity/document" \
    | python3 -c "import sys, json; print(json.load(sys.stdin)['accountId'])"
}

if [[ -z "${CSPULSE_S3_BUCKET:-}" ]]; then
  if ACCOUNT_ID="$(_imds_account_id 2>/dev/null)"; then
    CSPULSE_S3_BUCKET="cspulse-container-artifacts-${ACCOUNT_ID}"
    log "Using bucket from IMDS: ${CSPULSE_S3_BUCKET}"
  else
    log "ERROR: Not on EC2 (IMDS unavailable) or CSPULSE_S3_BUCKET unset."
    exit 1
  fi
fi

if ! docker info >/dev/null 2>&1; then
  log "ERROR: docker not available or not running."
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  log "ERROR: container '$CONTAINER_NAME' not running."
  exit 1
fi

TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
DUMP_BASENAME="cspulse-db-${TIMESTAMP}.dump"
S3_URI="s3://${CSPULSE_S3_BUCKET}/${S3_PREFIX}/${DUMP_BASENAME}"

log "=== Host PG backup → S3 ==="
log "  Container: $CONTAINER_NAME  DB: $PG_DB  User: $PG_USER"
log "  Destination: $S3_URI"

# Stream custom-format dump to S3 (no disk spike for full DB copy)
set +e
docker exec "$CONTAINER_NAME" pg_dump -U "$PG_USER" -d "$PG_DB" -Fc \
  | aws s3 cp - "$S3_URI" --region "$AWS_REGION" --only-show-errors
RC=( "${PIPESTATUS[@]}" )
set -e
DUMP_RC="${RC[0]}"
S3_RC="${RC[1]}"
if [[ "$DUMP_RC" -ne 0 ]]; then
  log "ERROR: pg_dump failed (exit $DUMP_RC)."
  exit 1
fi
if [[ "$S3_RC" -ne 0 ]]; then
  log "ERROR: aws s3 cp failed (exit $S3_RC)."
  exit 1
fi

log "  Uploaded OK: $S3_URI"

# Retention: delete objects under S3_PREFIX older than RETENTION_DAYS (by YYYYMMDD in filename)
CUTOFF_DATE="$(date -u -d "-${RETENTION_DAYS} days" +%Y%m%d 2>/dev/null || date -u -v-${RETENTION_DAYS}d +%Y%m%d)"
log "  Retention: removing dumps with date token < $CUTOFF_DATE under ${S3_PREFIX}/"

while IFS= read -r key; do
  [[ -z "$key" ]] && continue
  base="$(basename "$key")"
  file_date="$(echo "$base" | grep -oE '[0-9]{8}' | head -1 || true)"
  [[ -z "$file_date" ]] && continue
  if [[ "$file_date" < "$CUTOFF_DATE" ]]; then
    log "  Deleting s3://${CSPULSE_S3_BUCKET}/${key}"
    aws s3 rm "s3://${CSPULSE_S3_BUCKET}/${key}" --region "$AWS_REGION" --only-show-errors || true
  fi
done < <(aws s3api list-objects-v2 \
  --bucket "$CSPULSE_S3_BUCKET" \
  --prefix "${S3_PREFIX}/" \
  --query 'Contents[].Key' \
  --output text \
  --region "$AWS_REGION" 2>/dev/null | tr '\t' '\n' | grep '\.dump$' || true)

log "=== Done ==="
