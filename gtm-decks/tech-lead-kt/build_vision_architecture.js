// Build CSPulse_Vision_Architecture_Guide.docx
// Tech-lead onboarding doc #2 — vision, roadmap, system architecture, admin operations.
// Audience: incoming tech lead. Companion docs: User Perspective (1), Technical Deep Dive (3).

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType, ShadingType,
  ImageRun,
} = require('docx');

// Embed a PNG diagram (constrains to ~580px usable Word width, preserves aspect ratio).
function diagram(filename, maxWidth = 580) {
  const imgPath = path.join(__dirname, 'diagrams', filename);
  if (!fs.existsSync(imgPath)) {
    return new Paragraph({ children: [new TextRun({ text: `[diagram missing: ${filename}]`, italics: true, color: "808080" })] });
  }
  // Read original dimensions via PNG IHDR (bytes 16-23)
  const buf = fs.readFileSync(imgPath);
  const origW = buf.readUInt32BE(16);
  const origH = buf.readUInt32BE(20);
  const scale = Math.min(1, maxWidth / origW);
  const w = Math.round(origW * scale);
  const h = Math.round(origH * scale);
  return new Paragraph({
    children: [new ImageRun({ data: buf, transformation: { width: w, height: h } })],
    alignment: AlignmentType.CENTER,
    spacing: { before: 120, after: 180 },
  });
}
function caption(text) {
  return new Paragraph({
    children: [new TextRun({ text, italics: true, size: 18, color: "606060" })],
    alignment: AlignmentType.CENTER,
    spacing: { after: 240 },
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
  children: [new TextRun({ text: "CS Pulse — Vision, Roadmap & Architecture", bold: true, size: 36 })],
  alignment: AlignmentType.CENTER, spacing: { after: 200 },
}));
children.push(new Paragraph({
  children: [new TextRun({ text: "Tech-lead onboarding · admin-level architectural view", italics: true, size: 22, color: "606060" })],
  alignment: AlignmentType.CENTER, spacing: { after: 360 },
}));
children.push(para(
  "Doc #2 of three. The strategic + structural view of CS Pulse. Where User Perspective (doc #1) shows what customers experience, this doc shows WHY the product is built that way and HOW the system is structured to deliver it. Companion: Technical Deep Dive (doc #3) for the implementation-level internals."
));
children.push(para(
  "Audience: tech lead joining the team. Outcome: by the end of this doc you can (a) articulate the product vision to a buyer, (b) point at the right module when someone asks 'where does X live?', (c) make architectural calls about what's overlay-customizable vs base-dev territory, and (d) reason about the governance + roadmap pressure CS Pulse is operating under."
));

// ============================================================
// SECTION 1 — Vision
// ============================================================

children.push(h1NoBreak("1. Vision — What CS Pulse Is"));
children.push(para(
  "CS Pulse is the AI-native Customer Success platform for PE-backed B2B portfolios. The bumper-sticker is 'Revenue Intelligence over generic AI' — but the underlying thesis is more specific. Three claims define the product:"
));
children.push(bullet("CS work has been undermeasured. Most CS platforms (Gainsight, Catalyst, etc.) capture activity volume — not revenue impact. CS Pulse measures the dollar consequence of every CS intervention."));
children.push(bullet("AI without local context is generic. A Claude or ChatGPT prompt over a CS dataset answers shallow questions. CS Pulse bridges generic LLM capability to the customer's local business DNA via the MCP tool surface — same model, dramatically more useful answer."));
children.push(bullet("Investment allocation is the unmet question. CRO + CFO buyers ask 'where should the next $1M of CS investment go?' — and that's the question CS Pulse is uniquely positioned to answer, because it has both the leading-indicator layer (signals + qualitative narrative) AND the trailing-indicator layer (KPI rollups), reconciled in one engine."));

children.push(h2("1.1 The two-layer indicator model (the foundational design choice)"));
children.push(para(
  "This is the most important conceptual call in CS Pulse and it's worth understanding before reading anything else. Most CS platforms have ONE health-score layer — usually a KPI rollup. CS Pulse has TWO layers, intentionally not reconciled. From session memory (product_two_layer_indicator_design.md):"
));
children.push(diagram("d1_two_layer.png"));
children.push(caption("Figure 1 — The two-layer indicator model. Leading layer (signals → context graph) flags revenue-at-risk before KPIs reflect it; trailing layer (KPI rollup) is mathematically rigorous but lagging. The gap between them is the product."));
children.push(table([2400, 4400, 2800], [
  ["Layer", "What it is", "Latency"],
  ["Leading (qualitative)", "Signal-driven revenue outcomes. Email/Slack/transcript signals → context graph OUTCOME nodes → revenue-impact attribution. Captures things that haven't yet shown up in the KPI numbers — champion loss, executive sponsor change, NPS decline, escalation patterns.", "Real-time as signals arrive"],
  ["Trailing (quantitative)", "KPI rollup health score. Pillars (5) → KPIs (9–43) → weighted aggregation → account health. The traditional CS health score, mathematically rigorous, but lags reality by ~30–90 days because it's KPI-driven.", "Monthly with KPI uploads"],
], { zebra: true }));
children.push(para(
  "The GAP between the two layers IS the product. When the leading layer shows revenue-at-risk that the trailing layer doesn't yet reflect, that's CS Pulse's value-add — early warning. When the trailing layer shows risk the leading layer doesn't flag, that's where weight calibration (Wizard C) gets re-examined."
));
children.push(para(
  "Critical operational consequence: DO NOT filter the narrative layer as a default. It looks 'noisy' compared to the KPI layer because it captures things KPIs don't — but filtering it hides the USP. Apr 20–21 demo session validated this; it's design intent from day one."
));

children.push(h2("1.2 Investment Allocation Intelligence (the positioning)"));
children.push(para(
  "Per session memory positioning_investment_allocation_intelligence.md, CS Pulse's core positioning to CFO/CRO buyers is: tells CRO/CFO where every CS dollar should go. Built CFO-first (proof — historical defensibility) and CRO-second (growth opportunity — forward expansion). Investment is scaled in Power-of-1 scenarios at 1–2.5% of ARR — not per-playbook unit costs."
));
children.push(para(
  "This framing changes how every demo flows. Don't lead with 'we score account health.' Lead with: 'every dollar of your CS budget needs an attribution chain back to revenue — and a forward projection. We give you that, in three lenses, with audit-grade provenance.'"
));

children.push(h2("1.3 Two-phase product vision"));
children.push(para("Per session memory project_vision_two_phases.md:"));
children.push(table([2400, 7200], [
  ["Phase", "What it means"],
  ["Phase 1 (today)", "Intelligence layer over existing SoR — sits on top of Salesforce, Gainsight, etc. via CSV onboarding + future SoR connectors. Customer keeps their CRM as the source of truth; CS Pulse provides intelligence + AI surface + governance. ~99% of current deployments."],
  ["Phase 2 (roadmap)", "AI-native system of record. Replace the CRM for CS workflows entirely — direct ingest from email/Slack/transcripts, native renewal pipeline, native playbook execution. Gated on customer demand + base-dev capacity. Not in active development; vision target."],
], { zebra: true }));

// ============================================================
// SECTION 2 — Three Layers of AI
// ============================================================

children.push(h1("2. The Three Layers of AI (defensible AI narrative)"));
children.push(para(
  "Per session memory positioning_three_layers_of_ai.md — CS Pulse's defensible AI narrative for AI-DD reviews. Each layer is a concrete subsystem with named technology. The win: 'AI-native CS platform, three complementary AI layers; competitors have one, none have all three.'"
));

children.push(h2("2.1 The three layers"));
children.push(diagram("d2_three_layers_ai.png"));
children.push(caption("Figure 2 — The three layers of AI in CS Pulse. Bottom-up: user/buyer hits the Generative surface (Ask AI + MCP); generative calls into the Causal layer (context graph + invariants) for trustworthy answers; causal layer leans on the Predictive layer (the 4 wizards) for statistical signal. Competitors typically have one layer; none have all three."));
children.push(table([2200, 3600, 3800], [
  ["Layer", "What it does", "Named technology"],
  ["Predictive (statistical learning)", "Forecasts NRR per account on 12mo horizon. Calibrates KPI + signal weights per tenant. Detects pattern signatures across accounts.", "Wizard B (counterfactual pattern analysis), Wizard C (KPI weight calibration), Wizard D (GLMM-calibrated predictor v3). Pre-Bayesian frequentist hierarchical model today; Bayesian variant on roadmap."],
  ["Causal (graph + invariants)", "Maintains a typed, weighted, temporal graph of signals → decisions → outcomes per account. Enforces polarity invariants (a positive signal can't cause a negative outcome). Provides the trace 'why is this account at risk' that the AI surface relies on.", "ContextNode + ContextEdge ORM tables, Wizard A (causal graph generation), 11 graph invariants validated in CI + pytest + audit CLI."],
  ["Generative (LLM-backed surfaces)", "Ask AI tool calls + natural-language summaries. Signal enrichment (LLM tagging of unknown signal subtypes). Explanation generation for forecast drivers. Prompt registry for governance.", "Anthropic Claude (primary) + OpenAI (selectable per tenant). MCP server (~52 tools), prompt registry, LLMUsageLog for cost tracking, BYOK roadmap."],
], { zebra: true }));

children.push(h2("2.2 Naming discipline"));
children.push(para(
  "NEVER call Wizards B + C 'generative AI' in technical or AI-DD contexts. They're predictive ML — statistical hierarchical models, not LLM generation. Confusing the categories has bitten us before; reviewers anchor on it and lose trust. The shorthand 'AI' in customer conversations is fine; the precise terms apply when the buyer's technical team asks."
));
children.push(bullet("Wizards A/B/C/D = Predictive (with A also being causal graph generation)."));
children.push(bullet("Ask AI, signal enrichment, narrative generation = Generative."));
children.push(bullet("Context graph + invariants = Causal."));

children.push(h2("2.3 Trust levers (V45 trust framework)"));
children.push(para("Per session memory the V45 deck enumerates trust levers used in buyer pitches. Levers #6 (self-calibrates from YOUR outcomes — Wizard C) and #7 (per-account explainability — context graph + GLMM drivers) are the strongest defensibility claims. Don't make claims the code can't back; the Apr 27 roadmap note (roadmap_wizard_c_learn_from_context_graph.md) is the prototype gap to close before AI-DD pressure mounts on lever #6."));

// ============================================================
// SECTION 3 — Module surface
// ============================================================

children.push(h1("3. Module Surface (10 modules)"));
children.push(para(
  "The platform image exposes ten top-level modules. As tech lead you'll touch all of them within your first month. This section is the map; the Technical Deep Dive (doc #3) goes into implementation per module."
));
children.push(diagram("d3_modules.png"));
children.push(caption("Figure 3 — Module surface + data flow. Yellow = customer upload; purple = wizards + predictor (the predictive core); orange = context graph (the causal layer); blue = AI chat surfaces; green = persona dashboards. Solid arrows = primary data path; dotted = subordinate / enrichment paths."));

children.push(table([2400, 4800, 2400], [
  ["Module", "Capability", "Change ownership"],
  ["predictor/", "Per-account forward NRR forecasting on 12-month horizon. Provides portfolio rollup and per-account explanation surface. GLMM-based.", "Base dev"],
  ["wizards/", "Wizard A (causal-graph generation), Wizard B (pattern + counterfactual analysis), Wizard C (KPI weight calibration), Wizard D (predictor recalibration).", "Base dev"],
  ["signal_engine/", "Qualitative-signal ingestion, deduplication, enrichment, urgency classification, alert dispatch. Three channels: CSV (default), live email forwarding, live Slack/Teams webhooks.", "FDE wires channels per tenant; engine itself is base-dev"],
  ["verticals/", "Vertical-specific KPI catalogs, pillar weights, and overlays. Default verticals: dc2_s, saas_premium. Customer overlays live here under verticals/customer{N}-{vertical}/.", "FDE owns customer overlays; base dev owns vertical modules"],
  ["mcp_server/", "MCP tool surface — ~52 @mcp.tool-decorated callables that expose the platform to Claude.ai, Ask AI, and external agents.", "Base dev owns signatures + auth"],
  ["outcome_roi_engine.py", "Historical proof and forward projection of CS ROI using Power-of-1 scaling. Three layers: historical / forward / bridge. Disclosure logic for non-repeatable historical gains.", "Base dev"],
  ["health_score_engine.py", "Account-level health score derived from KPI rollups with reference-range scoring. Loads weights from CustomerConfig → bootstrap_weights_config.json → kpi_definitions.py fallback chain.", "Base dev"],
  ["agents/", "Agent memory, tool registry, event subscribers for autonomous workflows. Memory + recall via memory_remember / memory_recall MCP tools.", "Base dev"],
  ["llm/", "LLM-backed features: Ask AI, signal enrichment, explanation generation, prompt registry, cost tracking (LLMUsageLog table + record_usage discipline).", "Base dev"],
  ["integrations/", "Third-party connectors — Salesforce, Slack, email (SendGrid inbound), webhook receivers, n8n workflow handoff.", "FDE configures per tenant; base dev owns connector code"],
], { zebra: true }));

children.push(h2("3.1 Customer-facing surfaces (what each module contributes)"));
children.push(para("Five persona dashboards plus Ask AI consume from the modules above. The lookup is roughly:"));
children.push(bullet("CRO Dashboard ← predictor/ + signal_engine/ + outcome_roi_engine.py + context graph"));
children.push(bullet("CFO Dashboard ← outcome_roi_engine.py + predictor/ + wizards/ (Wizard B for counterfactual) + context graph"));
children.push(bullet("CEO Dashboard ← predictor/ portfolio rollup + signals summary"));
children.push(bullet("VPCS Dashboard ← wizards/ + signal_engine/ + per-CSM aggregations"));
children.push(bullet("CSM Cockpit ← signal_engine/ + recommendations engine + context graph drill-down"));
children.push(bullet("Ask AI (both Claude.ai + in-product) ← mcp_server/ tool catalog"));

// ============================================================
// SECTION 4 — Multi-tenant + lifecycle model
// ============================================================

children.push(h1("4. Multi-Tenant Architecture"));

children.push(h2("4.1 The customer entity"));
children.push(para(
  "Every tenant is a Customer row in the customers table (kpi-dashboard/backend/models.py:11). Tenant isolation is enforced at every query boundary — there is no cross-tenant data leakage path by design. Every API call must resolve to a customer_id; the auth middleware (auth_middleware.py:get_current_customer_id) blocks requests that can't."
));
children.push(table([3000, 6400], [
  ["Field", "Role"],
  ["customer_id (int) / uuid (str)", "Primary key + UUID. Both work as identifiers (post UUID migration). UUID preferred in new code; integer ID still works for backwards compatibility."],
  ["vertical", "First-class vertical: dc2_s or saas_premium today. Drives KPI catalog, pillar labels, playbook archetypes."],
  ["tier", "Subscription tier — enterprise, etc. Drives entitlements."],
  ["allowed_account_ids (CustomerApiKey)", "Per-key account scoping — supports per-CSM API keys that only see their book."],
  ["profile_metadata (JSON)", "Flexible per-tenant config — sub-vertical (saas_enterprise vs saas_startup), industry vertical labels, CSM org structure."],
], { zebra: true }));

children.push(h2("4.2 The vertical layer"));
children.push(para(
  "Two first-class verticals (dc2_s, saas_premium) loaded via utils/vertical_registry.py with a DB → JSON catalog → Python fallback chain. The JSON catalog approach is ~80% complete: new verticals can be added by dropping a JSON file in config/, with no Python deploy required for KPI catalog changes."
));
children.push(para("What's verticalized — see User Perspective Guide §5.1 for the full table. Critical things the tech lead should know are first-class-per-vertical:"));
children.push(bullet("KPI catalog (verticals/{vertical}/kpi_definitions.py + config/{vertical}_kpi_catalog.json)"));
children.push(bullet("Playbook templates (vertical_config.py) — PR #26 fixed a long-running bug where SaaS tenants got DC playbooks system-wide"));
children.push(bullet("Pillar labels rendered on dashboards (PR #35 wired drill-drawer consumption)"));
children.push(bullet("Wizard D calibration — one (customer × vertical × profile × sub_model) row per active calibration"));

children.push(h2("4.3 The customer phase layer (lifecycle gating)"));
children.push(para("Customer phases drive dashboard tile visibility. See User Perspective Guide §6 for the user-side view. Architecturally:"));
children.push(bullet("Phase is COMPUTED at request time, not stored. PRE-DEPLOY / ONBOARDING / ACTIVE / MATURE derived from PlaybookExecutionV2 row count + (planned) first-PB-execution timestamp."));
children.push(bullet("Phase determines: empty-state copy, tile filtering, disclosure logic, what the persona grader expects."));
children.push(bullet("CFO Three-Lenses uses customer_phase to gate Lens C visibility. Disclosure logic in outcome_roi_engine.py uses it indirectly via the historical-ROI heuristic."));

// ============================================================
// SECTION 5 — Roadmap
// ============================================================

children.push(h1("5. Roadmap State"));
children.push(para(
  "What's shipped, what's in flight, what's deferred. As tech lead you'll need this to set customer expectations and to prioritize base-dev requests against. Sources: session memory MEMORY.md index, gtm_readiness_assessment.md, governance_15_model_unblock_criteria.md."
));

children.push(h2("5.1 Shipped (production-ready as of May 22 2026)"));
children.push(bullet("CFO Three-Lenses with full A/B/C honesty UI (PR #38 Phase 0–2, PR #43 Wizard B label fix)."));
children.push(bullet("CRO Phases 0–5 honesty UI (commit 904184fed) — metric guide, context-graph strip, pre-proof banner, ARR exposure footnote, period_meta echo, Phase 5 proof path."));
children.push(bullet("Pending Decisions Queue v1 (PR #39) — exec-altitude action list on CRO + CFO sidebars."));
children.push(bullet("Historical ROI disclosure (PR #20 backend + PR #40 UI) — auditor-grade caveat when non-repeatable gains dominate."));
children.push(bullet("Account-column ORM drift audit (PR #32) + Flask + MCP duplication-drift audit (PR #37) — both now CI gates."));
children.push(bullet("EC2 acceptance harness (commit dfae039f5) — scripts/run_acceptance_ec2.sh + ACCEPTANCE_* env knobs + persona grading orchestration."));
children.push(bullet("FDE KT versioned (PRs #41/#42) — playbook v1.2, discovery workbook, eval reports, generators."));
children.push(bullet("Predictor v3 (Wizard D-calibrated GLMM) — 4 sub-models per (customer × vertical × profile), portfolio rollup live for cust 334."));
children.push(bullet("Persona grading framework (tests/persona_grading) — 5 personas × 5–7 questions, LLM-as-judge with letter grades, ~$3–5/run."));

children.push(h2("5.2 In flight / pending"));
children.push(bullet("Real bootstrap CIs (replace ci_method: placeholder_uncalibrated) — Phase 1 task #4 in the NRR roadmap. CRO-3/4/8 + CFO-10 stay partial-credit until this lands."));
children.push(bullet("CFO-2 product question — should realized defensive ROI surface from outcome CSVs at ingest, or only from closed playbook executions over time? Carries from v3 eval reports."));
children.push(bullet("Wizard C edge-aware weight column (Tier 2 calibration) — secondary column consuming context graph trustworthy-edge count. Trigger: ≥3 customers with ≥30 LLM-enriched edges + AI-DD probe."));
children.push(bullet("Wizard C should learn from context-graph OUTCOMEs (not HealthScore) — roadmap_wizard_c_learn_from_context_graph.md. Closes V41/V44/V45 pitch claims that are currently ahead of code."));
children.push(bullet("Decision Queue write-back v2 — state transitions (approve/escalate/defer), ContextNode audit trail, notification fan-out. Conditional on customer feedback after the next round of demos."));
children.push(bullet("Bayesian Wizard D (tenant_bayes fit_type) — gated on data volume + statistical hire."));
children.push(bullet("Per-customer Anthropic API key (BYOK) — column exists in plan, 18 callers currently bypass the resolution helper. ~half-day finish; only promote out of backlog when a buyer asks."));
children.push(bullet("Cross-product uncertainty propagation — 5 user-facing point estimates (health, RaR, ROI, NRR, renewal-prob) ship without CIs today. ~1wk/surface for disclosure tier."));

children.push(h2("5.3 Governance roadmap"));
children.push(para(
  "Per project_governance_layer_apr20.md, the platform shipped 7 governance docs in April 2026: AI_GOVERNANCE_FRAMEWORK + MODEL_INVENTORY (15 models) + CHANGE_MANAGEMENT + AUDIT_TRAIL_REQUIREMENTS + DRIFT_MONITORING + GOVERNANCE_ROADMAP (beta disclosure) + SOC2/RBAC v1.1 refresh."
));
children.push(para("15-model unblock fast path (per governance_15_model_unblock_criteria.md):"));
children.push(bullet("MOD-007 prompt register — first unblock."));
children.push(bullet("MOD-002 approval gate — closes 9 of 15 by reuse."));
children.push(bullet("MOD-008 admin UI — completes the wave."));
children.push(bullet("MOD-003 (renewal probability model) + MOD-012 — hard-blocked, separate launch decision required."));

children.push(h2("5.4 Phase 2 vision (AI-native SoR)"));
children.push(para(
  "Replacing the customer's CRM-as-SoR for CS workflows. Direct ingest from email/Slack/transcripts (already exists as signal engine), native renewal pipeline (gap), native playbook execution (partial — PlaybookExecutionV2 exists, customer-self-service playbook authoring does not). Not in active development; framed as a 2-year vision."
));

// ============================================================
// SECTION 6 — Competitive positioning
// ============================================================

children.push(h1("6. Competitive Positioning"));
children.push(para(
  "Tech lead should be able to articulate why a customer would pick CS Pulse over Gainsight, Catalyst, or a roll-your-own. The competitive matrix (per session memory Session 10 ref + GTM decks) anchors on three axes."
));

children.push(h2("6.1 Three competitive axes"));
children.push(table([2400, 3600, 3600], [
  ["Axis", "What CS Pulse claims", "Where competitors fall short"],
  ["Revenue attribution", "Every CS dollar back to a specific playbook + outcome (Lens C bottom-up). Audit-traceable to Salesforce renewal records.", "Most platforms measure CSM activity volume (touches, email sends, QBR cadence). They don't roll up to attributed revenue with audit-grade provenance."],
  ["Forward forecast with CIs", "Predictor v3 — per-account 12mo NRR forecast with calibrated 90% CI bands. GLMM per (customer × vertical × profile × sub_model). Driver attribution via feature contributions.", "Most platforms ship rule-based 'churn risk score' without statistical calibration, no CI bounds, no driver decomposition."],
  ["AI surface depth", "~52 MCP tools exposing every analytical surface. Native Claude.ai integration. Persona grader regression-tests AI quality. Anti-hallucination contract enforced.", "Most platforms have a chat-bot widget that summarizes their own dashboards. They don't expose tool calls to external AI; they don't have a regression framework for AI quality."],
], { zebra: true }));

children.push(h2("6.2 Three places competitors actually win"));
children.push(bullet("Maturity / market presence: Gainsight is 10+ years deep with thousands of deployments. CS Pulse is < 1 year old in production. Buyer risk-aversion plays in their favor for very-large-enterprise deals."));
children.push(bullet("Salesforce integration depth: Gainsight Salesforce-edition is the de-facto SoR for many CS teams. CS Pulse is intelligence-layer-over-Salesforce; replacing SF as SoR is Phase 2 vision."));
children.push(bullet("Reporting templates: Gainsight has decades of pre-built reports for every CS metric anyone has ever asked for. CS Pulse takes a different bet — fewer pre-built reports, deeper AI surface."));

children.push(h2("6.3 The right way to lose a deal"));
children.push(para(
  "If a customer prioritizes 'comprehensive Salesforce-native reporting over a rich AI surface' — that's a Gainsight customer. Don't try to win it. Focus CS Pulse pitches on CRO + CFO buyers in PE-backed B2B portfolios where 'where should the next $1M of CS investment go' is the unmet question, and the answer involves forward NRR forecasting + audit-grade attribution."
));

// ============================================================
// SECTION 7 — Admin operations
// ============================================================

children.push(h1("7. Admin Operations"));
children.push(para(
  "What an internal admin (or tech lead) actually does day-to-day to operate the platform. Not a runbook — that's in the FDE Playbook §3 — but the structural view of which knobs exist and what they control."
));

children.push(h2("7.1 Feature toggles"));
children.push(para(
  "Per kpi-dashboard/backend/feature_toggles.py and CustomerConfig DB columns. Toggles are per-customer; flipping one for one tenant doesn't affect others."
));
children.push(table([2800, 3400, 3400], [
  ["Toggle", "What it controls", "Typical setting"],
  ["CONTEXT_GRAPH", "Whether ContextNode/ContextEdge are populated + queried. Master switch for the two-layer indicator model.", "ON for every new tenant (default)"],
  ["FEATURE_SIGNAL_ENGINE", "Platform-level — whether signal_engine/ API surface is registered. Gates live email/Slack/transcript ingest.", "ON at the platform level (compose); per-tenant live ingest OFF until DPA signed (see FDE Playbook §2.4)"],
  ["FEATURE_PREDICTOR_V3_UI", "Whether the React UI renders the PredictorV3Tile. False → falls back to Wizard B's older counterfactual tile.", "ON for tenants with active Wizard D calibration"],
  ["FEATURE_ASK_AI_V2", "Whether /api/executive/ask-v2 is wired. Anti-hallucination + tool-routing improvements.", "ON globally as of v2.14.7"],
  ["story_arcs, signal_edges, stakeholder_tracking, decision_lifecycle, outcome_economics, industry_benchmarks", "Per-customer sub-toggles for context-graph features. Allow gradual enablement.", "Most ON by default; story_arcs requires manifest seed data"],
], { zebra: true }));

children.push(h2("7.2 Entitlements"));
children.push(para("Per-tenant entitlement record (visible on login response) gates feature surfaces. Default enterprise tier has all true. Common entitlements:"));
children.push(bullet("dashboards, data_upload, health_scores, approval_queue, revenue_intelligence — base feature gates"));
children.push(bullet("rag_queries, copilot_integration, multi_provider — AI feature gates"));
children.push(bullet("mcp_connectors — controls whether the MCP server is reachable for this tenant"));
children.push(bullet("agent_loop, agent_memory_shared — agent feature gates (recall + write)"));
children.push(bullet("decision_matrix, playbook_triggers, signal_analyst, power_of_1 — intelligence feature gates"));
children.push(bullet("api_key_self_service — whether tenant admins can issue API keys themselves"));

children.push(h2("7.3 Weight hierarchy (Wizard C source of truth)"));
children.push(para("Three-tier resolution order. The platform always reads in this priority — DO NOT bypass."));
children.push(numbered("CustomerConfig DB columns (dc2s_pillar_weights, dc2s_kpi_weights) — Wizard C calibrated, highest priority."));
children.push(numbered("verticals/customer{N}-{vertical}/journey/config/bootstrap_weights_config.json — FDE-managed customer overlay."));
children.push(numbered("kpi_definitions.py weight_l1 / weight_l2 defaults — fallback when neither above is set."));
children.push(para(
  "All scoring paths (utils/score_calculator.py, verticals/dc2_s/api_routes.py) consume from this chain. NEVER hardcode pillar weights or KPI weights inline — always use the resolver."
));

children.push(h2("7.4 Per-customer Anthropic API key (BYOK — partial)"));
children.push(para(
  "Today every tenant uses the platform's Anthropic key; cost attribution is per-customer via the LLMUsageLog table. BYOK is partially implemented — get_anthropic_api_key(customer_id) helper exists but the CustomerConfig.anthropic_api_key_encrypted column is missing AND 18 callers bypass the helper to read env directly. Half-day finish; promote out of backlog when a buyer asks. Don't ship marketing claiming BYOK is available."
));

children.push(h2("7.5 Health-score thresholds (standardized)"));
children.push(para("Centralized in kpi-dashboard/backend/config/health_thresholds.json — single source of truth. NEVER hardcode 70 or 50."));
children.push(bullet("Critical: 0–49 (score < 50)"));
children.push(bullet("At-risk: 50–69 (50 ≤ score < 70)"));
children.push(bullet("Healthy: 70–100 (score ≥ 70)"));
children.push(para("Backend imports: utils.health_thresholds. Frontend imports: utils/healthThresholds. API: GET/PUT /api/dc2s/config/health-thresholds (Settings UI can adjust boundaries per tenant). Boundary changes propagate to every tile + every classifier function in the same request."));

// ============================================================
// SECTION 8 — Engineering principles
// ============================================================

children.push(h1("8. Engineering Principles (what the team holds itself to)"));
children.push(para(
  "Not aspirational. These are the principles that have caught real bugs in production, encoded in session memory and enforced by CI audits. Read these before opening your first PR."
));

children.push(h2("8.1 Verify model schema before writing queries"));
children.push(para(
  "MUST DO: run Model.__table__.columns.keys() OR read the model definition before writing any debug/query script. NEVER guess column names from class names. Cost of violation: 30+ minutes chasing phantom bugs (Apr 14 2026 incident — journey_data vs journey_json field name guess caused a full HealthScore-fallback tangent when the data was there all along)."
));

children.push(h2("8.2 Revert fixes built on a wrong diagnosis"));
children.push(para(
  "When you discover a fix was built on a misdiagnosis, git revert it right away. NEVER rationalize keeping dead code as a 'safety net.' It adds DB query overhead, masks future real bugs, and the commit message becomes a lie. If the problem doesn't exist, the fix shouldn't exist."
));

children.push(h2("8.3 Account-column drift audit (PR #32) — CI-enforced"));
children.push(para(
  "Code that reads acct.<col> for <col> not in the Account ORM model 500s in production. The audit walks AST attr-access; catches all three forms (acct.health_score, acct.assigned_csm, acct.is_active). 9 latent violations were drained from playbook_triggers_api.py alone when the audit first ran. Documented in FDE Playbook §3.11."
));
children.push(para("Canonical replacements:"));
children.push(bullet("acct.health_score → batched HealthScore-table join"));
children.push(bullet("acct.assigned_csm → (acct.profile_metadata or {}).get('assigned_csm')"));
children.push(bullet("acct.name / status / id / arr → account_name / account_status / account_id / revenue (real column names)"));
children.push(bullet("acct.products (no relationship) → one-shot Product.query distinct lookup"));

children.push(h2("8.4 Flask + MCP duplication-drift audit (PR #37) — CI-enforced"));
children.push(para(
  "Same logical function lives in mcp_server/*.py AND Flask route file (api_v1_routes.py, executive_dashboard_api.py, outcome_roi_api.py, playbook_recommendations_api.py). When one is fixed, the other drifts silently. Buyer demos hit either path depending on entry point. 3 real instances landed in May 2026 — B-1 (team_capacity health), PR #30 (team_capacity response shape), PR #33 (vertical routing). The audit catches signature_drift, response_key_drift, helper_drift."
));

children.push(h2("8.5 Shift-left validation"));
children.push(para(
  "Catch issues upstream, don't expect downstream to validate. Upload validates types/enums/ranges → ingest validates FK/temporal/dedup → wizards assume clean data. The Layer 1 (CSV schema) validator catches 80%+ of customer-side data issues; Layer 2 (FK + temporal cross-CSV) is deferred until a real customer hits it."
));

children.push(h2("8.6 Every LLM call site proven tracked, not assumed tracked"));
children.push(para(
  "Apr 20 2026 incident — 6 production LLM callers (including MOD-007) were silently bypassing record_usage(). $0.45 of real Anthropic spend invisible to the cost dashboard. Lesson: import / doc / comment is NOT proof; only a grep-verified matching record_usage() call is. Add a record_usage() check to every PR that adds an LLM caller."
));

children.push(h2("8.7 Governance limitations auto-spawn a CR"));
children.push(para(
  "Tier-1 model-card 'known limitations' are NOT documentation — they're pending CRs (change requests). Apr 20 incident — MOD-004 'Layer C flags but does not block' known limitation got logged not CR'd; surfaced in buyer AI-DD the next day. Treat governance limitations as actionable backlog, not as disclosure-only."
));

children.push(h2("8.8 Intuitive file naming"));
children.push(para(
  "File names should let a reader infer purpose without opening the file. build_panel.py not panel.py. Pair files with companions (build_panel.py ↔ build_panel.sql). Drop the package name inside domain folders. Established May 7 2026 with predictor/panel.py → build_panel.py rename."
));

children.push(h2("8.9 Cold-start sanity step after every rebuild"));
children.push(para(
  "Per principle_cold_start_sanity_rebuild.md — every rehydrate/rebuild MUST be followed by a 5-minute cold-start probe (register new tenant via load-driver, exercise every MCP tool end-to-end, walk all 5 dashboards). Second proof point came May 17 when bug B-1 sat latent for 6 weeks because nobody ran end-to-end after the May 12 rebuild."
));

// ============================================================
// SECTION 9 — Where to go next
// ============================================================

children.push(h1("9. Where to Go Next"));
children.push(para("You now have the strategic + structural view. Read sequence:"));
children.push(bullet("CSPulse_Technical_Deep_Dive.docx (doc #3) — implementation internals. The four wizards in depth, Predictor v3 GLMM math, context graph + invariants, signal engine pipeline, DB schema, LLM cost tracking. ~45 min read."));
children.push(bullet("CSPulse_FDE_Playbook.docx (in gtm-decks/fde-kt/) — operational + deploy. Most useful for understanding the customer-facing engagement model."));
children.push(bullet("MEMORY.md (in ~/.claude/projects/.../memory/) — session memory index. The deepest source of decision history; cross-references topic files (positioning, governance, roadmap, etc.)."));
children.push(para(
  "First practical exercise after the three KT docs: open kpi-dashboard/backend/wizards/wizard_d_predictor_calibrator.py and trace one calibration end-to-end — what trigger_wizard('d') does, what coefficients it writes to predictor_calibrations, how predictor/inference.py reads them, how they surface on the CFO dashboard's FORECAST NRR tile. That single trace gives you the full predictive-AI layer in your head."
));

children.push(new Paragraph({
  children: [new TextRun({ text: "─── End of Document 2 (Vision, Roadmap & Architecture) ───", italics: true, size: 18, color: "808080" })],
  alignment: AlignmentType.CENTER, spacing: { before: 480 },
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

const outPath = path.join(__dirname, "CSPulse_Vision_Architecture_Guide.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(outPath, buf);
  console.log(`Wrote: ${outPath} (${buf.length} bytes)`);
});
