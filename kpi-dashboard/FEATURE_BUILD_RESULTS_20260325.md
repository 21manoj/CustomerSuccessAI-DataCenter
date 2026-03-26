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

### 9e. Validation Results — EC2 Run 2026-03-26 03:00 UTC

**Manifests tested:** 424 (mount_peak_saas), 425 (dr1_ai_dc2s), 427 (granite_peak_dc2s), 428 (alpine_saas_partners)
**Total accounts:** 58 across 4 customers

#### Arc Assignment Results (all 58 accounts)

| Customer | Account | arc_type | confidence | phase | Note |
|---|---|---|---|---|---|
| 424 | Zermatt Analytics | budget_pressure | 0.55 | baseline | Fallback |
| 424 | Eiger Cloud Services | crisis_recovery | 0.80 | baseline | ✓ Rule match |
| 424 | Jungfrau, Matterhorn, Bernina | budget_pressure | 0.55 | baseline | Fallback |
| 424 | Pilatus–Interlaken (5 accts) | steady_performer | 0.60 | baseline | ✓ Rule match |
| 425 | Titan Hyperscale Labs | budget_pressure | 0.55 | baseline | ⚠ Expected champion_loss |
| 425 | Meridian Cloud Services | crisis_recovery | 0.80 | baseline | ✓ Rule match |
| 425 | Apex–Quantum (3 accts) | budget_pressure | 0.55 | baseline | Fallback |
| 425 | Stratos–Helix (5 accts) | steady_performer | 0.60 | baseline | ✓ Rule match |
| 427 | Ironridge Manufacturing | crisis_recovery | 0.80 | baseline | ✓ Rule match |
| 427 | Vertex, Sentinel, Meridian FS, Clearwater, Quantum (5) | budget_pressure | 0.55 | baseline | Fallback |
| 427 | Blackstone–Forge (12 accts) | steady_performer | 0.60 | baseline | ✓ Rule match |
| 428 | Eiger Cloud Services | crisis_recovery | 0.80 | baseline | ✓ Rule match |
| 428 | Zermatt, Jungfrau, Matterhorn, Bernina, Pilatus (5) | budget_pressure | 0.55 | baseline | Fallback |
| 428 | Grindelwald–Titlis (14 accts) | steady_performer | 0.60 | baseline | ✓ Rule match |

#### Overall Pass/Fail

| Acceptance Criterion | Status | Notes |
|---|---|---|
| All 58 accounts have arc_type set | ✅ PASS | 58/58 rows populated |
| arc_type persisted to accounts.arc_type | ✅ PASS | DB confirmed |
| arc_phase persisted | ✅ PASS | All `baseline` — correct for these manifests |
| arc_confidence persisted | ✅ PASS | 0.55 / 0.60 / 0.80 values stored |
| Wizard A wired into process_data (non-fatal) | ✅ PASS | No pipeline crashes across 4 runs |
| crisis_recovery correctly fires | ✅ PASS | 1 per customer where health<50 + critical_incident |
| steady_performer correctly fires | ✅ PASS | Healthy accounts (≥70, slope≥-2) correctly identified |
| champion_loss fires for Titan Hyperscale | ❌ FAIL | Falls to budget_pressure fallback (0.55) |
| Arc variety > 2 types (excl. fallback) | ❌ FAIL | Only crisis_recovery + steady_performer firing from rules |
| budget_pressure fallback < 30% of accounts | ❌ FAIL | ~40% hit fallback — classifier too narrow |
| True simulation (no signal_edges.csv) | ⏳ NOT RUN | All 4 runs uploaded WITH signal_edges.csv |
| Zero 404 in post-validation | ⚠ PARTIAL | 404s in post-check only (scope bug), loads succeeded |

---

### Root Cause — Arc Classifier Too Narrow

**Problem**: 40% of accounts fall to `budget_pressure` fallback (confidence 0.55).
Only `crisis_recovery` and `steady_performer` fire from explicit rules.
`champion_loss`, `infrastructure_decay`, `stalled_deployment`, `competitor_evaluation` never fire.

**Why**: Classifier reads `signal_subtype` / `node_subtype` from ContextNode rows and builds
a Counter. Rules match against specific strings like `'champion_loss'`, `'stakeholder_departure'`,
`'budget_freeze'`. But ContextNode stores load-driver subtype values (`'stakeholder_escalation'`,
`'kpi_recovery'`, `'critical_incident'`) which don't match classifier's expected strings.

**Fix required in `arc_classifier.py`**:

| Rule | Current match string | Should also match |
|---|---|---|
| champion_loss | `'champion_loss'`, `'stakeholder_departure'` | `'stakeholder_escalation'`, `'executive_departure'`, title contains 'champion'/'executive left' |
| budget_pressure | `'budget_freeze'`, `'budget_cut'` | `'financial_concern'`, `'cost_reduction'`, `'contract_risk'` |
| infrastructure_decay | (slope only) | `'performance_degradation'`, `'system_outage'`, `'sla_breach'` |
| stalled_deployment | (p1_delta only) | `'deployment_blocked'`, `'technical_blocker'`, `'integration_failure'` |
| competitor_evaluation | `'competitor'`, `'rfp'` | `'evaluation'`, `'vendor_review'`, `'competitive_threat'` |

Also: add fuzzy title/description scan as secondary signal source (many accounts have
rich signal text but narrow subtype values).

### Next Steps Before Sprint 1 Merge

1. **Fix arc_classifier.py** — expand keyword sets, add title/description text scan
2. **Run true simulation** — reload granite_peak WITHOUT signal_edges.csv, verify
   Wizard A regenerates equivalent edges independently
3. **Verify edge counts** — query ContextEdge counts per account to confirm
   arc_edge_generator fired (separate from load-driver edges)
