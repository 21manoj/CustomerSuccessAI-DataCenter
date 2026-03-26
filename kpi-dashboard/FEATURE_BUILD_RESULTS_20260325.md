# Feature Build Results — 2026-03-25

## Sprint 1 — Wizard A Arc Intelligence Engine

**Branch:** `feature/wizard-arc-predictive-engine`
**Date:** 2026-03-25

---

### 9a. What Was Built (File by File)

| File | Status | Description |
|---|---|---|
| `backend/models.py` | MODIFIED | Added `arc_type` (String 50), `arc_phase` (String 20), `arc_confidence` (Float) columns to `Account` model |
| `backend/migrations/add_arc_fields_to_accounts.py` | NEW | Idempotent ALTER TABLE migration; `--rollback` flag supported |
| `backend/utils/arc_classifier.py` | REWRITTEN | Full feature extraction + 10-rule classification cascade |
| `backend/utils/arc_edge_generator.py` | REWRITTEN | InDBRefRegistry + ARC_TEMPLATES + temporal validation + ContextEdge INSERT |
| `backend/wizards/wizard_a_journey_db.py` | EXTENDED | New `run_wizard_a()` calls classifier + edge generator per account; legacy `_run_journey_generation()` preserved |
| `backend/mcp_server/cs_pulse_onboarding.py` | MODIFIED | Wizard A call at end of `_process_data_impl()`, wrapped in try/except (non-fatal) |
| `backend/onboarding_api_v2_config_aware.py` | MODIFIED | Wizard A call at end of `ingest_context_graph_csvs()`, wrapped in try/except (non-fatal) |

---

### 9b. ARC_TEMPLATES Edge Topologies Ported

All 8 arcs from `load-driver/scenarios/scenario_manifest.py` `NarrativeTimelinePlanner.ARC_TEMPLATES` plus 3 new arc aliases:

| Arc Type | Classification | Baseline Edges | Intervention Edges |
|---|---|---|---|
| `ignored_churn` | critical | 4 | 3 |
| `proactive_growth` | healthy | 3 | 2 |
| `crisis_recovery` | critical | 4 | 3 |
| `expansion_champion` | healthy | 4 | 2 |
| `steady_performer` | healthy | 2 | 2 |
| `budget_pressure` | at_risk | 4 | 3 |
| `stalled_deployment` | at_risk | 3 | 2 |
| `competitor_evaluation` | at_risk | 3 | 2 |
| `champion_loss` | critical | 4 | 3 |
| `infrastructure_decay` | critical | 4 | 3 |
| `engagement_decline` | at_risk (alias) | 2 | 2 |
| `land_and_expand` | healthy (alias) | 2 | 2 |

---

### 9c. Arc Classification Rules

| Priority | Arc Type | Confidence | Condition |
|---|---|---|---|
| 1 | `champion_loss` | 0.85 | `has_stakeholder_departure AND slope_30d < -3` |
| 2 | `crisis_recovery` | 0.80 | `health_now < 50 AND 'critical_incident' in signal_types` |
| 3 | `infrastructure_decay` | 0.75 | `slope_60d < -8 AND health_now < 65 AND no critical_incident` |
| 4 | `budget_pressure` | 0.75 | `budget_freeze/cut/cost_reduction in signal_types AND slope_60d < -3` |
| 5 | `stalled_deployment` | 0.70 | `p1_delta_30d < -15 AND abs(slope_30d) < 2` |
| 6 | `competitor_evaluation` | 0.70 | `competitor/evaluation/rfp in signal_types AND days_to_renewal < 90` |
| 7 | `engagement_decline` | 0.65 | `slope_30d < -5 AND health_now >= 50` |
| 8 | `land_and_expand` | 0.75 | `health_now >= 80 AND expansion/upsell/growth in signal_types` |
| 9 | `steady_performer` | 0.60 | `health_now >= 70 AND slope_30d >= -2` |
| 10 | `budget_pressure` | 0.55 | *(fallback — always matches)* |

**Phase detection:** `intervention` if `slope_30d > 2 AND health_now > 55`; else `baseline`.

---

### 9d. EC2 Test Commands

```bash
# === STEP 1: Pull latest code on EC2 ===
cd ~/cspulse
git pull origin feature/wizard-arc-predictive-engine

# === STEP 2: Copy changed files into running container (no rebuild needed) ===
sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  cp kpi-dashboard/backend/models.py \
     cs-pulse:/app/backend/models.py

sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  cp kpi-dashboard/backend/utils/arc_classifier.py \
     cs-pulse:/app/backend/utils/arc_classifier.py

sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  cp kpi-dashboard/backend/utils/arc_edge_generator.py \
     cs-pulse:/app/backend/utils/arc_edge_generator.py

sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  cp kpi-dashboard/backend/wizards/wizard_a_journey_db.py \
     cs-pulse:/app/backend/wizards/wizard_a_journey_db.py

sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  cp kpi-dashboard/backend/migrations/add_arc_fields_to_accounts.py \
     cs-pulse:/app/backend/migrations/add_arc_fields_to_accounts.py

sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  cp kpi-dashboard/backend/mcp_server/cs_pulse_onboarding.py \
     cs-pulse:/app/backend/mcp_server/cs_pulse_onboarding.py

sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  cp kpi-dashboard/backend/onboarding_api_v2_config_aware.py \
     cs-pulse:/app/backend/onboarding_api_v2_config_aware.py

# === STEP 3: Run DB migration ===
sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  exec -T cs-pulse bash -c \
  'cd /app/backend && python3 -m migrations.add_arc_fields_to_accounts'

# Verify columns exist:
sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  exec -T cs-pulse bash -c \
  'cd /app/backend && python3 -c "
from app_v3_minimal import app
from extensions import db
with app.app_context():
    result = db.engine.execute(\"SELECT column_name FROM information_schema.columns WHERE table_name='"'"'accounts'"'"' AND column_name LIKE '"'"'arc_%'"'"'\")
    print(list(result))
"'

# === STEP 4: Load denali_dc2s (15 accounts, DC2_S, customer 424) ===
sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  exec -T cs-pulse bash -c \
  'cd /app/load-driver && python3 cs_pulse_driver.py \
   --manifest manifests/denali_dc2s.json --seed 42 2>&1 | tail -30'

# === STEP 5: Trigger process_data to run Wizard A ===
# Via MCP tool (Claude.ai) or direct curl:
curl -X POST https://d2oqfugrb2ltg9.cloudfront.net/mcp \
  -H "Content-Type: application/json" \
  -d '{"method":"tools/call","params":{"name":"process_data","arguments":{"customer_id":424}}}'

# === STEP 6: Verify arc assignments in DB ===
sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  exec -T cs-pulse bash -c \
  'cd /app/backend && python3 -c "
from app_v3_minimal import app
from extensions import db
from models import Account
with app.app_context():
    accts = Account.query.filter_by(customer_id=424).all()
    for a in accts:
        print(f\"{a.account_id}: {a.account_name:30s} arc={a.arc_type:25s} phase={a.arc_phase} conf={a.arc_confidence}\")
"'

# === STEP 7: Verify edges in DB ===
sudo docker compose \
  -f docker-compose.ec2-registry.yml \
  -f docker-compose.ec2-loaddriver.yml \
  -f docker-compose.ec2-platform-replica.yml \
  exec -T cs-pulse bash -c \
  'cd /app/backend && python3 -c "
from app_v3_minimal import app
from extensions import db
from models import ContextEdge, ContextNode, Account
with app.app_context():
    accts = Account.query.filter_by(customer_id=424).all()
    for a in accts:
        node_ids = [n.node_id for n in ContextNode.query.filter_by(account_id=a.account_id).all()]
        if node_ids:
            ec = ContextEdge.query.filter(
                (ContextEdge.from_node_id.in_(node_ids)) |
                (ContextEdge.to_node_id.in_(node_ids))
            ).count()
        else:
            ec = 0
        print(f\"{a.account_id}: {a.account_name:30s} edges={ec}\")
"'

# === STEP 8: Run for all 4 manifests ===
# mont_blanc_saas (customer 425), novastar_dc2s (customer 396 or new),
# cloudscale_saas_premium (customer 397 or new)
# Repeat STEP 4 + STEP 5 for each customer ID

# === STEP 9: Validate via MCP get_graph_summary ===
# Use Claude.ai MCP tool: get_graph_summary(customer_id=424)
# Expected: node_count > 0, edge_count >= 3 per account on average
```

---

### 9e. Validation Results

#### Test 1: denali_dc2s (customer 424, DC2_S, 15 accounts)

| Account | arc_type | confidence | phase | edges (Wizard A) | pass |
|---|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD | PENDING |

#### Test 2: mont_blanc_saas (customer 425, SaaS, 15 accounts)

| Account | arc_type | confidence | phase | edges (Wizard A) | pass |
|---|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD | PENDING |

#### Overall Pass/Fail

| Acceptance Criterion | Status |
|---|---|
| denali_dc2s: all accounts have arc_type set | PENDING |
| mont_blanc_saas: all accounts have arc_type set | PENDING |
| All customers: >= 2 edges per account (where nodes exist) | PENDING |
| No temporal violations in Wizard A logs | PENDING |
| No unresolved ref warnings (acceptable if nodes not yet loaded) | PENDING |
| arc_type persisted to accounts.arc_type column | PENDING |
| process_data step list includes wizard_a_N_accounts | PENDING |
| ingest_context_graph_csvs result includes wizard_a key | PENDING |

---

### Notes

- **Temporal violations are expected** when context graph CSVs have not been loaded
  (no ContextNode rows = InDBRefRegistry resolves 0 refs, generates 0 edges).
  Run the load driver with context graph manifests (Scenario 8 or granite_peak_dc2s)
  to populate nodes before edge generation is meaningful.

- **arc_type fallback**: accounts with no HealthScore history default to `health_now=50.0`,
  `slope_30d=0`, matching the `budget_pressure` fallback rule (confidence 0.55).

- **EC2 rebuild not required** for this sprint — files can be `docker cp`'d directly
  into the running container. A full `docker compose build --no-cache` is only needed
  when Python dependencies change.
