#!/usr/bin/env bash
# Ensure kpi-dashboard/.env has required vars for docker-compose.production.yml.
# Generates SECRET_KEY and POSTGRES_PASSWORD if missing; adds ANTHROPIC_API_KEY placeholder if missing.
# Run from repo root: ./scripts/ensure-platform-env.sh

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$REPO_ROOT/kpi-dashboard/.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "Creating $ENV_FILE with required variables..."
  mkdir -p "$(dirname "$ENV_FILE")"
  touch "$ENV_FILE"
fi

append_if_missing() {
  local name="$1"
  local value="$2"
  if ! grep -q "^${name}=" "$ENV_FILE" 2>/dev/null; then
    echo "${name}=${value}" >> "$ENV_FILE"
    echo "  Added $name"
  fi
}

echo "Ensuring required env vars in kpi-dashboard/.env..."

if ! grep -q "^SECRET_KEY=" "$ENV_FILE" 2>/dev/null; then
  SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
  append_if_missing "SECRET_KEY" "$SECRET_KEY"
fi

if ! grep -q "^POSTGRES_PASSWORD=" "$ENV_FILE" 2>/dev/null; then
  POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null | tr -d '\n' | head -c 48)
  append_if_missing "POSTGRES_PASSWORD" "$POSTGRES_PASSWORD"
fi

if ! grep -q "^ANTHROPIC_API_KEY=" "$ENV_FILE" 2>/dev/null; then
  echo "ANTHROPIC_API_KEY=your-anthropic-api-key-here" >> "$ENV_FILE"
  echo "  Added ANTHROPIC_API_KEY (placeholder — replace with your key)"
fi

echo "Done. Restart platform: cd kpi-dashboard && docker compose -f docker-compose.production.yml up -d"
