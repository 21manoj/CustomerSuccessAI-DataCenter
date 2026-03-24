#!/usr/bin/env bash
# Update only OPENAI_API_KEY and ANTHROPIC_API_KEY on the EC2 instance.
# Does NOT overwrite POSTGRES_PASSWORD or SECRET_KEY (avoids breaking the DB).
#
# Prerequisites: SSH key (cspulse-v6-key.pem), EC2 host, and a local .env
#   that contains OPENAI_API_KEY and ANTHROPIC_API_KEY.
#
# Usage:
#   ./scripts/update-ec2-api-keys.sh [EC2_IP]
#   CSPULSE_EC2_HOST=3.81.222.159 ./scripts/update-ec2-api-keys.sh
#
# Reads keys from (first found): kpi-dashboard/.env, kpi-dashboard/backend/.env

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY_FILE="${REPO_ROOT}/cspulse-v6-key.pem"
EC2_HOST="${1:-${CSPULSE_EC2_HOST}}"

if [[ -z "$EC2_HOST" ]]; then
  echo "Usage: $0 <EC2_IP>"
  echo "   or: CSPULSE_EC2_HOST=<EC2_IP> $0"
  exit 1
fi

ENV_FILE=""
for candidate in "${REPO_ROOT}/kpi-dashboard/.env" "${REPO_ROOT}/kpi-dashboard/backend/.env"; do
  if [[ -f "$candidate" ]]; then
    ENV_FILE="$candidate"
    break
  fi
done
if [[ -z "$ENV_FILE" ]]; then
  echo "No .env found in kpi-dashboard/ or kpi-dashboard/backend/. Create one with OPENAI_API_KEY and ANTHROPIC_API_KEY."
  exit 1
fi
if [[ ! -f "$KEY_FILE" ]]; then
  echo "SSH key not found: $KEY_FILE"
  exit 1
fi

# Read keys (support KEY=value and export KEY=value; no quotes required)
get_key() {
  local name="$1"
  grep -E "^(export[[:space:]]+)?${name}=" "$ENV_FILE" | head -1 | sed -E "s/^(export[[:space:]]+)?${name}=//" | tr -d '\r'
}
OPENAI_KEY="$(get_key OPENAI_API_KEY)"
ANTHROPIC_KEY="$(get_key ANTHROPIC_API_KEY)"
if [[ -z "$OPENAI_KEY" ]] || [[ -z "$ANTHROPIC_KEY" ]]; then
  echo "Both OPENAI_API_KEY and ANTHROPIC_API_KEY must be set in $ENV_FILE"
  exit 1
fi

# Temp file for the two lines (avoid passing secrets on command line)
KEYS_TMP="$(mktemp)"
trap 'rm -f "$KEYS_TMP"' EXIT
printf "OPENAI_API_KEY=%s\nANTHROPIC_API_KEY=%s\n" "$OPENAI_KEY" "$ANTHROPIC_KEY" > "$KEYS_TMP"

echo "Updating only OPENAI_API_KEY and ANTHROPIC_API_KEY on EC2 ($EC2_HOST)..."
echo "  (POSTGRES_PASSWORD and SECRET_KEY are left unchanged.)"

# Copy keys file to EC2, merge into .env without touching other vars, restart platform only
scp -o StrictHostKeyChecking=no -i "$KEY_FILE" "$KEYS_TMP" "ec2-user@${EC2_HOST}:~/cspulse/.env.api-keys.new"

ssh -o StrictHostKeyChecking=no -i "$KEY_FILE" "ec2-user@${EC2_HOST}" "cd ~/cspulse && \
  cp -a .env .env.bak.$(date +%Y%m%d%H%M%S) && \
  (grep -v -E '^OPENAI_API_KEY=' .env | grep -v -E '^ANTHROPIC_API_KEY=' || true) > .env.tmp && \
  cat .env.api-keys.new >> .env.tmp && \
  mv .env.tmp .env && \
  rm -f .env.api-keys.new && \
  echo 'Restarting platform container only...' && \
  sudo docker compose -f docker-compose.ec2-registry.yml -f docker-compose.ec2-loaddriver.yml -f docker-compose.ec2-platform-replica.yml up -d --force-recreate cs-pulse"

echo "Done. Check health: curl -s http://${EC2_HOST}/api/health"
