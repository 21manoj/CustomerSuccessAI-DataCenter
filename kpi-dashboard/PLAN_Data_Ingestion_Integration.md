# Data Ingestion & Integration — Sprint Plan

## Context

Data ingestion framework is 75% done: CSV pipeline (11 file types), webhook integration API, connector registry (sfdc/hubspot/zendesk/n8n), action providers (Salesforce/Jira/Slack/Email), SQS async worker, and n8n workflow templates all exist. The remaining 25% is about turning the framework into production connectors that pull data from real systems — especially Gainsight, which unlocks existing CS customers as buyers for CRO/CFO-level insights.

## Strategic Rationale

**Gainsight/third-party data ingestion via API** is the fastest path to revenue:
- 10,000+ companies use Gainsight/Totango/ChurnZero for CSM workflows
- They already HAVE the data (accounts, health scores, signals, stakeholders)
- CS Pulse adds CRO/CFO-level intelligence they CAN'T get from Gainsight
- API ingestion = no CSV re-mapping = 30-minute onboarding instead of 2 hours

---

## Sprint 1: Gainsight Connector (2 days)

### 1.1 Gainsight REST API Ingestion Provider

**Problem:** Gainsight customers have structured CS data but no CRO/CFO intelligence layer.

| File | Change |
|------|--------|
| `backend/providers/gainsight_provider.py` | **NEW** — GainsightProvider class. Pull: Company (→ accounts.csv), Relationship (→ stakeholders), Scorecard (→ kpi_measurements), CTA (→ signals), Timeline Activity (→ engagement_events). OAuth2 auth via Gainsight API v1. Rate limit: 100 req/min. |
| `backend/integration_models.py` | Add `gainsight` to CONNECTOR_TYPES with default field mappings (Company.ARR → arr, Company.Industry → industry, Scorecard.Score → health_score, etc.) |

### 1.2 Gainsight Field Mapping Engine

**Problem:** Field mappings stored in DB (`IntegrationConnector.field_mapping` JSON) but no engine applies them.

| File | Change |
|------|--------|
| `backend/utils/field_mapper.py` | **NEW** — `apply_field_mapping(source_records, mapping_config) -> csv_rows`. Applies column renames, type coercion (string→number, date parsing), value transforms (e.g., Gainsight health color → numeric score). Returns data shaped like our CSV schemas. |
| `backend/data_ingestion_api.py` | Wire field_mapper into the `/api/data-ingestion/*` endpoints. Before inserting records, apply mapping from the connector's `field_mapping` config. |

### 1.3 Gainsight Sync Scheduler

| File | Change |
|------|--------|
| `backend/utils/sync_scheduler.py` | **NEW** — `SyncScheduler` class. Reads `IntegrationConnector.sync_frequency_hours` and triggers pulls on schedule. Uses DailyProcessDataScheduler pattern (daemon thread). Writes IntegrationSyncLog for each run. |

---

## Sprint 2: Incremental Sync + Generic API Connectors (2 days)

### 2.1 Incremental Sync (Watermark-based)

**Problem:** Full-replace on every sync is wasteful. Need last-modified tracking.

| File | Change |
|------|--------|
| `backend/integration_models.py` | Add `last_sync_watermark` (DateTime) and `sync_mode` (full/incremental) to IntegrationConnector model. |
| `backend/providers/base.py` | Add `pull_incremental(since: datetime)` method to ProviderBase. Each provider implements incremental query (e.g., Gainsight: `WHERE LastModifiedDate > ?`). |
| `backend/utils/sync_scheduler.py` | On each sync: if `sync_mode='incremental'`, pass `last_sync_watermark` to provider. After success, update watermark to current time. |

### 2.2 Totango Connector

| File | Change |
|------|--------|
| `backend/providers/totango_provider.py` | **NEW** — Pull: Accounts, Attributes (→ kpi_measurements), Touchpoints (→ engagement_events), Users (→ stakeholders). REST API with app-token auth. |
| `backend/integration_models.py` | Add `totango` to CONNECTOR_TYPES. |

### 2.3 ChurnZero Connector

| File | Change |
|------|--------|
| `backend/providers/churnzero_provider.py` | **NEW** — Pull: Accounts, Segments (→ KPIs), Events (→ signals), Contacts (→ stakeholders). REST API with API key auth. |
| `backend/integration_models.py` | Add `churnzero` to CONNECTOR_TYPES. |

---

## Sprint 3: Zendesk/ServiceNow + Data Quality (2 days)

### 3.1 Zendesk Provider

**Problem:** Type registry + field mappings exist but no Python provider class.

| File | Change |
|------|--------|
| `backend/providers/zendesk_provider.py` | **NEW** — Pull: Tickets (→ signals/kpi_measurements for P3 support metrics), Users (→ stakeholders), Organizations (→ account enrichment). OAuth2 + API token auth. Maps ticket priority/status to KPI scores. |

### 3.2 ServiceNow Provider

| File | Change |
|------|--------|
| `backend/providers/servicenow_provider.py` | **NEW** — Pull: Incidents, Change Requests (→ operational KPIs for P2), Configuration Items (→ products). REST API with OAuth2. |

### 3.3 Data Quality Framework

**Problem:** No validation of ingested data quality — null rates, anomalies, completeness.

| File | Change |
|------|--------|
| `backend/utils/data_quality.py` | **NEW** — `assess_quality(customer_id) -> DataQualityReport`. Checks: null rates per column, value range violations, temporal gaps (missing months), cardinality anomalies (sudden spikes in record counts). Returns quality_score (0-100) + recommendations. |
| `backend/data_ingestion_api.py` | Add `GET /api/data-ingestion/quality?customer_id=X` endpoint. |

---

## Sprint 4: Integration Admin UI + Lineage (2 days)

### 4.1 Integration Management UI

**Problem:** Connectors can only be managed via API. Admin needs a UI.

| File | Change |
|------|--------|
| `src/components/admin/IntegrationManager.tsx` | **NEW** — List connectors (name, type, status, last sync, error count). Add/edit connector modal (type selector, credential fields, field mapping editor, sync frequency). Sync history table. Manual "Sync Now" button. |
| `src/components/SuperAdminConsole.tsx` | Add "Integrations" tab that renders IntegrationManager. |

### 4.2 Data Lineage Tracking

**Problem:** No tracking of which records came from which connector.

| File | Change |
|------|--------|
| `backend/models.py` | Add `source_connector_id` (nullable FK to IntegrationConnector) to Account, DC2SKPI, QualitativeSignal, ContextNode. Nullable — CSV-uploaded records have NULL. |
| `backend/data_ingestion_api.py` | Set `source_connector_id` on every record ingested via connector. |
| `backend/utils/data_quality.py` | Add lineage report: per connector, show record counts, last sync, coverage % of total data. |

---

## Files Summary

| Sprint | New Files | Modified Files |
|--------|-----------|----------------|
| 1 | gainsight_provider.py, field_mapper.py, sync_scheduler.py | integration_models.py, data_ingestion_api.py |
| 2 | totango_provider.py, churnzero_provider.py | integration_models.py, providers/base.py, sync_scheduler.py |
| 3 | zendesk_provider.py, servicenow_provider.py, data_quality.py | data_ingestion_api.py |
| 4 | IntegrationManager.tsx | SuperAdminConsole.tsx, models.py, data_ingestion_api.py, data_quality.py |

**Total: 10 new files, 8 modified across 4 sprints (~8 days)**

## Priority Order

1. **Sprint 1 (Gainsight)** — highest revenue impact. Existing Gainsight customers can get CRO/CFO insights within 30 minutes.
2. **Sprint 2 (Totango/ChurnZero + incremental)** — expands TAM to other CS platform users.
3. **Sprint 3 (Zendesk/ServiceNow)** — enriches P2/P3 pillar data from operational systems.
4. **Sprint 4 (UI + lineage)** — operational maturity for managing integrations at scale.
