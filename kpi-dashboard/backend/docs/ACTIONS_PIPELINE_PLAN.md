# Actions Pipeline — Push Not Pull
**Created:** 2026-03-25
**Branch:** feature/actions-pipeline-push
**Status:** Planning complete, implementation not started

---

## Problem Statement

Every CSM-facing tool today is **pull**: the CSM must open the dashboard, query an account,
or ask the AI chatbot. The platform has no ability to proactively alert CSMs when something
critical happens. This plan adds a push layer on top of the existing health scoring,
context graph, and wizard infrastructure.

---

## Shared Infrastructure (Build First)

### 1. Trigger Points
Events that fire the push pipeline. Three sources:

| Trigger | Where | Condition |
|---|---|---|
| Process-data completes | `_process_data_impl()` exit | Always — check delta since last run |
| Wizard run completes | Each wizard exit hook | Always — wizard result may contain alerts |
| New ContextEdge ingested | `ingest_context_graph_csvs()` exit | `confidence > 0.85` |

### 2. Notification Bus

**New DB model** — `Notification`:
```python
class Notification(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    customer_id   = db.Column(db.Integer, db.ForeignKey('customers.customer_id'))
    account_id    = db.Column(db.Integer, db.ForeignKey('accounts.account_id'), nullable=True)
    type          = db.Column(db.String(50))   # signal_insight | playbook_triggered | urgent_alert
    priority      = db.Column(db.String(20))   # normal | high | critical
    payload       = db.Column(db.JSON)         # structured content per type
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    read_at       = db.Column(db.DateTime, nullable=True)
```

**New API endpoint:**
```
GET /api/notifications/unread   → { count, notifications[] }
PUT /api/notifications/{id}/read
```

**Frontend:**
- Badge count in CSM dashboard header (polls `/api/notifications/unread` every 60s)
- Notification drawer: sorted by priority (critical first), then created_at desc
- Urgent alerts rendered above playbook queue regardless of age

**Phase 2 (deferred):** webhook → Slack/Teams via `POST /api/notifications/webhook`

---

## Layer A — Signal Analyst (Proactive LLM Narrative)

**New file:** `backend/utils/signal_analyst.py`

### Trigger Conditions
- Account health drops > 10pts since last process-data run
- New `ContextNode(SIGNAL)` with `severity=critical` ingested

### Logic
```python
def analyze_account(account_id, health_before, health_after, arc_type) -> dict:
    # Collect context
    kpi_deltas   = get_pillar_deltas(account_id)          # L2 scores before/after
    signals      = get_recent_signals(account_id, n=5)    # last 5 ContextNode(SIGNAL) texts

    # Build LLM prompt
    prompt = f"""
    Account {account_id} health dropped from {health_before} → {health_after}.
    Arc type: {arc_type}.
    KPI changes: {kpi_deltas}
    Recent signals: {signals}

    Generate:
    1. A 3-sentence narrative insight explaining what's happening
    2. Top 2 risks with estimated impact
    3. One recommended immediate action
    """

    # Call LLM (reuse existing /api/rag-query infrastructure)
    insight = call_llm(prompt)

    # Store as notification
    create_notification(
        customer_id=..., account_id=account_id,
        type='signal_insight', priority='high',
        payload={'insight': insight, 'health_delta': health_after - health_before}
    )
```

### Files
| File | Change |
|---|---|
| `backend/utils/signal_analyst.py` | **NEW** — LLM wrapper, trigger logic |
| `backend/mcp_server/cs_pulse_onboarding.py` | Call `signal_analyst.check_and_analyze()` at `_process_data_impl()` exit |
| `backend/models.py` | Add `Notification` model |
| `backend/api_routes.py` | Add `/api/notifications/unread` + `/api/notifications/{id}/read` |
| `src/components/csm/NotificationDrawer.tsx` | **NEW** — badge + drawer UI |

---

## Layer B — Playbook Auto-Trigger

**New config:** `backend/config/arc_playbook_map.json`
**New model:** `PlaybookTask`

### Arc → Playbook Mapping
```json
{
  "crisis_recovery":        ["PB-02", "PB-01"],
  "champion_loss":          ["PB-04", "PB-01"],
  "budget_pressure":        ["PB-06", "PB-03"],
  "stalled_deployment":     ["PB-01", "PB-05"],
  "competitor_evaluation":  ["PB-03", "PB-04"],
  "infrastructure_decay":   ["PB-05", "PB-02"],
  "steady_performer":       ["PB-07"],
  "land_and_expand":        ["PB-08"],
  "engagement_decline":     ["PB-06", "PB-04"],
  "budget_pressure":        ["PB-06"]
}
```

### PlaybookTask Model
```python
class PlaybookTask(db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    customer_id    = db.Column(db.Integer, db.ForeignKey('customers.customer_id'))
    account_id     = db.Column(db.Integer, db.ForeignKey('accounts.account_id'))
    playbook_id    = db.Column(db.String(20))      # PB-04
    trigger_reason = db.Column(db.String(200))     # 'arc_assigned:champion_loss'
    trigger_source = db.Column(db.String(50))      # 'wizard_a' | 'health_threshold' | 'manual'
    assigned_csm   = db.Column(db.String(100))
    due_date       = db.Column(db.DateTime)
    status         = db.Column(db.String(20), default='pending')  # pending|active|done|dismissed
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
```

### Trigger Points
1. **Wizard A assigns arc type** → look up `arc_playbook_map.json` → create `PlaybookTask`
2. **Health crosses boundary** (healthy→at_risk, at_risk→critical) in `_process_data_impl()`

### Integration with get_csm_daily_actions
```python
# Current: generates recommendations from scratch every call
# New: reads PlaybookTask first, appends generated recommendations

def get_csm_daily_actions(customer_id):
    # 1. Pending PlaybookTasks (system-triggered, appear first)
    queued = PlaybookTask.query.filter_by(customer_id=customer_id, status='pending').all()

    # 2. Generated recommendations (as today)
    generated = generate_recommendations(customer_id)

    return {'queued_tasks': queued, 'recommendations': generated}
```

### Files
| File | Change |
|---|---|
| `backend/config/arc_playbook_map.json` | **NEW** — arc → playbook mapping |
| `backend/models.py` | Add `PlaybookTask` model |
| `backend/verticals/dc2_s/api_routes.py` | `get_csm_daily_actions` reads `PlaybookTask` first |
| `backend/wizards/wizard_a_journey_db.py` | Create `PlaybookTask` after arc assignment |
| `backend/mcp_server/cs_pulse_onboarding.py` | Create `PlaybookTask` on health boundary crossing |

---

## Layer C — Context Graph Urgent Pre-emption

**New file:** `backend/utils/urgent_signal_scanner.py`

### Scan Logic
```python
def scan_for_urgent_signals(customer_id, account_id):
    # Find high-confidence causal chains ending in negative outcomes
    edges = ContextEdge.query.filter(
        ContextEdge.account_id == account_id,
        ContextEdge.confidence >= 0.85
    ).all()

    for edge in edges:
        to_node = ContextNode.query.get(edge.to_node_id)
        if to_node.node_type == 'OUTCOME' and to_node.revenue_impact < -50000:
            account = Account.query.get(account_id)
            days_to_renewal = (account.renewal_date - datetime.utcnow()).days

            if days_to_renewal <= 60:
                urgency = abs(to_node.revenue_impact) * edge.confidence / max(days_to_renewal, 1)

                if urgency > URGENCY_THRESHOLD:
                    create_notification(
                        type='urgent_alert', priority='critical',
                        payload={
                            'revenue_at_risk': to_node.revenue_impact,
                            'confidence': edge.confidence,
                            'days_to_renewal': days_to_renewal,
                            'causal_chain': build_chain_summary(edge),
                            'urgency_score': urgency
                        }
                    )
```

### Trigger Points
- End of `ingest_context_graph_csvs()` — after edges land
- End of Wizard A edge generation (Sprint 1) — after arc-derived edges land

### Files
| File | Change |
|---|---|
| `backend/utils/urgent_signal_scanner.py` | **NEW** — graph traversal + urgency scoring |
| `backend/onboarding_api_v2_config_aware.py` | Call scanner after `ingest_context_graph_csvs()` |
| `src/components/csm/NotificationDrawer.tsx` | Urgent alerts rendered above playbook queue |

---

## Sprint Execution Plan

### Sprint 1 — Wizard A Arc Intelligence Engine
**Goal:** Real customer CSV → arc classified → context graph edges generated without load driver
**Duration:** 2 sessions | **Priority:** Must-have

#### Session 1 — Arc Classifier + Backend RefRegistry
| File | Change |
|---|---|
| `backend/utils/arc_classifier.py` | **NEW** — feature extraction + arc pattern matching |
| `backend/utils/arc_edge_generator.py` | **NEW** — backend RefRegistry equivalent, ContextEdge INSERT |

#### Session 2 — Wizard A Rewrite + Integration
| File | Change |
|---|---|
| `backend/wizards/wizard_a_journey_db.py` | Rewrite — calls arc_classifier + arc_edge_generator per account |
| `backend/models.py` | Add `arc_type`, `arc_phase`, `arc_confidence` to `Account` |
| `backend/onboarding_api_v2_config_aware.py` | Call Wizard A after `ingest_context_graph_csvs()` |
| `backend/mcp_server/cs_pulse_onboarding.py` | `_process_data_impl()` calls `run_wizard_a()` at Path 2 exit |

**Validation test:** `granite_peak_dc2s.json --generate-only` → strip `signal_edges.csv` → upload 9 CSVs →
process-data → Wizard A regenerates equivalent edges → compare node/edge counts vs full 10-CSV run.

---

### Sprint 2 — Wizard B Predictive Risk + Basic Push
**Goal:** 60-day churn/expansion signal + proactive CSM alert on threshold breach
**Duration:** 3 sessions | **Priority:** Urgent

#### Session 1 — KPI Feature Extraction + Clustering
| File | Change |
|---|---|
| `backend/utils/kpi_feature_extractor.py` | **NEW** — normalized feature vector per account |
| `backend/wizards/wizard_b_pattern_db.py` | Rewrite: KMeans replaces GroupBy shell |
| `backend/models.py` | Add `RiskScore` model |

Feature vector: `[health_now, health_30d, health_60d, health_90d, slope_14d, slope_30d, slope_60d, p1..p5_score, p1..p5_delta_30d, signal_count_critical_30d, signal_count_positive_30d, days_to_renewal, arr_normalized]`

KMeans k=4: `early_warning | active_recovery | stable_growth | churn_risk`

#### Session 2 — Peer Matching + Change-Point Detection
| File | Change |
|---|---|
| `backend/utils/peer_matcher.py` | **NEW** — fastdtw similarity, top-3 peers with outcome history |
| `backend/utils/changepoint_detector.py` | **NEW** — per-KPI slope scan, early decay flag |
| `backend/wizards/wizard_b_pattern_db.py` | Wire peer_matcher + changepoint_detector |

#### Session 3 — Churn Probability + Push Infrastructure
| File | Change |
|---|---|
| `backend/utils/churn_probability.py` | **NEW** — `P(churn) = w1×arc + w2×health + w3×slope + w4×renewal + w5×peer` |
| `backend/models.py` | Add `Notification` + `PlaybookTask` models |
| `backend/utils/urgent_signal_scanner.py` | **NEW** — causal chain urgency scoring |
| `backend/api_routes.py` | `GET /api/notifications/unread` |
| `backend/mcp_server/cs_pulse_onboarding.py` | Wizard B + scanner at `_process_data_impl()` exit |
| `src/components/csm/NotificationDrawer.tsx` | **NEW** — badge + drawer |

Churn formula (v1, rule-weighted — no training data needed):
```
P(churn) = w1 × arc_risk_score[arc_type]
         + w2 × (1 - health_norm)
         + w3 × slope_signal
         + w4 × (1 / days_to_renewal_norm)
         + w5 × peer_churn_rate

arc_risk_score: champion_loss=0.8, crisis_recovery=0.7, budget_pressure=0.5,
                stalled_deployment=0.45, steady_performer=0.1
```

---

### Sprint 3 — Wizard C Adaptive + Full Push Pipeline
**Goal:** Platform learns from actual outcomes. Full CSM push experience.
**Duration:** 3 sessions | **Priority:** Nice-to-have

#### Session 1 — Outcome Feedback Loop
| File | Change |
|---|---|
| `backend/wizards/wizard_c_weight_calibrator_db.py` | Add `ingest_outcome_feedback()` |
| `backend/models.py` | Add `ArcOutcomeMatrix` model |
| `backend/api_routes.py` | `POST /api/accounts/{id}/record-outcome` |

#### Session 2 — Per-Customer Arc Fingerprint
| File | Change |
|---|---|
| `backend/wizards/wizard_c_weight_calibrator_db.py` | Add `compute_arc_fingerprint()` |
| `backend/models.py` | Add `CustomerArcFingerprint` model |
| `backend/wizards/wizard_a_journey_db.py` | Load fingerprint as Bayesian prior |

#### Session 3 — Full Push Completion
| Component | What |
|---|---|
| `config/arc_playbook_map.json` | 10 arcs × recommended playbooks |
| `utils/signal_analyst.py` | LLM narrative on health drop / critical signal |
| Layer B auto-queue | `PlaybookTask` created on arc assignment → feeds `get_csm_daily_actions` |
| Layer C pre-emption | `urgent_signal_scanner.py` wired to post-ingestion + post-Wizard-A |
| Slack webhook | `POST /api/notifications/webhook` |
| Email digest | Daily summary: at-risk accounts, triggered playbooks, urgent alerts |

---

## File Map (All New Files This Branch)

```
backend/
  utils/
    signal_analyst.py          ← Layer A: LLM narrative trigger
    urgent_signal_scanner.py   ← Layer C: causal chain urgency
    arc_classifier.py          ← Sprint 1: arc pattern matching
    arc_edge_generator.py      ← Sprint 1: backend RefRegistry + edge INSERT
    kpi_feature_extractor.py   ← Sprint 2: feature vectors
    peer_matcher.py            ← Sprint 2: fastdtw peer similarity
    changepoint_detector.py    ← Sprint 2: early KPI decay detection
    churn_probability.py       ← Sprint 2: P(churn) scoring model
  config/
    arc_playbook_map.json      ← Layer B: arc → playbook mapping
  models.py                    ← Notification, PlaybookTask, RiskScore,
                                  ArcOutcomeMatrix, CustomerArcFingerprint

src/components/csm/
  NotificationDrawer.tsx       ← Sprint 2 Session 3: badge + alert drawer
```

---

## Open Questions / Decisions Needed

1. **LLM provider for signal_analyst.py** — reuse existing OpenAI key from customer config, or separate key?
2. **URGENCY_THRESHOLD value** — needs calibration. Start at `revenue_impact × confidence / days = 5000`?
3. **Notification TTL** — how long do unread notifications persist? 30 days?
4. **PlaybookTask assignment** — auto-assign to account's CSM owner, or leave unassigned for CSM to claim?
5. **Slack webhook** — per-customer config or platform-wide? Suggest per-customer via `integration_credentials` table.
