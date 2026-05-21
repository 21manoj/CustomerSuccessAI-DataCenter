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
children.push(para("The compose file brings up postgres, the platform, and the load-driver. Hot-reload on the platform is on by default so file changes inside the mounted customer overlay take effect without a restart."));

children.push(h2("3.3 Deploying back to the customer environment"));
children.push(para("There is one canonical deploy script. Use it. Do not docker-cp files into a running container — that pattern has burned us before."));
children.push(code("./scripts/rehydrate-ec2-ecr.sh <INSTANCE_ID>"));
children.push(para("This pulls from ECR using local AWS credentials and recreates the platform + postgres + load-driver containers on the EC2 instance. The script is idempotent and self-healing: it will repair a missing env file, reissue a stale magic-link, and write SESSION_COOKIE_SECURE=false if the customer is on direct-HTTP."));

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
  "Bundled verify scripts (run them; do not re-derive them): scripts/verify_cfo_phase1_ec2.py and scripts/verify_cro_phases_ec2.py. Pattern: per-PR scripts that hit known endpoints, assert known invariants, and exit non-zero on regression. When you ship a new persona-facing PR, add a sibling verify script in the same shape."
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
children.push(para("Every PR must:"));
children.push(bullet("Pass the existing pytest suite (no skips, no xfail without justification)."));
children.push(bullet("Pass the persona-eval matrix at the customer's pass threshold (default: 16 of 20 per persona)."));
children.push(bullet("Include a diff of results/sanity/ snapshots showing exactly which numbers moved and why."));
children.push(bullet("Include a one-line entry in the customer's CHANGELOG.md inside their overlay folder."));

// ---------- Section 5: Persona-eval framework ----------
children.push(h1("5. Persona-Eval Framework"));
children.push(para(
  "A platform that works for a CRO can fail a CSM. The eval matrix is how you prove the customer's deployment lands for every persona — not just the loudest one in the room."
));

children.push(h2("5.1 The rubric"));
children.push(para("Five personas, ten questions each, scored 0-2 per question. Pass = 16 of 20 per persona. Total possible: 100. Customer-acceptance threshold: 80, with no single persona below 14."));

children.push(table([1600, 4800, 3200], [
  ["Persona", "What the eval tests", "Pass threshold"],
  ["CRO", "Revenue at risk visibility, NRR forecast credibility, top expansion opportunities, account-level explainability.", "16/20"],
  ["CFO", "ROI traceability, CS investment scaling, attribution back to playbooks, audit-trail of every dollar claim.", "16/20"],
  ["CEO", "Portfolio rollup, board-ready summary numbers, cross-customer comparison if PE/portfolio mode is on.", "16/20"],
  ["VP CS", "Team capacity, CSM ranking, playbook execution rates, weekly business review readiness.", "16/20"],
  ["CSM", "Daily Kanban (FIRE / THIS WEEK / OPPORTUNITIES), per-account action recommendations, signal triage, time-to-next-action.", "16/20"],
], { zebra: true }));

children.push(h2("5.2 Question categories per persona"));
children.push(bullet("Numbers (2 questions): Are the headline numbers on the persona's dashboard correct and reconcile-able to a source?"));
children.push(bullet("Explainability (2 questions): When the persona clicks into a number, do they get an answer they can defend in a meeting?"));
children.push(bullet("Actionability (2 questions): Does the dashboard tell them what to do next?"));
children.push(bullet("Trust (2 questions): Is the confidence interval / governance disclosure visible where it matters?"));
children.push(bullet("Workflow (2 questions): Does the surface fit the persona's actual cadence (CSM = daily, CFO = monthly, CEO = quarterly)?"));

children.push(h2("5.3 The practical instrument: MCP replay"));
children.push(para("The rubric is the conceptual framework. The instrument you actually run is MCP replay."));
children.push(para("Each persona has a fixed prompt-set (10 prompts, matching the 10 rubric questions). You run them through Ask AI against the customer's tenant. The script captures the answer and diffs it against a golden JSON in results/sanity/."));
children.push(code("./scripts/sanity_check_cust{N}.py --persona cro --persona cfo --persona ceo --persona vpcs --persona csm"));
children.push(para("The script emits a per-persona scorecard: pass / fail per question, total per persona, and a portfolio rollup. The golden JSON is checked into the customer overlay so future runs are reproducible."));

children.push(h2("5.4 Calibration loop"));
children.push(para("When a persona scores below threshold, the fix loop is:"));
children.push(numbered("Identify which question failed (the script tells you)."));
children.push(numbered("Map the question to a root cause: wrong KPI weight, missing signal source, wrong pillar weight, stale Wizard C calibration, or a playbook gap."));
children.push(numbered("Make the smallest possible change in the customer overlay — usually a weight adjustment in bootstrap_weights_config.json or a new signal channel."));
children.push(numbered("Re-run the persona's eval. The script will show which questions moved and by how much."));
children.push(numbered("Repeat until threshold is crossed. Cap at 5 calibration cycles. If you cannot close the gap in 5, file a base-dev ticket — the issue is likely deeper than a weight."));

children.push(h2("5.5 Golden-file maintenance"));
children.push(para("Once a persona passes, snapshot the answers into results/sanity/golden_{persona}.json. That becomes the regression baseline for every future image upgrade for this customer. Re-running the script after a deploy is how you prove the upgrade did not silently drift the numbers."));

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
children.push(para("Use the platform's onboarding wizard from the admin UI, or the MCP create_customer tool if you are scripting. Pick the vertical (DC2_S, SaaS, Healthcare). Pick the KPI tier (Starter 9, Predictive 11 — default, Full 43)."));
children.push(para("The Consolidation tab in the discovery workbook has the field names that map straight into the create_customer call. Copy them across."));

children.push(h2("7.3 Step 3 — The canonical 4-CSV upload"));
children.push(para("This is the only onboarding pattern we support by default. Anything else is a special case requiring base-dev approval."));
children.push(table([3200, 6400], [
  ["File", "Contents"],
  ["accounts.csv", "Account records with products, champion contacts, contract details, firmographic data."],
  ["kpi_measurements.csv", "Monthly KPI time-series from the customer's source systems."],
  ["enhanced_qualitative_signals.csv", "Signal feed (NPS, escalations, champion changes, executive feedback)."],
  ["outcomes.csv", "CRM renewal / churn / expansion history (Salesforce export)."],
], { zebra: true }));
children.push(para("Upload via the admin UI or the MCP upload_csv tool. After all four are uploaded, call process_data. Wizard A and Wizard B auto-run. Wizard C does NOT auto-fire — that is a deliberate policy decision. Wizard C runs only on an outcome-count threshold (≥10 new closed outcomes) or an explicit admin trigger. Do not change this."));

children.push(h2("7.4 Step 4 — First sanity check"));
children.push(para("Run the sanity script against the new tenant. Confirm the dashboards render and the numbers are non-zero. Common first-day issues:"));
children.push(bullet("Revenue Protected $0: post-load attribution did not run. Trigger it from the admin endpoint."));
children.push(bullet("NRR forecast 0%: Wizard D did not converge. Check the Wizard D log; refit manually if needed."));
children.push(bullet("Ask AI says \"I don't know\" to dashboard questions: a tool was not wired into the customer's enabled set. Check entitlements."));

children.push(h2("7.5 Step 5 — Run the first persona-eval"));
children.push(para("Once the dashboards render, run the persona-eval matrix (Section 5). Expect at least one persona to score below threshold on day one. The discovery workbook answers are the calibration starting point — adjust the weights, re-run, repeat. Target: all five personas at threshold within the first week."));

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
  ["KPI catalog (canonical, do not edit)", "backend/verticals/dc2_s/kpi_definitions.py"],
  ["Signal channel config", "verticals/customer{N}-{vertical}/config/signal_channels.json"],
  ["Sanity script", "scripts/sanity_check_cust{N}.py"],
  ["Sanity snapshots + golden files", "results/sanity/"],
  ["Deploy script", "scripts/rehydrate-ec2-ecr.sh"],
  ["Docker compose (local)", "docker-compose.cspulse.yml"],
  ["MCP tool catalog (51 tools)", "kpi-dashboard/backend/mcp_server/"],
  ["Discovery workbook (this engagement)", "Companion file: CSPulse_FDE_Discovery.xlsx"],
], { zebra: true }));

children.push(h2("8.3 The 51 MCP tools (by capability area)"));
children.push(para("You will call these via Ask AI or directly through the MCP server. You may NOT add new ones — those go through base dev."));
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
