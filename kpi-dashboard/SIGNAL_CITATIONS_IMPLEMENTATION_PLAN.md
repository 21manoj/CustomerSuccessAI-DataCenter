# Signal Citations, KPI Analysis & Signal–KPI Correlation – Implementation Plan

## Objective

Augment the Signal Analyst report so that:

1. **Evidence section** explicitly cites **which signals were analyzed** (qualitative and quantitative) **and which KPIs** were used, with traceable references.
2. **Signal attributes** such as **sender/role** (account champion, CIO, CEO, executive) are available and surfaced so high-impact signals (e.g. “important email from account champion/CIO/CEO”) can be called out in the report.
3. **KPI analysis** is explicit: which KPIs drove the health score, their values vs ranges/trends, and how they contribute to at-risk vs healthy.
4. **Signal–KPI correlation** at the LLM level: the model must use **both** the KPI channel and the signal channel to **correlate** and explain **why** the customer is at-risk (or healthy). Scenarios to address:
   - **KPI looks good, signals say otherwise** (e.g. usage KPIs in range, but CIO/CEO emails or support escalations indicate dissatisfaction → at-risk due to experience/relationship, not usage).
   - **Signals look good, KPIs say otherwise** (e.g. positive engagement but usage/health KPIs declining → at-risk despite relationship).
   - **Both align** (KPIs and signals both negative or both positive → clear at-risk or healthy story).
   - **Combinations** (some KPIs good / some bad; some signals positive / some negative) → explain the combined reason for the prediction.

This document is **analysis and plan only**; no code changes are made here.

---

## 1. Current State Summary

| Layer | What exists today | Gap |
|-------|-------------------|-----|
| **Data model** | `QualitativeSignal`: `stakeholder_level`, `stakeholder_title`; `SignalData.payload` carries these from DB/converter. | No explicit “sender_role” enum (Champion/CIO/CEO); role is free text in `stakeholder_level` / `stakeholder_title`. No “importance” or “executive” flag on signals. |
| **KPI / quantitative** | Health score passed as single number; quantitative_signals are KPI-derived metrics (pillar, metric_type, value, trend) formatted in prompt. | No explicit “KPI picture” (which KPIs, values vs healthy range, trend). No requirement to **correlate** KPI channel with signal channel or explain agree/disagree. |
| **Converter** | `qualitative_signal_converter.py` puts `stakeholder_level`, `stakeholder_title` into payload. | All good for passing through. |
| **Prompt formatting** | `format_qualitative_signals()` uses: `signal_type`, `signal_source`, `sentiment`, `severity`, `text`. `format_quantitative_signals()` uses pillar, metric_type, value, trend. | **Does not include** stakeholder_level/title or stable refs for qualitative; no stable refs for quantitative; no instruction to compare KPI vs signal channel. |
| **Output model** | `RiskDriver` / `GrowthDriver` have `supporting_signals: List[str]`. `data_alignment` exists but optional. | Prompt does not require citing [Kn]/[Qn]; no required “KPI vs signals” correlation narrative; agreement/disagreement between channels not explicit. |
| **Report body** | Reasoning and insights are high-level. | No “Signals analyzed” section; no “KPI vs signal channel” explanation; no explicit reasoning for *why* at-risk when KPI and signals diverge. |

So: **signals and KPIs are both fed** to the LLM, but (1) neither channel is cited with stable refs, (2) stakeholder/role is not surfaced, and (3) **the model is not required to correlate the two channels** or explain why the account is at-risk when “KPI may look good but signals tell otherwise” (or the reverse, or combinations).

---

## 2. Implementation Plan

### 2.0 KPI analysis and signal–KPI correlation (LLM-level)

The report must use **both** the **KPI channel** (quantitative metrics that feed health score and trends) and the **signal channel** (qualitative signals: emails, meetings, escalations, executive/champion feedback) at the LLM level to:

1. **Cite KPIs:** Say which KPIs ([K1]–[Kn]) drove the health score and at-risk assessment (values, ranges, trends), not only “health 66”.
2. **Cite signals:** Say which qualitative signals ([Q1]–[Qn]) were analyzed and, when relevant, sender role (champion, CIO, CEO).
3. **Correlate the two channels:** Compare KPI picture vs signal picture and state whether they **agree**, **disagree**, or are **mixed**.
4. **Explain why at-risk (or healthy):** Give a **combined reason** that uses both channels. Examples:
   - **KPI may look good, but signals say otherwise** → “KPIs [K1],[K2] in range; signals [Q1],[Q2] (including CIO email [Q2]) indicate dissatisfaction → at-risk due to **experience/relationship**, not usage.”
   - **Signals may look good, but KPIs say otherwise** → “Engagement [Q1] positive; KPIs [K1],[K2] declining → at-risk despite relationship; focus on **usage/adoption**.”
   - **Both align** → “KPIs [K1]–[K3] and signals [Q1],[Q2] both negative → clear at-risk.”
   - **Combinations** → “Some KPIs good ([K1],[K2]), others bad ([K3]); signals mixed ([Q1] negative, [Q2] neutral) → at-risk primarily because of [K3] and [Q1].”

Implementation: feed both channels with **stable refs** ([Kn], [Qn]), then require in the **prompt** a dedicated reasoning subsection (e.g. **## KPI vs Signal Channel**) and optional structured output (`kpi_signal_correlation`) so the report explicitly correlates and explains the combined “why.”

---

### Phase 1: Expose signal identity and stakeholder attributes to the LLM

**1.1 Enrich prompt context for qualitative signals**

- **Where:** `kpi-dashboard/backend/agents/prompts.py` → `format_qualitative_signals()`.
- **Change:** For each qualitative signal, include in the formatted line:
  - A **stable reference** (e.g. `[Q1]`, `[Q2]` or `signal_id` if short) so the LLM can cite “Signal [Q2]” or “qualitative signal 2”.
  - **Stakeholder attributes:** `stakeholder_level`, `stakeholder_title` (e.g. “Executive”, “CTO”, “Champion”).
- **Example format:**  
  `Signal [Q1] [email] 💬 (negative/high) From: Jane Smith, CTO — "Integration broken for 2 weeks..."`  
  so the model sees both **who** (title/level) and **what** (content).
- **Payload:** Converter already provides `stakeholder_level`, `stakeholder_title` in payload; ensure `format_qualitative_signals` reads `payload.get('stakeholder_level')`, `payload.get('stakeholder_title')` and uses a consistent label (e.g. “Champion”, “CIO”, “CEO”) when applicable.

**1.2 Optional: Normalize “sender role” for high-impact signals**

- **Where:** Either in `qualitative_signal_converter.py` or in a small helper used by `format_qualitative_signals`.
- **Idea:** Map `stakeholder_level` / `stakeholder_title` to a small set of **sender_role** values: e.g. `champion`, `cio`, `ceo`, `executive`, `other`. Use case-insensitive keyword matching (e.g. “CTO”, “VP Engineering” → optional tagging). This is **optional** for v1; even without it, showing raw `stakeholder_title` + `stakeholder_level` in the prompt improves citations.
- **Schema:** If you add a derived field, add it to the payload only (no DB migration). Example: `payload['sender_role'] = 'executive'` when title contains “CEO” or “CIO” or “CTO”.

**1.3 Quantitative signals / KPI – cite which metrics**

- **Where:** `format_quantitative_signals()` in `prompts.py`.
- **Change:**
  - Give each quantitative line a **stable reference** (e.g. `[K1]`, `[K2]`) so the LLM can cite “[K1]” and “[K3]” in reasoning.
  - Where available, include **value vs healthy range or trend** (e.g. “GPU utilization 72% (healthy 60–90%), trend ↑ 5%”) so the report can say “KPI [K1] is in range but …” or “[K2] is below target”.
- **KPI analysis in report:** Prompt must require the LLM to summarize **which KPIs** contributed to the health score and at-risk assessment (citing [K1]–[Kn]), not only “overall health 66”. Example: “Health is pulled down by [K2] (server uptime 99.2%, target >99.9%) and [K4] (support ticket backlog ↑ 40%); [K1] and [K3] remain in range.”

**Deliverable:** LLM receives, for each quantitative signal/KPI, a clear [Kn] ref and (where possible) value/range/trend, so it can cite KPIs explicitly and explain how they contribute to at-risk vs healthy.

---

### Phase 2: Require the LLM to cite signals and KPIs in the report

**2.1 Prompt instructions (citations)**

- **Where:** `prompts.py` → `get_analysis_prompt()` (ANALYSIS REQUIREMENTS and CRITICAL RULES).
- **Add:**
  - “In **reasoning** and **key_insights**, cite specific **KPI/metric references** ([K1]–[Kn]) and **qualitative signal references** ([Q1]–[Qn]). For qualitative signals, when the sender is an account champion, CIO, CEO, or other executive, mention that (e.g. ‘Email from CIO [Q3] indicates…’).”
  - “Summarize **which KPIs** drove the health score and at-risk assessment: cite [K1]–[Kn] with their contribution (in range, below target, declining, etc.), not only the overall health number.”
  - “In **risk_drivers** and **growth_drivers**, **supporting_signals** must reference the exact references used (e.g. [Q1], [Q4], [K2]), not generic descriptions.”
- **Optional:** Add a short “Signals analyzed” summary requirement: “Include a bullet list of the signals and KPIs that most influenced the prediction (with their references and, for qualitative, sender role when relevant).”

**2.2 Signal–KPI correlation at LLM level (mandatory)**

- **Where:** `prompts.py` → `get_analysis_prompt()` (CRITICAL RULES and, if needed, a dedicated “Correlation” subsection in the reasoning template).
- **Requirement:** The LLM must use **both** the KPI channel and the signal channel to **correlate** and explain **why** the customer is at-risk (or healthy). Add explicit instructions and a required reasoning subsection:

  - **“KPI vs signal channel”:** “In your **reasoning**, include a subsection (e.g. ## KPI vs Signal Channel or ## Why This Account Is At-Risk) that states:
    - Whether **KPIs and qualitative signals agree**, **disagree**, or are **mixed**.
    - The **combined reason** for your prediction. Examples:
      - **KPI good, signals bad:** ‘KPIs [K1],[K2] are in healthy range, but qualitative signals [Q1],[Q2] (including email from CIO [Q2]) indicate dissatisfaction and escalation risk → at-risk due to **experience/relationship**, not usage.’
      - **Signals good, KPI bad:** ‘Engagement signals [Q1] are positive, but usage KPIs [K1],[K2] are declining → at-risk despite **relationship**; address **adoption/usage**.’
      - **Both align:** ‘KPIs [K1]–[K3] show decline and support escalations [Q1],[Q2] confirm frustration → **clear at-risk**; both channels agree.’
      - **Mixed:** ‘Some KPIs ([K1],[K2]) in range, others ([K3]) below target; signals [Q1] negative, [Q2] neutral → at-risk primarily because of [K3] and [Q1].’”
  - “Do not give only a single-channel story: always relate **KPI picture** ([K1]–[Kn]) to **signal picture** ([Q1]–[Qn]) and state the combined reason for at-risk or healthy.”

- **Output model (optional):** Add an optional field to `SignalAnalystOutput`, e.g. `kpi_signal_correlation: Optional[Dict]` with keys like `agreement` (“agree” | “disagree” | “mixed”), `kpi_summary` (one line citing [Kn]), `signal_summary` (one line citing [Qn]), `combined_reason` (one line). Populated by the LLM in JSON so the frontend can show “KPI vs signals: disagree – at-risk due to experience, not usage” without parsing markdown. For v1, enforcing the **reasoning** subsection may be enough without this structured field.

**2.3 Output model (optional extensions)**

- **Where:** `agents/models.py`.
- **Optional:** 
  - `signals_cited: List[Dict]` with `reference`, `type` (quantitative/qualitative), `sender_role` (if qualitative), `summary_one_line` — for UI “Signals analyzed” table.
  - `kpi_signal_correlation: Optional[Dict]` as in 2.2 — for UI “KPI vs signals” badge or one-liner.

**Deliverable:** Report reasoning explicitly compares KPI channel and signal channel, states agree/disagree/mixed, and gives a combined “why at-risk” (or why healthy) using both [Kn] and [Qn]. Citations [Q1]/[Kn] appear in reasoning, key_insights, and supporting_signals.

---

### Phase 3: Optional “importance” / executive flag (data model)

**3.1 If you want “important email from champion/CIO/CEO” as a first-class concept**

- **Option A – No schema change:** Use only existing `stakeholder_level` and `stakeholder_title`. In the prompt, instruct the LLM: “When a qualitative signal is from an executive (CEO, CIO, CTO, VP) or an account champion, treat it as high influence and mention the sender role in your reasoning.”
- **Option B – Add column to `qualitative_signals`:** e.g. `sender_role` (enum or string: `champion`, `cio`, `ceo`, `executive`, `other`) and/or `is_high_importance` (boolean). Populated at ingest (CSV column or rule from title/level). Then include in converter and in `format_qualitative_signals`, and in the prompt: “Signals marked as from Champion/CIO/CEO or is_high_importance should be cited with their sender role.”

**Recommendation:** Start with **Option A** (prompt + existing stakeholder fields). Add Option B only if product requires filterable “executive signals” or reporting on “champion/CIO/CEO signals” in the UI.

**Deliverable:** Either prompt-only handling of “executive/champion” signals, or schema + ingest + prompt for explicit sender_role/importance.

---

### Phase 4: Frontend – show “Signals analyzed”, “KPI vs signals”, and stakeholder context

**4.1 Report UI**

- **Where:** Component that renders Signal Analyst output (e.g. `SignalAnalyst.tsx` or Journey dashboard report block).
- **Change:**
  - **“Signals analyzed”** section: e.g. “Qualitative: 12 (3 from executives/champions). Quantitative/KPIs: 8 metrics.” If the API returns `signals_cited`, render a small table: reference, type (KPI vs qualitative), sender role (if any), one-line summary.
  - **“KPI vs signal channel”** (correlation): If the API returns `kpi_signal_correlation`, show a one-liner or badge: e.g. “KPI and signals: **disagree** – at-risk due to experience/relationship, not usage.” Otherwise, the reasoning subsection “## KPI vs Signal Channel” will already be in the markdown; optionally highlight that subsection in the UI.
  - In the reasoning/insights block, ensure **references [Q1], [K2]** are visible; optional: tooltip that maps [Q1] → “Email from CTO, 2025-01-15” and [K1] → “GPU utilization, 72%”.

**4.2 API response**

- **Where:** `signal_analyst_api.py` (and any DTO).
- **Change:** If you add `signals_cited` or `kpi_signal_correlation`, include them in the JSON so the frontend can show “Signals analyzed”, “Key signals by role”, and “KPI vs signals” without parsing markdown.

**Deliverable:** User sees which KPIs and signals were analyzed, whether they agree or disagree, the combined reason for at-risk/healthy, and can connect “[Q3]” / “[K2]” in the narrative to the evidence.

---

## 3. Implementation Order (summary)

| Step | Task | Owner / Notes |
|------|------|----------------|
| 1 | Enrich `format_qualitative_signals` with signal ref + stakeholder_level/title | Backend |
| 2 | Add stable refs + value/range/trend to `format_quantitative_signals` ([K1], [K2]) | Backend |
| 3 | Update prompt: require **KPI citation** ([K1]–[Kn]) and which KPIs drove health/at-risk | Backend |
| 4 | Update prompt: require **signal–KPI correlation** (agree/disagree/mixed + combined reason) | Backend |
| 5 | Update prompt: require citation by ref + sender role for executive/champion in reasoning/supporting_signals | Backend |
| 6 | (Optional) Add `kpi_signal_correlation` and/or `signals_cited` to output model | Backend |
| 7 | (Optional) Normalize sender_role in payload (champion/cio/ceo/executive) | Backend |
| 8 | Frontend: “Signals analyzed” + “KPI vs signals” (correlation) section | Frontend |
| 9 | (Optional) DB column sender_role / is_high_importance + ingest | Backend + migrations |

---

## 4. Risks and Mitigations

### 4.1 Data quality & availability

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Missing stakeholder fields** | Many rows may have null `stakeholder_level` / `stakeholder_title`. | In formatter, show “From: —” or “Sender: unknown” when null; prompt says “when sender role is known, cite it.” Do not require role for every signal. |
| **Inconsistent role labels** | Titles vary (“CTO”, “VP Eng”, “Chief Technology Officer”). | Prefer displaying raw title in prompt; optional normalization (Phase 1.2) with keyword rules; accept “executive” as a bucket. |
| **CSV doesn’t have stakeholder columns** | Older or minimal CSVs might not have these columns. | Onboarding/loader already maps CSV columns to table; ensure optional columns don’t break load. Default nulls. |

### 4.2 LLM behavior

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Hallucinated citations** | Model invents [Q99] or cites signals not in the context. | Strict instruction: “Only cite references from the list above ([Q1]–[Qn], [K1]–[Kn]).” Optional: post-parse validation that every cited ref exists in the input set. |
| **Over-weighting executive signals** | Treating every “CEO” email as critical. | Prompt: “Weigh executive/champion signals by content and recency, not by title alone.” |
| **Under-citing** | Model still gives generic “signals suggest” without refs. | Make citation a hard requirement in the prompt and in CRITICAL RULES; few-shot example in prompt showing “[Q2] and [K1] drive…” |
| **Ignoring one channel** | LLM explains at-risk using only KPIs or only signals, not both. | Require a dedicated “KPI vs signal channel” subsection in reasoning; require “agree / disagree / mixed” and “combined reason” in plain language. |
| **No “why” when channels disagree** | Report says “at-risk” but doesn’t explain that KPI good + signals bad → at-risk due to experience. | Prompt examples: “KPI good, signals bad → at-risk due to experience/relationship”; “Signals good, KPI bad → at-risk due to usage/adoption.” Require the model to state which channel dominates and why. |
| **Over-weighting one channel** | Always favoring KPIs or always favoring signals when they conflict. | Prompt: “When KPI and signal channels disagree, state both and explain which you weight more and why (e.g. recency, severity, executive source).” |

### 4.3 Privacy & compliance

| Risk | Description | Mitigation |
|------|-------------|------------|
| **PII in report** | stakeholder_title might be “Jane Smith” (name). | Prefer “CTO”, “Champion” in report text; if title is a name, prompt: “In the report, refer to role (e.g. ‘CTO’) rather than personal names unless necessary.” Option: strip or hash names at display time. |
| **Sensitive content in “signals cited”** | One-line summary could repeat sensitive content. | Instruct LLM to keep summaries generic (“Escalation about integration”) and not quote full content. |

### 4.4 Performance & scope

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Longer prompts** | Adding refs and stakeholder text increases token count. | Keep refs short ([Q1]); truncate content (already 200 chars); cap number of qualitative signals (e.g. top 15 by recency/importance). |
| **More tokens in output** | reasoning and supporting_signals get longer. | Accept slightly longer output; set max_tokens if needed; optional “signals_cited” as structured list instead of long prose. |

### 4.5 Backward compatibility

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Existing clients expect old output shape** | Adding optional fields is fine; changing structure of supporting_signals might break. | Keep supporting_signals as List[str]; allow new format “[Q2] Email from CIO: …” as string content; or add new optional field signals_cited and leave supporting_signals as-is. |
| **Qdrant payloads** | If qualitative signals come from Qdrant, payload must include stakeholder_level/title there too. | Ensure Qdrant ingestion (or DB→Qdrant sync) stores these fields in payload; converter from Qdrant to SignalData already uses payload. |

### 4.6 Product / UX

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Confusion if refs don’t match UI** | User sees [Q3] in report but UI doesn’t list “Q3”. | Either show a small “Signal reference” legend (Q1–Qn = qualitative, K1–Kn = quantitative) or render the same refs in a “Signals analyzed” panel so [Q3] is findable. |
| **Over-emphasis on “executive”** | Sales may over-prioritize “CEO said” over stronger usage signals. | Training and prompt: “Executive/champion signals are one input; combine with quantitative and other qualitative signals.” |

---

## 5. Success Criteria

- **KPI analysis:** Report states **which KPIs** ([K1]–[Kn]) contributed to the health score and at-risk assessment, with values/trends where relevant (e.g. “[K2] below target”, “[K1] in range”).
- **Signal–KPI correlation:** Report includes a **KPI vs signal channel** comparison: agree / disagree / mixed, and a **combined reason** for why the account is at-risk (or healthy). When “KPI looks good but signals say otherwise” (or the reverse), the report explicitly explains the reason (e.g. “at-risk due to experience/relationship, not usage”).
- **Evidence:** Report reasoning and key_insights explicitly reference both **KPI refs** ([K1]–[Kn]) and **qualitative signal refs** ([Q1]–[Qn]).
- **Stakeholder:** When a qualitative signal is from an account champion, CIO, CEO, or other executive, that is mentioned in the report (e.g. “Email from CIO [Q3] indicates…”).
- **Traceability:** supporting_signals in risk_drivers/growth_drivers use the same refs ([Qn], [Kn]) so a reader can map each driver back to the evidence.
- **No regression:** Existing health score, churn/expansion probability, and actions still behave as today; only evidence, KPI analysis, and correlation narrative are augmented.

---

## 6. References (code locations)

- **Prompt formatting:** `kpi-dashboard/backend/agents/prompts.py` (`format_qualitative_signals`, `format_quantitative_signals`, `get_analysis_prompt`).
- **Converter:** `kpi-dashboard/backend/agents/qualitative_signal_converter.py` (payload already has stakeholder_level, stakeholder_title).
- **Models:** `kpi-dashboard/backend/models.py` (`QualitativeSignal`), `kpi-dashboard/backend/agents/models.py` (`SignalData`, `SignalAnalystOutput`, `RiskDriver`, `GrowthDriver`).
- **API:** `kpi-dashboard/backend/agents/signal_analyst_api.py`.
- **Journey API (signal shape):** `journey_api_dynamic.py` uses `from_contact` (= stakeholder_title), and could expose “from_role” from stakeholder_level for UI consistency.

---

*Document: Signal Citations & Stakeholder Attributes – Implementation Plan. Analysis and plan only; implementation to be done in follow-up work.*
