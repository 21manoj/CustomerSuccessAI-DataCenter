# Signal Analyst — Status, Scope & Architecture

**Document version:** 1.0  
**Last updated:** 2026-01  
**Location:** `kpi-dashboard/backend/agents/`

---

## 1. Status & Scope

### 1.1 Current Status

| Area | Status | Notes |
|------|--------|--------|
| **Core Agent** | ✅ Production | `SignalAnalystAgent` with GPT-4o, retries, cost tracking |
| **API** | ✅ Production | `POST /api/signal-analyst/analyze`, `POST /api/signal-analyst/test` |
| **Signal Sources** | ✅ Active | Qdrant (vector) + PostgreSQL (Account, KPI, DC2SKPI, AccountNote) |
| **Verticals** | ✅ Supported | SaaS Customer Success, Data Center Infrastructure |
| **Frontend** | ✅ Integrated | Executive Dashboard, Journey V3, shared SignalAnalyst, DC Platform |
| **Cost Tracking** | ✅ Enabled | `CostTracker` → DB when `DATABASE_URL` set |
| **Tests** | ✅ Present | `test_run_analysis_and_rag.py`, `test_dc2s_endpoints_auth.py`, journey/vertical tests |

### 1.2 Scope

**In scope:**

- Churn probability (0–100%)
- Expansion probability (0–100%)
- Health score (0–100)
- Predicted outcome: `churn` | `expansion` | `stable` | `downgrade` | `contraction`
- Risk drivers and growth drivers with impact + supporting signals
- Recommended actions (priority, owner, deadline_days, expected_impact)
- Confidence (overall + factors: signal_quality, signal_quantity, historical_matches, pattern_clarity)
- Reasoning (markdown) and key insights (bullets)
- Tenant isolation via `customer_id`; account-scoped signals

**Out of scope (current design):**

- Real-time streaming; responses are request/response only
- Model choice from client; fixed to `gpt-4o`
- Embedding generation inside the agent; uses RAG system’s `_generate_embedding` for Qdrant queries
- Historical patterns from DB; only from Qdrant or mock (DB path returns `historical_patterns: []`)

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SIGNAL ANALYST PIPELINE                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  HTTP Request          Signal Collection           Agent              Response  │
│  ─────────────         ─────────────────           ─────              ───────   │
│                                                                                 │
│  POST /analyze    →    Qdrant + PostgreSQL   →   SignalAnalystAgent   →  JSON   │
│  (account_id,          (quant + qual +            (prompts, OpenAI,       │
│   analysis_type,        historical signals)        parse, validate)        │
│   time_horizon_days)                                                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

**Processing layers (high level):**

1. **API layer** — Auth, validation, orchestration
2. **Signal collection** — Qdrant + DB → `SignalData`
3. **Conversion** — DB models / Qdrant results → normalized signals
4. **Prompt layer** — Vertical-specific system prompt + analysis user prompt
5. **LLM layer** — OpenAI GPT-4o, retries, circuit breaker, cost tracking
6. **Parse & validate** — JSON → `SignalAnalystOutput` (Pydantic)
7. **Response** — JSON to client + optional `_metadata`

---

## 3. Inputs

### 3.1 HTTP API Request

**Endpoint:** `POST /api/signal-analyst/analyze`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `account_id` | string or int | ✅ | — | Account to analyze; must be positive integer when parsed |
| `analysis_type` | string | ❌ | `"comprehensive"` | `comprehensive` \| `churn_risk` \| `expansion_opportunity` \| `health_analysis` |
| `time_horizon_days` | int | ❌ | `60` | Prediction horizon; must be 30–365 |
| `use_qdrant` | bool | ❌ | `true` | Use Qdrant for signal retrieval |
| `use_database` | bool | ❌ | `true` | Use PostgreSQL (Account, KPI/DC2SKPI, Notes) for signals |

**Headers:** Session auth; `customer_id` from `get_current_customer_id()`.

**Example:**

```json
{
  "account_id": "119001",
  "analysis_type": "comprehensive",
  "time_horizon_days": 60,
  "use_qdrant": true,
  "use_database": true
}
```

### 3.2 Internal Input Model: `SignalAnalystInput`

Used by the agent. Built by the API from the HTTP request + DB + Qdrant.

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | str | Account identifier |
| `customer_id` | int | Tenant ID |
| `vertical_type` | str | `saas_customer_success` or `data_center_infrastructure` |
| `account_name` | str, optional | From `Account` |
| `account_arr` | float, optional | From `Account.revenue` |
| `account_segment` | str, optional | smb / mid_market / enterprise |
| `quantitative_signals` | `List[SignalData]` | KPIs, usage, revenue, etc. |
| `qualitative_signals` | `List[SignalData]` | Notes, tickets, sentiment, etc. |
| `historical_patterns` | `List[SignalData]` | Similar past outcomes |
| `analysis_type` | literal | Same as API |
| `time_horizon_days` | int | Same as API |

### 3.3 Signal Model: `SignalData`

Unified shape for all signals (Qdrant or DB).

| Field | Type | Description |
|-------|------|-------------|
| `similarity` | float | 0–1; from vector search or default (e.g. 0.8–0.9 for DB) |
| `payload` | dict | Type-specific attributes (see below) |

**Payload conventions:**

- **Quantitative:** `pillar`, `metric_type`, `current_value`, `trend`, `account_id`, `kpi_id`, `text`, …
- **Qualitative:** `signal_type`, `signal_source` (internal/external), `sentiment`, `severity`, `text`, …
- **Historical:** `outcome_type`, `signals_summary`, …
- **DC2S:** `kpi_code`, `pillar`, `target_value`, `status`, `weight`, …

---

## 4. Outputs

### 4.1 HTTP API Response

**Success:** `200` + JSON body = `SignalAnalystOutput` (see below), with optional `_metadata`:

```json
{
  "_metadata": {
    "endpoint": "/api/signal-analyst/analyze",
    "model": "gpt-4o",
    "cost_tracked": true,
    "timestamp": 1234567890.123
  },
  "account_id": "119001",
  "customer_id": 119,
  "vertical_type": "saas_customer_success",
  "predicted_outcome": "stable",
  "churn_probability": 40.0,
  "expansion_probability": 20.0,
  "health_score": 60.0,
  "time_to_event": "45-60 days",
  "risk_drivers": [...],
  "growth_drivers": [...],
  "confidence": {...},
  "reasoning": "## Overall Health Status...",
  "key_insights": ["...", "..."],
  "recommended_actions": [...],
  "signals_analyzed": {"quantitative": 12, "qualitative": 3},
  "analysis_timestamp": "2026-01-22T20:00:00",
  "model_used": "gpt-4o",
  "analysis_duration_ms": 2500
}
```

**Errors:** `400` (validation), `401` (auth), `404` (account not found), `500` (analysis/parse failure).

**Test endpoint:** `POST /api/signal-analyst/test` — Same auth and `analysis_type` / `time_horizon_days` validation, but uses **mock** quantitative, qualitative, and historical signals (no Qdrant/DB). Returns `SignalAnalystOutput` with `_test_mode: true` and `_mock_data_used: true`. Useful for verifying agent and prompts without real data.

### 4.2 Output Model: `SignalAnalystOutput`

| Field | Type | Description |
|-------|------|-------------|
| `account_id` | str | Echo of input |
| `customer_id` | int | Echo of input |
| `vertical_type` | str | Echo of input |
| `predicted_outcome` | `OutcomeType` | `churn` \| `expansion` \| `stable` \| `downgrade` \| `contraction` |
| `churn_probability` | float | 0–100 |
| `expansion_probability` | float, optional | 0–100 |
| `health_score` | float | 0–100 |
| `time_to_event` | str, optional | e.g. `"45-60 days"` |
| `risk_drivers` | `List[RiskDriver]` | Churn drivers |
| `growth_drivers` | `List[GrowthDriver]` | Expansion drivers |
| `confidence` | `PredictionConfidence` | Overall + factors |
| `reasoning` | str | Markdown explanation |
| `key_insights` | `List[str]` | Bullet takeaways |
| `recommended_actions` | `List[RecommendedAction]` | Action plan |
| `signals_analyzed` | `Dict[str, int]` | Counts by type |
| `analysis_timestamp` | datetime | Run time |
| `model_used` | str | e.g. `gpt-4o` |
| `analysis_duration_ms` | int, optional | Wall-clock ms |

### 4.3 Nested Output Types

**`RiskDriver`:** `driver`, `impact` (critical|high|medium|low), `supporting_signals`, `confidence`  
**`GrowthDriver`:** same shape, for expansion.  
**`RecommendedAction`:** `action`, `priority`, `owner`, `deadline_days`, `expected_impact`.  
**`PredictionConfidence`:** `overall_confidence`, `confidence_level` (very_high → very_low), `confidence_factors` (e.g. signal_quality, signal_quantity, historical_matches, pattern_clarity).

---

## 5. Processing Layers

### 5.1 Layer 1: API (`signal_analyst_api.py`)

- **Auth:** `get_current_customer_id()`; reject if missing.
- **Validation:** `account_id` (positive int), `analysis_type`, `time_horizon_days`, `use_qdrant`, `use_database`.
- **Account resolution:** `Account` by `(account_id, customer_id)`; 404 if not found.
- **Vertical:** `map_vertical_to_agent_type` (default `saas` → `saas_customer_success`); DC detected via `account.vertical` or presence of `DC2SKPI`.
- **Orchestration:** Call signal collection → build `SignalAnalystInput` → run agent → return `SignalAnalystOutput` as JSON.

### 5.2 Layer 2: Signal Collection

Two optional sources (both can be used):

**A. Qdrant (`qdrant_integration.py`)**

- Collection: `kpi_dashboard_vectors_customer_{customer_id}`.
- Uses `EnhancedRAGSystemQdrant` (`get_qdrant_rag_system(customer_id)`) for client and `_generate_embedding`.
- Three query types:
  - **Quantitative:** `get_quantitative_signals_from_qdrant` — query like “account X KPI metrics usage revenue health score …”; `top_k` (default 20).
  - **Qualitative:** `get_qualitative_signals_from_qdrant` — “account X support tickets emails notes sentiment …”; `top_k` 20.
  - **Historical:** `get_historical_patterns_from_qdrant` — “account X historical trends patterns …”; `top_k` 10.
- Results filtered by `account_id` in payload; converted to `SignalData` via `convert_qdrant_results_to_signal_data` (or equivalent in-place mapping).
- On Qdrant errors, API logs and continues with DB-only signals when `use_database` is true.

**B. PostgreSQL (`signal_converter.py` + API)**

- **Account →** `convert_account_to_signal_data` → quantitative-style `SignalData` (revenue, industry, etc.).
- **SaaS:** `KPI` → `convert_kpi_to_signal_data` → quantitative `SignalData` (pillar, metric_type, current_value, trend).
- **DC:** `DC2SKPI` → `convert_dc2s_kpi_to_signal_data` → quantitative `SignalData` (kpi_code, pillar, target, status, weight).
- **Notes:** `AccountNote` → `convert_account_notes_to_signal_data` → qualitative `SignalData` (signal_type, sentiment, severity, text).
- `convert_database_models_to_signals` returns `quantitative_signals`, `qualitative_signals`, `historical_patterns` (DB path leaves `historical_patterns` empty).

### 5.3 Layer 3: Vertical Mapping (`vertical_mapper.py`)

- `map_vertical_to_agent_type`: `saas` → `saas_customer_success`; `datacenter` / `data_center` → `data_center_infrastructure`.
- Used by API when building `SignalAnalystInput.vertical_type` and in prompts.

### 5.4 Layer 4: Prompts (`prompts.py`)

- **System prompt:** `SignalAnalystPrompts.get_system_prompt(vertical_type)`  
  - Base: data-driven, explainable, actionable, honest, nuanced.  
  - Vertical-specific: SaaS vs Data Center churn/expansion indicators.
- **User prompt:** `get_analysis_prompt(...)`  
  - Account info (id, name, ARR).  
  - Formatted quantitative, qualitative, and historical sections (from `format_*` helpers).  
  - Required JSON schema for the model output (outcome, probabilities, drivers, confidence, reasoning, insights, actions).  
  - Rules: base predictions only on provided signals, handle conflicts, consider recency/severity, etc.
- **Formatting:**  
  - `format_quantitative_signals`: pillar, metric_type, value, trend.  
  - `format_qualitative_signals`: signal_type, source, sentiment, severity, text.  
  - `format_historical_patterns`: outcome_type, signals_summary.

### 5.5 Layer 5: Agent & LLM (`signal_analyst_agent.py`)

- **`SignalAnalystAgent.analyze(input_data: SignalAnalystInput) -> SignalAnalystOutput`**
  1. Format signals via prompt helpers.
  2. Build system + user prompts.
  3. Check circuit breaker (opens after 3 failures; 2 min cooldown).
  4. `_call_openai_with_tracking`: GPT-4o, `response_format={"type": "json_object"}`, retries (`@retry_on_openai_error`), cost logging to `CostTracker`.
  5. `_parse_response`: strip markdown code fences, `json.loads`, map to `SignalAnalystOutput` (including `PredictionConfidence` and `confidence_level` inference).
  6. Set `analysis_duration_ms`.
  7. Return `SignalAnalystOutput`.

- **Exceptions:** `AnalysisError` (e.g. circuit breaker, analysis failure), `ResponseParseError` (invalid or non-JSON LLM output).

### 5.6 Layer 6: Parse & Validate

- Raw LLM string → strip ```json / ``` → parse JSON.
- Build `SignalAnalystOutput` with Pydantic; infer `confidence_level` from `overall_confidence` if missing.
- On failure → `ResponseParseError` → API returns 500 with generic message.

### 5.7 Layer 7: Response

- `result_dict = analysis_result.model_dump()`.
- Add `_metadata` (endpoint, model, cost_tracked, timestamp).
- `jsonify(result_dict)`, 200.

---

## 6. Data Flow (End-to-End)

```
Client                    API                     Signal collection           Agent                     OpenAI
  │                        │                              │                      │                         │
  │  POST /analyze         │                              │                      │                         │
  │  {account_id, ...}     │                              │                      │                         │
  │ ──────────────────────>│  auth, validate              │                      │                         │
  │                        │  load Account                │                      │                         │
  │                        │  vertical, DC check          │                      │                         │
  │                        │                              │                      │                         │
  │                        │  use_qdrant?                 │                      │                         │
  │                        │ ────────────────────────────>│  Qdrant queries      │                         │
  │                        │                              │  (quant, qual, hist) │                         │
  │                        │<────────────────────────────│  List[SignalData]     │                         │
  │                        │                              │                      │                         │
  │                        │  use_database?               │                      │                         │
  │                        │ ────────────────────────────>│  Account,KPI,DC2S,   │                         │
  │                        │                              │  Notes → convert_*   │                         │
  │                        │<────────────────────────────│  List[SignalData]     │                         │
  │                        │                              │                      │                         │
  │                        │  SignalAnalystInput          │                      │                         │
  │                        │ ──────────────────────────────────────────────────>│  format signals         │
  │                        │                              │                      │  build prompts          │
  │                        │                              │                      │ ───────────────────────>│  chat completion
  │                        │                              │                      │<───────────────────────│  JSON
  │                        │                              │                      │  parse → Output         │
  │                        │<──────────────────────────────────────────────────│                         │
  │                        │  jsonify(Output)             │                      │                         │
  │<───────────────────────│                              │                      │                         │
  │  200 + JSON            │                              │                      │                         │
```

---

## 7. File Structure

```
kpi-dashboard/backend/agents/
├── __init__.py              # Exports: Agent, Input/Output, Errors, etc.
├── models.py                # SignalData, SignalAnalystInput, SignalAnalystOutput, RiskDriver, ...
├── prompts.py               # System/user prompts, signal formatting
├── signal_analyst_agent.py  # SignalAnalystAgent, analyze(), _call_openai_with_tracking, _parse_response
├── signal_analyst_api.py    # Flask blueprint: /analyze, /test
├── signal_converter.py      # DB → SignalData (Account, KPI, DC2SKPI, AccountNote)
├── qdrant_integration.py    # Qdrant → SignalData (quant, qual, historical)
├── vertical_mapper.py       # saas/datacenter → agent vertical types
├── README.md                # Quick start, API usage
└── SIGNAL_ANALYST_ARCHITECTURE.md   # This document
```

**Dependencies:**

- `auth_middleware`, `extensions`, `models` (App DB), `openai_key_utils`
- `enhanced_rag_qdrant` (`get_qdrant_rag_system`)
- `utils.error_handling` (retry, circuit breaker), `utils.logging_config`, `utils.cost_tracker`

---

## 8. Integration Points

### 8.1 Backend

- **App registration:** `app_v3_minimal` / `app` register `signal_analyst_api` blueprint → `/api/signal-analyst/*`.
- **Auth:** `get_current_customer_id()`; no custom auth inside agent.
- **OpenAI key:** `get_openai_api_key(customer_id)`; 400 if missing.
- **RAG:** `EnhancedRAGSystemQdrant` per customer for Qdrant + embeddings.
- **Cost tracking:** `CostTracker` in `utils`; writes to DB when `DATABASE_URL` is set.

### 8.2 Frontend

| Component | Usage |
|-----------|--------|
| **Executive Dashboard** | “Run Analysis” on account cards → `POST /api/signal-analyst/analyze`; updates health/churn/expansion and shows reasoning. |
| **Journey V3** | “Run Analysis” in analyst view → same endpoint; displays outcome, churn/expansion, insights. |
| **Shared SignalAnalyst** | Generic Run Analysis UI → same endpoint. |
| **DC Platform** | `/dc-dashboard/signal-analyst` tab → uses same analyst/API. |
| **AnalysisProgressModal** | Optional progress UI around `POST /api/signal-analyst/analyze`. |

All use `credentials: 'include'` (or equivalent) for session auth.

### 8.3 Tests

- `test_run_analysis_and_rag.py`: Run Analysis + RAG sanity checks.
- `test_dc2s_endpoints_auth.py`: Auth’d hit on `/api/signal-analyst/analyze`.
- `test_cs_pulse.py`: Optional `test_signal_analyst_api`.
- Vertical-specific: e.g. `verticals/customerXXX-dc2_s/journey/scripts/phase5/test_signal_analyst.py`, various `test_signal_analyst_v*.py`.

---

## 9. Verticals, Cost & Operations

### 9.1 Verticals

- **SaaS:** Usage, champion, support, NPS, payment, feature adoption, funding/product launches.
- **Data Center:** GPU health, utilization, RMA, support escalations, competitor mentions; expansion via utilization, funding, benchmarks, new workloads.

### 9.2 Cost

- **Model:** GPT-4o (~$2.50 / 1M input, $10 / 1M output).
- **Per run:** ~\$0.02–\$0.05 per account (README).
- **Tracking:** Logged via `CostTracker` (provider, model, tokens, cost, customer_id, account_id, success/error).

### 9.3 Reliability

- **Retries:** `@retry_on_openai_error(max_attempts=3)` for OpenAI calls.
- **Circuit breaker:** 3 failures → open; 2 min timeout before retry.
- **Parsing:** `ResponseParseError` on invalid JSON; API returns 500 without leaking internals.

---

## 10. Summary

| Aspect | Summary |
|--------|---------|
| **Role** | Account-level churn/expansion prediction and health scoring using quantitative + qualitative + historical signals. |
| **Inputs** | `account_id`, `analysis_type`, `time_horizon_days`; signals from Qdrant and/or PostgreSQL. |
| **Outputs** | `SignalAnalystOutput`: outcome, probabilities, health score, drivers, confidence, reasoning, insights, actions. |
| **Processing** | API → signal collection (Qdrant + DB) → convert to `SignalData` → prompts → GPT-4o → parse → JSON response. |
| **Integrations** | Auth, OpenAI key store, RAG/Qdrant, cost tracker, Executive Dashboard, Journey V3, SignalAnalyst, DC Platform. |

For quick usage and examples, see `agents/README.md`.
