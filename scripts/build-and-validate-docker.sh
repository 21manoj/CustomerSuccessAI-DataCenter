#!/usr/bin/env bash
# Build all 3 Docker images, set up Sacme & Tacme (10 accounts each), then run load driver scenarios.
#
# Platform is exposed on host port 9080 (not 80) to avoid conflict with other servers.
#
# Prerequisites:
#   - Docker daemon running
#   - In kpi-dashboard/, a .env file with: POSTGRES_PASSWORD, SECRET_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
#     (see docs/PRODUCTION_ENV_TEMPLATE.md)
#   - For step 5b (Sacme/Tacme): host Python 3 with load-driver deps (pip install -r load-driver/requirements.txt)
#     so setup_sacme_tacme.py can run (uses backend for context graph generator)
#
# Usage: from repo root:
#   ./scripts/build-and-validate-docker.sh
# Or from kpi-dashboard (platform env required):
#   cd kpi-dashboard && ../scripts/build-and-validate-docker.sh

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KPI_DIR="${REPO_ROOT}/kpi-dashboard"
LOAD_DRIVER_DIR="${REPO_ROOT}/load-driver"
# Host port for CS Pulse (container still listens on 80 internally)
CSPULSE_HOST_PORT="${CSPULSE_HOST_PORT:-9080}"

echo "=== 1. Building Postgres and CS Pulse platform images ==="
cd "$KPI_DIR"
docker compose -f docker-compose.production.yml build postgres cs-pulse

echo ""
echo "=== 2. Building Load Driver image ==="
cd "$LOAD_DRIVER_DIR"
docker build -t cspulse-load-driver:latest .

echo ""
echo "=== 3. Starting platform and Postgres ==="
cd "$KPI_DIR"
if [ ! -f .env ]; then
  echo "ERROR: kpi-dashboard/.env not found. Create it with POSTGRES_PASSWORD, SECRET_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY (see docs/PRODUCTION_ENV_TEMPLATE.md)"
  exit 1
fi
docker compose -f docker-compose.production.yml up -d

echo ""
echo "=== 4. Waiting for platform health on port $CSPULSE_HOST_PORT (up to 90s) ==="
for i in $(seq 1 45); do
  if curl -sf -o /dev/null "http://localhost:${CSPULSE_HOST_PORT}/api/health" 2>/dev/null; then
    echo "Platform is healthy."
    break
  fi
  if [ "$i" -eq 45 ]; then
    echo "WARNING: Platform health check did not pass in time. Continuing anyway."
  fi
  sleep 2
done

echo ""
echo "=== 5. Seeding customer 291 (admin@loadtest.com / test123) if needed ==="
# Use admin@loadtest.com for 291 so step 5b can create Sacme (admin@sacme.com) and Tacme (admin@tacme.com) without duplicate key.
docker exec -w /app/backend cspulse-platform python3 -c "
from werkzeug.security import generate_password_hash
from sqlalchemy import text
from app_v3_minimal import app
from extensions import db
from models import Customer, CustomerConfig, User
import json
with app.app_context():
    cid, email, pw = 291, 'admin@loadtest.com', 'test123'
    cust = Customer.query.get(cid)
    if not cust:
        cust = Customer(customer_id=cid, customer_name='LoadTest-291', email=email, domain='loadtest.com')
        db.session.add(cust)
        db.session.flush()
        try:
            db.session.execute(text(\"SELECT setval(pg_get_serial_sequence('customers', 'customer_id'), GREATEST(291, (SELECT COALESCE(MAX(customer_id), 1) FROM customers)))\"))
        except Exception: pass
        cfg = CustomerConfig(customer_id=cid, vertical='dc2_s', kpi_upload_mode='account_rollup', category_weights=json.dumps({'Relationship Strength': 0.20, 'Adoption & Engagement': 0.25, 'Support & Experience': 0.20, 'Product Value': 0.20, 'Business Outcomes': 0.15}))
        db.session.add(cfg)
        db.session.flush()
    else:
        cust.email, cust.customer_name, cust.domain = email, 'LoadTest-291', 'loadtest.com'
    user = User.query.filter_by(customer_id=cid).filter((User.email == email) | (User.user_name == 'admin')).first()
    if not user:
        user = User(customer_id=cid, user_name='admin', email=email, password_hash=generate_password_hash(pw), active=True)
        db.session.add(user)
    else:
        user.email, user.password_hash, user.user_name, user.active = email, generate_password_hash(pw), 'admin', True
    db.session.commit()
    print('Customer 291 and admin@loadtest.com ready')
" 2>/dev/null || true

echo ""
echo "=== 5b. Sacme & Tacme: 10 accounts each, synthetic + context graph, process-data (--skip-incremental) ==="
cd "$LOAD_DRIVER_DIR"
if python3 -c "import requests" 2>/dev/null; then
  python3 setup_sacme_tacme.py --base-url "http://localhost:${CSPULSE_HOST_PORT}" --skip-incremental
else
  echo "WARNING: Skipping Sacme/Tacme setup (install load-driver deps: pip install -r load-driver/requirements.txt)"
fi
cd "$REPO_ROOT"

echo ""
echo "=== 6. Running load driver: scenarios 1,2a–2e,3,5,7,8 then cleanup 4 (cleanup last so auth remains valid) ==="
# Reach platform via host port (host.docker.internal:9080). On Linux, --add-host makes host.docker.internal resolve.
# Order: cleanup (4) last so customer/user not deleted before ROI (5) and data_ingestion (7).
SCENARIOS="1,2a,2b,2c,2d,2e,3,5,7,8,4"
BASE_URL="${CS_PULSE_BASE_URL:-http://host.docker.internal:${CSPULSE_HOST_PORT}}"
echo "BASE_URL=$BASE_URL (host port $CSPULSE_HOST_PORT)"
docker run --rm \
  --add-host=host.docker.internal:host-gateway \
  -e CS_PULSE_BASE_URL="$BASE_URL" \
  -e CS_PULSE_ADMIN_EMAIL="${CS_PULSE_ADMIN_EMAIL:-admin@loadtest.com}" \
  -e CS_PULSE_ADMIN_PASSWORD="${CS_PULSE_ADMIN_PASSWORD:-test123}" \
  cspulse-load-driver:latest \
  --scenarios "$SCENARIOS" \
  --customers "291"

echo ""
echo "=== Done. Platform: http://localhost:${CSPULSE_HOST_PORT} — To stop: cd kpi-dashboard && docker compose -f docker-compose.production.yml down ==="
