# Quadrant Message Types: Quant vs Qual Signals

This doc analyzes the **decision matrix** (quadrant logic) that combines **quantitative** and **qualitative** signals in the Signal Analyst, and catalogs the **signal/message types** used for each.

---

## 1. Quadrant logic (decision matrix)

The system uses a **2-axis decision matrix** that produces five alignment outcomes (effectively “message types” for the combined quant+qual view):

| Axis | Dimension | Values |
|------|------------|--------|
| **Quantitative** | KPI / health trend | `IMPROVING` \| `STABLE` \| `DECLINING` \| `UNKNOWN` |
| **Qualitative** | Aggregated sentiment | `POSITIVE` \| `NEGATIVE` \| `NEUTRAL` \| `MIXED` |

**Output: alignment (quadrant message type)**

| Alignment | Meaning | Typical quant × qual |
|-----------|---------|----------------------|
| **agreement** | Both point to same issue (high-confidence churn risk) | DECLINING × NEGATIVE |
| **disagreement** | Conflicting signals (needs investigation) | DECLINING × POSITIVE, or STABLE × NEGATIVE, or IMPROVING × NEGATIVE |
| **neutral** | Stable, no strong story | STABLE × NEUTRAL/MIXED/POSITIVE, or DECLINING × NEUTRAL |
| **positive_alignment** | Both confirm positive trajectory (expansion) | IMPROVING × POSITIVE |
| **insufficient_data** | Cannot determine trend or not enough signals | UNKNOWN or no data |

So the “quadrant message types” for the **combined** view are these five alignment values. They are computed in `kpi-dashboard/backend/agents/decision_matrix.py` (LLM or rule-based).

---

## 2. Quantitative signal (message) types

These feed the **quant** axis (KPI trend / health). They are used to derive `TrendDirection` and health status.

| signal_type | Source | Role in quadrant |
|-------------|--------|-------------------|
| **account_health_score** | Health score storage / DC2S | Primary driver of trend (healthy / at-risk / critical over time). |
| **kpi_metric** | SaaS KPI, generic KPI | Health status per KPI; contributes to trend when multiple points in time. |
| **dc2s_kpi** | DC2S vertical (DC2SKPI) | Same as kpi_metric for DC2_S; `health_status`, `kpi_code`, `measured_at`. |
| **account_metadata** | Account model | Context (revenue, industry); not used for trend direction. |
| **context_graph_outcome** | Context graph (outcomes) | Revenue outcome → treated as quantitative. |
| **context_graph_summary** | Context graph | Revenue-at-risk summary → quantitative. |

**Trend derivation (quant):**

- `analyze_kpi_health_trend()` in `decision_matrix.py` uses:
  - `account_health_score` → `overall_health_score` and health band (e.g. ≥67 healthy, 34–66 at-risk, &lt;34 critical).
  - `health_status` on any signal (healthy / at-risk / critical).
- Sequence of health statuses over time → **IMPROVING** / **STABLE** / **DECLINING** / **UNKNOWN**.

So the **quant message types** that actually drive the quadrant are mainly **account_health_score** and **kpi_metric** / **dc2s_kpi**; the rest add context or revenue view.

---

## 3. Qualitative signal (message) types

These feed the **qual** axis (sentiment). They are aggregated into `SignalSentiment`: POSITIVE, NEGATIVE, NEUTRAL, MIXED.

| signal_type | Source | Role in quadrant |
|-------------|--------|-------------------|
| **qualitative_signal** | QualitativeSignal table | Generic qual; `sentiment` and `content` drive sentiment. |
| **account_note** | AccountNote | CSM notes; sentiment and text. |
| **email** | QualitativeSignal / ingestion | Treated as internal; sentiment. |
| **meeting** | QualitativeSignal / ingestion | Internal; sentiment. |
| **ticket** | QualitativeSignal / ingestion | Support/case; sentiment. |
| **escalation** | QualitativeSignal / ingestion | Internal; sentiment. |
| **health_check** | QualitativeSignal / ingestion | Internal; sentiment. |
| **support_ticket** | Mock / ingestion | Same role as ticket. |
| **executive_change** | QualitativeSignal (external) | External; sentiment. |
| **context_graph_decision** | Context graph | Decision node → qualitative. |
| **context_graph_stakeholder** | Context graph | Stakeholder node → qualitative. |
| **context_graph_signal** | Context graph | Signal node → qualitative. |

**Sentiment derivation (qual):**

- `analyze_signal_sentiment()` in `decision_matrix.py` uses:
  - `payload.sentiment` (normalized to positive / negative / neutral).
  - Optional keyword hints in `content` (e.g. frustrated, happy).
- Counts of positive / negative / neutral → **POSITIVE** / **NEGATIVE** / **NEUTRAL** / **MIXED**.

So the **qual message types** above all contribute to the same sentiment bucket; the only distinction in code is **internal vs external** (e.g. in `qualitative_signal_converter.py`: internal = email, meeting, ticket, escalation, health_check; external = funding_raised, executive_change, market_event, competitor_mention). External vs internal does not change the quadrant logic today; both feed the same sentiment aggregation.

---

## 4. How quant vs qual map into the quadrant (rule-based)

| Quant trend | Qual sentiment | Alignment (message type) |
|-------------|----------------|--------------------------|
| DECLINING | NEGATIVE | **agreement** (high-confidence churn risk) |
| DECLINING | POSITIVE | **disagreement** (conflicting; investigate) |
| DECLINING | MIXED | **disagreement** |
| DECLINING | NEUTRAL | **neutral** |
| IMPROVING | POSITIVE | **positive_alignment** (expansion opportunity) |
| IMPROVING | NEGATIVE | **disagreement** |
| IMPROVING | NEUTRAL/MIXED | **neutral** |
| STABLE | NEGATIVE | **disagreement** (qual as leading indicator) |
| STABLE | POSITIVE | **neutral** |
| STABLE | NEUTRAL/MIXED | **neutral** |
| UNKNOWN | any | **insufficient_data** |

So the **quadrant message types** you can surface to users are: **agreement**, **disagreement**, **neutral**, **positive_alignment**, **insufficient_data**.

---

## 5. Gaps and consistency notes

1. **Quant message types**
   - **account_metadata** and **context_graph_summary** do not carry a time series of health; they don’t directly drive trend. Trend is driven by **account_health_score** and **kpi_metric** / **dc2s_kpi**.
   - If you add new quant sources (e.g. usage events, product scores), they should expose either `health_status` or feed into a health score so `analyze_kpi_health_trend()` can use them.

2. **Qual message types**
   - All qual types are flattened to one sentiment bucket. The decision matrix does **not** weight by type (e.g. escalation vs email). For future “message types” per channel, you could:
     - Keep current single sentiment for the quadrant, and/or
     - Add a separate breakdown (e.g. “by signal_type”) for UX or reporting.

3. **Context graph**
   - Context graph nodes are correctly split: outcomes/summary → quant; decision/stakeholder/signal → qual. No change needed for quadrant logic; ensure `signal_type` and sentiment/revenue are set when building `SignalData` from context graph.

4. **External vs internal**
   - Currently used only for labeling (internal/external), not for quadrant or confidence. You could later use “external” to adjust confidence or to show a separate “external signal” message type.

---

## 6. Where it’s implemented

| Piece | Location |
|-------|----------|
| Alignment enum & quadrant logic | `kpi-dashboard/backend/agents/decision_matrix.py` |
| Quant trend from signals | `analyze_kpi_health_trend()` (same file) |
| Qual sentiment from signals | `analyze_signal_sentiment()` (same file) |
| Signal types (quant) | `signal_converter.py`, `signal_analyst_api.py` (DC2SKPI, health_trends, context graph) |
| Signal types (qual) | `qualitative_signal_converter.py`, `signal_deduplicator.py`, `signal_analyst_api.py` |
| Output to API | `SignalAnalystOutput.data_alignment` in `agents/models.py` |

---

## 7. Summary table: quadrant message types

| Quadrant (alignment) | Quant axis | Qual axis | Typical use |
|----------------------|------------|-----------|-------------|
| **agreement** | DECLINING | NEGATIVE | Churn risk (high confidence) |
| **disagreement** | DECLINING / IMPROVING / STABLE | Opposite or mixed | Investigate; lower confidence |
| **neutral** | STABLE or DECLINING + neutral qual | NEUTRAL / MIXED / POSITIVE | Monitor; no strong story |
| **positive_alignment** | IMPROVING | POSITIVE | Expansion opportunity |
| **insufficient_data** | UNKNOWN or no data | any | Need more data |

Quant **message types** = signal_type values that feed the quant axis (mainly **account_health_score**, **kpi_metric**, **dc2s_kpi**).  
Qual **message types** = signal_type values that feed the qual axis (e.g. **qualitative_signal**, **account_note**, **email**, **meeting**, **ticket**, **support_ticket**, **context_graph_***).  
The **quadrant message type** shown to the user is the **alignment** (agreement / disagreement / neutral / positive_alignment / insufficient_data).
