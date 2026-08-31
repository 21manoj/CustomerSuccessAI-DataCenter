// Build CSPulse_Technical_Deep_Dive.docx
// Tech-lead onboarding doc #3 — implementation internals.
// Audience: incoming tech lead, post User Perspective (1) + Vision/Architecture (2).

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType,
  ImageRun,
} = require('docx');

function diagram(filename, maxWidth = 580) {
  const imgPath = path.join(__dirname, 'diagrams', filename);
  if (!fs.existsSync(imgPath)) {
    return new Paragraph({ children: [new TextRun({ text: `[diagram missing: ${filename}]`, italics: true, color: "808080" })] });
  }
  const buf = fs.readFileSync(imgPath);
  const origW = buf.readUInt32BE(16);
  const origH = buf.readUInt32BE(20);
  const scale = Math.min(1, maxWidth / origW);
  const w = Math.round(origW * scale);
  const h = Math.round(origH * scale);
  return new Paragraph({
    children: [new ImageRun({ data: buf, transformation: { width: w, height: h } })],
    alignment: AlignmentType.CENTER, spacing: { before: 120, after: 180 },
  });
}
function caption(text) {
  return new Paragraph({
    children: [new TextRun({ text, italics: true, size: 18, color: "606060" })],
    alignment: AlignmentType.CENTER, spacing: { after: 240 },
  });
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "B8B8B8" };
const cellBorders = { top: border, bottom: border, left: border, right: border };
const headerShade = { fill: "1F3A5F", type: ShadingType.CLEAR, color: "auto" };
const altShade = { fill: "F2F2F2", type: ShadingType.CLEAR, color: "auto" };

const para = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, ...opts.run })],
  spacing: { after: 120, ...opts.spacing }, ...opts.para,
});
const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1, children: [new TextRun({ text })],
  spacing: { before: 360, after: 200 }, pageBreakBefore: true,
});
const h1NoBreak = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1, children: [new TextRun({ text })],
  spacing: { before: 360, after: 200 },
});
const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2, children: [new TextRun({ text })],
  spacing: { before: 240, after: 140 },
});
const h3 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3, children: [new TextRun({ text })],
  spacing: { before: 180, after: 100 },
});
const bullet = (text, level = 0) => new Paragraph({ text, bullet: { level }, spacing: { after: 60 } });
const numbered = (text) => new Paragraph({ text, numbering: { reference: "default-numbering", level: 0 }, spacing: { after: 60 } });
const code = (text) => new Paragraph({
  children: [new TextRun({ text, font: "Courier New", size: 18 })],
  shading: { fill: "F2F2F2", type: ShadingType.CLEAR }, spacing: { before: 80, after: 80 },
});
function table(colWidths, rows, opts = {}) {
  const zebra = opts.zebra !== false;
  const tableRows = rows.map((row, i) => new TableRow({
    children: row.map((cell, j) => new TableCell({
      children: typeof cell === 'string' ? [para(cell, { run: { size: 18 } })] : cell,
      borders: cellBorders,
      shading: i === 0 ? headerShade : (zebra && i % 2 === 0 ? altShade : undefined),
      width: { size: colWidths[j], type: WidthType.DXA },
      margins: { top: 80, bottom: 80, left: 100, right: 100 },
    })),
    tableHeader: i === 0,
  }));
  return new Table({ rows: tableRows, width: { size: colWidths.reduce((a, b) => a + b, 0), type: WidthType.DXA } });
}

const children = [];

// ============================================================
// FRONT MATTER
// ============================================================

children.push(new Paragraph({
  children: [new TextRun({ text: "CS Pulse — Technical Deep Dive", bold: true, size: 36 })],
  alignment: AlignmentType.CENTER, spacing: { after: 200 },
}));
children.push(new Paragraph({
  children: [new TextRun({ text: "Tech-lead onboarding · implementation internals", italics: true, size: 22, color: "606060" })],
  alignment: AlignmentType.CENTER, spacing: { after: 360 },
}));
children.push(para(
  "Doc #3 of three. Where User Perspective (#1) shows what customers see and Vision/Architecture (#2) shows what the system promises, THIS doc shows how the code actually delivers it. File paths + line numbers throughout — open the editor alongside this doc and trace as you read."
));
children.push(para(
  "Audience: tech lead who has read docs #1 and #2 and now wants to ramp on the codebase. By the end you should be able to (a) trace a Wizard D calibration end-to-end, (b) explain the GLMM math to an AI-DD reviewer, (c) modify a context-graph invariant without breaking the audit, (d) add a new MCP tool with proper auth + cost tracking, and (e) write a verify_*.py script for a new persona-facing surface."
));
children.push(para("All references match the deployed image as of late May 2026 (main HEAD eaec74db8)."));

// ============================================================
// SECTION 1 — Stack overview
// ============================================================

children.push(h1NoBreak("1. The Stack — One-Page Map"));

children.push(table([2400, 7200], [
  ["Component", "Implementation"],
  ["Backend HTTP API", "Flask (Python 3.11), entry point app_v3_minimal.py. ~9 blueprints registered: executive_dashboard_api, outcome_roi_api, ask_ai_endpoint, predictor_api, customer_playbook_api, signal_engine ingest_api, admin_api, integration_api, action_interface_api, plus RAG variants."],
  ["Database", "PostgreSQL (cs_pulse). All ORM models in kpi-dashboard/backend/models.py. Migrations via Alembic; auto-run at container bootstrap."],
  ["Frontend", "React 18 + TypeScript + Tailwind. Entry point src/App.tsx → CSPlatform.tsx mounts persona dashboards by route."],
  ["Vector store", "Qdrant (signal semantic search). Optional — falls back to keyword matching if QDRANT_URL not set."],
  ["MCP server", "FastMCP-style decorators (@mcp.tool) across kpi-dashboard/backend/mcp_server/cs_pulse_*.py. ~52 tools. JSON-RPC streamable-HTTP over /mcp endpoint."],
  ["LLM provider", "Anthropic Claude (primary). OpenAI selectable per tenant via llm_provider config. Cost tracked in LLMUsageLog table via record_usage() — every call site must invoke."],
  ["Container", "Docker. Image cspulse-platform built on amd64. docker-compose.cspulse.yml for local stack. Hot-reload on React only; Flask requires restart."],
  ["Deploy", "EC2 single-instance today. Two deploy scripts: deploy-ec2-git-pull.sh (primary, ~5–10 min, always matches main HEAD) and rehydrate-ec2-ecr.sh (~1–2 min, ECR tag based, honors PLATFORM_TAG)."],
], { zebra: true }));

children.push(h2("1.1 Request lifecycle (one API call end-to-end)"));
children.push(diagram("d5_request_lifecycle.png"));
children.push(caption("Figure 1 — End-to-end request lifecycle. Top: customer upload of 4 CSVs → process_data → Wizard A/B fire automatically. Middle: admin runs trigger_wizard('d') to fit the per-tenant GLMM. Bottom: end user hits the CFO dashboard, handler ARR-weights per-account predictor v3 forecasts into the FORECAST NRR tile."));
children.push(para("Walking the lifecycle in detail. For an Ask AI call from Claude.ai resolving to get_account_nrr_forecast:"));
children.push(numbered("Claude.ai sends JSON-RPC POST to https://d2oqfugrb2ltg9.cloudfront.net/mcp?api_key=csp_server_... (Bearer header also works)."));
children.push(numbered("CloudFront → EC2 origin (3.94.106.197) → cspulse-platform Docker container :80."));
children.push(numbered("Nginx (in-container) routes /mcp → Flask /mcp endpoint."));
children.push(numbered("MCP server validates the Bearer token via validate_server_key() against MCP_SERVER_API_KEY env var. EMPTY env = 'Invalid or revoked API key' regardless of token (§3.10 footgun)."));
children.push(numbered("Tool resolver in mcp_server/cs_pulse_predictor.py routes the call to get_account_nrr_forecast(customer_id, account_id, horizon)."));
children.push(numbered("Tool body calls predictor.inference.predict_for_account_id() which loads the active PredictorCalibration rows (4 sub-models per customer × vertical × profile) and runs inference."));
children.push(numbered("LLMUsageLog row written via record_usage() if any LLM call happened inside (none for this pure-inference tool)."));
children.push(numbered("JSON-RPC response back through CloudFront to Claude.ai."));

// ============================================================
// SECTION 2 — The Four Wizards
// ============================================================

children.push(h1("2. The Four Wizards"));
children.push(para(
  "Wizards are the predictive-AI backbone. A through D, each owning a distinct concern. The biggest tech-lead mistake is treating them as a uniform 'AI pipeline' — they're four DIFFERENT models with different runtime contracts."
));

children.push(h2("2.1 Wizard A — Causal-graph generation"));
children.push(bullet("Purpose: build the per-account causal graph (ContextNode + ContextEdge) from raw uploaded signals + KPI deltas."));
children.push(bullet("Entry point: wizards/wizard_a_*.py invoked by process_data_pipeline.py."));
children.push(bullet("Runtime: auto-fires as part of process_data. Customer doesn't trigger explicitly."));
children.push(bullet("Output: ContextEdges with edge_type (CAUSED_BY / INDICATES / LED_TO / etc.), polarity, weight, revenue_impact. The 'natural arc' classification (crisis_recovery, champion_loss, etc.) lives on Account.arc_type, also written by Wizard A."));
children.push(bullet("Validation: 11 graph invariants (per session memory context_graph_invariants.md), 3 layers — prod WARN, pytest CI, audit CLI. Polarity invariants are the most-watched: a positive signal can't cause a negative-revenue-impact OUTCOME."));

children.push(h2("2.2 Wizard B — Pattern + counterfactual analysis"));
children.push(bullet("Purpose: pattern-match historical journeys against canonical arcs (silent_churn, expansion_champion, etc.). Compute counterfactual NRR — 'what would NRR have been if CS Pulse had been running through this period?'"));
children.push(bullet("Entry point: wizards/wizard_b_pattern_db.py → run_wizard_b(customer_id). Wraps verticals/_template/journey/wizard_b/wizard_b_pattern_analyzer.py."));
children.push(bullet("Runtime: auto-fires as part of process_data."));
children.push(bullet("Output (stored in portfolio_nrr_forecast field): without_cs_pulse_nrr_pct, with_cs_pulse_nrr_pct, with_interventions_nrr_pct, cs_pulse_delta_pct, cs_pulse_arr_protected, cs_pulse_accounts_saved, T+30/60/90 trajectory."));
children.push(bullet("CRITICAL FOR DEMOS: Wizard B's NRR figures are FORWARD-projected, NOT historical (despite the panel header 'PAST — Three Lenses' implying past-looking). The 88.49 / 109.26 / 88.09 numbers are forward simulations using arc-pattern signature × ARR-weighted projection. Lens A (90.21% historical) uses gross outcome math on uploaded events — DIFFERENT denominator AND different time direction. Don't try to reconcile by subtraction; the panel disambiguates inline (PR #43 + PR #44 fix)."));
children.push(bullet("Architecture decision (legitimate but confusing): Wizard B's 88.09% 'natural-arc baseline' is from a cross-customer pattern set, NOT this tenant's actual history. By design — counterfactual modeling needs an out-of-sample baseline. The 0.4pp lift (with-CS minus without-CS in Wizard B's world) is the legitimate attributable lift."));

children.push(h2("2.3 Wizard C — KPI weight calibration"));
children.push(bullet("Purpose: per-customer KPI weights are dynamic, not hardcoded. Wizard C correlates historical KPI values against HealthScore-derived success/fail labels, then re-derives kpi_weights_L1 and pillar_weights_L2."));
children.push(bullet("Entry point: wizards/wizard_c_weight_calibrator_db.py."));
children.push(bullet("Runtime: NOT auto-fired by process_data. Explicit-only via trigger_wizard('c') MCP tool OR admin endpoint. Policy rationale (per policy_wizard_c_decoupled_from_process_data.md): correlation needs stable signal, weight churn breaks WeightCalibrationHistory audit trail. Right cadence is outcome-count threshold (≥10 new closed outcomes) OR monthly cron — NOT per-process_data."));
children.push(bullet("Important caveat: the ≥10-outcomes auto-trigger is POLICY-STATED but NOT CODE-ENFORCED today. Treat as admin-trigger-only until base dev confirms the threshold is wired. Documented in FDE Playbook §7.3."));
children.push(bullet("Output: writes to CustomerConfig.dc2s_pillar_weights (L2) and dc2s_kpi_weights (L1). Audit trail in WeightCalibrationHistory."));
children.push(bullet("Roadmap (Tier 2): a second 'edge-aware' weight column that consumes count_trustworthy_causal_edges() — surfacing context graph quality into the calibration. Triggers: ≥3 customers with ≥30 LLM-enriched edges + AI-DD probe. See backlog_wizard_c_edge_aware_weights.md."));

children.push(h2("2.4 Wizard D — Predictor recalibration (the GLMM)"));
children.push(para(
  "Wizard D is the most consequential model in CS Pulse — it powers the forward NRR forecast that anchors the CFO + CRO demos. Worth understanding deeply."
));
children.push(diagram("d4_wizard_d_flow.png"));
children.push(caption("Figure 2 — Wizard D calibration + inference flow. Top: trigger (MCP or admin endpoint) → run_wizard_d builds training panel → fits 4 sub-models (hazard, contraction, expansion_event, expansion_size). Middle: INSERTs to predictor_calibrations, flips prior is_active=false (audit trail). Bottom: predictor/inference.py reads active rows at request time; output surfaces on CFO rollup (103.71% ARR-weighted for cust 334) and MCP tools."));

children.push(h3("Entry point + storage"));
children.push(bullet("Entry: wizards/wizard_d_predictor_calibrator.py → run_wizard_d(customer_id). Admin trigger: POST /api/admin/wizard-d/run (admin_api.py:1057). MCP trigger: trigger_wizard('d')."));
children.push(bullet("Output stored in DB table predictor_calibrations (models.py:1862 — PredictorCalibration class)."));
children.push(bullet("Schema: calibration_id (unique) + customer_id (nullable) + vertical + saas_profile + sub_model + fit_type + coefficients (JSON) + prior_used (JSON) + metrics (JSON) + panel_summary (JSON) + is_active + fit_completed_at."));
children.push(bullet("One row per (customer × vertical × profile × sub_model) at any active moment. Wizard D never UPDATEs; INSERTs new + flips prior is_active to False (audit trail preserved)."));
children.push(bullet("4 sub-models per tenant (A6 architecture decision):"));
children.push(bullet("  hazard — monthly logit, P(account churns in this month)", 1));
children.push(bullet("  contraction — conditional logit, P(contraction event | account survives)", 1));
children.push(bullet("  expansion_event — monthly logit, P(any expansion event)", 1));
children.push(bullet("  expansion_size — log link, E[size | expansion event occurred]", 1));
children.push(bullet("fit_type: cdi_seed (cross-customer prior, cold start) → tenant_glmm (frequentist hierarchical, default Phase 1) → tenant_bayes (Bayesian hierarchical, Phase 2, gated on data + hire)."));

children.push(h3("The GLMM (Generalized Linear Mixed Model)"));
children.push(para(
  "Why GLMM and not plain regression? Because the NRR outcomes aren't normally distributed. Churn is binary (0/1), expansion size is continuous-but-skewed. A plain linear regression doesn't respect those bounds; GLM's link functions (logit, log) map them onto a well-behaved linear scale."
));
children.push(para(
  "Why 'mixed'? Because the model needs BOTH fixed effects (parameters that apply across all tenants — e.g. 'high health-score lowers churn probability') AND random effects (per-tenant intercepts that capture this customer's specific baseline). The 'mixed' part is what lets cross-customer patterns and tenant-specific idiosyncrasies coexist in one model without overfitting."
));
children.push(para(
  "Why not deep learning? GLMM coefficients are INTERPRETABLE. When a CFO asks 'why is account X forecasted at 107%?', Wizard D names the features (health, expansion signals, signal count, ARR bucket) and how much each contributed. A neural net can't do that natively. For auditor-defensibility, interpretability matters more than marginal accuracy."
));

children.push(h3("Inference path"));
children.push(bullet("predictor/inference.py — predict_for_account_id(customer_id, account_id, horizon). Loads active PredictorCalibration rows for (customer × vertical × profile × *). Runs the 4 sub-models per account."));
children.push(bullet("Returns expected_nrr.{point, lower_90, upper_90} + term_decomposition (p_churn, p_survive, e_contract, e_expand) + top_drivers (feature contributions) + expansion_outlook (P(event), expected_size, ARR_lift) + calibration_id (provenance)."));
children.push(bullet("Portfolio rollup: NO standalone HTTP route. Happens inline in executive_dashboard_api.py:1353–1395 (cfo_dashboard handler loops predict_for_account_id over every account, ARR-weights, returns as predictor_v3_portfolio_nrr block)."));

children.push(h3("Per-account HTTP route + MCP tools"));
children.push(bullet("HTTP: GET /api/predictor/account/<int:account_id>/nrr-forecast (predictor_api.py:71)."));
children.push(bullet("MCP get_account_nrr_forecast(customer_id, account_id, horizon) — cs_pulse_predictor.py:48"));
children.push(bullet("MCP get_portfolio_nrr_forecast_v3(customer_id, horizon) — line 126"));
children.push(bullet("MCP get_top_expansion_opportunities_v3(customer_id, horizon, limit) — line 278"));
children.push(bullet("MCP get_top_at_risk_accounts_v3(customer_id, horizon, limit) — line 355"));

children.push(h3("Live data sample (cust 334 today)"));
children.push(code("arr_weighted_nrr_pct:    103.71\nsimple_avg_nrr_pct:       88.78\nactive_account_count:    25\ncalibration_id:           wizard_d_7824d7c1f4c8__saas_enterprise__expansion_size\ncalibrated_at:            2026-05-12T18:01:31"));

children.push(h3("Confidence intervals — what they mean + what's pending"));
children.push(para(
  "Each account returns expected_nrr.lower_90 and upper_90. The 90% CI is a frequentist interval — formally 'if we re-ran the calibration many times, the true NRR would fall inside this range in ~90% of those runs.' For the demo audience, use the colloquial: 'in 9 out of 10 cases the realized NRR lands inside this band.'"
));
children.push(para(
  "What's still placeholder (Phase 1 task #4 pending): the CI WIDTH today is a placeholder, not from a fully calibrated bootstrap. Tagged via ci_method: placeholder_uncalibrated on every v3 response. The point estimate IS calibrated; only the bounds aren't yet. AI-DD reviewers WILL catch this — the honest answer is 'point uses the calibrated GLMM; width is conservative until bootstrap CIs land.' CRO-3 / CRO-4 / CRO-8 / CFO-10 stay partial-credit until Phase 1 task #4 ships."
));

// ============================================================
// SECTION 3 — Context graph
// ============================================================

children.push(h1("3. Context Graph (the causal layer)"));
children.push(para(
  "Every revenue-relevant fact in CS Pulse — a signal arriving, a decision made, an outcome realized — lands in the context graph. Two tables, ContextNode and ContextEdge, with eleven invariants enforced in CI."
));

children.push(h2("3.1 Schema"));
children.push(diagram("d6_context_graph.png"));
children.push(caption("Figure 3 — Context Graph schema. Two tables (ContextNode + ContextEdge) with 6 node_type values and 9 edge_type values, validated by 11 CI-enforced invariants. Polarity invariants (I2) are the most-watched — a positive signal cannot cause a negative-revenue OUTCOME."));
children.push(h3("ContextNode (models.py:719)"));
children.push(bullet("node_id (PK), customer_id, account_id — tenant + account isolation"));
children.push(bullet("node_type — ACCOUNT / SIGNAL / STAKEHOLDER / DECISION / OUTCOME / EXTERNAL_CONTEXT"));
children.push(bullet("node_subtype — finer-grained (e.g. SIGNAL.nps_decline, DECISION.playbook, OUTCOME.churn_lost)"));
children.push(bullet("source — 'customer' (CSV upload) or 'system' (Wizard A / signal_analyst / urgent_scanner)"));
children.push(bullet("tier — 1 (permanent) / 2 (decaying with TTL) / 3 (ephemeral)"));
children.push(bullet("title, properties (JSON), revenue_impact (Numeric 15,2), revenue_impact_type (at_risk / protected / expansion / lost), confidence (0–1)"));
children.push(bullet("source_platform (sfdc / hubspot / intercom / csv_import), source_event_id (dedup key)"));
children.push(bullet("occurred_at, expires_at (NULL for tier 1), weight_decay"));

children.push(h3("ContextEdge (models.py:798)"));
children.push(bullet("edge_id (PK), from_node_id + to_node_id (CASCADE delete)"));
children.push(bullet("edge_type — CAUSED_BY / INDICATES / LED_TO / CORRELATES_WITH / INVOLVES / BELONGS_TO / BENCHMARKED_BY / SOURCED_FROM / SUPERSEDES"));
children.push(bullet("polarity, weight, revenue_impact, confidence"));
children.push(bullet("source — 'customer' / 'wizard_a' / 'wizard_b_pattern' / 'llm_enrichment' / 'signal_analyst'"));

children.push(h2("3.2 The eleven invariants"));
children.push(para(
  "Per context_graph_invariants.md. Validators run in three places: prod WARN (logs but doesn't block), pytest CI (blocks merges), audit CLI (one-shot baseline diff). Any new invariant must ship with paired clean+dirty tests — meta-test enforces this."
));
children.push(bullet("I1 — node existence: edges reference nodes that exist"));
children.push(bullet("I2 — polarity match: edge polarity matches node revenue_impact_type"));
children.push(bullet("I3 — tier consistency: tier-1 nodes can't have edges from tier-3 nodes"));
children.push(bullet("I4 — temporal causality: CAUSED_BY edges require from_node.occurred_at < to_node.occurred_at"));
children.push(bullet("I5 — tenant isolation: nodes + edges share customer_id"));
children.push(bullet("I6 — account scope: account_id matches across connected nodes for account-scoped subgraphs"));
children.push(bullet("I7 — decay weights: weight_decay ∈ [0, 1]"));
children.push(bullet("I8 — provenance: every system-source node has a non-null source_event_id"));
children.push(bullet("I9 — orphan policy: tier-1 nodes can't be orphaned (no incoming or outgoing edges)"));
children.push(bullet("I10 — confidence range: confidence ∈ [0, 1] on edges + nodes"));
children.push(bullet("I11 — bucket map: revenue_impact_type subtype matches polarity classification"));
children.push(para(
  "Baseline on cust 384/385: ~280 violations each. I11 dominates but is trivially fixable; I1/I8/I10 are audit-indefensible (high-priority cleanup); I2 reveals template edge generators producing polarity-mismatched edges (systemic, not per-tenant). Tech lead heuristic: NEW invariant should NEVER ship without a paired migration that clears the existing baseline OR an explicit grandfather entry."
));

children.push(h2("3.3 Query helpers"));
children.push(para("utils/context_graph.py provides: get_nodes(customer_id, filters), get_edges, traverse_2hop, upsert_node (handles dedup via source_platform + source_event_id), add_edge, get_revenue_at_risk (aggregates revenue_impact where revenue_impact_type='at_risk')."));
children.push(para("Aggregation helper aggregate_revenue_across_accounts is the engine behind the 'Confirmed Revenue at Risk' tile on both CRO and CFO dashboards. Same function call, two surfaces — the Flask + MCP duplication-drift audit (PR #37) catches cases where this aggregation drifts between dashboards."));

// ============================================================
// SECTION 4 — Signal engine
// ============================================================

children.push(h1("4. Signal Engine (three channels)"));
children.push(para(
  "Qualitative signals are the leading-indicator layer (per Vision/Architecture §1.1). Three ingest paths into the same destination — ContextNode rows with node_type='SIGNAL'."
));
children.push(diagram("d7_signal_engine.png"));
children.push(caption("Figure 4 — Signal engine three-channel pipeline. Channel 1 (CSV) bypasses enrichment; Channels 2+3 (live email/Slack) go through the shared LLM-enrichment + fusion + urgency pipeline. All three converge on the context graph + Qdrant index. CSV is default-ON, live channels are OFF until DPA signed (per playbook §2.4)."));

children.push(h2("4.1 Channel 1 — CSV upload (default)"));
children.push(bullet("File: qualitative_signals.csv or enhanced_qualitative_signals.csv (both accepted)"));
children.push(bullet("Loader: cs_pulse_onboarding.py via process_data → context graph upsert"));
children.push(bullet("Default state: ON for every new tenant. Signals land directly during process_data."));

children.push(h2("4.2 Channel 2 — Live email forwarding"));
children.push(bullet("File: signal_engine/email_receiver.py"));
children.push(bullet("Source: SendGrid Inbound Parse hits an HTTP endpoint when emails arrive at a customer-specific forwarding address."));
children.push(bullet("Pipeline: email → enrichment.py (LLM tags signal_type + sentiment) → fusion.py (dedup against existing context nodes) → urgency.py (priority classification) → context graph insert + alert dispatch."));
children.push(bullet("Default state: OFF per tenant until DPA signed."));

children.push(h2("4.3 Channel 3 — Live Slack/Teams webhooks"));
children.push(bullet("File: signal_engine/slack_events.py"));
children.push(bullet("Source: Slack/Teams event webhook → ingest_api.py route."));
children.push(bullet("Same enrichment/fusion/urgency pipeline as email."));
children.push(bullet("Default state: OFF per tenant until DPA signed + Slack workspace integration approved."));

children.push(h2("4.4 The enrichment pipeline"));
children.push(para("Shared across channels 2+3 (channel 1 bypasses since CSVs come pre-classified):"));
children.push(numbered("Raw event arrives → ingest_api.py → ingest_queue."));
children.push(numbered("Worker picks up event → enrichment.py — LLM call to tag signal_type, sentiment, severity, stakeholder_level. Logged via record_usage()."));
children.push(numbered("Worker passes to fusion.py — dedup against recent context nodes (source_platform + source_event_id + time-window heuristic)."));
children.push(numbered("Worker passes to urgency.py — assigns priority bucket (critical / high / medium / low) based on signal_type + sentiment + account health."));
children.push(numbered("Worker writes to ContextNode + (optionally) ContextEdge → fires alert if priority='critical'."));
children.push(numbered("Worker calls SignalVectorStore.index_signal() (if QDRANT_URL set) → Qdrant index updated for semantic search."));

children.push(h2("4.5 Hard rules"));
children.push(bullet("DO NOT edit enrichment.py, fusion.py, urgency.py, collision.py in a customer overlay. These are the shared signal-processing pipeline. Bespoke rules go to base-dev."));
children.push(bullet("Auto-fix policy for unknown signal subtypes (policy_taxonomy_runtime_auto_fix.md): polarity subtypes silent LLM auto-classify; revenue-bucket subtypes quarantine + human review. Customers never edit the taxonomy directly; they pick via CDI DNA templates."));

// ============================================================
// SECTION 5 — Outcome ROI engine
// ============================================================

children.push(h1("5. Outcome ROI Engine"));
children.push(para(
  "Three lenses of CS ROI proof: historical (what closed), forward (Power-of-1 projection), bridge (continuity narrative). The CFO dashboard reads from this engine; the Outcome ROI dashboard renders all three in one view."
));
children.push(diagram("d8_outcome_roi.png"));
children.push(caption("Figure 5 — Outcome ROI 3-lens architecture. Lens A (Historical) goes through the disclosure heuristic which fires the auditor caveat when ROI > 500% AND avg improvement > 2× forward steady-state. Bridge ties historical + forward + steers the reader to the credible headline number. Lens C (Realized) is rendered on the same CFO panel but takes a different data path — bottom-up sum of PlaybookExecutionV2.revenue_protected."));

children.push(h2("5.1 The OutcomeROIResult dataclass (outcome_roi_engine.py:380+)"));
children.push(bullet("view_type — 'historical' or 'forward'"));
children.push(bullet("period_label — 'Last 6 Months' or backend-rewritten 'Last 6 Months (since onboarding — includes one-time gains)' when disclosure fires"));
children.push(bullet("summary — total_investment, total_impact, revenue_protected, revenue_expanded, cost_savings, roi_pct, payback_months, improvement_pct_avg"));
children.push(bullet("metric_outcomes — per-metric drill: baseline_value, current_value, improvement_pct, dollar_impact, revenue/savings_portion, linked_kpis, linked_playbooks"));
children.push(bullet("disclosure (PR #20) — populated when historical view surfaces non-repeatable one-time gains. Shape: { non_repeatable, period_basis, headline, detail, recommended_label }"));

children.push(h2("5.2 The disclosure heuristic (the auditor caveat trigger)"));
children.push(para("_build_historical_disclosure (outcome_roi_engine.py:612). The disclosure fires when both conditions hold:"));
children.push(bullet("ROI > 500% (well above steady-state CS ROI, which sits in 200–500% per Bain/TSIA benchmarks)"));
children.push(bullet("AVG historical improvement > 2× forward_steady_state_pct (or > 2.0pp absolute when forward signal absent)"));
children.push(para(
  "When triggered: period_label gets rewritten with the 'since onboarding' suffix, bridge.recommended_headline_roi_pct steers the reader to forward steady-state, an amber disclosure block renders on the PROVEN panel (PR #40 UI). Cust 334 example: 7,652% historical → triggered; 7,652% with improvement_pct=1 forward target (lift threshold 2.0); SUPPRESSED at improvement_pct=4 (threshold 8.0)."
));

children.push(h2("5.3 Stable-window baseline (Option A — opt-in)"));
children.push(para(
  "_extract_historical_actuals supports skip_unstable_months kwarg. When set to N (e.g. 3), the loader drops the earliest N distinct months per KPI before computing baseline — anchors past the typical onboarding ramp / synthetic-decline phase. Exposed via ?stable=N query param on /api/outcome-roi/historical AND via ROI_HISTORICAL_SKIP_UNSTABLE_MONTHS env var on the MCP tool."
));
children.push(para("Default 0 preserves legacy behavior. Use when a buyer demands strict trailing-window proof. Provenance recorded as data_source='..._stable_skip3' and historical_period_basis='stable_window'."));

children.push(h2("5.4 The bridge"));
children.push(para(
  "Bridges historical → forward with a narrative. bridge.trajectory ('accelerating' / 'sustaining'), bridge.narrative (auto-built string), bridge.momentum_metrics (per-metric historical_dollars + forward_dollars). When historical disclosure fires, bridge.recommended_headline_roi_pct = forward steady-state — explicit steer for the auditor to anchor on the credible number."
));

// ============================================================
// SECTION 6 — MCP server
// ============================================================

children.push(h1("6. MCP Server"));

children.push(h2("6.1 Anatomy"));
children.push(bullet("Tools live in kpi-dashboard/backend/mcp_server/cs_pulse_*.py. Each tool is a Python function decorated with @mcp.tool with a docstring + typed signature."));
children.push(bullet("Tool count: ~52 today. NOT auto-generated — count by greping for @mcp.tool before quoting."));
children.push(bullet("Transport: JSON-RPC streamable-HTTP over /mcp. Both query-param (?api_key=) and Bearer-header forms work."));
children.push(bullet("Auth: validate_server_key() checks MCP_SERVER_API_KEY env var. EMPTY env = all keys rejected — see §3.10 footgun in FDE Playbook."));
children.push(bullet("Per-account auth: _require_account_auth + _validate_account_ownership for tools that take account_id. Prevents cross-tenant leakage if a valid customer key tries an account from a different tenant."));

children.push(h2("6.2 Adding a new MCP tool (base-dev only)"));
children.push(numbered("Pick the right file: cs_pulse_predictor.py for forecast tools, cs_pulse_revenue.py for revenue/ROI tools, cs_pulse_onboarding.py for customer ops, etc."));
children.push(numbered("Decorate with @mcp.tool. Write a TIGHTLY-SCOPED docstring — the Ask AI router uses this to decide when to call the tool. Vague docstrings → wrong-tool calls."));
children.push(numbered("Add typed args with sensible defaults. customer_id is always required as the first positional arg (convention from PR #18 onwards)."));
children.push(numbered("Add per-account auth if relevant: _validate_account_ownership(customer_id, account_id)."));
children.push(numbered("Add a paired Flask route IF the dashboard needs it. WARNING: this triggers the Flask+MCP duplication-drift audit (PR #37) — sibling functions across layers must match in signature, response keys, and helper routing."));
children.push(numbered("If the tool makes an LLM call, ensure record_usage() is called. Grep-verify; do NOT trust assumed-tracked."));
children.push(numbered("Add a persona-grader fixture if any persona will ask a question that should route here."));

children.push(h2("6.3 Ask AI vs MCP — two consumption surfaces"));
children.push(para(
  "Same tool catalog, two entry points. Ask AI (in-product floating portal) routes through ask_ai_endpoint.py which uses TOOL_DEFINITIONS in ask_ai_tools.py — a curated subset of MCP tools. Claude.ai connects directly to the MCP HTTP endpoint and sees all ~52 tools."
));
children.push(para(
  "Risk: drift between the two surfaces. Apr 26 incident — had to manually wire get_csm_scorecard / get_csm_ranking / get_team_capacity / get_portfolio_revenue_breakdown into Ask AI even though all 4 had been in MCP for weeks. Roadmap (backlog_auto_derive_ask_ai_tools_from_mcp.md): auto-derive Ask AI TOOL_DEFINITIONS from the @mcp.tool registry. ~1.5–2 days. Trigger: next time a 4th–5th tool surfaces this drift."
));

// ============================================================
// SECTION 7 — Database schema (key tables)
// ============================================================

children.push(h1("7. Database Schema (key tables)"));
children.push(para("Highlights only. Full schema in kpi-dashboard/backend/models.py."));
children.push(diagram("d9_db_schema.png", 600));
children.push(caption("Figure 6 — ER diagram of the key tables. Customers is the root; everything fans out tenant-isolated. Note PREDICTOR_CALIBRATIONS (Wizard D output, 4 sub-models per active tenant), CONTEXT_NODES + CONTEXT_EDGES (the causal layer with self-referential edges via from/to_node_id), and LLM_USAGE_LOG (every LLM call tracked for cost attribution + governance audit)."));

children.push(table([2800, 6800], [
  ["Table", "Purpose"],
  ["customers", "One row per tenant. Customer_id (int) + uuid. vertical, profile_metadata (JSON), tier."],
  ["accounts", "Per-tenant accounts. account_id (PK), customer_id (FK), account_name, revenue, account_status, industry, vertical, region, external_account_id, profile_metadata (JSON — includes assigned_csm), uuid, customer_uuid, arc_type/arc_phase/arc_confidence (Wizard A output)."],
  ["health_scores", "Monthly health score snapshots. account_id, measurement_month, health_score, status, contributing_pillars (JSON), kpi_only_score, trend."],
  ["pillar_scores + kpi_scores", "Pillar and KPI breakdowns per account-month."],
  ["context_nodes", "The graph node table. See §3.1 for schema. Indexed on account+type, customer+type, occurred_at, tier+expires_at, source_platform+source_event_id."],
  ["context_edges", "The graph edge table. See §3.1."],
  ["playbook_executions_v2", "Realized ROI Tracker. execution_id, customer_id, account_id, playbook_id, status (in_progress / completed / failed / cancelled), phase (stabilize / rebuild / secure), csm_hours, total_cost, health_at_trigger, health_at_close, revenue_protected, revenue_expanded, realized_roi_pct, projected_roi_pct, roi_variance_pct, action_log (JSON), skill_output (JSON), executive_briefing (text)."],
  ["predictor_calibrations", "Wizard D output. See §2.4. 4 sub-models × is_active=true rows per active (customer × vertical × profile)."],
  ["customer_playbooks", "Per-tenant playbook customizations via /api/playbooks/library."],
  ["weight_calibration_history", "Wizard C audit trail."],
  ["roi_snapshots", "Audit trail of ROI calculations."],
  ["llm_usage_log", "EVERY LLM call. provider, model, tokens_in/out, cost_usd, tool_called, customer_id (for attribution). Required for cost dashboard + governance."],
  ["wizard_runs", "Audit trail per wizard invocation. wizard_type, customer_id, started_at, completed_at, status, results (JSON)."],
  ["users", "Auth subjects. user_id, customer_id, email, password_hash, role, allowed_account_ids (JSON, per-CSM scoping), magic_link_token + magic_link_expires_at."],
  ["customer_configs", "Per-tenant config: dc2s_pillar_weights + dc2s_kpi_weights (Wizard C output), feature toggles, entitlements."],
], { zebra: true }));

// ============================================================
// SECTION 8 — Data flow
// ============================================================

children.push(h1("8. End-to-End Data Flow"));
children.push(para("One representative slice — what happens between a customer uploading their 4 CSVs and a CFO seeing the FORECAST NRR tile."));

children.push(numbered("Customer uploads 4 CSVs via admin UI OR MCP upload_csv. Files land in verticals/customer{N}-{vertical}/data/."));
children.push(numbered("Customer (or admin) calls process_data. cs_pulse_onboarding._process_data_impl orchestrates: validate schemas → insert accounts → insert KPI measurements → insert qualitative signals → insert outcomes → fire Wizard A → fire Wizard B → (optionally) Qdrant indexing → mark complete."));
children.push(numbered("Wizard A walks each account's signals + KPI deltas → emits ContextNodes (DECISION + OUTCOME) and ContextEdges (CAUSED_BY, INDICATES). Account arc_type, arc_phase, arc_confidence written back."));
children.push(numbered("Wizard B reads Wizard A output → pattern-matches against canonical arcs → builds portfolio_nrr_forecast (without_cs / with_cs / with_interventions, ARR-weighted across active accounts) → stored as WizardRun.results."));
children.push(numbered("Admin runs trigger_wizard('d'). Wizard D fits 4 sub-models on the tenant's panel data + prior. INSERTs 4 PredictorCalibration rows, flips prior is_active=False."));
children.push(numbered("CFO loads /cfo-dashboard. Handler queries: latest health, pillar scores, OUTCOME nodes (for Lens A), Wizard B output (for Lens B), PlaybookExecutionV2 (for Lens C), predictor_calibrations (for FORECAST NRR tile)."));
children.push(numbered("Handler loops predict_for_account_id over every account → loads active PredictorCalibration rows → runs 4 sub-models → aggregates ARR-weighted → returns as predictor_v3_portfolio_nrr block."));
children.push(numbered("React renders all blocks. FORECAST NRR — NEXT 12MO tile shows arr_weighted_nrr_pct (e.g. 103.71% for cust 334). User clicks the (i) tooltip → calibration_id + calibrated_at."));

// ============================================================
// SECTION 9 — LLM cost tracking + governance
// ============================================================

children.push(h1("9. LLM Cost Tracking + Governance"));
children.push(para(
  "Every LLM call is a financial transaction. The discipline is: every call site invokes record_usage() with provider, model, tokens, cost_usd, tool_called, customer_id. Per-customer cost attribution lives in the llm_usage_log table; the platform dashboard rolls it up."
));

children.push(h2("9.1 record_usage discipline"));
children.push(bullet("Helper: utils/llm_budget_controller.record_usage(...). Also can_call() for pre-flight budget check."));
children.push(bullet("Wrap every Anthropic / OpenAI SDK call. The wrapper around the SDK call should be the ONLY place that talks to the provider; bare provider calls bypass tracking."));
children.push(bullet("Apr 20 incident: 6 production callers bypassed record_usage. $0.45 of real spend invisible. After the audit: grep-verified every call site has a matching record_usage call before considering a PR done."));

children.push(h2("9.2 Governance framework"));
children.push(para(
  "Per project_governance_layer_apr20.md, CS Pulse shipped 7 governance docs in April: AI_GOVERNANCE_FRAMEWORK + MODEL_INVENTORY (15 models) + CHANGE_MANAGEMENT + AUDIT_TRAIL_REQUIREMENTS + DRIFT_MONITORING + GOVERNANCE_ROADMAP + SOC2/RBAC v1.1."
));
children.push(para("Key principles:"));
children.push(bullet("Model card per LLM-backed feature — declared in MODEL_INVENTORY. Tier 1/2/3 by risk."));
children.push(bullet("Known limitations are CRs (change requests), not documentation. Apr 20 incident: MOD-004 limitation got logged not CR'd; surfaced in buyer AI-DD next day."));
children.push(bullet("MOD-002 approval gate + MOD-007 prompt register + MOD-008 admin UI form the fast-unblock path for 9 of 15 models. MOD-003 (renewal probability) + MOD-012 stay hard-blocked until Phase 1 controls land."));

// ============================================================
// SECTION 10 — Testing architecture
// ============================================================

children.push(h1("10. Testing Architecture"));
children.push(diagram("d10_test_architecture.png"));
children.push(caption("Figure 7 — Testing architecture. Red = CI gates (must pass to merge — narrow pytest subset + 2 audits + TypeScript compile). Green = opt-in post-merge or pre-release (persona grading, verify scripts, acceptance harness, load-driver E2E). Yellow = developer discipline enforced by code review (verify-diff, CHANGELOG, record_usage grep, local audit run)."));

children.push(h2("10.1 What CI runs as a gate"));
children.push(bullet("Narrow pytest subset — score calculator, account-column ORM audit (PR #32), Flask + MCP duplication-drift audit (PR #37)."));
children.push(bullet("Frontend TypeScript compile (catches type drift pytest misses)."));
children.push(bullet("Account-column audit: AST-walks every Account attribute access against the actual ORM column list. Drained 9 latent violations on first run."));
children.push(bullet("Flask + MCP drift audit: pairs Flask handlers with MCP sibling tools via name + URL stem + manual alias map. Catches signature_drift, response_key_drift, helper_drift. 0 NEW violations on the last 5 main commits."));

children.push(h2("10.2 What CI does NOT run automatically (opt-in)"));
children.push(bullet("Persona grading (tests/persona_grading) — costs $3–5 per run. Opt in via PERSONA_GRADING_ENABLED=1 pytest flag, or run manually before tagging a release."));
children.push(bullet("HTTP verify scripts (scripts/verify_*.py) — run post-rehydrate, not at PR time. Acceptance harness scripts/run_acceptance_ec2.sh orchestrates."));
children.push(bullet("Load-driver E2E — full lifecycle test, manual on demo tenants."));

children.push(h2("10.3 Persona grading framework"));
children.push(bullet("Location: kpi-dashboard/backend/tests/persona_grading/"));
children.push(bullet("Five fixtures: ceo.py (5 Qs), cfo.py (6), cro.py (6), csm.py (6), vpcs.py (7). ~30 total."));
children.push(bullet("Each Question has: question text, must_cite list (facts that must appear), must_call_tools list, tone_check, anti_hallucination list."));
children.push(bullet("Grader (grader.py) is a Claude Sonnet call role-playing as a 15-year-veteran of the persona (5-yr for CSM). Returns letter grade A–F + numeric (~4.0 scale) + rationale."));
children.push(bullet("Invocation: python3 -m tests.persona_grading.runner --customer N --output PATH. Flags: --personas (subset), --shots (default 1, use 3 for calibration confidence), --model (default claude-sonnet-4-20250514)."));

children.push(h2("10.4 Verify scripts (deterministic gate)"));
children.push(bullet("Primary: scripts/verify_executive_phases_ec2.py with --suite all|cfo|cro|vpcs|cfo-phase1. Env-driven, reads scripts/.env.acceptance."));
children.push(bullet("Per-PR scripts kept for surgical re-runs: verify_cfo_phases_ec2.py, verify_cro_phases_ec2.py, verify_vpcs_phases_ec2.py, verify_cfo_phase1_ec2.py."));
children.push(bullet("Pattern for new persona-facing PRs: extend scripts/ec2_acceptance/checks.py with new invariants + add a new --suite name in the primary script. Do NOT add another standalone verify_*.py — the per-PR pattern predates the env-driven runner."));

children.push(h2("10.5 Acceptance harness"));
children.push(bullet("scripts/run_acceptance_ec2.sh + scripts/.env.acceptance(.example) + scripts/ec2_acceptance/{config,http_client,checks}.py."));
children.push(bullet("Two stages: (1) HTTP suites via verify_executive_phases_ec2.py, (2) optional persona grading via docker exec into the platform container."));
children.push(bullet("Knobs: ACCEPTANCE_CUSTOMER_ID, ACCEPTANCE_SUITE, ACCEPTANCE_RUN_PERSONA, ACCEPTANCE_PERSONAS, ACCEPTANCE_PERSONA_SHOTS, ACCEPTANCE_MIN_GRADE_NUMERIC (gate, e.g. 3.7 for A-), ACCEPTANCE_SEED_VPCS, CSPULSE_CONTAINER."));
children.push(bullet("Exit non-zero on any HTTP failure or below-gate grade — wire into post-rehydrate runbooks."));

// ============================================================
// SECTION 11 — Engineering principles
// ============================================================

children.push(h1("11. Engineering Principles (the discipline layer)"));
children.push(para("Restated from Vision/Architecture §8 for technical completeness — these have caught real bugs. Internalize before opening your first PR."));

children.push(h2("11.1 Verify model schema before writing queries"));
children.push(para("Always run Model.__table__.columns.keys() OR read the model definition. NEVER guess column names. Cost of violation: 30+ minute phantom-bug hunts."));

children.push(h2("11.2 Revert fixes built on a wrong diagnosis"));
children.push(para("Don't keep dead code as a 'safety net.' Git revert immediately when the diagnosis turns out wrong."));

children.push(h2("11.3 Account-column drift audit (CI-enforced)"));
children.push(para("acct.health_score → HealthScore-join, acct.assigned_csm → profile_metadata.assigned_csm, acct.name → account_name, etc. See FDE Playbook §3.11."));

children.push(h2("11.4 Flask + MCP duplication-drift audit (CI-enforced)"));
children.push(para("Sibling functions across layers must match in signature, response keys, helper routing. 3 real instances caught in May 2026 (B-1, PR #30, PR #33)."));

children.push(h2("11.5 Shift-left validation"));
children.push(para("Upload validates schema; ingest validates FK + temporal; wizards assume clean data. Don't punt validation downstream."));

children.push(h2("11.6 LLM call sites proven tracked"));
children.push(para("record_usage() is non-negotiable. Grep-verify before merging any LLM caller."));

children.push(h2("11.7 Governance limitations spawn CRs"));
children.push(para("Model-card limitations are pending change requests, not documentation. Treat as actionable backlog."));

children.push(h2("11.8 Intuitive file naming"));
children.push(para("File names communicate purpose without opening. build_panel.py not panel.py."));

children.push(h2("11.9 Cold-start sanity after every rebuild"));
children.push(para("5-minute end-to-end probe (register new tenant, exercise every MCP tool, walk all 5 dashboards) AFTER every rehydrate. Two proof points (Apr 5, May 17) where this caught silent bugs."));

children.push(h2("11.10 Prefer branches over worktrees"));
children.push(para("Per feedback_worktree.md — worktrees cause edit-loss and merge friction. Use branches for routine work. Worktrees are a tool for agent-isolated parallel work, not the default."));

// ============================================================
// CLOSING
// ============================================================

children.push(h1("12. First Practical Exercises"));
children.push(para("You've now read all three onboarding docs. Three exercises in order — each takes 30–90 min and gives you closed-loop intuition."));

children.push(h2("Exercise 1 — Trace a Wizard D calibration end-to-end (~60 min)"));
children.push(numbered("Open wizards/wizard_d_predictor_calibrator.py. Read run_wizard_d. Identify which DB tables it reads (panel data) and writes (predictor_calibrations + WizardRun.results)."));
children.push(numbered("Open predictor/inference.py. Read predict_for_account_id. Identify which PredictorCalibration rows it loads and how it composes the 4 sub-models."));
children.push(numbered("Open executive_dashboard_api.py:1352–1395. Read the cfo_dashboard handler's Predictor v3 block — how it loops predict_for_account_id and ARR-weights."));
children.push(numbered("Hit live: curl /api/executive/cfo-dashboard for cust 334 and find the predictor_v3_portfolio_nrr block. Confirm arr_weighted_nrr_pct matches what the CFO tile renders."));
children.push(numbered("Open CFODashboard.tsx. Find where predictor_v3_portfolio_nrr is rendered (FORECAST NRR — NEXT 12MO tile). Trace from JSON to pixels."));

children.push(h2("Exercise 2 — Run scripts/run_acceptance_ec2.sh + the persona grader (~45 min, ~$3–5 cost)"));
children.push(numbered("Copy scripts/.env.acceptance.example → scripts/.env.acceptance. Fill in CS_PULSE_BASE_URL=http://3.94.106.197 + creds + ANTHROPIC_API_KEY."));
children.push(numbered("Run ./scripts/run_acceptance_ec2.sh (HTTP-only, no LLM cost). Confirm exit 0. Read scripts/datasets/<timestamp>.json — that's the deterministic verify output."));
children.push(numbered("Run ACCEPTANCE_RUN_PERSONA=1 ACCEPTANCE_PERSONAS=cfo ACCEPTANCE_PERSONA_SHOTS=3 ./scripts/run_acceptance_ec2.sh. Costs ~$1–2 for one persona × 3 shots."));
children.push(numbered("Open the grader output JSON. Read the rationale + specific_concerns fields per question. That's the closed-loop quality signal."));

children.push(h2("Exercise 3 — Add a new MCP tool + paired persona-grader question (~90 min)"));
children.push(numbered("Pick a small surface — e.g. get_arc_breakdown(customer_id) that returns per-arc-type ARR aggregations. Don't ship anything substantive; this is for ramp-up."));
children.push(numbered("Add @mcp.tool to cs_pulse_admin.py (or another appropriate file). Tightly-scoped docstring. customer_id as first arg."));
children.push(numbered("Add a Flask route IF it'd be dashboard-visible (skip for this exercise)."));
children.push(numbered("Add a fixture entry to tests/persona_grading/fixtures/csm.py with a question that should route here. must_call_tools should include 'get_arc_breakdown'."));
children.push(numbered("Run the grader with --personas csm --shots 1 against cust 334. Confirm the AI routes through your new tool."));
children.push(numbered("Open a PR. Watch the Flask + MCP drift audit + Account-column audit on CI. Get a green build before merging."));

children.push(new Paragraph({
  children: [new TextRun({ text: "─── End of Document 3 (Technical Deep Dive) ───", italics: true, size: 18, color: "808080" })],
  alignment: AlignmentType.CENTER, spacing: { before: 480 },
}));
children.push(new Paragraph({
  children: [new TextRun({ text: "You've finished the three-doc onboarding kit. Open a Slack thread with the team for questions; the FDE Playbook (gtm-decks/fde-kt/) is the operational companion when you start working with customers.", italics: true, size: 20, color: "606060" })],
  alignment: AlignmentType.CENTER, spacing: { before: 240, after: 240 },
}));

// ============================================================
// BUILD
// ============================================================

const doc = new Document({
  numbering: {
    config: [{
      reference: "default-numbering",
      levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.START,
        style: { paragraph: { indent: { left: 360, hanging: 240 } } } }],
    }],
  },
  styles: {
    paragraphStyles: [
      { id: "Normal", name: "Normal", run: { font: "Calibri", size: 22, color: "242424" } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", run: { bold: true, size: 32, color: "1F3A5F" }, paragraph: { spacing: { before: 360, after: 200 } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", run: { bold: true, size: 26, color: "1F3A5F" }, paragraph: { spacing: { before: 240, after: 140 } } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", run: { bold: true, size: 22, color: "404040" }, paragraph: { spacing: { before: 180, after: 100 } } },
    ],
  },
  sections: [{ properties: {}, children }],
});

const outPath = path.join(__dirname, "CSPulse_Technical_Deep_Dive.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(outPath, buf);
  console.log(`Wrote: ${outPath} (${buf.length} bytes)`);
});
