#!/usr/bin/env bash
# Troubleshoot why curl http://localhost:9080/api/health doesn't return OK.
# Run from repo root: ./scripts/troubleshoot-platform-health.sh

set -e
CSPULSE_HOST_PORT="${CSPULSE_HOST_PORT:-9080}"

echo "=== 1. Containers (cs-pulse, postgres) ==="
docker ps -a --filter "name=cspulse" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== 2. Port ${CSPULSE_HOST_PORT} on host ==="
if command -v lsof >/dev/null 2>&1; then
  lsof -i :${CSPULSE_HOST_PORT} 2>/dev/null || echo "Nothing listening on ${CSPULSE_HOST_PORT} (or lsof not available)"
else
  echo "lsof not installed; check manually if port ${CSPULSE_HOST_PORT} is in use"
fi

echo ""
echo "=== 3. curl -v http://localhost:${CSPULSE_HOST_PORT}/api/health (first 5s) ==="
curl -v --max-time 5 "http://localhost:${CSPULSE_HOST_PORT}/api/health" 2>&1 || true

echo ""
echo "=== 4. Last 80 lines of cspulse-platform logs ==="
docker logs cspulse-platform 2>&1 | tail -80

echo ""
echo "=== 5. Check .env in kpi-dashboard ==="
KPI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../kpi-dashboard" && pwd)"
if [ -f "$KPI_DIR/.env" ]; then
  echo ".env exists. Required vars (values hidden):"
  for v in POSTGRES_PASSWORD SECRET_KEY OPENAI_API_KEY ANTHROPIC_API_KEY; do
    if grep -q "^${v}=" "$KPI_DIR/.env" 2>/dev/null; then
      echo "  $v is set"
    else
      echo "  $v is MISSING"
    fi
  done
else
  echo ".env NOT FOUND at $KPI_DIR/.env — create it (see docs/PRODUCTION_ENV_TEMPLATE.md)"
fi

echo ""
echo "=== Done ==="
echo "Common fix: ensure kpi-dashboard/.env has POSTGRES_PASSWORD, SECRET_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY."
echo "  Generate SECRET_KEY: python3 -c \"import secrets; print(secrets.token_hex(32))\""
echo "  Then: cd kpi-dashboard && docker compose -f docker-compose.production.yml up -d"
echo "  If container was Restarting, it should become Up after .env is fixed."
