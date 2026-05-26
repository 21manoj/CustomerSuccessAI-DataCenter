// Build CSPulse_User_Perspective_Guide.docx
// Tech-lead onboarding doc #1 — what the customer experiences end-to-end.
// Audience: incoming tech lead. Companion docs: Vision/Architecture, Technical Deep Dive.

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageBreak, Header, Footer, PageNumber, TabStopType,
  TabStopPosition, TableOfContents
} = require('docx');

// ---------- helpers (copied from FDE Playbook for consistency) ----------
const border = { style: BorderStyle.SINGLE, size: 4, color: "B8B8B8" };
const cellBorders = { top: border, bottom: border, left: border, right: border };
const headerShade = { fill: "1F3A5F", type: ShadingType.CLEAR, color: "auto" };
const altShade = { fill: "F2F2F2", type: ShadingType.CLEAR, color: "auto" };

const para = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, ...opts.run })],
  spacing: { after: 120, ...opts.spacing },
  ...opts.para,
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

const bullet = (text, level = 0) => new Paragraph({
  text, bullet: { level }, spacing: { after: 60 },
});
const numbered = (text) => new Paragraph({
  text, numbering: { reference: "default-numbering", level: 0 }, spacing: { after: 60 },
});

const code = (text) => new Paragraph({
  children: [new TextRun({ text, font: "Courier New", size: 18 })],
  shading: { fill: "F2F2F2", type: ShadingType.CLEAR },
  spacing: { before: 80, after: 80 },
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
  return new Table({
    rows: tableRows,
    width: { size: colWidths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  });
}

const children = [];

// ============================================================
// FRONT MATTER
// ============================================================

children.push(new Paragraph({
  children: [new TextRun({ text: "CS Pulse — User Perspective Lifecycle Guide", bold: true, size: 36 })],
  alignment: AlignmentType.CENTER,
  spacing: { after: 200 },
}));
children.push(new Paragraph({
  children: [new TextRun({ text: "Tech-lead onboarding · what the customer experiences end-to-end", italics: true, size: 22, color: "606060" })],
  alignment: AlignmentType.CENTER,
  spacing: { after: 360 },
}));
children.push(para(
  "This is the FIRST of three knowledge-transfer documents for an incoming CS Pulse tech lead. It walks the platform from the customer's seat — what they upload during onboarding, what they see on each persona's dashboard, how they interact with Ask AI, and how the experience shifts as the deployment matures from pre-deploy to active."
));
children.push(para(
  "Companion docs (read in order): (2) CSPulse_Vision_Architecture_Guide.docx — vision, roadmap, system architecture, admin operations. (3) CSPulse_Technical_Deep_Dive.docx — implementation internals, the four wizards, GLMM math, context graph, signal engine. Read THIS one first to understand what we're delivering; read those next to understand HOW we deliver it."
));
children.push(para(
  "All file paths in this doc are relative to the repo root. All API responses + behaviours described match the deployed image as of late May 2026 (commit eaec74db8 — Wizard B three-state labeling fix on the CRO Forward NRR tile)."
));

// ============================================================
// SECTION 1 — The customer lifecycle
// ============================================================

children.push(h1("1. The Customer Lifecycle"));
children.push(para(
  "CS Pulse models every customer through four phases. The phase isn't cosmetic — it actually drives what tiles render, what numbers populate, and what story we tell the buyer. As a tech lead you'll hear 'cold-start' and 'pre-deploy' and 'mature tenant' in conversations; this section gives you the working vocabulary."
));

children.push(h2("1.1 The four customer phases"));
children.push(table([1800, 4400, 3000], [
  ["Phase", "What it means", "What's visible to the buyer"],
  ["PRE-DEPLOY", "Customer has been provisioned in CS Pulse but has not yet uploaded outcomes / run any playbooks. No closed-loop data exists.", "Lens A (historical outcomes) shows empty state. Lens B (Wizard B counterfactual) may render if Wizard A has run on uploaded KPI + signal data, otherwise empty. Lens C (realized attribution) is empty by design. Predictor v3 forecast tile may render with wide CIs."],
  ["ONBOARDING (0–3mo)", "First three months. Some KPI history, some signals, a few playbook executions resolving but no statistically meaningful closed-loop ROI yet.", "Lens A + Lens B populated. Lens C is sparse — \"first proof points\" framing. CSM cockpit is fully usable; CFO dashboard shows leading indicators only."],
  ["ACTIVE (3–12mo)", "Steady-state. Playbook executions accumulating, attribution working, Wizard D calibrated to this tenant's GLMM.", "All three lenses populated. Row C is the primary CFO story. Forecast NRR + realized NRR both render with narrowed CIs."],
  ["MATURE (12mo+)", "Full audit trail across all three lenses. CDI (Community Domain Intelligence) inputs may apply if 5+ peer customers exist in the vertical.", "All three lenses fully populated. Long-term attribution decomposition surfaces. Trajectory tiles show 6+ months of history. Calibration audit trail available for AI-DD reviews."],
], { zebra: true }));
children.push(para(
  "The CFO dashboard's PHASE BADGE (visible at the top right of the Three Lenses panel) is the FDE's tell of where you are. If a customer is in PRE-DEPLOY and Lens C is empty, that's not a bug — it's the design. Setting customer expectations to match the phase is half the job during the first month."
));

children.push(h2("1.2 What's the same across phases"));
children.push(bullet("All five persona dashboards (CRO / CFO / CEO / VP CS / CSM) render from day one. Tiles show empty states with explanatory copy when their data isn't ready."));
children.push(bullet("Ask AI works from day one for any tool whose data is present. Try it on a fresh tenant — the experience is 'I can answer the questions you've given me data for; I can't fabricate the rest' (anti-hallucination is a hard rule in the persona grader)."));
children.push(bullet("Context graph populates from day one — every uploaded signal becomes a ContextNode; every causal inference (Wizard A) adds ContextEdges."));
children.push(bullet("MCP server is live from day one — Claude.ai can connect even before the customer's first persona-eval."));

children.push(h2("1.3 What changes as phases advance"));
children.push(bullet("ROI tiles transition from PROJECTED (Power-of-1 benchmarks) → REALIZED (PlaybookExecutionV2 sums). The CFO Three-Lenses panel makes this transition visible: Lens C populates when playbooks close."));
children.push(bullet("Wizard D recalibration moves the tenant off the CDI-seed prior and onto a tenant-specific GLMM. The calibration_id changes from a vertical-level seed to a per-tenant fit."));
children.push(bullet("Persona grader expectations rise. A new tenant grading B- on CSM (cold-start data limitations) might grade A- once 90+ days of playbook executions accumulate."));
children.push(bullet("Forecast CIs narrow. Wider CIs on day one shrink as Wizard D refits on more tenant-specific data."));

// ============================================================
// SECTION 2 — Onboarding flow
// ============================================================

children.push(h1("2. Onboarding — From Discovery to First Sanity"));
children.push(para(
  "Customer onboarding is the FDE's job, but the tech lead needs to understand the flow because it's where 80% of customer-facing bugs are caught. There's exactly one supported path — the canonical 4-CSV upload. Any other pattern is base-dev approval territory."
));

children.push(h2("2.1 Pre-flight — Discovery workbook"));
children.push(para(
  "Before any data hits the platform, the FDE runs five 30-minute discovery interviews using CSPulse_FDE_Discovery.xlsx (lives in gtm-decks/fde-kt/). One stakeholder per persona at the customer side. The workbook captures: top 5 KPIs, pillar-weight preferences, signal sources, success outcomes, current process pain. The Consolidation tab rolls all five into a config-export view that maps directly into create_customer."
));
children.push(para(
  "Why the tech lead should care: this is where customer-side mismatches surface BEFORE upload. If the discovery says 'they don't track NPS' and Wizard A then complains about a missing nps_decline signal subtype, that's a configuration problem traceable to the workbook, not a code problem."
));

children.push(h2("2.2 Provisioning"));
children.push(para("Use the admin UI's onboarding wizard, or the MCP create_customer tool if scripting. Two first-class verticals today:"));
children.push(bullet("dc2_s — data-center hardware vertical. KPIs: deployment velocity, operational stability, AI workload performance, channel/partner health, expansion readiness."));
children.push(bullet("saas_premium — SaaS B2B vertical. KPIs: product adoption, engagement, sentiment, partner, revenue."));
children.push(para(
  "Other industry labels (healthcare, financial services, etc.) flow as account firmographic data — they're NOT separate vertical modules. If a customer asks 'do you have a healthcare vertical?' the honest answer is 'we have CS-Pulse infrastructure that's vertical-aware via JSON catalogs; healthcare-specific KPIs would be a base-dev request to add as a third first-class vertical.'"
));
children.push(para("KPI tier choice: Starter 9 (B+ for cost-conscious tenants), Predictive 11 (A-, the default), Full 43 (A+ for mature CS teams that already track everything)."));

children.push(h2("2.3 The 4-CSV upload"));
children.push(para(
  "This is the only onboarding pattern we support by default. Customer prepares four CSVs from their source systems (CRM, KPI dashboards, signal channels):"
));
children.push(table([3000, 6600], [
  ["File", "What it contains"],
  ["account_details.csv (preferred) or accounts.csv", "Account records — name, products, champion contacts, contract details, firmographic data. Loader prefers account_details.csv when both are present."],
  ["kpi_measurements.csv", "Monthly KPI time-series. Schema validated at upload — wrong unit, wrong type, out-of-range values are rejected with explicit error messages."],
  ["enhanced_qualitative_signals.csv (preferred) or qualitative_signals.csv", "Signal feed — NPS scores, escalations, champion changes, executive feedback events. The enhanced_ variant carries additional columns; the loader accepts either."],
  ["outcomes.csv", "CRM renewal / churn / expansion history (typically a Salesforce export). This is what populates Lens A on the CFO Three-Lenses panel."],
], { zebra: true }));
children.push(para(
  "Upload via the admin UI or the MCP upload_csv tool. After all four are uploaded, the customer (or admin) calls process_data. This kicks off the pipeline: schema validation → DB inserts → Wizard A (causal graph) → Wizard B (counterfactual NRR) → Qdrant signal indexing (if QDRANT_URL is set). Wizards C and D do NOT auto-fire — they're explicit admin triggers (see §3 in the Technical Deep Dive doc)."
));

children.push(h2("2.4 First sanity check"));
children.push(para("After process_data, the FDE runs scripts/run_acceptance_ec2.sh as a deterministic gate. It hits CFO + CRO + VPCS HTTP suites against the live host and asserts known invariants. Common first-day issues:"));
children.push(bullet("Revenue Protected = $0 on Lens C: post-load attribution didn't run. Trigger via the admin endpoint."));
children.push(bullet("NRR forecast 0% or stuck at the prior tenant's value: Wizard D wasn't refit. Run trigger_wizard('d') manually."));
children.push(bullet("Ask AI returns \"I don't know\" to dashboard questions: the relevant MCP tool wasn't wired into the customer's enabled set. Check entitlements."));
children.push(bullet("Dashboard tile shows context-graph $ but CRO and CFO numbers don't match: this is the PR #38 parity regression — re-run scripts/verify_cfo_phase1_ec2.py to localize."));

children.push(h2("2.5 First persona-eval"));
children.push(para(
  "Once §2.4 is green, run the persona grader for all 5 personas at --shots 3. Expect at least one persona to grade below the customer's bar on day one — usually CSM (no closed-loop revenue attribution yet) or CFO (no realized defensive ROI until playbooks resolve). The discovery workbook answers are the calibration starting point — adjust weights in bootstrap_weights_config.json, re-run, repeat. Target: all 5 personas at the customer's bar (typically B+ or higher) within the first week."
));
children.push(para("This is the closed-loop calibration mechanism. The grader's specific_concerns field names exactly what's missing — usually a weight or a signal-channel issue, not code."));

// ============================================================
// SECTION 3 — Five-persona dashboard tour
// ============================================================

children.push(h1("3. The Five Personas — Dashboard Tour"));
children.push(para(
  "CS Pulse ships five persona-specific dashboards. Each is its own React component with its own data-fetch path. A buyer working from any one persona should be able to answer the questions that matter to THEIR role without leaving the dashboard. As a tech lead you'll touch all five within your first month — this section is the map."
));

children.push(h2("3.1 CRO — Revenue Intelligence (the headline persona)"));
children.push(para("Route: /cro-dashboard. Component: CRODashboard.tsx. Audience: head of revenue, head of CS, CRO at a $50M–$5B ARR B2B SaaS."));
children.push(h3("Top-of-fold layout"));
children.push(bullet("REVENUE INTELLIGENCE header with period selector (Q3 / Q4 / TTM tabs — PR #38 + commit 904184fed). Tab switching is a pure UI transform on cached data; no new API call fires per tab change (only a cro_period_change analytics event)."));
children.push(bullet("HOW TO READ CRO METRICS — expandable metric guide added by 904184fed."));
children.push(bullet("REVENUE INTELLIGENCE (CONTEXT GRAPH) strip — 'Confirmed Risk · 97 OUTCOME nodes with $ · same engine as CFO Overview.' Three confirmed-revenue tiles: Confirmed Revenue at Risk, Confirmed Revenue Protected, Expansion Pipeline (Confirmed)."));
children.push(bullet("REVENUE AT RISK / REVENUE PROTECTED / EXPANSION PIPELINE — the legacy main tiles, each with a Confirmed badge after the 0–5 honesty rework."));

children.push(h3("Mid-fold — Predictor v3 tile"));
children.push(para(
  "<PredictorV3Tile> renders below the fold. It shows Top Expansion Opportunities + Top At-Risk Accounts with per-account 90% CI bands from Wizard D. Sample rows from cust 334: Polaris Cloud (+$1.52M expansion, 41.9% P(event), 12mo horizon), Antares Holdings (+$1.46M, 39.2%), etc. Hover the warning icon to see calibration_id provenance."
));

children.push(h3("Right-sidebar — Forward NRR tile"));
children.push(para(
  "Three-state truthful labeling (PR #44, May 22): Natural-arc baseline (88.09%) → Today with CS Pulse (88.49%) → If interventions succeed (109.26%). All three are Wizard B outputs. The leftmost is what NRR would be without any CS Pulse intervention; the middle is current state; the rightmost is upside if all recommended interventions succeed. This replaces an earlier 2-column layout that mislabeled the with-CS value as 'Without CS Pulse.'"
));
children.push(para(
  "The Pending Decisions Queue (PR #39, May 17) sits above Power of 1 in the right sidebar — 5 items awaiting CRO decision, sorted by revenue at stake, headlines framed account-altitude ('Decide intervention for X')."
));

children.push(h3("Below-fold — Trajectory + Waterfall"));
children.push(bullet("NRR Trajectory · all accounts — T+30 / T+60 / T+90 projection with a 5% churn floor on every account. Different from the Forward NRR tile (at-risk only, no floor) — same data, different attribution windows."));
children.push(bullet("Revenue Waterfall — per-account exposure → expected loss → residual risk → attributed save, with playbook cost + projected ROI per row."));

children.push(h2("3.2 CFO — Investment Intelligence (the auditor persona)"));
children.push(para("Route: /cfo-dashboard. Component: CFODashboard.tsx. Audience: CFO, head of FP&A, board-prep finance partner."));

children.push(h3("Top-of-fold"));
children.push(bullet("INVESTMENT INTELLIGENCE header + Portfolio Pulse summary (16 Healthy / 9 At Risk / 5 Critical for cust 334)."));
children.push(bullet("HOW TO READ CFO METRICS — expandable, added by PR #38 Phase 0–2 honesty work."));
children.push(bullet("REVENUE INTELLIGENCE (CONTEXT GRAPH) strip — same engine as CRO, evidence-weighted. Confirmed Revenue at Risk ($39.9M for cust 334), Protected ($32.5M), Expansion ($24.5M). 'View 8 sample outcomes →' links into the OUTCOME nodes for audit."));
children.push(bullet("4-tile row — Total ARR / CS Investment / Realized NRR — TTM (Wizard B counterfactual) / Forecast NRR — Next 12mo (Predictor v3, Wizard D-calibrated)."));

children.push(h3("PAST — THREE LENSES (the auditor's panel)"));
children.push(para("Below the fold sits the signature CFO surface — three rows answering the same question through three lenses:"));
children.push(bullet("Lens A — Historical Performance (Pre-CS-Pulse). Uploaded OUTCOME data. Historical NRR TTM, ARR churned/expanded/contracted, with raw event counts. Sources from outcomes.csv via context graph OUTCOME nodes — not GL-reconciled."));
children.push(bullet("Lens B — Counterfactual (Wizard B). 'What would NRR have been if CS Pulse had been running through this period?' Subtitle ends with 'not directly comparable to Lens A's gross-outcome NRR' (PR #43). Four tiles: Hypothetical NRR (88.49%, vs 88.1% natural-arc baseline), Counterfactual NRR Lift (+0.4pp, ≈$701K), ARR Protected (Saved Accounts) ($17M, NOT the NRR-lift dollars), Accounts Could've Been Saved (3)."));
children.push(bullet("Lens C — Realized — Actual CS Pulse Attribution. Bottom-up sum of PlaybookExecutionV2.revenue_protected across closed playbooks. Attributed Revenue, Realized ROI, Playbooks Resolved, CS Investment Closed. Drill-down via Playbook ROI Proof table below."));

children.push(h3("Modeled Cost of Inaction"));
children.push(para(
  "Below Lens C — projection of revenue impact if no CS Pulse intervention. Health-weighted churn probability × account ARR. The Modeled Cost of Inaction is DISTINCT from Confirmed Revenue at Risk: the latter is evidence-weighted (only ARR with explicit OUTCOME-node backing); the former is a model-derived churn projection."
));

children.push(h3("Outcome ROI dashboard (linked from CFO)"));
children.push(para(
  "Route: /outcome-roi. Component: OutcomeROIDashboard.tsx. Renders historical (PROVEN) vs forward (PROJECTED) panels side by side. After PR #40 the PROVEN panel includes an amber disclosure block when the 6-month ROI reflects non-repeatable one-time gains (heuristic: ROI > 500% AND avg improvement > 2× forward steady-state). The disclosure: 'Includes one-time onboarding gains' with detail explaining the buyer should treat the forward projection as the repeatable number."
));

children.push(h2("3.3 CEO — Executive Scorecard"));
children.push(para("Route: /ceo-dashboard. Component: CEODashboard.tsx. Audience: CEO at the customer (or PE-portfolio CEO at the parent level if portfolio mode is on)."));
children.push(h3("Layout"));
children.push(bullet("Single-tenant mode (when only one customer exists under a portfolio_id) — Executive Scorecard headline with portfolio NRR, total ARR, account-status breakdown."));
children.push(bullet("Portfolio mode (PE-fund deployment with multiple customers under one portfolio_id) — Company Comparison Table with portfolio rollup. cust 334 today is single-tenant so this surface collapses; PR #31 (May 17) shipped the Executive Scorecard alternative for that case."));
children.push(bullet("Top 3 Strategic Moves tile (PR #31) — Conservative / Recommended / Stretch scenarios derived from Power-of-1 scaling. The CEO altitude of the action queue."));
children.push(bullet("Quarter selector with live computation (was hardcoded 'Q1 2026' until 904184fed)."));

children.push(h2("3.4 VP CS — Operations Intelligence"));
children.push(para("Route: /vpcs-dashboard. Component: VPCSDashboard.tsx. Audience: VP of Customer Success — the operational counterpart to the CFO."));
children.push(bullet("Team Capacity gauge — hours-based utilization (resource_pool / utilization_pct / bottlenecks / recommendation). Came online via PR #30 (May 17) — earlier the tile fell back to a client-side account-count derived gauge."));
children.push(bullet("CSM Scorecards — per-CSM accounts_rescued / accounts_lost / health_delta / playbook_success_rate. Counts ARE auditable: critical→healthy = rescue, healthy→critical = lost; explicit lifecycle definitions."));
children.push(bullet("Per-CSM ranking with composite score."));
children.push(bullet("Top Performers panel (PR fed7d7834, May 22)."));
children.push(bullet("Renewal Pipeline widget — accounts with renewal_date < 90 days, with days_until + forecast_category from CRM data."));

children.push(h2("3.5 CSM — Daily Cockpit"));
children.push(para("Route: /csm or /saas-dashboard/csm. Component: CSMCockpit.tsx. Audience: individual CSM. This is the most-used surface in the product — designed for a 2-minute morning briefing."));
children.push(bullet("FOCUS MODE — sequential task queue across all CSM's accounts, prioritised by impact × time-decay."));
children.push(bullet("KANBAN BOARD — FIRE (critical) / THIS WEEK / OPPORTUNITY columns. Drag-drop persistence via @dnd-kit (kanban_column PATCH stored in profile_metadata)."));
children.push(bullet("Account-drill drawer — pillar scores, signals timeline, recommendations panel, stakeholder map, support tickets, journey timeline."));
children.push(bullet("Playbook recommendations — drill-drawer pulls vertical-aware recs (PR #26 fixed routing; PR #33 wired UI consumption). Sample for SaaS Premium tenant: activation-blitz, voc-sprint, renewal-safeguard."));
children.push(bullet("Email draft modal — pre-filled outbound for an at-risk account. Champion contact pulled from account.profile_metadata.champion (only populated if the customer included it in account_details.csv)."));

// ============================================================
// SECTION 4 — Ask AI (Claude.ai + in-product)
// ============================================================

children.push(h1("4. Ask AI — Two Surfaces, One Tool Catalog"));
children.push(para(
  "Ask AI is the conversational layer over the same MCP tool catalog the dashboards use. Two consumption surfaces — Claude.ai with the MCP connector, or the in-product floating Ask AI portal. Both are gated by entitlements; both share the same anti-hallucination discipline (the persona grader is the regression test)."
));

children.push(h2("4.1 The MCP tool surface (~52 @mcp.tool decorations)"));
children.push(para(
  "All tools live in kpi-dashboard/backend/mcp_server/cs_pulse_*.py. New tools are base-dev only — they go through the API contract review. The categories (curated, not auto-generated — grep mcp_server/ for @mcp.tool to count live decorators before quoting a number to a buyer):"
));
children.push(h3("Customer + onboarding"));
children.push(para("create_customer, list_customers, clone_customer, complete_onboarding, configure_customer_kpis, enable_features, get_csv_templates, upload_csv, download_customer_csv, process_data, list_verticals, get_platform_instructions."));
children.push(h3("Health + accounts"));
children.push(para("get_account_health, get_at_risk_accounts, get_account_journey_timeline, get_account_nrr_forecast, get_health_score_history, get_kpi_catalog, list_accounts, get_crm_account_data, get_stakeholder_map, get_support_tickets."));
children.push(h3("Predictor + portfolio (Wizard D / GLMM-calibrated)"));
children.push(para("get_nrr_forecast, get_portfolio_nrr_forecast_v3, get_top_at_risk_accounts_v3, get_top_expansion_opportunities_v3, get_revenue_at_risk, get_portfolio_cross_customer_comparison, get_portfolio_roi_summary."));
children.push(h3("ROI + economics"));
children.push(para("calculate_power_of_1, get_outcome_roi_story, get_playbook_economics."));
children.push(h3("Playbooks"));
children.push(para("get_playbook_recommendations, execute_playbook, close_playbook, get_playbook_success_metrics, generate_playbook_from_description."));
children.push(h3("CSM + team"));
children.push(para("get_csm_daily_actions, get_csm_ranking, get_csm_scorecard, get_team_capacity, get_customer_feedback."));
children.push(h3("Causal graph + signals"));
children.push(para("get_causal_chain, get_context_graph_mermaid, get_graph_summary, search_signals, submit_signal."));
children.push(h3("Wizards + admin"));
children.push(para("trigger_wizard, get_llm_cost_summary, partner_portal."));

children.push(h2("4.2 Sample Ask AI questions — by persona"));
children.push(para("These are paraphrases of the actual questions in tests/persona_grading/fixtures/{persona}.py. The grader is calibrated against responses to these — your AI surface must answer them well to pass acceptance."));

children.push(h3("CRO"));
children.push(bullet("\"What's our revenue at risk this quarter, by account?\""));
children.push(bullet("\"Which 3 accounts are the top expansion opportunities?\""));
children.push(bullet("\"Show me NRR forecast with confidence interval for Polaris Cloud — and why.\""));
children.push(bullet("\"When NRR moved last quarter, which accounts drove it?\""));
children.push(bullet("\"Compare this quarter's risk vs last quarter.\""));

children.push(h3("CFO"));
children.push(bullet("\"Give me an auditor-acceptable ROI number with methodology.\""));
children.push(bullet("\"How does CS investment scale at 2× ARR? What's the unit economics rationale?\""));
children.push(bullet("\"Trace every dollar of attributed revenue to a specific playbook.\""));
children.push(bullet("\"Where does Power of 1 lift come from? Show me the assumptions and bounds.\""));
children.push(bullet("\"Distinguish realized vs forecasted dollars in last 6 months.\""));

children.push(h3("CEO"));
children.push(bullet("\"What's the portfolio headline number — NRR, ARR, health? Is it reconcile-able?\""));
children.push(bullet("\"Which company in the portfolio is healthiest? Weakest?\""));
children.push(bullet("\"What 3 strategic moves matter most this quarter?\""));
children.push(bullet("\"Where should the next $1M go — capital-allocation guidance.\""));
children.push(bullet("\"Generate a board-ready summary — one page.\""));

children.push(h3("VP CS"));
children.push(bullet("\"Team capacity utilization — hours used vs available, per CSM.\""));
children.push(bullet("\"Playbook completion + success rate across the team.\""));
children.push(bullet("\"Per-CSM ranking — who's outperforming, who's behind?\""));
children.push(bullet("\"For the next at-risk account on my list, what's the root cause and recommended playbook?\""));
children.push(bullet("\"Weekly business review prep — give me a snapshot for Monday's team meeting.\""));

children.push(h3("CSM"));
children.push(bullet("\"My book — how many accounts, total ARR, breakdown.\""));
children.push(bullet("\"What's the top 10 prioritized action queue for today?\""));
children.push(bullet("\"Why is account X at risk? Drill into pillar scores + journey timeline.\""));
children.push(bullet("\"Recommend the next playbook for account Y.\""));
children.push(bullet("\"Draft an outbound email to the champion at account Z.\""));

children.push(h2("4.3 The Anti-Hallucination Contract"));
children.push(para(
  "Every persona fixture has a must_cite list AND an anti_hallucination list. The grader docks heavily for fabricated account IDs, made-up dollar amounts, or made-up calibration provenance. As a tech lead, the discipline you'll enforce: AI surface must say 'I don't have data on that' rather than guessing. Three places this discipline lives in code:"
));
children.push(bullet("ask_ai_endpoint.py — the in-product surface, with explicit refusal templates."));
children.push(bullet("tests/persona_grading/grader.py — the LLM-as-judge with anti-hallucination checks per question."));
children.push(bullet("MCP tool docstrings — tightly scoped descriptions that tell the AI 'use THIS tool for THIS question, not THAT one.'"));

// ============================================================
// SECTION 5 — Multi-vertical
// ============================================================

children.push(h1("5. Multiple Verticals — How They Coexist"));
children.push(para(
  "Today the platform supports two first-class verticals: dc2_s (data center) and saas_premium. A vertical is more than a label — it's a tuple of (KPI catalog, pillar weights, signal subtypes, playbook archetypes, dashboard pillar labels). Understanding the vertical model is essential before promising a new vertical to a customer."
));

children.push(h2("5.1 What's verticalized vs shared"));
children.push(table([3000, 3400, 3200], [
  ["Concern", "Shared (one definition for all)", "Per-vertical (different per vertical)"],
  ["Account schema", "Account, HealthScore, ContextNode, PlaybookExecutionV2 ORM tables — shared", "—"],
  ["KPI catalog", "—", "verticals/dc2_s/kpi_definitions.py vs verticals/saas_premium equivalent. Each ~9–43 KPIs depending on tier."],
  ["Pillar names + weights", "—", "5 pillars per vertical; weights load via bootstrap_weights_config.json"],
  ["Signal taxonomy", "Polarity invariants are shared", "Subtype catalog is per-vertical (signal channels.json overlay layered on top)"],
  ["Playbook archetypes", "—", "verticals/dc2_s/vertical_config.py (PB-DC-01 etc.) vs verticals/saas_premium/vertical_config.py (activation-blitz, voc-sprint, renewal-safeguard etc.). PR #26 fixed routing — pre-fix, SaaS tenants got DC playbooks system-wide."],
  ["Dashboard pillar labels", "—", "verticals/{vertical}/pillar_labels.json — PR #35 wired the drill-drawer consumption"],
  ["Predictor v3 calibration", "GLMM model class is shared", "Per (customer × vertical × profile × sub_model) — Wizard D fits one row per combination"],
  ["MCP tool surface", "All 52 tools available to every vertical", "Some tools internally route via vertical (e.g. get_playbook_recommendations uses customer's vertical to pick the catalog)"],
], { zebra: true }));

children.push(h2("5.2 Adding a new vertical"));
children.push(para("This is base-dev territory — NOT FDE overlay work. To add a 3rd first-class vertical (e.g. healthcare_payer), base dev must:"));
children.push(numbered("Create verticals/healthcare_payer/ directory: kpi_definitions.py + vertical_config.py + pillar_labels.json + JSON catalog file."));
children.push(numbered("Add vertical alias mapping in utils/vertical_registry.py (e.g. 'healthcare' → 'healthcare_payer')."));
children.push(numbered("Add playbook templates: vertical-specific playbook_id namespace + cost model."));
children.push(numbered("Calibrate Wizard D for the new vertical — initially via CDI seed (cross-customer prior); refined to tenant_glmm once data accumulates."));
children.push(numbered("Add a test fixture per persona — tests/persona_grading/fixtures/ entries that exercise the vertical's KPIs."));
children.push(numbered("Run the Flask + MCP duplication-drift audit (scripts/audit_flask_mcp_drift.py) — new vertical-aware code paths need to be added to the audit's allowlist or grandfathered explicitly."));

children.push(h2("5.3 What a customer sees with multi-vertical"));
children.push(para(
  "Each customer is assigned ONE vertical at provisioning (customer.vertical column). The dashboard reads this and renders the vertical's KPI catalog + pillar labels accordingly. A customer doesn't 'see' multiple verticals — they see their own vertical's catalog. A PE-portfolio CEO viewing multiple customers does see the portfolio aggregate (CEO dashboard portfolio mode), but each customer's contribution is computed in its own vertical context."
));

// ============================================================
// SECTION 6 — Customer phases & visibility logic
// ============================================================

children.push(h1("6. Phase-Driven Visibility Logic"));
children.push(para(
  "The customer phase from §1.1 directly controls which tiles render and which empty states display. As a tech lead, when a customer asks 'why is this tile empty?' the phase is usually the answer."
));

children.push(h2("6.1 Phase heuristic (current implementation)"));
children.push(para("Defined in CFODashboard.tsx + executive_dashboard_api.py. Driven by PlaybookExecutionV2 row count:"));
children.push(table([2200, 3600, 4000], [
  ["Phase", "Trigger (per current heuristic)", "What it gates"],
  ["pre_deploy", "0 PlaybookExecutionV2 rows for the tenant", "Lens C empty state on CFO Three Lenses; no playbook-attribution numbers anywhere; pending-decisions queue empty"],
  ["onboarding", "1–5 PlaybookExecutionV2 rows", "Lens C sparse; 'first proof points' framing"],
  ["active", "6+ PlaybookExecutionV2 rows", "Lens C is the primary CFO story"],
  ["mature", "12+ months since first playbook execution", "Trajectory tiles show 12mo+ history; CDI peer-cohort comparison available if cohort exists"],
], { zebra: true }));
children.push(para(
  "There's a known refinement target: phase should also consider days_since_first_pb_execution (not just count) — see customer_phase computation in CFODashboard.tsx ~line 2003. Listed in v3 eval reports as a follow-up."
));

children.push(h2("6.2 Examples of phase-gated UI"));
children.push(bullet("CFO Three Lenses — Lens C visibility (the proof row) is controlled by customer_phase. PRE-DEPLOY shows empty-state copy 'CS Pulse hasn't attributed closed-playbook revenue yet.' ACTIVE shows the full bottom-up sum."));
children.push(bullet("Pending Decisions Queue — empty for PRE-DEPLOY (no playbooks in flight); populates as accounts hit at-risk thresholds OR playbooks enter in_progress."));
children.push(bullet("Outcome ROI disclosure — only fires during ACTIVE/MATURE when historical ROI > 500% AND improvement > 2× forward steady-state. PRE-DEPLOY tenants don't trigger it because they have no historical ROI yet."));
children.push(bullet("CSM scorecard rescued/lost counts — definitionally zero for PRE-DEPLOY (no critical→healthy transitions in window). VPCS dashboard could add 'why zero' hover for this case (open follow-up)."));

// ============================================================
// SECTION 7 — Handover artifacts
// ============================================================

children.push(h1("7. Handover Artifacts"));
children.push(para(
  "Every customer engagement ends with a handover packet from the FDE to the customer-success team. As tech lead you'll review these for completeness. The packet is more important than the dashboard — it's how the customer's deployment becomes maintainable."
));
children.push(table([3200, 6400], [
  ["Artifact", "What it captures"],
  ["Discovery workbook (filled-in)", "Five-persona pain points, top-5 KPIs, pillar weight preferences, signal sources, success outcomes, current process pain. Lives in the engagement folder, not in git."],
  ["Persona-eval golden files (JSON)", "Latest persona grader output — per-persona question-by-question grades, rationale, anti-hallucination flags. Regression baseline for every future image upgrade."],
  ["CHANGELOG.md (in the customer overlay)", "Every overlay change made during the engagement — weight tweaks, signal channel adjustments, custom playbooks. One-line entries with dates."],
  ["'How to read this dashboard' notes (per persona)", "One-pager per persona cut from the GTM decks. Customer-facing — explains what each tile means in the customer's vocabulary."],
  ["Verify-script baseline outputs", "scripts/run_acceptance_ec2.sh output saved at handover time. Future acceptance runs diff against this baseline."],
  ["Deployment summary 1-pager", "gtm-decks/fde-kt/CSPulse_FDE_Deployment_Summary.md or equivalent — the operational ritual for the customer-success team."],
], { zebra: true }));

// ============================================================
// CLOSING
// ============================================================

children.push(h1("8. Where to Go Next"));
children.push(para("You've now seen what CS Pulse delivers from the customer's seat. Next two reads:"));
children.push(bullet("CSPulse_Vision_Architecture_Guide.docx (companion doc #2) — the strategic + structural view. Vision, three layers of AI, module surface, governance roadmap, admin operations. ~30 min read."));
children.push(bullet("CSPulse_Technical_Deep_Dive.docx (companion doc #3) — implementation internals. The four wizards, Predictor v3 GLMM math, context graph internals, signal engine pipeline, DB schema. ~45 min read."));
children.push(para("After both, your first practical exercise: run scripts/run_acceptance_ec2.sh against cust 334, then run the persona grader for one persona at --shots 3, then read tests/persona_grading/grader.py to understand the discipline that's enforced. That sequence will give you the closed-loop intuition for how customer-facing quality is maintained."));

children.push(new Paragraph({
  children: [new TextRun({ text: "─── End of Document 1 (User Perspective Lifecycle Guide) ───", italics: true, size: 18, color: "808080" })],
  alignment: AlignmentType.CENTER, spacing: { before: 480 },
}));

// ============================================================
// BUILD
// ============================================================

const doc = new Document({
  numbering: {
    config: [{
      reference: "default-numbering",
      levels: [{
        level: 0,
        format: LevelFormat.DECIMAL,
        text: "%1.",
        alignment: AlignmentType.START,
        style: { paragraph: { indent: { left: 360, hanging: 240 } } },
      }],
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

const outPath = path.join(__dirname, "CSPulse_User_Perspective_Guide.docx");
Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(outPath, buf);
  console.log(`Wrote: ${outPath} (${buf.length} bytes)`);
});
