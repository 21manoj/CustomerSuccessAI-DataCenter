# CS Pulse Feature Toggle Decision Tree

> **Updated**: 2026-03-12
> **Default tier**: Enterprise (all features accessible)
> **Default global toggles**: All ON
> **Default context graph sub-toggles**: All ON

---

## Three-Layer Gating Architecture

```
Request arrives
    |
    v
[Layer 1] Global Platform Toggle (feature_toggles.py)
    |  Is the feature's platform toggle ON?
    |  NO  --> 403: "Feature not available on this platform"
    |  YES
    v
[Layer 2] Customer Entitlement Tier (entitlements.py)
    |  Does the customer's tier include this feature?
    |  NO  --> 403: "Feature not available on your current plan"
    |          (returns required_tier + upgrade_to)
    |  YES
    v
[Layer 3] Per-Customer Override (feature_toggles DB table)
    |  Is there an explicit override row?
    |  YES + enabled=false --> 403 (admin disabled it)
    |  YES + enabled=true  --> ALLOWED (even if tier wouldn't grant it)
    |  NO override row     --> fall through to tier decision (Layer 2)
    |
    v
  ALLOWED - feature executes
```

### Special Case: Context Graph

```
Context Graph request
    |
    v
[Layer 1] Global: CONTEXT_GRAPH toggle ON?
    |  NO  --> flat signal path (no graph)
    |  YES
    v
[Layer 2] Per-customer DB: context_graph toggle row exists + enabled?
    |  NO  --> flat signal path
    |  YES
    v
[Layer 3] Sub-toggle check (story_arcs, signal_edges, etc.)
    |  Read from toggle.config JSON
    |  Each sub-feature gated independently
    v
  Sub-feature executes (or skipped if its sub-toggle is OFF)
```

---

## Layer 1: Global Platform Toggles

**File**: `backend/feature_toggles.py`
**Override**: Environment variables `FEATURE_<NAME>=true|false`
**Default**: All ON (as of 2026-03-12)

| Toggle | Env Var | Default | Dependencies | Description |
|--------|---------|---------|-------------|-------------|
| `FORMAT_DETECTION` | `FEATURE_FORMAT_DETECTION` | ON | None | Auto-detect and validate file formats |
| `REAL_TIME_INGESTION` | `FEATURE_REAL_TIME_INGESTION` | ON | None | Real-time data ingestion APIs |
| `EVENT_DRIVEN_RAG` | `FEATURE_EVENT_DRIVEN_RAG` | ON | REAL_TIME_INGESTION | Auto RAG rebuilds on data changes |
| `CONTINUOUS_LEARNING` | `FEATURE_CONTINUOUS_LEARNING` | ON | EVENT_DRIVEN_RAG | Continuous learning and model updates |
| `ENHANCED_UPLOAD` | `FEATURE_ENHANCED_UPLOAD` | ON | FORMAT_DETECTION | Enhanced upload with format detection |
| `TEMPORAL_ANALYSIS` | `FEATURE_TEMPORAL_ANALYSIS` | ON | None | Temporal analysis and historical trends |
| `MULTI_FORMAT_SUPPORT` | `FEATURE_MULTI_FORMAT_SUPPORT` | ON | FORMAT_DETECTION | Support for multiple file formats |
| `REVENUE_INTELLIGENCE` | `FEATURE_REVENUE_INTELLIGENCE` | ON | None | Power of 1 revenue intelligence |
| `CONTEXT_GRAPH` | `FEATURE_CONTEXT_GRAPH` | ON | None | Context graph: causal signals, stakeholders, outcomes |
| `MCP_SERVER` | `FEATURE_MCP_SERVER` | ON | None | MCP tool provider for Claude/Copilot/ChatGPT |

### Dependency Chain

```
CONTINUOUS_LEARNING
    └── requires EVENT_DRIVEN_RAG
            └── requires REAL_TIME_INGESTION

ENHANCED_UPLOAD
    └── requires FORMAT_DETECTION

MULTI_FORMAT_SUPPORT
    └── requires FORMAT_DETECTION
```

> If you disable a dependency, all features above it in the chain are also disabled (enforced by `FeatureToggleManager.is_enabled()`).

---

## Layer 2: Entitlement Tiers

**File**: `backend/entitlements.py`
**Default tier for new customers**: `enterprise`
**Override**: `DEFAULT_CUSTOMER_TIER` env var, or `PUT /api/entitlements/tier`
**Storage**: `feature_toggles` table, `feature_name='subscription_tier'`, `config={'tier': '...'}`

### Tier Feature Matrix (aligned with Bronze/Silver/Gold page tiers)

| Feature | Starter (Bronze) | Professional (Silver) | Enterprise (Gold) | Page / UI Surface | Description |
|---------|:----------------:|:---------------------:|:-----------------:|-------------------|-------------|
| `dashboards` | x | x | x | Executive Dashboard, Tenants Hub | Core KPI dashboards and health scores |
| `data_upload` | x | x | x | Data Integration, Onboarding Wizard | CSV/Excel data upload and validation |
| `health_scores` | x | x | x | Tenants Hub | Pillar-based health score calculation |
| `journey_generation` | x | x | x | *(basic journey views)* | Customer journey visualization |
| `reports_basic` | x | x | x | *(within Playbook reports)* | Basic RACI and status reports |
| `signal_analyst` | | x | x | Signal Analyst, Journey V3 | AI Signal Analyst (churn/expansion) |
| `agent_loop` | | x | x | *(backend — Settings UI: locked ON)* | Agentic reasoning loop (6-step PAOR) |
| `playbook_triggers` | | x | x | Playbooks | Manual playbook triggering |
| `power_of_1` | | x | x | Outcome ROI | Power of 1 financial impact calculator |
| `decision_matrix` | | x | x | *(backend — Settings UI: locked ON)* | AI-powered decision matrix |
| `approval_queue` | | x | x | Approval Queue | Human-in-the-loop approval workflow |
| `journey_visualizer` | | x | x | Journey Visualizer | Journey Visualizer (Wizard A/B patterns) |
| `rag_queries` | | x | x | AI Insights (RAG) | RAG-powered natural language queries |
| `test_runner_advanced` | | | x | Test Runner | Test Runner advanced options |
| `revenue_intelligence` | | | x | Revenue Intelligence | Revenue intelligence and context graph |
| `portfolio_synergy` | | | x | Power of 1 (Portco CEO) | PE portfolio synergy modeling |
| `onboarding_agent` | | | x | *(backend — Settings UI: locked ON)* | AI Onboarding Agent (TTFV, activation) |
| `auto_trigger_pipeline` | | | x | *(backend — Settings UI: locked ON)* | Event-driven auto-analysis + playbook |
| `feedback_loop` | | | x | *(backend — Settings UI: locked ON)* | Playbook outcome learning loop |
| `mcp_connectors` | | | x | *(backend — Settings UI: locked ON)* | MCP connectors (Salesforce, ServiceNow) |
| `copilot_integration` | | | x | *(backend — Settings UI: locked ON)* | Microsoft Copilot / Teams integration |
| `multi_provider` | | | x | *(backend — Settings UI: locked ON)* | Multi-LLM provider support |
| `agent_memory_shared` | | | x | *(backend — Settings UI: locked ON)* | Cross-agent shared memory |

**Feature count**: Starter/Bronze=5, Professional/Silver=13, Enterprise/Gold=23

### Ungated (All Tiers)

| Page / Feature | Notes |
|---------------|-------|
| Admin Insights (Wizard B/C) | Universal — visible to all tiers |
| Settings sub-sections | UI-only tier gating (future) |
| Login | Entry point |

### Backend-Only Entitlements (Settings UI: Locked ON)

These 9 features have no dedicated page/tab but appear in Settings > Entitlements as
always-ON informational rows (non-toggleable). They power backend capabilities:

`agent_loop`, `decision_matrix`, `onboarding_agent`, `auto_trigger_pipeline`,
`feedback_loop`, `mcp_connectors`, `copilot_integration`, `multi_provider`, `agent_memory_shared`

### Checking Entitlements in Code

```python
from entitlements import check_entitlement, require_entitlement

# Inline check
if check_entitlement(customer_id, 'signal_analyst'):
    run_analysis()

# Decorator (returns 403 automatically)
@require_entitlement('signal_analyst')
def analyze():
    ...
```

---

## Layer 3: Per-Customer Overrides

**Storage**: `feature_toggles` DB table
**API**: `PUT /api/entitlements/override`

Per-customer overrides **take precedence over tier defaults**. Use cases:
- Grant a Starter customer access to `signal_analyst` (upsell trial)
- Revoke a specific Enterprise feature for a customer (compliance)

```
PUT /api/entitlements/override
{
  "customer_id": 42,
  "feature": "signal_analyst",
  "enabled": true
}
```

> When no override exists, the tier default applies.

---

## Context Graph Sub-Toggles

**File**: `backend/feature_toggles.py` (CONTEXT_GRAPH_DEFAULT_CONFIG)
**Default**: All ON (as of 2026-03-12)
**Storage**: `feature_toggles` table, `feature_name='context_graph'`, `config={...}`

| Sub-Toggle | Default | What It Gates |
|-----------|---------|--------------|
| `story_arcs` | ON | 8 narrative arc manifests (silent_churn, expansion_champion, etc.) |
| `signal_edges` | ON | Causal signal→decision→outcome edges in graph |
| `stakeholder_tracking` | ON | Stakeholder Map tab in Revenue Intelligence |
| `decision_lifecycle` | ON | Decision nodes and evidence chains |
| `outcome_economics` | ON | Outcome nodes with revenue_value attribution |
| `industry_benchmarks` | ON | Benchmarks tab in Revenue Intelligence |

### Checking Sub-Toggles in Code

```python
from feature_toggles import is_context_graph_enabled, is_context_graph_sub_enabled

# Master check (global + per-customer)
if is_context_graph_enabled(customer_id):
    # Sub-toggle check
    if is_context_graph_sub_enabled(customer_id, 'story_arcs'):
        load_story_arcs()
```

---

## MCP Integration Sub-Services

**Storage**: `feature_toggles` table, `feature_name='mcp_integration'`, `config={...}`

| Sub-Service | Default | Description |
|------------|---------|-------------|
| `salesforce` | OFF | Salesforce CRM connector |
| `servicenow` | OFF | ServiceNow ticket connector |
| `surveys` | OFF | Survey platform connector |

> These require external credentials — OFF by default until configured.

---

## API Reference

### Global Toggle APIs
```
GET  /api/feature-status                     # All global toggles
POST /api/feature-toggle                     # Toggle a feature {feature, enabled}
GET  /api/feature-toggle/<name>              # Single toggle status
POST /api/feature-toggle/reset               # Reset all to defaults
```

### Entitlement APIs
```
GET  /api/entitlements                       # All entitlements for current customer
GET  /api/entitlements/check/<feature>       # Check single feature
GET  /api/entitlements/tier                  # Get customer's tier + features
PUT  /api/entitlements/tier                  # Set tier {customer_id, tier}
PUT  /api/entitlements/override              # Set override {customer_id, feature, enabled}
GET  /api/entitlements/catalog               # Full feature catalog
```

### Context Graph APIs
```
GET  /api/features/context-graph             # Status + sub-toggles
POST /api/features/context-graph             # Toggle on/off {customer_id, enabled, config}
PUT  /api/features/context-graph/sub-toggle  # Single sub-toggle {customer_id, sub_toggle, enabled}
```

### MCP Integration APIs
```
GET  /api/features/mcp                       # MCP status + sub-services
POST /api/features/mcp                       # Toggle on/off
GET  /api/features/mcp/status                # Real-time connection status
```

---

## Decision Tree: "Why Can't a Customer Access Feature X?"

```
1. Is the global platform toggle ON?
   Check: GET /api/feature-status
   Fix:   POST /api/feature-toggle {feature: "X", enabled: true}
   Fix:   Set FEATURE_X=true in environment

2. What is the customer's tier?
   Check: GET /api/entitlements/tier?customer_id=N
   Fix:   PUT /api/entitlements/tier {customer_id: N, tier: "enterprise"}

3. Is there a per-customer override blocking it?
   Check: GET /api/entitlements/check/X?customer_id=N
   Fix:   PUT /api/entitlements/override {customer_id: N, feature: "X", enabled: true}

4. (Context Graph only) Is the per-customer context_graph toggle ON?
   Check: GET /api/features/context-graph?customer_id=N
   Fix:   POST /api/features/context-graph {customer_id: N, enabled: true}

5. (Context Graph only) Is the specific sub-toggle ON?
   Check: GET /api/features/context-graph?customer_id=N (check config)
   Fix:   PUT /api/features/context-graph/sub-toggle {customer_id: N, sub_toggle: "story_arcs", enabled: true}
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `backend/feature_toggles.py` | Global toggles + context graph sub-toggles + helpers |
| `backend/entitlements.py` | Tier catalog, check/require functions, API blueprint |
| `backend/feature_toggle_api.py` | Flask routes for toggle management |
| `backend/models.py` (FeatureToggle) | DB model for per-customer state |
| `src/components/dc/settings/EntitlementsAdmin.tsx` | Frontend UI for tier/feature management |
