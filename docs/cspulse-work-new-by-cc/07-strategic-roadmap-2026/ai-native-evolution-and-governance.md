# CS Pulse — AI-Native Evolution & Governance Roadmap

**Owner-directed strategic update, 2026-08-28.** Five themes the owner raised as missing from the working documentation: (1) incorporating AI tooling that didn't exist when this project started ~10 months ago, (2) mapping vertical differentiation onto Jensen Huang's AI-stack layer framing, (3) the missing signal engine and signal-analyst "decision machine," (4) a critique of Wizard C's place in the A→B→C→D sequence, (5) DBS Bank's SGD 24M security/auditability/data-lineage program as inspiration for CS Pulse's own governance layer.

This is a **direction-setting document, not a status ledger** — `state-of-play.md` remains the operational source of truth for what's shipped/broken/verified. Where a claim below touches existing code, it's been checked against the current repo, not asserted from memory; where it's forward-looking, it's marked as such.

---

## 1. Ten months of AI-tooling evolution — what to actually adopt

The honest framing: CS Pulse's founding bet on **MCP as the product's core interface** (not a bolt-on chatbot, the actual system boundary — `cs_pulse_mcp_server.py` delegating to modular tool files) was ahead of the curve and doesn't need revisiting. What's changed since is mostly *execution* tooling, not architecture tooling. Four adoptions worth making, each tied to a real subsystem already in this codebase rather than speculative:

- **Multi-agent orchestration for calibration validation.** Wizard C's weight recalibration currently has no adversarial check — it computes new weights and (in direct-apply mode, the only mode ever actually enabled in production) writes them straight to `CustomerConfig`. A cheap, high-value addition: before applying, fan out 2-3 independent "does this weight shift make business sense" critiques (the same adversarial-verification pattern this session used repeatedly for code review) against the `significant_changes` list, and route anything a majority flags as implausible into the (already-built, currently-unused) approval queue instead of direct-apply. This uses infrastructure that already exists (`approval_queue.py`) plus a pattern that's now cheap to run (parallel agent fan-out), not a new subsystem.
- **Structured output reliability for `signal_analyst`'s decision matrix.** The reasoning brain that computes quant-vs-qual alignment → urgency (see §3) predates reliable forced-schema tool calling. Re-platforming its urgency/confidence output onto strict structured output would remove a class of silent parsing failures without touching the reasoning logic itself.
- **Cheaper-model routing for signal enrichment.** `signal_engine/worker.py`'s `SignalEnrichmentWorker` (real code, currently gated behind `FEATURE_SIGNAL_ENGINE=false` — see §3) is exactly the kind of high-volume, low-complexity classification task (sentiment, urgency triage on inbound email/Slack) that belongs on a small, fast model rather than the same tier used for Ask AI's reasoning. Worth deciding this *before* the flag flips on, not after.
- **Eval/red-team harnesses for agent reliability**, directly reusable for the governance work in §5 — this is the one adoption that isn't optional if the DBS-inspired direction is taken seriously; see the SGD 5.0M red-teaming line item DBS itself funds separately from the engineering build.

What I'd explicitly *not* chase: computer-use/browser agents (no CS Pulse workflow needs a human-interface-shaped agent today) and swapping the foundation model — Claude's role in this stack (Tier-1 KPI inference, signal_analyst, Ask AI) is working technology, not a bottleneck.

---

## 2. Jensen's 5-layer AI stack applied to CS Pulse's multi-vertical reality

Layers: **Infrastructure → Foundation Model → Data/RAG → Agent/Orchestration → Application.**

The useful question isn't "does CS Pulse have all five layers" (it does) — it's **which layer should carry vertical differentiation**, because that's the architectural decision that determines whether adding a 6th vertical costs a day or a quarter. Mapped against what this session verified is actually true today:

| Layer | Vertical-specific today? | Assessment |
|---|---|---|
| Infrastructure (EC2/Docker/Postgres) | No | Correct — no reason this should ever differ by vertical. |
| Foundation Model (Claude, via Tier-1 inference / signal_analyst / Ask AI) | No | Correct — same model serves dc2_s and datacenter_v1 alike. A vertical-specific fine-tune would be a regression, not an upgrade. |
| Data/RAG (KPI catalogs, `pillar_roles` registry, taxonomy overlays, Power-of-1 metric maps) | **Yes, by design** | This is where differentiation *should* live, and — validated 2026-08-12, `ScoreCalculator` built generically from any vertical's JSON catalog, parity-tested against the old dc2_s-specific scorer — mostly does. The exception, already flagged (item 5/11 in `state-of-play.md`): Power-of-1's six metrics are still the SaaS set re-labeled for every vertical, not genuinely re-derived per vertical's own P&L levers (GPU utilization/PUE for datacenter_v1, not TTFV/NRR). That's a Data/RAG-layer gap, not an architecture problem — it's the right layer to fix it in. |
| Agent/Orchestration (Wizards A-D, `signal_analyst`, `push_intelligence_subscriber`) | **Mostly no, with named exceptions** | The wizards and reasoning logic are vertical-agnostic by construction — they operate on whatever catalog the Data/RAG layer hands them. The tracked exceptions (`DC2S_PILLAR_METRIC_MAP`, `playbook_recommendations_api._evaluate_dc2s_playbooks`) are exactly the residual dc2_s coupling already logged as backlog, not new news — but worth naming here because they're the pattern to watch for as more verticals ship: any time orchestration code branches on vertical name instead of reading from the registry, that's the layer boundary leaking. |
| Application/UI | **Currently ambiguous — the actual open question** | The owner's framing ("the UI will... be diff. across these verticals") is forward-looking, and it's the right thing to get ahead of. The backend's registry-driven discipline (a new vertical = drop a catalog JSON, `ScoreCalculator` picks it up automatically) is the standard the UI needs to match. The risk, visible in the existing `dc_*`-prefixed component family (`dc_TenantHub`, `dc_Platform`, `dc_InfrastructureHealth`), is building bespoke per-vertical component trees instead of one registry-driven UI that renders whatever pillars/KPIs/taxonomy the Data/RAG layer declares. That's not yet a confirmed problem — it needs an actual audit of whether `dc_*` components are genuinely dc2_s-hardcoded or just historically-named generic components — but it's the specific thing to check before a 6th vertical makes retrofitting expensive. |

**The design principle worth stating explicitly, because it's the actual takeaway from the layer-cake framing**: differentiation belongs in the Data/RAG layer's *content* (catalogs, taxonomy, metric definitions) and nowhere else. Every time it leaks into Infrastructure, Foundation Model, or hardcoded Application/Orchestration branches, that's N-times maintenance cost per additional vertical instead of one JSON file. This session's Track B work (fail-closed registry, no `dc2_s` fallback, catalog-shape conformance tests) already enforces this discipline at the backend boundary — extending the same discipline to the frontend is the concrete next step this framing points to.

---

## 3. The signal engine and signal-analyst "decision machine" — actual current state

This was described as missing. Checked directly against the code rather than assumed — the real picture is more specific than "missing," and the specificity matters for scoping the work correctly:

**Ingestion — partially built, not missing:**
- `signal_engine/` is a real module: `email_receiver.py`, `slack_events.py`, `enrichment.py`, `fusion.py`, `urgency.py`, `worker.py`, `ingest_api.py`. This is inbound email + Slack connector infrastructure, not a stub.
- It's gated behind `FEATURE_SIGNAL_ENGINE`, defaulting to `false` in `app_v3_minimal.py` — almost certainly never enabled on any live tenant. Built, dormant.
- **Meeting transcripts have zero implementation** — grepped for `transcript`/`zoom`/`gong`/`chorus` across the whole backend; the only hits are in a synthetic-data generator script. This piece is genuinely, not just dormantly, missing. Matches the existing backlog spec (`spec_signal_processing_pipeline.md`, P1, ~7-9 days estimated) — that estimate already accounted for this gap.
- Outbound Slack alerting (the "send an alert on Slack" half of the owner's ask) **does not exist at all** — grepped for any outbound Slack client/webhook call; zero hits. `slack_events.py` is inbound-only.

**Reasoning — the "brain" is real, its inputs are incomplete:**
- `signal_analyst`'s decision matrix genuinely computes quant-vs-qual alignment → urgency — this is not vaporware, it's a working reasoning component.
- Two of the three things it needs to make a genuinely autonomous "alert vs. playbook" call are documented gaps, not new findings: Power-of-1 revenue input into its urgency scoring (missing), ROI justification for a recommended action (missing), playbook self-trigger (partial — some but not full autonomy).

**Actuation — the layer that doesn't exist yet, already correctly identified.** The roadmap note already on file (`roadmap_agentic_action_layer.md`) names this precisely: sense (signals) → reason (signal_analyst) → **act** (Slack alert, playbook trigger) → measure is a real 4-layer loop, and the missing piece is specifically the *act* layer. The substrate for it already exists — MCP tools, the context graph, `n8n`/webhook plumbing, an `automation_level` governance concept — the work is the reasoning-to-action wiring, not new infrastructure.

**Net assessment**: this isn't "build the signal engine" — ingestion (2 of 3 channels) and reasoning (1 of 1 core component, missing 2 of 3 inputs) already exist in code. The real, correctly-scoped work is: (a) meeting-transcript ingestion (genuinely new), (b) feed Power-of-1/ROI into `signal_analyst`'s existing decision matrix (wiring, not new logic), (c) build the actuation layer (Slack outbound + playbook self-trigger) that nothing in the codebase does today. Framing it as "the signal engine is missing" would risk re-building the 60% that's already there.

---

## 4. Wizard sequencing — A, B, C, D reconsidered

The premise as stated — "Wizard C, a calibration agent, is embedded between classification, measurement, and prediction agents" — doesn't match the runtime architecture, and the mismatch is worth naming because it's evidence *for* the underlying critique, not against it.

**What's actually true, checked against `trigger_wizard`'s dispatcher (`mcp_server/cs_pulse_onboarding.py`) and the automatic pipeline (`process_data_pipeline.py`):**
- Wizard A (arc classification) and Wizard B (pattern analysis) run **automatically** as part of every `process_data` pipeline execution.
- Wizard D (predictor calibration) is **not** automatic either — it requires an explicit call (the load-driver has to call `/api/admin/wizard-d/recalibrate` after every registration, which this session did by hand for every test tenant all day).
- Wizard C (weight calibration) is **not** in the automatic pipeline at all. It only fires via an explicit `trigger_wizard(wizard='c')` call — and there's an existing, deliberate policy note on file (`policy_wizard_c_decoupled_from_process_data.md`) recording exactly this as an intentional decision: *"only fires on explicit trigger, not every CSV refresh — reject future 'auto-run all wizards' cleanups."*

So Wizard C is already decoupled from the per-customer pipeline, correctly, for the reason the owner's instinct points at: **weight calibration is a model-tuning operation across accumulated outcomes, not a per-customer data-processing step** — it doesn't belong in the same execution shape as "classify this account's arc" or "predict this account's NRR." That decoupling already happened at the *trigger* level.

**Where the critique still lands, and it's a real gap**: the decoupling is functional but not conceptual. Wizard C is still named and numbered as if it's the third step in an A→B→C→D sequence (`WizardRun.config={'wizard': 'c', ...}`, the same `trigger_wizard` dispatcher, the same mental model as A/B/D), even though it operates on a completely different cadence (periodic, cross-account, outcome-driven) and a completely different kind of input (aggregate calibration statistics, not a single account's KPIs). That naming invites exactly the confusion in the owner's framing — a fair critique of the *presentation* of the architecture even where the *execution* already got it right.

**Concrete recommendation**: stop presenting Wizard C as a step in the A-B-C-D sequence. It's structurally closer to a periodic model-retraining job than to a per-account wizard — worth a name and a trigger surface that reflect that (e.g., "weight recalibration," triggered from a scheduled/threshold-based job or an explicit admin action, not from the same `trigger_wizard('a'|'b'|'c'|'d')` menu that implies a fixed order). This is a renaming/re-presentation exercise, not a re-architecture — the actual execution decoupling this session confirmed is already correct.

---

## 5. Governance, auditability, and data lineage — DBS Bank as the reference model

DBS's SGD 24.0M framework breaks into three pillars: **metadata tagging, immutable trace logging, compliance reporting.** Mapped against what CS Pulse already has (checked against real code, not aspirational) versus what's genuinely absent — the gap is narrower than "build this from zero," but the absent pieces are exactly the ones that matter for regulator-facing credibility:

**1. Metadata tagging — CS Pulse has a real analog, at a different granularity.**
The WS-2 evidence-provenance system (`observed` / `asserted` / `inferred` / `unknown` tiers, stamped on every `ContextNode`/`ContextEdge`, with a signed adjudication matrix governing which writer gets which tier) is structurally the same idea as DBS's sensitivity stamping — a machine-readable trust/classification tag attached to every data asset before it reaches an LLM's context window. What's missing relative to DBS's framing: this tags **evidentiary confidence**, not **data sensitivity/PII classification**. There's no equivalent of "this field is Restricted/PII, mask it before it reaches the LLM" — the already-documented SOC2 gap (`gap_soc2_code_verified.md`: no MFA/SSO, tenant isolation is per-query not centralized, `SESSION_COOKIE_SECURE=false` on the live box) confirms this isn't just a missing feature, it's a live exposure. A "Zero-Trust Data Broker" checking a user's clearance against a document's tag, the way DBS describes for a teller querying a high-net-worth client's profile, doesn't exist here in any form.

**2. Trace logging — a genuine partial match, and the closest of the three to "already built."**
The context graph's Signal→Decision→Outcome chains, with `model_id`/`prompt_version` (content-hashed, so it can't silently drift) and `inferred_at` stamped on every LLM-written node (WS-1, item 1.5) is a real, working analog to DBS's "log the exact model version, temperature, and prompt utilized" requirement — for *business* decisions. What's missing is the *agent reasoning* layer DBS is actually describing: there's no equivalent of an "Agent Execution Graph" capturing an LLM's own step-by-step tool calls and intermediate outputs (as opposed to the business artifact those calls produced), no WORM/tamper-proof storage for any of it, and no deterministic-replay capability. The `opportunity_grc_ai_agents_reuse.md` finding from earlier work is directly relevant here: `context_graph.py`, `llm_budget_controller.py`, and `approval_queue.py` are already decoupled enough from CS-Pulse-specific logic to be the actual substrate for this — the gap is a genuine agent-execution-trace layer sitting on top of them, not a rebuild.

**3. Compliance reporting — genuinely absent, and the most valuable of the three to build.**
No "Explain Dashboard," no automated drift/bias monitoring on agent outputs, no regulatory export format. This is the pillar with the least existing substrate and the most direct product value — CS Pulse already tracks the data needed for a primitive version of this (Wizard C's `WeightCalibrationHistory`, now surfaced as a notification per this session's item-38-adjacent work; the context graph's own evidence chains) but nothing renders it as a compliance-facing artifact. Given the platform's own positioning already includes a GRC-for-AI-Agents opportunity (`opportunity_grc_ai_agents_reuse.md`) with a near-zero-coupling reusable core, this pillar is the one where "inspired by DBS" could become a genuine product surface, not just an internal safeguard — worth treating as a roadmap item in its own right rather than pure infrastructure hardening.

**What this section is not**: a claim that CS Pulse needs a SGD 24M program. The value of the DBS framework here is structural — three pillars, each individually scoped, each with a clear "what exists / what's missing" answer above — not the specific staffing or budget numbers, which are bank-regulatory-scale and not the right comparison for this platform's current size.

---

## Cross-references

- `state-of-play.md` — operational status ledger; items 25/28-38 (this session) are the concrete engineering work this roadmap's §2 and §5 build on.
- `roadmap_agentic_action_layer.md` (memory) — the actuation-layer gap named in §3, already scoped before this document.
- `tbd_signal_analyst_reasoning_wiring.md` (memory) — the signal_analyst input gaps (Power-of-1, ROI) named in §3.
- `opportunity_grc_ai_agents_reuse.md` (memory) — the reusable governance substrate named in §5.
- `gap_soc2_code_verified.md` (memory) — the live security gaps that make §5's metadata-tagging pillar more than a nice-to-have.
- `spec_signal_processing_pipeline.md` — the existing backlog spec for meeting-transcript ingestion named in §3.
- `policy_wizard_c_decoupled_from_process_data.md` (memory) — the existing decision §4 builds on and extends.
