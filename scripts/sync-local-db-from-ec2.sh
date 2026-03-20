#!/usr/bin/env bash
# Sync local PostgreSQL database from EC2 (overwrite local with EC2 data).
# Requires: AWS CLI, SSH key (cspulse-v6-key.pem), EC2 instance running, local PostgreSQL.
# Reads local DB URL from kpi-dashboard/backend/.env (DATABASE_URL).
#
# Usage: ./scripts/sync-local-db-from-ec2.sh [INSTANCE_ID]

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY_FILE="${REPO_ROOT}/cspulse-v6-key.pem"
AWS_REGION="${AWS_REGION:-us-east-1}"
BACKEND_ENV="${REPO_ROOT}/kpi-dashboard/backend/.env"
DUMP_FILE="${REPO_ROOT}/.sync-ec2-dump.dump"

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

if [[ ! -f "$KEY_FILE" ]]; then
  echo "SSH key not found: $KEY_FILE"
  exit 1
fi
if [[ ! -f "$BACKEND_ENV" ]]; then
  echo "Backend .env not found: $BACKEND_ENV"
  exit 1
fi

# Parse DATABASE_URL from .env (e.g. postgresql://user:pass@host:5432/dbname)
DATABASE_URL=$(grep -E '^DATABASE_URL=' "$BACKEND_ENV" | sed 's/^DATABASE_URL=//' | tr -d '\r' | head -1)
if [[ -z "$DATABASE_URL" ]]; then
  echo "DATABASE_URL not set in $BACKEND_ENV"
  exit 1
fi

# Extract components for pg_restore (simple parse)
# postgresql://user:pass@host:port/dbname
if [[ "$DATABASE_URL" =~ postgresql://([^:]+):([^@]+)@([^:]+):([0-9]+)/(.+) ]]; then
  PGUSER="${BASH_REMATCH[1]}"
  PGPASS="${BASH_REMATCH[2]}"
  PGHOST="${BASH_REMATCH[3]}"
  PGPORT="${BASH_REMATCH[4]}"
  PGNAME="${BASH_REMATCH[5]}"
else
  echo "Could not parse DATABASE_URL"
  exit 1
fi

PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$AWS_REGION" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text 2>/dev/null)
if [[ -z "$PUBLIC_IP" || "$PUBLIC_IP" == "None" ]]; then
  echo "Could not get public IP for $INSTANCE_ID"
  exit 1
fi

echo "=== Sync local DB from EC2 ==="
echo "  EC2 instance: $INSTANCE_ID ($PUBLIC_IP)"
echo "  Local DB:     $PGHOST:$PGPORT/$PGNAME"
echo ""

echo "1. Dumping database from EC2 (cs_pulse)..."
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" \
  "sudo docker exec cspulse-postgres pg_dump -U cspulse -d cs_pulse -Fc" > "$DUMP_FILE"
if [[ ! -s "$DUMP_FILE" ]]; then
  echo "   Error: dump is empty or failed."
  rm -f "$DUMP_FILE"
  exit 1
fi
echo "   Dump size: $(du -h "$DUMP_FILE" | cut -f1)"

echo "2. Dropping and recreating local schema (public)..."
export PGPASSWORD="$PGPASS"
psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGNAME" -v ON_ERROR_STOP=1 -c \
  "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO $PGUSER;" || { unset PGPASSWORD; echo "   Failed to drop schema (need DB owner)."; exit 1; }

echo "3. Restoring EC2 dump into local database..."
pg_restore -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGNAME" --no-owner "$DUMP_FILE" || { unset PGPASSWORD; echo "   pg_restore had errors."; exit 1; }

echo "4. Verifying (customer 430)..."
COUNT=$(psql -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGNAME" -t -A -c "SELECT COUNT(*) FROM customers WHERE customer_id = 430;" 2>/dev/null || echo "0")
unset PGPASSWORD
if [[ "$COUNT" -gt 0 ]]; then
  echo "   OK: customer 430 exists in local DB."
else
  echo "   Note: customer 430 not found (restore may still have completed)."
fi

rm -f "$DUMP_FILE"
echo ""
echo "=== Done. Local DB synced from EC2 ==="
