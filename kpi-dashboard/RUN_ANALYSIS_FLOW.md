# Current Flow: "Run Analysis"

End-to-end flow when the user clicks **Run Analysis** (Signal Analyst).

---

## 1. Entry points (frontend)

| Location | Trigger | Request body |
|----------|--------|--------------|
| **SignalAnalyst** (`shared/SignalAnalyst.tsx`, `SignalAnalyst.tsx`) | Button "Run Analysis" | `{ account_id, analysis_type: "comprehensive", time_horizon_days: 60 }` |
| **JourneyDashboardV3** (`journey-visualizer/JourneyDashboardV3.tsx`) | Button "Run Analysis" in Analyst tab | `{ account_id }` (defaults on backend for type/horizon) |
| **ExecutiveDashboard** (`dashboard/ExecutiveDashboard.tsx`) | "Run Analysis" on account row | Same as above via `handleRunAnalysis(accountId)` |
| **AnalysisProgressModal** | Progress modal flow | `apiCall('/api/signal-analyst/analyze', { account_id, ... })` |

All call **POST `/api/signal-analyst/analyze`** with `credentials: 'include'` (session cookie).  
Optional headers: `X-Customer-ID` (JourneyDashboardV3).

---

## 2. Backend: route and auth

- **App registration:** `app_v3_minimal.py` / `app.py` register `signal_analyst_api` blueprint.
- **Route:** `POST /api/signal-analyst/analyze` → `analyze_account()` in `backend/agents/signal_analyst_api.py`.
- **Auth:** `get_current_customer_id()`; no `customer_id` → **401 Authentication required**.
- **Request body:** Must be JSON; must include `account_id` (positive int). Optional: `analysis_type`, `time_horizon_days`, `use_qdrant`, `use_database`.

---

## 3. Backend: validation and context

1. **account_id**  
   Parsed as int; must be > 0. **404 Account not found** if no `Account` for `(account_id, customer_id)`.

2. **Vertical**  
   From `CustomerConfig.vertical` or default `'saas'` → mapped to agent vertical (e.g. `saas_customer_success`, `data_center_infrastructure`).

3. **Analysis params**  
   - `analysis_type`: one of `comprehensive`, `churn_risk`, `expansion_opportunity`, `health_analysis` (default `comprehensive`).  
   - `time_horizon_days`: 30–365 (default 60).  
   - `use_qdrant`: default True.  
   - `use_database`: default True.

4. **Health score**  
   - **DC2_S:** From `dc2s_kpis` via `calculate_kpi_health()` (latest per KPI code).  
   - **SaaS:** From `HealthTrend` or `HealthScoreStorageService` (recent trend or recalc).  
   Stored in `overall_health_score` and passed to the agent.

---

## 4. Backend: signal collection

Signals are collected from **Qdrant** and/or **database**, then **deduplicated** (prefer database).

### 4.1 Qdrant (if `use_qdrant`)

- `get_qdrant_rag_system(customer_id)`.
- **Quantitative:** `get_quantitative_signals_from_qdrant(..., top_k=20)`.
- **Qualitative:** `get_qualitative_signals_from_qdrant(..., top_k=20)`.
- **Historical:** `get_historical_patterns_from_qdrant(..., top_k=10)`.
- On error: log and continue; database is still used if `use_database` is True.

### 4.2 Database (if `use_database`)

- **Vertical detection:** `account.vertical` or presence of `DC2SKPI` for account.
- **Quantitative:**  
  - DC2_S: `DC2SKPI` for account, last 50, → converted via `convert_database_models_to_signals` (quantitative part).  
  - SaaS: `KPI` for account/customer, 50, same converter.
- **Qualitative:**  
  - `QualitativeSignal` for account, last 30, by `signal_date` desc.  
  - Converted with `convert_qualitative_signals_to_signal_data` (keeps `stakeholder_level`, `stakeholder_title`, etc.).
- **Other:**  
  - `AccountNote` (last 20) folded into the same converter where applicable.  
- Converter returns `quantitative_signals`, `qualitative_signals`, `historical_patterns`; DB qualitative list is extended with the `QualitativeSignal`-derived list.

### 4.3 Deduplication

- `deduplicate_signals(..., prefer_source='database')` for quantitative, qualitative, and historical.
- Final counts are logged and passed to the agent.

---

## 5. Backend: OpenAI key and agent input

- **OpenAI key:** `get_openai_api_key(customer_id)`. If missing → **400** with message to set key in Settings.
- **Agent input:** `SignalAnalystInput` with:
  - `account_id`, `customer_id`, `vertical_type`, `account_name`, `account_arr` (revenue), `health_score`,
  - `quantitative_signals`, `qualitative_signals`, `historical_patterns`,
  - `analysis_type`, `time_horizon_days`.

---

## 6. Backend: agent run (`SignalAnalystAgent.analyze`)

**File:** `backend/agents/signal_analyst_agent.py`.

1. **Format context for prompt**  
   - `format_quantitative_signals(...)` → string (pillar, metric_type, value, trend).  
   - `format_qualitative_signals(...)` → string (signal_type, source, sentiment, severity, text).  
   - `format_historical_patterns(...)` → string (outcome_type, signals_summary).

2. **Build prompts**  
   - System: `get_system_prompt(vertical_type)` (principles + vertical-specific churn/expansion cues).  
   - User: `get_analysis_prompt(..., quantitative_context, qualitative_context, historical_context, ...)` (account info, health, three signal blocks, JSON output spec, CRITICAL RULES).

3. **Call OpenAI**  
   - Circuit breaker checked; if open → `AnalysisError`.  
   - `_call_openai_with_tracking(system_prompt, user_prompt, ...)` with retries and cost tracking.  
   - Model: `gpt-4o`, `response_format={"type": "json_object"}`.

4. **Parse response**  
   - `_parse_response(raw_response, input_data, model_used)` → strip markdown fences, `json.loads`, build `SignalAnalystOutput` (predicted_outcome, churn/expansion probability, health_score, risk_drivers, growth_drivers, confidence, reasoning, key_insights, recommended_actions, etc.).

5. **Timing**  
   - `analysis_duration_ms` set on output.

6. **Return**  
   - Returns `SignalAnalystOutput` to the API.

---

## 7. Backend: response shaping and return

- `analysis_result.model_dump()` → `result_dict`.
- **Health score override:** If backend computed `overall_health_score` (e.g. DC2_S), it overwrites the agent’s `health_score` in `result_dict`; if the agent returned “bogus” default (e.g. 0 health, 85% churn), churn/expansion are recomputed from the real health score.
- **Metadata:** `_metadata`: endpoint, model, cost_tracked, timestamp.
- **Response:** `jsonify(result_dict)`, **200**.

On failure: **AnalysisError** / **ResponseParseError** → **500** with generic message; validation errors → **400**.

---

## 8. Frontend: after response

- **SignalAnalyst:** `setAnalysisResult(data)`, `setLastAnalyzed(new Date())`; UI renders reasoning, key_insights, risk_drivers, growth_drivers, recommended_actions, confidence, etc.
- **JourneyDashboardV3:** `setAnalystOutput({ ...result })` (maps API fields to local analyst state); only a subset of fields (e.g. `analysis_id`, `timestamp`, health/churn/expansion, drivers, actions, `signals_analyzed`, `model_used`, `analysis_duration_ms`) are explicitly set; reasoning/key_insights may be in `result` and rendered if the UI reads them.
- **ExecutiveDashboard:** Similar: analysis result is stored and can be shown (e.g. report modal).

---

## 9. Flow diagram (summary)

```
[User clicks "Run Analysis"]
        ↓
[Frontend: POST /api/signal-analyst/analyze { account_id, analysis_type?, time_horizon_days? }]
        ↓
[Backend: auth → validate account_id & params → load vertical & health score]
        ↓
[Collect signals: Qdrant (quant + qual + historical) and/or DB (DC2SKPI/KPI + QualitativeSignal + notes)]
        ↓
[Deduplicate signals (prefer DB)]
        ↓
[OpenAI key check → build SignalAnalystInput]
        ↓
[Agent: format quant/qual/historical context → build system + user prompt → call OpenAI (gpt-4o) → parse JSON → SignalAnalystOutput]
        ↓
[Override health score / churn–expansion if needed → add _metadata → 200 JSON]
        ↓
[Frontend: setAnalysisResult / setAnalystOutput → render report]
```

---

## 10. Time scope (how many weeks of data?)

The analysis does **not** use a fixed “last N weeks” filter. It uses:

| Concept | What it is | Value |
|--------|------------|--------|
| **Prediction horizon** | “Predict outcome **within** X days” (forward-looking) | **60 days** default; request can send 30–365. Only affects the prompt (“predict within {time_horizon_days} days”), not which data is fetched. |
| **Data window** | How much **past** data is used | **Not expressed in weeks.** Data is capped by **record count** only (most recent first). |

**Record limits (database):**

- **DC2S KPIs:** last **50** by `measured_at` desc  
- **SaaS KPIs:** last **50**  
- **Qualitative signals:** last **30** by `signal_date` desc  
- **Account notes:** last **20** by `created_at` desc  

**Qdrant:** top **20** quantitative, top **20** qualitative, top **10** historical (by similarity + account filter); no date filter.

So the **effective** time span in weeks depends on how often data is written (e.g. weekly KPIs → up to ~50 weeks; daily signals → up to ~30 days). The prompt tells the model to weight “**last 4 weeks**” more, but that is LLM guidance only; the backend does not restrict the fetched data to those 4 weeks.

**Summary:** There is no single “analysis uses last X weeks” setting. Default behavior is “last 60 days **prediction** horizon” and “most recent 50 KPIs / 30 qualitative signals / 20 notes” (and Qdrant top_k) as the **data** scope; the calendar length of that scope varies with data density.

---

## 11. Relevant files

| Layer | File(s) |
|------|--------|
| Frontend – Signal Analyst UI | `src/components/shared/SignalAnalyst.tsx`, `src/components/SignalAnalyst.tsx` |
| Frontend – Journey | `src/components/journey-visualizer/JourneyDashboardV3.tsx` |
| Frontend – Executive dashboard | `src/components/dashboard/ExecutiveDashboard.tsx` |
| API route | `backend/agents/signal_analyst_api.py` (`analyze_account`) |
| Agent | `backend/agents/signal_analyst_agent.py` (`SignalAnalystAgent.analyze`) |
| Prompts | `backend/agents/prompts.py` (`format_*`, `get_system_prompt`, `get_analysis_prompt`) |
| Signal conversion | `backend/agents/signal_converter.py`, `backend/agents/qualitative_signal_converter.py` |
| Qdrant fetch | `backend/agents/qdrant_integration.py` |
| App registration | `backend/app_v3_minimal.py`, `backend/app.py` |
