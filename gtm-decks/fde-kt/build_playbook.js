// Build CSPulse_FDE_Playbook.docx
// Internal knowledge transfer doc for Forward Deployment Engineers (FDEs).
// Redaction line: full module/capability surface, NO math / NO prompts / NO coefficients.

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageBreak, Header, Footer, PageNumber, TabStopType,
  TabStopPosition, TableOfContents
} = require('docx');

// ---------- helpers ----------
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
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text })],
  spacing: { before: 360, after: 200 },
  pageBreakBefore: true,
});

const h1NoBreak = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text })],
  spacing: { before: 360, after: 200 },
});

const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [new TextRun({ text })],
  spacing: { before: 240, after: 140 },
});

const h3 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3,
  children: [new TextRun({ text })],
  spacing: { before: 180, after: 100 },
});

const bullet = (text, level = 0) => new Paragraph({
  numbering: { reference: "bullets", level },
  children: [new TextRun({ text })],
  spacing: { after: 80 },
});

const bulletRich = (runs, level = 0) => new Paragraph({
  numbering: { reference: "bullets", level },
  children: runs,
  spacing: { after: 80 },
});

const numbered = (text) => new Paragraph({
  numbering: { reference: "numbers", level: 0 },
  children: [new TextRun({ text })],
  spacing: { after: 80 },
});

const code = (text) => new Paragraph({
  children: [new TextRun({ text, font: "Courier New", size: 20 })],
  spacing: { after: 80 },
  shading: { fill: "F5F5F5", type: ShadingType.CLEAR, color: "auto" },
  indent: { left: 360 },
});

// Simple horizontal rule via paragraph border
const rule = () => new Paragraph({
  children: [new TextRun({ text: "" })],
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 1 } },
  spacing: { after: 200 },
});

// Table helper. cols = array of column widths (DXA); rows = array of arrays of cell text.
// First row is treated as header.
function table(cols, rows, opts = {}) {
  const totalWidth = cols.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: cols,
    rows: rows.map((cells, rIdx) => new TableRow({
      tableHeader: rIdx === 0,
      children: cells.map((text, cIdx) => new TableCell({
        borders: cellBorders,
        width: { size: cols[cIdx], type: WidthType.DXA },
        shading: rIdx === 0 ? headerShade : (opts.zebra && rIdx % 2 === 0 ? altShade : undefined),
        margins: { top: 100, bottom: 100, left: 140, right: 140 },
        children: [new Paragraph({
          children: [new TextRun({
            text: text || "",
            bold: rIdx === 0,
            color: rIdx === 0 ? "FFFFFF" : "000000",
            size: rIdx === 0 ? 20 : 20,
          })],
        })],
      })),
    })),
  });
}

// ---------- DOCUMENT CONTENT ----------

const children = [];

// Cover
children.push(new Paragraph({
  children: [new TextRun({ text: "CS Pulse", bold: true, size: 56, color: "1F3A5F" })],
  spacing: { before: 2400, after: 240 },
  alignment: AlignmentType.CENTER,
}));
children.push(new Paragraph({
  children: [new TextRun({ text: "Forward Deployment Engineer Playbook", bold: true, size: 44, color: "1F3A5F" })],
  spacing: { after: 240 },
  alignment: AlignmentType.CENTER,
}));
children.push(new Paragraph({
  children: [new TextRun({ text: "Internal — for contracted FDEs only. NDA covered.", italics: true, size: 22, color: "666666" })],
  spacing: { after: 600 },
  alignment: AlignmentType.CENTER,
}));
children.push(new Paragraph({
  children: [new TextRun({ text: "Version 1.0", size: 22, color: "666666" })],
  alignment: AlignmentType.CENTER,
}));
children.push(new Paragraph({
  children: [new TextRun({ text: "May 2026", size: 22, color: "666666" })],
  spacing: { after: 1200 },
  alignment: AlignmentType.CENTER,
}));

// TOC
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text: "Table of Contents" })],
  spacing: { after: 200 },
}));
children.push(new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }));

// ---------- Section 1: Scope & boundary ----------
children.push(h1("1. Scope and Boundary"));
children.push(para(
  "You are a Forward Deployment Engineer (FDE) working with a CS Pulse customer. Your job is to make the platform fit the customer — not to rebuild the platform. This section defines exactly what you own, what the base development team owns, and where the line sits."
));

children.push(h2("1.1 What you own"));
children.push(bullet("Customer onboarding: running the discovery workbook, capturing KPI selections, weights, signal sources, and stakeholder data."));
children.push(bullet("Customer-specific configuration: writing per-tenant config that lives in the customer overlay folder."));
children.push(bullet("Customer-specific overlays: new playbook templates, custom KPI definitions for a vertical you are tailoring, custom signal channel wiring."));
children.push(bullet("Persona evals: running the 5-persona eval matrix, reading the scoreboard, calibrating weights and signal sensitivity until each persona crosses the pass threshold."));
children.push(bullet("Customer-facing deliverables: tutorials, deployment guides, scorecards, and weekly business reviews adapted from the GTM templates."));
children.push(bullet("First-line incident response on customer environments: docker restart, log triage, magic-link reissue, sanity-diff checks."));

children.push(h2("1.2 What the base development team owns"));
children.push(bullet("Core algorithms: the math inside the Predictor, the Wizards, the health-score engine, the outcome-ROI engine."));
children.push(bullet("Prompt text and prompt registry contents for every LLM-backed module."));
children.push(bullet("MCP tool signatures and contract changes — adding, removing, or changing the shape of any MCP tool."));
children.push(bullet("Database schema: tables, columns, indexes, and any migration that touches them."));
children.push(bullet("Authentication, RBAC, governance controls, model cards, and the audit-trail layer."));
children.push(bullet("Image build pipeline and the ECR push path."));

children.push(h2("1.3 The line — stay in lane vs. cross the line"));
children.push(table([3120, 3120, 3120], [
  ["Action", "FDE", "Base dev"],
  ["Add a new KPI to a customer overlay", "Yes", ""],
  ["Edit weights on an existing KPI per customer", "Yes", ""],
  ["Add a new playbook template for one customer", "Yes", ""],
  ["Wire a customer-specific Slack channel to signal_engine", "Yes", ""],
  ["Tune the per-persona eval thresholds for a customer", "Yes", ""],
  ["Change the math inside the Predictor", "", "Yes"],
  ["Change a prompt sent to Claude", "", "Yes"],
  ["Add a new MCP tool", "", "Yes"],
  ["Change a database column or add an index", "", "Yes"],
  ["Add a new vertical (e.g. fintech)", "Draft only", "Owns merge"],
  ["Adjust governance flags or model-card content", "", "Yes"],
], { zebra: true }));

children.push(para(""));
children.push(para(
  "If you are unsure, the default is: file a coordination ticket and wait. The cost of a 24-hour delay is small. The cost of a customer-facing math change with no review can be a buyer escalation.",
  { run: { italics: true } }
));

// ---------- Section 2: Module + capability surface ----------
children.push(h1("2. Module and Capability Surface"));
children.push(para(
  "The platform image exposes ten top-level modules. This section names each module and the capability it provides. It does not document the internals — that is intentional, and you should not need them to do customer work."
));

children.push(table([2400, 4800, 2160], [
  ["Module", "Capability", "Change ownership"],
  ["predictor/", "Per-account forward NRR forecasting on a 12-month horizon. Provides portfolio rollup and per-account explanation surface.", "Base dev"],
  ["wizards/", "Wizard A (causal-graph generation), Wizard B (pattern + counterfactual analysis), Wizard C (KPI weight calibration), Wizard D (predictor recalibration).", "Base dev"],
  ["signal_engine/", "Qualitative-signal ingestion, deduplication, enrichment, urgency classification, alert dispatch.", "FDE wires channels"],
  ["verticals/", "Vertical-specific KPI catalogs, pillar weights, and overlays. Default verticals: DC2_S (data center hardware), SaaS Premium, Healthcare Provider.", "FDE owns overlays"],
  ["mcp_server/", "The MCP tool surface — 51 tools that expose the platform to Claude, Ask AI, and external agents.", "Base dev owns signatures"],
  ["outcome_roi_engine.py", "Historical proof and forward projection of Customer Success ROI using Power-of-1 scaling.", "Base dev"],
  ["health_score_engine.py", "Account-level health score derived from KPI rollups with reference-range scoring.", "Base dev"],
  ["agents/", "Agent memory, tool registry, event subscribers for autonomous workflows.", "Base dev"],
  ["llm/", "LLM-backed features: Ask AI, signal enrichment, explanation generation, prompt registry.", "Base dev"],
  ["integrations/", "Third-party connectors (Salesforce, Slack, email, webhook).", "FDE configures, base dev owns connector code"],
], { zebra: true }));

children.push(h2("2.1 What a customer sees vs. what you touch"));
children.push(para(
  "A customer interacts with five dashboards (CRO, CFO, CEO, VP CS, CSM) and Ask AI. Every number on those dashboards comes from one of the modules above. Your customer-facing work is almost always one of three things: a wrong number, a missing number, or a weight that does not match the customer's reality. The fix is almost always in the customer overlay, the discovery workbook, or a weight in CustomerConfig — not in the module itself."
));

children.push(h2("2.2 Capability terms — what they mean for customer conversations"));
children.push(table([2400, 7200], [
  ["Term", "What to tell the customer"],
  ["Pillar", "A grouping of related KPIs (e.g. Deployment Velocity, Operational Stability). 5 pillars total. Each pillar rolls into account health."],
  ["KPI", "A single measured number a customer reports each month. Each KPI sits inside one pillar and has a weight."],
  ["Signal", "A qualitative event — a Slack message, an email, a transcript snippet, a CSM note. Signals enrich KPI-based health with context."],
  ["Predictor", "The forward NRR forecast. Tells you where the portfolio will land in 12 months if nothing changes."],
  ["Wizards", "Background workers that derive structure from raw inputs (causal graphs, patterns, weight calibration, predictor calibration)."],
  ["Power of 1", "A unit-economics tool that translates one percentage point of NRR improvement into dollars at the customer's ARR."],
  ["NRR", "Net Revenue Retention — the canonical CS health metric. Realized (trailing), Forecast (forward), Historical (raw)."],
], { zebra: true }));

children.push(h2("2.3 Executive Decision Queue (CRO + CFO right sidebar)"));
children.push(para(
  "Added May 18, 2026 in response to customer feedback after the v2 eval walkthrough. The right-sidebar area next to the Context Graph on the CRO and CFO dashboards was empty; a buyer asked for a 'what needs my attention' surface. This is the first executive-altitude pending-action list in the product."
));
children.push(para(
  "The queue is a unified ranked list of at most five items pulled from three existing sources: in-flight playbooks awaiting continuation/spend decisions (PlaybookExecutionV2 where status = in_progress); at-risk accounts without an active playbook (a launch-or-escalate decision); and open expansion opportunities from the context graph (ContextNode where revenue_impact_type = expansion). No new tables, no new ingestion path."
));
children.push(para(
  "The CRO and CFO consume the same data with different framing. CRO sorts by revenue at stake and frames items as 'Decide intervention for X' / 'Staff expansion on X' — account-altitude decisions. CFO sorts by dollar spend and frames the same items as 'Approve continued spend on X' / 'Authorise budget to protect X' — investment-altitude decisions. Same source, different lens."
));
children.push(para(
  "v1 is read-only. The follow-up — write-back v2 (approve / escalate / defer state transitions plus a ContextNode audit trail and notification fan-out) — is conditional on customer feedback after the next demo. Do not promise write-back to the customer until the design is agreed with base dev."
));

children.push(h3("FDE responsibilities for the Decision Queue"));
children.push(bullet("If a customer asks where the queue is on VP CS or CSM dashboards: VPCS has the Action Queue rollup, CSM has the Kanban plus daily-actions. The Decision Queue is exec-altitude on purpose. Do not duplicate it down to operational personas without base-dev approval."));
children.push(bullet("If the panel renders 'Could not load — API 404' during a demo: the deploy has not picked up this code yet. Re-run rehydrate-ec2-ecr.sh with PLATFORM_TAG re-pinned to :latest, same runbook as the May 17 deploy."));
children.push(bullet("If a customer requests new sources in the queue (e.g. a churn-imminent renewal, a CRM stage flip): treat as a base-dev request — the queue's data contract should not drift per-customer."));
children.push(bullet("Never modify the persona sort or headline framing in a customer overlay. The persona split (revenue-at-stake for CRO, dollar-spend for CFO) is a product decision, not a configuration knob."));

children.push(h2("2.4 Signal path — CSV default vs. live signal engine"));
children.push(para(
  "Qualitative signals reach the platform through one of two channels. Most pilots run Channel 1 only. Channel 2 (live ingest) is opt-in per tenant after DPA + admin enablement."
));
children.push(table([1800, 4200, 3600], [
  ["Channel", "What it is", "Default state"],
  ["1 — CSV", "qualitative_signals.csv or enhanced_qualitative_signals.csv shipped as part of the 4-CSV onboarding (see §7.3). Signals land directly in the DB + context graph during process_data.", "ON. The default onboarding path."],
  ["2 — Live ingest", "Email forwarding (SendGrid inbound), Slack/Teams webhooks (signal_engine/slack_events.py, signal_engine/ingest_api.py), transcript uploads, MCP submit_signal. Worker enriches + writes QualitativeSignal + context graph + fires the proactive scan.", "OFF per tenant until DPA + admin enablement. Platform-level FEATURE_SIGNAL_ENGINE=true is typically already set in compose/EC2 — this just gates the API surface, not per-tenant ingest."],
], { zebra: true }));
children.push(para("FDE decision tree:"));
children.push(bullet("Did the customer supply qualitative_signals.csv (or enhanced_) in the 4-CSV? → Leave live ingest OFF for pilot. Verify process_data loaded the rows. signal_analyst will use health-score deltas plus the CSV-derived signals."));
children.push(bullet("Customer wants live email / Slack / transcript ingest? → Confirm DPA is signed. Enable the per-tenant feature toggle. Wire the channels you need (email forwarder, Slack webhook, etc.). Configure verticals/customer{N}-{vertical}/config/signal_channels.json. Confirm the worker is running. Use the MCP submit_signal tool for a smoke test before pointing live channels at it."));
children.push(bullet("Customer wants BOTH (CSV historical + live going forward)? → Common for established tenants. Land the CSV first, run process_data, then enable live ingest. Watch for collision dedup — two channels feeding the same signal should fuse via signal_engine/collision.py, not double-count."));
children.push(para(
  "Signal engine modules you should NOT edit in an overlay: enrichment.py, fusion.py, urgency.py, collision.py. They are the shared signal-processing pipeline. If a customer needs a bespoke enrichment rule, that is a base-dev request."
));

children.push(h2("2.5 Playbook execution model — choose one spine per customer"));
children.push(para(
  "Playbooks have two halves: the catalog (what playbooks exist) and the execution spine (how they actually run). Four different mechanisms touch playbooks today; the FDE picks ONE execution spine per customer and documents it in the engagement notes."
));
children.push(table([2000, 4800, 3200], [
  ["Mechanism", "What it does", "Who edits"],
  ["Catalog (UI definitions)", "kpi-dashboard/src/lib/playbooks.ts — built-in playbook cards rendered in the CSM kanban + recommendation panels (e.g. PB-01 Activation Blitz, PB-02 VoC Sprint, PB-04 Renewal Safeguard).", "Base dev. Do NOT edit in a customer overlay."],
  ["Per-tenant customizations", "customer_playbooks DB table, managed via /api/playbooks/library + /api/playbooks/* in customer_playbook_api.py. Per-tenant variants, custom playbooks, parameter overrides.", "FDE via admin UI or MCP — this is where tenant-specific playbook tailoring lives."],
  ["Claude skills (.md)", "kpi-dashboard/backend/skills/*.md — multi-step playbook runbooks for Claude.ai / Ask AI. One ships today: pb-champion-recovery.md. Used for power-user paths where the playbook is mostly conversational analysis.", "FDE can author new .md skills with base-dev sign-off."],
  ["n8n workflows", "External orchestration. n8n-workflows/templates/playbook-actions/ has Slack alert + Jira issue templates. Triggered via integration_api / action_interface_api webhooks; callbacks update PlaybookExecutionV2.", "FDE designs the n8n graph; base dev owns the callback contract."],
], { zebra: true }));
children.push(para(
  "Execution spine — pick ONE per customer (you can mix later, but start with one):"
));
children.push(bullet("(A) Platform-only. CSM clicks 'Launch' in the kanban → MCP execute_playbook → PlaybookExecutionV2 row → CSM logs progress → close_playbook → realized ROI snapshot. Simplest. Best when the customer is using CS Pulse as the system of record for CS work."));
children.push(bullet("(B) n8n. execute_playbook fires a webhook → n8n graph runs external steps (Slack messages, Jira ticket creation, sheet updates, etc.) → callback to /api/.../execution updates PlaybookExecutionV2 with the outcome. Best when the customer already has automation in n8n / Zapier / etc. and wants CS Pulse to be the trigger and the system of record but not the actor."));
children.push(bullet("(C) Claude skill. The playbook is documented as a .md file that Claude.ai (with MCP) reads and walks through with the user. Best for advisory playbooks (champion recovery analysis) where the value is in the prompted workflow more than in side-effects."));
children.push(para(
  "Hard rules: (1) Advisory playbooks (CSM recommendations, ROI story narration) are platform + Ask AI tools — not 'playbook execution' in the (A)/(B)/(C) sense. (2) The admin UI does NOT support customer-self-service playbook authoring today. Do not promise it. (3) Mapping playbook_id → n8n URL per customer is not fully shipped — confirm with base dev before promising the (B) spine in production."
));

children.push(h2("2.6 Knowledge base (RAG) — Qdrant signal index + KPI RAG APIs"));
children.push(para(
  "The platform has retrieval surfaces that the FDE playbook v1.0 omitted. They are not modules in §2's table — they're spread across the codebase and serve different jobs."
));
children.push(table([2400, 4800, 2400], [
  ["Surface", "Purpose", "When it runs"],
  ["Qdrant signal index", "Semantic search over qualitative signals. SignalVectorStore (utils/qdrant_signal_search.py) embeds and stores; signal_engine/enrichment.py and utils/signal_analyst.py read it. Powers the search_signals MCP tool.", "On every signal write when QDRANT_URL + QDRANT_API_KEY are set on EC2. If env vars are missing the system runs without semantic search and falls back to keyword matching."],
  ["direct_rag_api", "Legacy 'working RAG' path — KPI + account knowledge base, rebuild on CSV upload events.", "Registered as a blueprint; rebuild fires from enhanced_upload_api after material data changes."],
  ["enhanced_rag_* (temporal / openai / qdrant variants)", "Newer experimental RAG paths — temporal context, OpenAI embeddings, Qdrant-backed. Admin/upload flows; not on the critical path for all tenants.", "Registered blueprints; on-demand."],
  ["governance_rag_api", "Governance doc search (policies, model cards, AI-DD responses).", "Optional blueprint."],
], { zebra: true }));
children.push(para("What RAG is FOR (and what it isn't):"));
children.push(bullet("RAG is for: semantic signal lookup (search_signals), legacy product/KPI Q&A in Ask AI fallback paths."));
children.push(bullet("RAG is NOT for: CFO/CRO dashboard tile numbers. Those are SQL + context graph, not retrieval. If a tile is wrong, do not look at Qdrant — look at the underlying API call's data path."));
children.push(bullet("Persona grading (§5.3) tests tool use, not RAG retrieval. A persona grade of A- doesn't say anything about whether the Qdrant index is healthy."));
children.push(para("FDE responsibilities around RAG:"));
children.push(bullet("Confirm QDRANT_URL + QDRANT_API_KEY on EC2 if the customer's overlay expects semantic search. Without them, search_signals will keyword-match only."));
children.push(bullet("After a material data change (signals CSV refresh, new signal batch), trigger a rebuild via enhanced_upload_api or by re-running process_data so the index reflects new content."));
children.push(bullet("Regression-test the KB with load-driver scenario 2b (50-account RAG queries) before customer acceptance. The HTTP verify scripts (§5.6) do not cover RAG."));

// ---------- Section 3: Docker image lifecycle ----------
children.push(h1("3. Docker Image Lifecycle"));
children.push(para(
  "The platform ships as a single Docker image plus a load-driver image. You will pull, run, and occasionally rebuild. You will not change the build pipeline."
));

children.push(h2("3.1 Pulling the image"));
children.push(para("Authenticate against ECR using the credentials your engagement lead provides:"));
children.push(code("aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ECR-host>"));
children.push(para("Pull the latest tagged image:"));
children.push(code("docker pull <ECR-host>/cspulse-platform:latest"));

children.push(h2("3.2 Local development loop"));
children.push(para("Run a local stack with the customer's data mounted as a read-only volume:"));
children.push(code("docker compose -f docker-compose.cspulse.yml up -d"));
children.push(para(
  "The compose file brings up postgres, the platform, and the load-driver. Volume mounts make customer overlay files visible to the running container, but the Flask backend does NOT auto-reload on Python changes; you typically need to restart the cs-pulse service after editing overlay code. React dev server (when run separately, not in compose) does hot-reload on .tsx changes. Treat 'no restart needed' as the exception, not the rule."
));

children.push(h2("3.3 Deploying back to the customer environment"));
children.push(para(
  "Two scripts, two purposes. Pick deliberately. Do not docker-cp files into a running container — that pattern has burned us before."
));
children.push(table([3000, 5400, 2400], [
  ["Script", "When to use", "What it does"],
  ["./scripts/deploy-ec2-git-pull.sh", "Day-to-day. You want EC2 running the latest main, bit-for-bit, no PLATFORM_TAG indirection.", "Pulls main on the EC2 host, rebuilds the image locally on EC2, recreates containers. Slower (~5–10 min) but the image always matches main HEAD."],
  ["./scripts/rehydrate-ec2-ecr.sh <INSTANCE_ID>", "Image was already built by CI and pushed to ECR; you want to deploy that specific tag.", "Pulls from ECR using local AWS creds, recreates containers. Fast (~1–2 min). HONORS the PLATFORM_TAG env var on EC2 — see §3.6 about the promotion gap."],
], { zebra: true }));
children.push(para(
  "Both scripts are idempotent and self-healing: they repair a missing env file, reissue a stale magic-link, and write SESSION_COOKIE_SECURE=false if the customer is on direct-HTTP. If the bundle hash doesn't change after a rehydrate, you hit the PLATFORM_TAG gap (§3.6) — switch to the git-pull script or re-pin the tag."
));

children.push(h2("3.4 Rolling back"));
children.push(para("Every promoted tag stays in ECR. To roll back, flip the PLATFORM_TAG environment variable on the EC2 host and re-run the rehydrate script. Recovery time is under one minute. Do not delete prior tags from ECR — that is your only safety net."));

children.push(h2("3.5 Common gotchas"));
children.push(bullet("Magic-link login expires in 15 minutes and is single-use. If a customer demo runs long, reissue from the container logs (look for the MAGIC LINK block on stdout). Never put raw tokens in the database."));
children.push(bullet("Cookie loss after EC2 stop / start: SESSION_COOKIE_SECURE must be false when the customer is on direct HTTP. The rehydrate script auto-sets this on a fresh EC2."));
children.push(bullet("Frontend bundle hash will change on every rebuild — this is expected. Only flag a diff if the *numbers* on the dashboard changed."));
children.push(bullet("After any image upgrade, refit Wizard D for existing tenants. Old calibration coefficients become stale relative to new feature vectors."));

children.push(h2("3.6 PLATFORM_TAG promotion — the biggest deploy footgun"));
children.push(para(
  "rehydrate-ec2-ecr.sh pulls from ECR, but it does NOT promote a new image. The EC2 host's ~/cspulse/.env file has PLATFORM_TAG pinned to a specific tag (e.g. phase1-2026-05-12.8-clean-from-main). After CI pushes a fresh :latest, rehydrate runs cleanly — but the cs-pulse container stays on the pinned tag. Your new code is in ECR; it just isn't running."
));
children.push(para("Two fix paths:"));
children.push(bullet("Quick (per-deploy): on the EC2 host, edit ~/cspulse/.env so PLATFORM_TAG=latest, then re-run rehydrate. The cs-pulse service force-recreates onto the freshly-pulled image."));
children.push(bullet("Durable (per release): promote the new build to the pinned tag in ECR. The .env stays pointing at the pinned tag; every rehydrate from that point pulls the new image."));
children.push(para(
  "How to detect the gap: after rehydrate, hit the root URL and look for the frontend bundle hash (main.<sha>.js). If the hash is unchanged from the prior deploy, your new code is not running. The bundle hash is the cheapest tell — cheaper than running a verify script."
));
children.push(code("curl -s http://<EC2_IP>/ | grep -oE 'main\\.[a-f0-9]+\\.js' | head -1"));

children.push(h2("3.7 Post-rehydrate cold-start sanity check (mandatory)"));
children.push(para(
  "Every rehydrate must be followed by a 5-minute cold-start probe. Two separate incidents in May 2026 proved this: bug B-1 (team_capacity AttributeError) sat latent for 6 weeks because nobody exercised MCP tools end-to-end after a clean-from-main rebuild. The cost of skipping this step is a customer demo failure on a basic call."
));
children.push(para("The recipe:"));
children.push(bullet("(a) Confirm the bundle hash changed. If it did not, you are on the old image — see §3.6."));
children.push(bullet("(b) Register a new test tenant via load-driver --register. Watch for HTTP 4xx in post-validation."));
children.push(bullet("(c) Call list_customers, get_at_risk_accounts, get_csm_daily_actions, and get_portfolio_nrr_forecast_v3 via MCP for the new tenant. Any 500 means a model/schema drift slipped through."));
children.push(bullet("(d) Open all 5 persona dashboards in the browser, walk top-of-fold, and compare against the prior verify-script baseline. A tile that flips from a number to '$0' or shows 'Failed to fetch' is a regression."));
children.push(para(
  "Bundled verify scripts (run them; do not re-derive them) — see §5.6 for the full inventory. Today's set covers CFO (verify_cfo_phase1_ec2.py for Phase 1 only, verify_cfo_phases_ec2.py for Phases 0–5), CRO (verify_cro_phases_ec2.py), and VPCS (verify_vpcs_phases_ec2.py). The sanity_check_cust333.py script is a numeric-snapshot harness for cust 333, NOT a persona-eval matrix — it does not exercise the persona grader. When you ship a new persona-facing PR, add a sibling verify script in the same shape (login → hit endpoints → assert known invariants → exit non-zero on regression)."
));

children.push(h2("3.8 CI concurrency cancellation (the multi-merge pattern)"));
children.push(para(
  "The cspulse-ecr-build-push workflow has concurrency.cancel-in-progress=true. If two PRs are merged into main within ~15 seconds of each other, the older build is killed mid-flight and the newer one becomes the only run. End state is correct (the surviving run's image contains all prior commits), but the cancelled run is noise. Do not panic when you see a 'cancelled' run on a SHA that did land — verify by inspecting the newer run's SHA against main HEAD."
));
children.push(para(
  "When merging multiple PRs in a session: aim for one merge at a time, wait for the CI run to actually start (~10 seconds), and only then merge the next. Or merge all in a batch and watch only the latest run. Either is fine; just do not chase cancelled runs."
));

children.push(h2("3.9 EC2 unreachable during rehydrate (HTTP 000)"));
children.push(para(
  "While docker-compose recreates the cs-pulse service, the HTTP listener drops for 30-90 seconds. Curl returns HTTP 000 (connection refused) during that window. This is normal. Do not start tearing things down."
));
children.push(para("When to actually worry:"));
children.push(bullet("More than 5 minutes of HTTP 000 with no rehydrate in progress → check the cs-pulse container logs for a crash loop. Common cause: a missing env var (see §3.10) or a failed migration on a model mismatch (see §3.11)."));
children.push(bullet("HTTP 502 / 504 from CloudFront → origin reachable but slow. Check container CPU and DB connection pool."));
children.push(bullet("HTTP 200 but bundle hash matches the prior deploy → §3.6 (PLATFORM_TAG gap), not a connectivity issue."));

children.push(h2("3.10 MCP server auth failures on an apparently-healthy deploy"));
children.push(para(
  "May 17 incident: HTTP transport accepted Bearer tokens and returned 200 on health checks, but every MCP tool call returned 'Invalid or revoked API key'. Root cause: ~/cspulse/.env on EC2 did not have a MCP_SERVER_API_KEY=... line. docker-compose expanded ${MCP_SERVER_API_KEY} to an empty string, so server-side validate_server_key() returned False for any incoming token. This took 5 days to diagnose."
));
children.push(para("Diagnostic recipe (run BEFORE blaming the client config):"));
children.push(bullet("From the EC2 host: grep -c MCP_SERVER_API_KEY ~/cspulse/.env — must be ≥1."));
children.push(bullet("From any client: try list_customers via MCP. If it returns 'Invalid or revoked API key' on an otherwise-healthy deploy, the server env is the culprit, NOT the client token."));
children.push(bullet("Fix: append MCP_SERVER_API_KEY=<canonical-server-key> to ~/cspulse/.env, then docker compose up -d --no-deps --force-recreate cs-pulse."));
children.push(para(
  "More broadly: 'HTTP 401 with structured error' from auth_middleware fires BEFORE Flask routing matches a path. A 401 on an unauthenticated probe is NOT proof that the route exists. Always re-probe with valid credentials to distinguish auth vs. routing failures."
));

children.push(h2("3.11 Schema drift across image versions"));
children.push(para(
  "When code on main outpaces the deployed image's DB schema (i.e. models.py expects a column the DB lacks), API responses will surface psycopg2.errors.UndefinedColumn. The image bootstrap runs Alembic migrations automatically, so this should not happen on a clean deploy. It DOES happen when:"
));
children.push(bullet("Migrations are skipped (CI build failed mid-bootstrap; container starts on old schema)."));
children.push(bullet("Local dev runs against a production-vintage docker-compose DB that hasn't been migrated."));
children.push(bullet("A clone of the docker postgres volume from a prior image is mounted into a newer container."));
children.push(para(
  "Defensive pattern in the codebase: ContextNode/HealthScore queries are wrapped in try/except in the high-traffic endpoints, so a missing column degrades the panel rather than collapsing the response. When you write a new endpoint that reads from these models, mirror that pattern — see executive_dashboard_api.py line 567 (cro_dashboard signal-counts) and line 2284 (pending-decisions queue) for the canonical shape."
));

children.push(h2("3.12 gh CLI + worktree friction during merge"));
children.push(para(
  "gh pr merge --squash --delete-branch tries to checkout main locally after the merge succeeds on GitHub. If main is checked out in another worktree (common when you're working in agent-isolated worktrees), the local-cleanup step fails with 'fatal: main is already used by worktree at ...'. The merge itself completed on GitHub; only the local branch deletion failed."
));
children.push(para("Manual cleanup when this happens:"));
children.push(code("gh api -X DELETE repos/<owner>/<repo>/git/refs/heads/<branch-name>"));
children.push(para(
  "Same pattern if the source branch is in another worktree — the local branch delete fails. Detach HEAD with 'git checkout --detach' or switch to a different branch before retrying 'git branch -D'."
));

// ---------- Section 4: Building / enhancing modules via Claude Code ----------
children.push(h1("4. Building and Enhancing Modules with Claude Code"));
children.push(para(
  "Most of your module work runs through Claude Code. This section is the contract. Follow it and your work merges. Break it and your PR will bounce."
));

children.push(h2("4.1 Where customer-specific code lives"));
children.push(para("Every customer gets a dedicated overlay folder:"));
children.push(code("verticals/customer{N}-{vertical}/"));
children.push(para("Inside that folder you will find:"));
children.push(bullet("config/bootstrap_weights_config.json — pillar weights (L2) and KPI weights (L1) for this customer."));
children.push(bullet("config/playbook_overlays.json — customer-specific playbook templates."));
children.push(bullet("config/signal_channels.json — Slack channels, email aliases, transcript sources."));
children.push(bullet("data/ — the customer's mounted CSV directory."));
children.push(bullet("journey/ — generated context graph snapshots."));

children.push(h2("4.2 The branch and PR pattern"));
children.push(numbered("Create a branch named customer{N}-{short-description} (e.g. customer428-add-slack-channel)."));
children.push(numbered("Run Claude Code against the overlay folder only. Do not let it edit anything outside verticals/customer{N}-{vertical}/ unless you have explicit base-dev sign-off."));
children.push(numbered("Run the persona-eval matrix locally (Section 5)."));
children.push(numbered("Commit with the customer ID in the subject line: feat(cust428): wire #cs-acme Slack into signal_engine."));
children.push(numbered("Open a PR against main. Tag the customer engagement lead and the base dev on-call."));

children.push(h2("4.3 Hard rules — non-negotiable"));
children.push(bullet("Do not edit kpi_definitions.py. KPI catalog edits go through base dev. Customer-specific KPI selections live in the overlay, not in the canonical catalog."));
children.push(bullet("Do not edit prompts. Every LLM call uses a prompt registered in llm/prompts/. If a customer needs a different tone, file a base-dev request."));
children.push(bullet("Do not bypass record_usage(). Every LLM call must go through the centralized usage tracker. There have been incidents where new callers shipped without it and $0.45 of real spend went invisible. Grep-verify before you ship."));
children.push(bullet("Do not edit the math in the Predictor, Wizards, or scoring engines. Coefficients are calibrated, not authored. If a number looks wrong, the answer is almost always re-running Wizard C or Wizard D — not patching the formula."));
children.push(bullet("Do not add a new MCP tool. Use existing tools. If you genuinely need a new one, file a base-dev ticket with the use case."));

children.push(h2("4.4 Tests and eval gates"));
children.push(para("What CI runs on every PR (gate — must pass to merge):"));
children.push(bullet("A narrow pytest subset — score calculator, account-column ORM audit (PR #32), Flask/MCP duplication-drift audit (PR #37). NOT the full suite."));
children.push(bullet("Frontend TypeScript compile via the Docker build (catches type drift that pytest misses)."));
children.push(para("What CI does NOT run automatically (opt-in — your responsibility before customer acceptance):"));
children.push(bullet("Persona grading (tests/persona_grading) — costs $3–5 per run. Opt in via PERSONA_GRADING_ENABLED=1 pytest flag, or run --shots 3 locally before tagging a release. See §5.3."));
children.push(bullet("HTTP verify scripts (scripts/verify_*.py) — run these post-rehydrate, not at PR time. See §5.6."));
children.push(bullet("Load-driver E2E (load-driver/manifests + process_data + Wizard D refit) — manual on demo tenants."));
children.push(para("What every PR must include (manual discipline — not enforced by CI):"));
children.push(bullet("A diff of the verify-script output (or the persona-grader JSON) for any persona-facing change."));
children.push(bullet("A one-line entry in the customer's CHANGELOG.md inside their overlay folder."));
children.push(bullet("If the change touches Flask + MCP siblings, run scripts/audit_flask_mcp_drift.py locally before pushing — the audit catches drift but the message is easier to act on locally than in the CI logs."));

// ---------- Section 5: Persona-eval framework ----------
children.push(h1("5. Persona-Eval Framework"));
children.push(para(
  "A platform that works for a CRO can fail a CSM. The eval matrix is how you prove the customer's deployment lands for every persona — not just the loudest one in the room. There are two parallel instruments today; you need both, for different purposes."
));

children.push(h2("5.1 Two instruments — what they cover"));
children.push(table([2400, 3600, 3600], [
  ["Instrument", "What it tests", "When to run"],
  ["HTTP verify scripts (scripts/verify_*.py)", "Dashboard tile shapes, API payloads, source labels, period transforms. Deterministic — no LLM in the loop.", "After every rehydrate. Run-to-completion in <60s per script."],
  ["LLM-as-judge persona grading (tests/persona_grading)", "Ask-AI response quality against a 15-yr-veteran-of-the-persona grader. Captures tone, citation discipline, anti-hallucination.", "Before customer acceptance, after image upgrades, when calibrating overlays."],
], { zebra: true }));
children.push(para(
  "The verify scripts prove the deploy didn't break what was working. The persona grader proves the AI surface still answers correctly. A green verify run with a B+ persona grade is the floor; an A- across all 5 personas is the customer-acceptance bar."
));

children.push(h2("5.2 The persona grading rubric (what the grader actually scores)"));
children.push(para(
  "Five personas, 5–7 canonical questions each (~30 total across the matrix — see kpi-dashboard/backend/tests/persona_grading/fixtures/{persona}.py for the exact list). Each question has an explicit rubric the grader is shown:"
));
children.push(bullet("must_cite — specific facts that must appear (e.g. 'specific dollar amount', 'specific account name')."));
children.push(bullet("must_call_tools — Ask-AI tools the system should have invoked to answer (e.g. get_revenue_at_risk, get_top_expansion_opportunities_v3)."));
children.push(bullet("tone_check — stylistic requirement (e.g. 'leads with $ first', 'frames as decision not analysis')."));
children.push(bullet("anti_hallucination — things the response must NOT do (e.g. 'no fabricated account_ids', 'no made-up calibration_id')."));
children.push(para(
  "The grader is a Claude Sonnet call role-playing as a 15-year-experienced version of the persona (5-yr for CSM). It returns a letter grade (A, A-, B+, B, B-, C+, C, C-, D+, D, F) plus a numeric (~4.0 scale) and free-text rationale. No grade inflation — the grader is prompted to be harsh."
));

children.push(h2("5.3 Running the grader"));
children.push(para(
  "From inside the cspulse-platform container (so TOOL_DEFINITIONS and execute_tool are importable), full run for one customer:"
));
children.push(code(
  "DATABASE_URL=postgresql://.../cs_pulse \\\n  ANTHROPIC_API_KEY=sk-ant-... \\\n  python3 -m tests.persona_grading.runner \\\n    --customer 334 \\\n    --output /app/scripts/datasets/persona_grades_$(date +%Y%m%d).json"
));
children.push(para("Useful flags:"));
children.push(bullet("--personas cro,cfo — comma-separated subset (default: all 5)."));
children.push(bullet("--shots 3 — re-run each question N times and report best/median/worst grade. Defaults to 1. Use 3 when calibrating overlays so a single bad LLM roll doesn't drive a bogus retry."));
children.push(bullet("--model claude-sonnet-4-20250514 — override the grader model. Keep this stable across runs for a customer so grades are comparable over time."));

children.push(h2("5.4 Cost + cadence"));
children.push(para(
  "~$0.10–$0.15 per question (one Ask-AI tool-use loop + one grader call). A full 30-question run is ≈$3–5 at default --shots=1; ≈$9–15 at --shots=3. Cheap enough to run on every deploy. Track the cumulative line in the customer's CHANGELOG.md so spend stays predictable."
));

children.push(h2("5.5 Calibration loop"));
children.push(para("When a persona's average grade slips below the customer's bar, the fix loop is:"));
children.push(numbered("Look at the JSON output. The grader's rationale + specific_concerns fields name exactly what was missing or hallucinated."));
children.push(numbered("Map to a root cause — usually one of: wrong KPI weight in bootstrap_weights_config.json, missing signal channel in the customer overlay, stale Wizard C calibration, or a playbook template that doesn't fit the customer's vertical."));
children.push(numbered("Make the smallest possible overlay change. Most regressions are weight or signal-channel issues, not code."));
children.push(numbered("Re-run with --shots 3 on the affected persona only. The JSON diff between runs tells you whether the change moved the needle or rolled the LLM."));
children.push(numbered("Cap at 5 calibration cycles. If you cannot reach the bar in 5, file a base-dev ticket — the issue is deeper than a weight."));

children.push(h2("5.6 HTTP verify scripts — the deterministic gate"));
children.push(para(
  "Before grading, every deploy runs the HTTP verify scripts. These are deterministic — same inputs, same outputs — so they pin invariants (right tile, right number shape, right source label, right period transform) without an LLM in the loop. Run each script post-rehydrate; they exit non-zero on regression."
));
children.push(table([3600, 6000], [
  ["Script", "What it pins"],
  ["scripts/verify_executive_phases_ec2.py", "Env-driven multi-suite runner. --suite all|cfo|cro|vpcs|cfo-phase1. Reads CS_PULSE_BASE_URL + creds from scripts/.env.acceptance. This is the script run_acceptance_ec2.sh (§5.7) calls under the hood — use this directly when you need to localize a failure."],
  ["scripts/verify_cfo_phases_ec2.py", "Single-PR-style CFO Phases 0–5 script: source labels, context-graph parity with CRO, period_meta echo, ARR exposure, proof-data tile. Predates the env-driven runner — kept for narrow re-runs."],
  ["scripts/verify_cfo_phase1_ec2.py", "Narrower CFO Phase 1 subset (context-graph $ parity only). Useful when iterating on just Phase 1 changes."],
  ["scripts/verify_cro_phases_ec2.py", "CRO Phases 0–5 single-PR script: metric guide, context-graph strip, pre-proof banner, ARR exposure footnote, period_meta, Phase 5 proof path."],
  ["scripts/verify_vpcs_phases_ec2.py", "VPCS dashboard: capacity tile, top performers, scorecard auditability."],
  ["scripts/sanity_check_cust333.py", "Numeric snapshot harness for cust 333 (legacy). API + 2 Ask-AI probes. NOT a persona matrix — use only as a pre/post deploy delta check on numeric tiles."],
], { zebra: true }));
children.push(para(
  "Pick verify_executive_phases_ec2.py for routine acceptance (or just call run_acceptance_ec2.sh in §5.7, which wraps it). The per-PR scripts (verify_cfo_phases_ec2.py etc.) are kept for surgical re-runs when you want to bisect a specific suite without booting the full harness."
));
children.push(para(
  "Pattern for new persona-facing PRs: extend scripts/ec2_acceptance/checks.py with the new invariants and add a new --suite name in verify_executive_phases_ec2.py. Do NOT add another standalone verify_*.py — the per-PR scripts predate the env-driven runner and should not multiply."
));

children.push(h2("5.7 Acceptance harness — one-command post-deploy"));
children.push(para(
  "scripts/run_acceptance_ec2.sh is the canonical 'step 7' post-deploy harness. It runs the HTTP suites and, optionally, persona grading inside the platform container. Use this instead of running verify scripts one at a time."
));
children.push(para("Quick start:"));
children.push(code(
  "cp scripts/.env.acceptance.example scripts/.env.acceptance\n# edit CS_PULSE_BASE_URL, credentials, ANTHROPIC_API_KEY\n./scripts/run_acceptance_ec2.sh"
));
children.push(para(
  "The wrapper sources scripts/.env.acceptance (or whatever ACCEPTANCE_ENV_FILE points to), then orchestrates two stages: (1) HTTP acceptance via scripts/verify_executive_phases_ec2.py (env-driven, --suite-aware — runs CFO/CRO/VPCS suites against the live host); (2) optional persona grading via docker exec into the platform container."
));
children.push(para("Environment knobs (see scripts/.env.acceptance.example for the full list):"));
children.push(table([2800, 2000, 4400], [
  ["Variable", "Default", "Purpose"],
  ["CS_PULSE_BASE_URL", "http://3.94.106.197", "Target host (local stack, EC2 IP, or CloudFront)."],
  ["ACCEPTANCE_CUSTOMER_ID", "334", "Tenant the acceptance run targets."],
  ["ACCEPTANCE_SUITE", "all", "Subset for HTTP stage: cfo | cro | vpcs | cfo-phase1 | all."],
  ["ACCEPTANCE_SKIP_HTTP", "0", "Set 1 to skip HTTP and run persona grading only."],
  ["ACCEPTANCE_RUN_PERSONA", "0", "Set 1 to run persona grading in the container. Requires ANTHROPIC_API_KEY."],
  ["ACCEPTANCE_PERSONAS", "cro,cfo,vpcs", "Subset of personas to grade."],
  ["ACCEPTANCE_PERSONA_SHOTS", "3", "Shots per question (see §5.3)."],
  ["ACCEPTANCE_MIN_GRADE_NUMERIC", "0", "Gate. Set e.g. 3.7 to fail the run below A-."],
  ["ACCEPTANCE_SEED_VPCS", "0", "Set 1 to run seed_vpcs_demo_334.py inside the container before checks (refreshes renewal + playbook attribution on cust 334 demos)."],
  ["CSPULSE_CONTAINER", "auto-detect", "Docker container name on EC2 (only needed if the host runs multiple cs-pulse containers)."],
], { zebra: true }));
children.push(para(
  "Outputs land in $ACCEPTANCE_OUTPUT_DIR (defaults to scripts/datasets/). The script exits non-zero on any HTTP failure or below-gate grade — wire it into your post-rehydrate runbook."
));
children.push(para("Three common invocations:"));
children.push(bullet("HTTP-only smoke after every rehydrate: ./scripts/run_acceptance_ec2.sh (no cost, ~60s)."));
children.push(bullet("Full acceptance before customer sign-off: ACCEPTANCE_RUN_PERSONA=1 ./scripts/run_acceptance_ec2.sh (~$3–5 + ~5min)."));
children.push(bullet("Persona grading only (HTTP already known good): ACCEPTANCE_SKIP_HTTP=1 ACCEPTANCE_RUN_PERSONA=1 ACCEPTANCE_PERSONAS=cfo ./scripts/run_acceptance_ec2.sh."));
children.push(para(
  "Supporting code lives in scripts/ec2_acceptance/ (config.py, http_client.py, checks.py) — that's the env-loading + suite-dispatch layer. You should not need to edit it; if you do, file a base-dev request."
));

children.push(h2("5.8 Golden-file maintenance"));
children.push(para(
  "Persona grader JSON outputs (with prompts, responses, grades, rationale) go in /app/scripts/datasets/ inside the container. Pull them out to the customer's overlay folder as the regression baseline. Re-running after a deploy is how you prove the upgrade did not silently drift the AI surface."
));

// ---------- Section 6: Coordination protocol ----------
children.push(h1("6. Coordination Protocol"));
children.push(para(
  "FDEs are not solo. Every customer-facing change has a coordination path back to base dev. This section tells you which path to use and when."
));

children.push(h2("6.1 The three paths"));
children.push(table([2000, 4400, 3200], [
  ["Path", "When to use", "Turnaround"],
  ["Overlay (no PR)", "Pure customer-specific config: weights, signal channels, playbook templates. Lives in verticals/customer{N}-*/. Does not touch shared code.", "Same day"],
  ["PR to main", "New capability that other FDEs would want: a new playbook archetype, a new signal channel adapter, a new persona-eval prompt-set.", "2-3 days"],
  ["Base-dev request", "Math change, prompt change, schema change, new MCP tool, new vertical, governance flag adjustment.", "1-2 weeks"],
], { zebra: true }));

children.push(h2("6.2 Decision tree"));
children.push(bullet("Does your change touch math, prompts, or schema? → Base-dev request."));
children.push(bullet("Does your change add a new MCP tool? → Base-dev request."));
children.push(bullet("Does your change benefit only this customer? → Overlay, no PR."));
children.push(bullet("Does your change benefit at least three future customers? → PR to main."));
children.push(bullet("Are you unsure? → Default to overlay, file a question in Slack."));

children.push(h2("6.3 Escalation"));
children.push(bullet("Customer-blocking incident (dashboard down, numbers wildly wrong, login broken): page the on-call base dev immediately. SLA: 30 minutes for first response."));
children.push(bullet("Suspected math drift or governance issue: hard stop. File an issue tagged ai-governance and page the model owner. Do not push a fix yourself."));
children.push(bullet("Customer asks for a feature you cannot ship in overlay: file a feature request, do not promise the customer a date."));

children.push(h2("6.4 Documentation discipline"));
children.push(para("Every overlay change goes in the customer's CHANGELOG.md. Every PR has a test plan in the description. Every base-dev request links to the customer ticket. The audit trail is the product — for governance, for buyer AI-DD reviews, and for the next FDE who picks up the engagement."));

// ---------- Section 7: Customer onboarding flow ----------
children.push(h1("7. Customer Onboarding Flow"));
children.push(para(
  "The discovery workbook is the start. The 4-CSV upload is the end of day one. Everything between is mechanical."
));

children.push(h2("7.1 Step 1 — Discovery"));
children.push(para("Open CSPulse_FDE_Discovery.xlsx (the companion workbook). Send the relevant tab to each persona at the customer. Aim for one stakeholder per persona — five interviews total."));
children.push(para("The workbook captures: pain points, top 5 KPIs they track today, weights they would assign each pillar, signal sources (Slack channels, email aliases, transcript tools), stakeholders, success outcomes, and current process pain. The Consolidation tab rolls all five into a config-export view."));

children.push(h2("7.2 Step 2 — Provision the customer"));
children.push(para(
  "Use the platform's onboarding wizard from the admin UI, or the MCP create_customer tool if you are scripting. Two first-class verticals today: dc2_s (data center) and saas_premium. Other industry labels (healthcare, etc.) flow in as account firmographic data, not as separate vertical modules — do not promise the customer a 'Healthcare vertical' surface that exists like dc2_s. Pick the KPI tier (Starter 9, Predictive 11 — default, Full 43)."
));
children.push(para("The Consolidation tab in the discovery workbook has the field names that map straight into the create_customer call. Copy them across."));

children.push(h2("7.3 Step 3 — The canonical 4-CSV upload"));
children.push(para("This is the only onboarding pattern we support by default. Anything else is a special case requiring base-dev approval."));
children.push(table([3200, 6400], [
  ["File", "Contents"],
  ["account_details.csv (preferred) or accounts.csv (fallback)", "Account records with products, champion contacts, contract details, firmographic data. The loader prefers account_details.csv when both are present."],
  ["kpi_measurements.csv", "Monthly KPI time-series from the customer's source systems."],
  ["enhanced_qualitative_signals.csv (preferred) or qualitative_signals.csv (fallback)", "Signal feed (NPS, escalations, champion changes, executive feedback). The enhanced_ variant carries additional columns; the loader accepts either."],
  ["outcomes.csv", "CRM renewal / churn / expansion history (Salesforce export)."],
], { zebra: true }));
children.push(para(
  "Upload via the admin UI or the MCP upload_csv tool. After all four are uploaded, call process_data. Wizard A (causal-graph) and Wizard B (counterfactual NRR) auto-run as part of process_data. Wizard C (KPI weight calibration) and Wizard D (predictor recalibration) DO NOT auto-fire from process_data."
));
children.push(para("Specifically on the wizard policy — what is actually true today:"));
children.push(bullet("Wizard C: explicit-only. Run via the MCP tool trigger_wizard('c') or the admin endpoint. The intended policy is 'auto-fire on ≥10 new closed outcomes or admin trigger,' but the auto-threshold is NOT enforced in code today — treat C as admin-trigger-only until base dev confirms the threshold is wired."));
children.push(bullet("Wizard D: explicit, post-load. After process_data lands and outcomes are present, run trigger_wizard('d') (or the equivalent admin call) so the predictor refits to this tenant. Skipping this leaves the tenant on the previous calibration — symptoms: NRR forecast looks plausible but doesn't move with the tenant's actual KPI trajectory."));

children.push(h2("7.4 Step 4 — First sanity check"));
children.push(para(
  "Run the HTTP verify scripts (§5.6) against the new tenant. They confirm tile shapes and source labels deterministically. Then visually walk all 5 dashboards and confirm the numbers are non-zero. Common first-day issues:"
));
children.push(bullet("Revenue Protected $0: post-load attribution did not run. Trigger it from the admin endpoint."));
children.push(bullet("NRR forecast 0% or unchanged from a previous tenant: Wizard D was not refit (see §7.3 wizard policy). Run trigger_wizard('d') manually."));
children.push(bullet("Ask AI says \"I don't know\" to dashboard questions: a tool was not wired into the customer's enabled set. Check entitlements."));
children.push(bullet("Dashboard tile shows context-graph $ but CRO and CFO numbers don't match: PR #38 parity regression — re-run scripts/verify_cfo_phase1_ec2.py to localize."));

children.push(para("Capability-level day-one checks (cross-references to §2.4–2.6):"));
children.push(bullet("Signal path (§2.4): If the customer shipped qualitative_signals.csv → confirm rows landed (count via search_signals or DB probe). If they want live ingest → confirm per-tenant feature_signal_engine toggle is ON, signal_channels.json is wired, worker is running, and an MCP submit_signal smoke test produced a fresh QualitativeSignal + context node."));
children.push(bullet("Playbook execution spine (§2.5): Confirm the one chosen spine end-to-end. (A) Platform: launch a low-stakes playbook from the CSM kanban → see PlaybookExecutionV2 row → close_playbook → realized ROI snapshot non-zero. (B) n8n: trigger a test playbook → confirm the webhook fired and the callback updated PlaybookExecutionV2. (C) Claude skill: walk the .md once with the customer's stakeholder to validate the prompts."));
children.push(bullet("Knowledge base (§2.6): If QDRANT_URL is set, run a search_signals query with a paraphrased keyword and confirm semantic match (not just substring). If the customer expects KPI Q&A in Ask AI fallback, fire load-driver scenario 2b before sign-off. Do NOT confuse RAG health with dashboard-tile correctness."));

children.push(h2("7.5 Step 5 — Run the first persona-grading pass"));
children.push(para(
  "Once §7.4 is green, run the persona grader (§5.3) for all 5 personas at --shots 3 to get a confident baseline. Expect at least one persona to grade below the customer's bar on day one — usually CSM (cold-start tenant has no closed-loop revenue attribution yet) or CFO (no realized defensive ROI until playbooks resolve). The discovery workbook answers are the calibration starting point — follow the loop in §5.5. Target: all 5 personas at the customer's bar (typically B+ or higher) within the first week."
));

children.push(h2("7.6 Step 6 — Handover"));
children.push(para("Once evals pass and the customer's stakeholders sign off, hand the engagement to the customer-success team. Your handover packet is: the discovery workbook, the persona-eval golden files, the CHANGELOG.md, and a one-page \"how to read this dashboard\" note per persona (cut from the GTM decks)."));

// ---------- Section 8: Appendix ----------
children.push(h1("8. Appendix"));

children.push(h2("8.1 Glossary"));
children.push(table([2400, 7200], [
  ["Term", "Definition"],
  ["FDE", "Forward Deployment Engineer. You. Contracted, NDA-covered, customer-embedded."],
  ["Overlay", "Customer-specific config and templates that live in verticals/customer{N}-{vertical}/. Does not affect other customers."],
  ["Pillar", "A grouping of related KPIs. Five pillars total."],
  ["KPI", "A single measured number a customer reports monthly. Each KPI belongs to one pillar and has a weight."],
  ["Signal", "A qualitative event captured from Slack, email, transcripts, or manual entry. Enriches KPI-based health."],
  ["Wizard", "A background worker that derives structure (causal graph, patterns, weight calibration, predictor calibration). Four wizards total."],
  ["Predictor", "The forward NRR forecast module. Gives a 12-month outlook per account and rolled up to portfolio."],
  ["NRR", "Net Revenue Retention. Realized = trailing 12 months. Forecast = forward 12 months. Historical = raw outcomes."],
  ["Power of 1", "Unit-economics translator: one percentage point of NRR improvement → dollars at the customer's ARR."],
  ["MCP", "Model Context Protocol. The mechanism by which Claude and other LLMs call into the platform."],
  ["Magic link", "Single-use, 15-minute auth link emitted on stdout. Never stored raw in the database."],
  ["Sanity diff", "A reproducible JSON snapshot of dashboard numbers used to prove an upgrade did not silently drift values."],
], { zebra: true }));

children.push(h2("8.2 File and path map"));
children.push(table([4800, 4800], [
  ["What you need", "Where it lives"],
  ["Customer overlay", "verticals/customer{N}-{vertical}/"],
  ["Pillar + KPI weights", "verticals/customer{N}-{vertical}/journey/config/bootstrap_weights_config.json"],
  ["KPI catalog (canonical, do not edit)", "backend/verticals/dc2_s/kpi_definitions.py (and verticals/saas_premium/ equivalent)"],
  ["Signal channel config", "verticals/customer{N}-{vertical}/config/signal_channels.json"],
  ["Persona grader runner", "kpi-dashboard/backend/tests/persona_grading/runner.py (invoke via python3 -m tests.persona_grading.runner)"],
  ["Acceptance harness (primary)", "scripts/run_acceptance_ec2.sh + scripts/.env.acceptance(.example) + scripts/ec2_acceptance/{config,http_client,checks}.py"],
  ["HTTP verify — env-driven multi-suite", "scripts/verify_executive_phases_ec2.py --suite all|cfo|cro|vpcs|cfo-phase1"],
  ["HTTP verify — per-PR scripts (kept for surgical re-runs)", "scripts/verify_cfo_phases_ec2.py, verify_cro_phases_ec2.py, verify_vpcs_phases_ec2.py, verify_cfo_phase1_ec2.py"],
  ["Legacy numeric-snapshot harness (cust 333 only, NOT persona)", "scripts/sanity_check_cust333.py"],
  ["Deploy scripts", "scripts/deploy-ec2-git-pull.sh (primary), scripts/rehydrate-ec2-ecr.sh (ECR tag-based)"],
  ["Docker compose (local)", "docker-compose.cspulse.yml"],
  ["MCP tool catalog (~52 @mcp.tool decorators today)", "kpi-dashboard/backend/mcp_server/cs_pulse_*.py"],
  ["Discovery workbook (this engagement)", "Companion file: CSPulse_FDE_Discovery.xlsx"],
], { zebra: true }));

children.push(h2("8.3 MCP tool inventory (by capability area)"));
children.push(para(
  "The platform exposes ~52 @mcp.tool-decorated callables today, spread across kpi-dashboard/backend/mcp_server/cs_pulse_*.py. The list below is curated and groups them by capability — it is NOT generated from code, so do not treat the count as authoritative; before quoting a number to a customer, grep mcp_server/ for @mcp.tool and count the live decorations. You may NOT add new tools — those go through base dev."
));
children.push(h3("Customer + onboarding"));
children.push(para("create_customer, list_customers, clone_customer, complete_onboarding, configure_customer_kpis, enable_features, get_csv_templates, upload_csv, download_customer_csv, process_data, partner_portal, list_portfolio_customers, list_verticals, get_platform_instructions."));
children.push(h3("Health + accounts"));
children.push(para("get_account_health, get_at_risk_accounts, get_account_journey_timeline, get_account_nrr_forecast, get_health_score_history, get_kpi_catalog, list_accounts, get_crm_account_data, get_stakeholder_map, get_support_tickets."));
children.push(h3("Predictor + portfolio"));
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
children.push(para("trigger_wizard, get_llm_cost_summary."));

children.push(h2("8.4 Common pitfalls"));
children.push(bullet("Treating 11-CSV mode as the default. It is not. The canonical pattern is 4-CSV. 11-CSV is a special case for customers with mature data engineering. Anything else is base-dev approval territory."));
children.push(bullet("Hardcoding a customer-specific weight in the kpi_definitions catalog. Use the overlay. The catalog is shared across all customers."));
children.push(bullet("Editing a prompt to make Ask AI \"sound better.\" Prompts are governed. File a base-dev request."));
children.push(bullet("Bypassing record_usage() when adding a new LLM caller. Every Anthropic call must be tracked. Grep-verify before you ship."));
children.push(bullet("Running Wizard C after every CSV refresh. Wizard C is decoupled from process_data by design. Auto-firing it breaks calibration audit trails."));
children.push(bullet("Calling a customer's number \"correct\" without a sanity-diff. Numbers can drift silently across image upgrades. Always run the diff."));
children.push(bullet("Forgetting to refit Wizard D after an image upgrade. Old calibration coefficients become stale relative to the new feature vector."));

children.push(h2("8.5 Escalation runbook"));
children.push(table([3200, 3200, 3200], [
  ["Symptom", "First action", "If unresolved in 30 min"],
  ["Dashboard returns 401 across the board", "Re-run rehydrate script; confirm SESSION_COOKIE_SECURE=false on EC2 env.", "Page on-call base dev."],
  ["Numbers visibly wrong vs. last week", "Run sanity-diff against the golden snapshot; check Wizard D + Wizard C log timestamps.", "Roll back to prior image tag; file incident."],
  ["Ask AI hallucinating numbers", "Confirm the right MCP tool fired (check llm_usage_log). Re-check tool entitlements.", "Page base dev on-call (model owner)."],
  ["Magic-link login fails", "Reissue from container stdout; check 15-min expiry; confirm email matches DB.", "Manual session reset via admin endpoint."],
  ["Wizard D will not converge", "Check minimum-event threshold; check feature vector parity with calibration set.", "Fall back to bucket-lookup NRR; file base-dev ticket."],
  ["Customer asks for math change", "Hard stop. File ai-governance ticket. Do not patch.", "Coordinate base-dev triage."],
], { zebra: true }));

children.push(h2("8.6 Sign-off checklist (use this before handover)"));
children.push(bullet("All five personas pass the eval matrix at threshold."));
children.push(bullet("Golden sanity files committed to the customer overlay."));
children.push(bullet("CHANGELOG.md in the overlay reflects every change made during the engagement."));
children.push(bullet("Discovery workbook is filled in and stored in the engagement folder."));
children.push(bullet("Customer admin has been issued credentials; magic-link flow tested."));
children.push(bullet("Rehydrate script has been run end-to-end at least once by the customer's ops contact (or the FDE on their behalf with witness)."));
children.push(bullet("Handover note (one-page per persona) cut from the GTM decks, customized for this customer."));
children.push(bullet("Customer engagement lead has signed the handover form."));

// ---------- Build the document ----------

const doc = new Document({
  creator: "CS Pulse",
  title: "CS Pulse FDE Playbook",
  description: "Internal knowledge transfer for Forward Deployment Engineers",
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } }, // 11pt
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: "1F3A5F" },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "2E5F8F" },
        paragraph: { spacing: { before: 240, after: 140 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: "444444" },
        paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 1440, hanging: 360 } } } },
        ]},
      { reference: "numbers",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        ]},
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          children: [
            new TextRun({ text: "CS Pulse  ·  FDE Playbook", size: 18, color: "888888" }),
            new TextRun({ text: "\tInternal — NDA", size: 18, color: "888888" }),
          ],
          tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "CCCCCC", space: 1 } },
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          children: [
            new TextRun({ text: "Version 1.0 · May 2026", size: 18, color: "888888" }),
            new TextRun({ text: "\tPage ", size: 18, color: "888888" }),
            new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "888888" }),
          ],
          tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
        })],
      }),
    },
    children,
  }],
});

const outPath = path.join(__dirname, "CSPulse_FDE_Playbook.docx");
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outPath, buffer);
  console.log("Wrote:", outPath, "(" + buffer.length + " bytes)");
});
