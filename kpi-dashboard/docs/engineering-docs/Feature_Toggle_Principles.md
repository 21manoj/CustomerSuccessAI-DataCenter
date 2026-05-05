# Feature Toggle Engineering Principles

**Status:** Active — all new features MUST follow these principles
**Date:** March 22, 2026
**Author:** Manoj / Claude

## Core Principle

**If nobody's watching, nothing should be there.**

A feature toggle is not just a UI switch. When a feature is OFF, it must have ZERO footprint — no data written, no tables queried, no blueprints registered, no background processes running.

## Rules

### 1. Data Isolation

New features MUST write to their own tables, never to existing source-of-truth tables.

```
❌ WRONG:  New feature writes directly to qualitative_signals
✅ RIGHT:  New feature writes to qsim_signals, joined via view when ON
```

When toggle is OFF, the feature's tables exist but are never read by any API, dashboard, or background job.

### 2. Query-Time Join, Not Write-Time Merge

Feature data is merged with core data at query time (SQL UNION/VIEW), not at ingestion time. This ensures:
- Core tables remain the uncontaminated source of truth
- Toggle OFF = instant, no cleanup required
- Toggle ON = instant, no migration required
- Rollback = DROP TABLE, baseline restored

### 3. No Phantom Data

If a feature is toggled OFF:
- No new data enters the system from that feature
- Existing feature data is not deleted (preserves audit trail)
- But existing feature data is NOT queried or surfaced anywhere
- No dashboard, API, or MCP tool returns feature-specific data

If a feature has never been fully implemented:
- Auto-purge any test/partial data when toggle is turned OFF
- Until the feature has a complete pipeline (ingestion → processing → oversight → surfacing), stale data is a liability

### 4. Blueprint & Endpoint Isolation

When toggle is OFF:
- Flask blueprints for the feature are NOT registered
- API endpoints return 403/404 with clear message: "Feature X disabled"
- MCP tools for the feature are not exposed
- No background workers, event subscribers, or cron jobs run

### 5. Per-Customer + System Toggle

Every feature has TWO toggle levels:
- **System toggle** (env var): `FEATURE_X=true/false` — gates code loading at startup
- **Per-customer toggle** (DB): `FeatureToggle(customer_id, feature_name)` — gates runtime access

Both must be ON for the feature to be active for a given customer.

```python
# System level: controls blueprint registration
if os.environ.get('FEATURE_SIGNAL_ENGINE') == 'true':
    app.register_blueprint(signal_api)

# Customer level: controls per-request access
if not is_feature_enabled(customer_id, 'signal_engine'):
    return {"error": "Signal Engine not enabled for this customer"}, 403
```

### 6. Separate Tables, Shared Schema

Feature tables should share the same core column schema as the tables they extend, plus feature-specific columns. This enables clean UNION joins:

```sql
-- Core table (source of truth)
qualitative_signals: signal_id, account_id, signal_date, signal_type, content, sentiment

-- Feature table (isolated)
qsim_signals: signal_id, account_id, signal_date, signal_type, content, sentiment,
              + source_channel, structural_urgency, enrichment_status, ...

-- Query-time join (only when toggle ON)
CREATE VIEW unified_signals AS
  SELECT *, 'core' as source FROM qualitative_signals
  UNION ALL
  SELECT core_cols, 'feature' as source FROM qsim_signals
```

### 7. Audit & Observability

Every feature toggle change must be logged:
- Who toggled it (user_id, admin action)
- When (timestamp)
- For which customer
- Previous state → new state

Feature-specific data must always be tagged with its source so it can be traced, filtered, or removed independently.

### 8. Graceful Degradation

Dashboards and APIs must work identically whether a feature is ON or OFF:
- No empty states caused by missing feature data
- No error messages from disabled feature code paths
- Core functionality (health scores, accounts, context graph) is never dependent on optional features

## Checklist for New Features

Before merging any new feature:

- [ ] Separate table(s) created (not writing to existing tables)
- [ ] System toggle env var defined (`FEATURE_X`)
- [ ] Per-customer toggle wired (`FeatureToggle` DB model)
- [ ] Blueprint registration gated by system toggle
- [ ] All API endpoints return 403 when toggle OFF
- [ ] Query-time join (VIEW or conditional UNION) — not write-time merge
- [ ] Core table schema unchanged
- [ ] All existing tests pass with toggle OFF
- [ ] Toggle change logged to audit trail
- [ ] No phantom data: toggle OFF → zero feature data in API responses

## Applies To

| Feature | Table | Toggle |
|---------|-------|--------|
| Signal Engine (QSIM) | `qsim_signals` | `FEATURE_SIGNAL_ENGINE` |
| Context Graph | `context_nodes`, `context_edges` | `FEATURE_CONTEXT_GRAPH` |
| Story Arcs | (config files) | `story_arcs` per-customer |
| Partner Portal | (scoped queries) | `FEATURE_MCP_SERVER` |
| Future features | Follow this pattern | `FEATURE_<NAME>` |
