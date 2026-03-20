#!/usr/bin/env bash
# Sync EC2 PostgreSQL database FROM local (overwrite EC2 DB with local data).
# Requires: AWS CLI, SSH key (cspulse-v6-key.pem), EC2 instance running, local PostgreSQL.
# Reads local DB from kpi-dashboard/backend/.env (DATABASE_URL).
#
# Usage: ./scripts/sync-ec2-db-from-local.sh [INSTANCE_ID]

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY_FILE="${REPO_ROOT}/cspulse-v6-key.pem"
AWS_REGION="${AWS_REGION:-us-east-1}"
BACKEND_ENV="${REPO_ROOT}/kpi-dashboard/backend/.env"
DUMP_FILE="${REPO_ROOT}/.sync-local-dump.sql"

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

# Parse DATABASE_URL from .env
DATABASE_URL=$(grep -E '^DATABASE_URL=' "$BACKEND_ENV" | sed 's/^DATABASE_URL=//' | tr -d '\r' | head -1)
if [[ -z "$DATABASE_URL" ]]; then
  echo "DATABASE_URL not set in $BACKEND_ENV"
  exit 1
fi

# Extract for pg_dump (simple parse: postgresql://user:pass@host:port/dbname)
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

echo "=== Sync EC2 DB from local ==="
echo "  Local DB:     $PGHOST:$PGPORT/$PGNAME"
echo "  EC2 instance: $INSTANCE_ID ($PUBLIC_IP)"
echo ""

echo "1. Dumping local database (plain SQL for compatibility)..."
export PGPASSWORD="$PGPASS"
pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" -d "$PGNAME" -Fp --no-owner > "$DUMP_FILE"
unset PGPASSWORD
if [[ ! -s "$DUMP_FILE" ]]; then
  echo "   Error: dump is empty or failed."
  rm -f "$DUMP_FILE"
  exit 1
fi
echo "   Dump size: $(du -h "$DUMP_FILE" | cut -f1)"

echo "2. Copying dump to EC2..."
scp -o StrictHostKeyChecking=no -i "$KEY_FILE" "$DUMP_FILE" "ec2-user@${PUBLIC_IP}:/home/ec2-user/cspulse_sync.sql"

echo "3. On EC2: dropping and recreating schema public, then restoring..."
ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" "sudo docker exec -i cspulse-postgres psql -U cspulse -d cs_pulse -v ON_ERROR_STOP=1 -c \"DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON SCHEMA public TO cspulse;\""
ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" "sudo docker cp /home/ec2-user/cspulse_sync.sql cspulse-postgres:/tmp/cspulse_sync.sql"
ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" "sudo docker exec -i cspulse-postgres psql -U cspulse -d cs_pulse -f /tmp/cspulse_sync.sql"
ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" "sudo docker exec cspulse-postgres rm -f /tmp/cspulse_sync.sql; rm -f /home/ec2-user/cspulse_sync.sql"

rm -f "$DUMP_FILE"

echo "4. Verifying on EC2..."
COUNT=$(ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" "ec2-user@${PUBLIC_IP}" "sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -t -A -c \"SELECT COUNT(*) FROM customers;\"" 2>/dev/null || echo "0")
echo "   Customers on EC2: ${COUNT}"

echo ""
echo "=== Done. EC2 DB synced from local ==="
