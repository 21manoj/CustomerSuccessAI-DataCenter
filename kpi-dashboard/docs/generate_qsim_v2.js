const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageNumber, PageBreak,
} = require('docx');
const fs = require('fs');

// ============================================================
// Styles & Constants
// ============================================================

const BLUE = '1F4E79';
const LIGHT_BLUE = 'D6E4F0';
const GRAY = 'F2F2F2';
const WHITE = 'FFFFFF';
const border = { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC' };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 60, bottom: 60, left: 100, right: 100 };

function headerCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: BLUE, type: ShadingType.CLEAR },
    margins: cellMargins,
    verticalAlign: 'center',
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, color: WHITE, font: 'Arial', size: 20 })] })],
  });
}

function cell(text, width, opts = {}) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: opts.shading ? { fill: opts.shading, type: ShadingType.CLEAR } : undefined,
    margins: cellMargins,
    children: [new Paragraph({
      children: [new TextRun({
        text,
        font: opts.font || 'Arial',
        size: opts.size || 18,
        bold: opts.bold || false,
        color: opts.color || '333333',
      })],
    })],
  });
}

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 }, children: [new TextRun({ text, bold: true, font: 'Arial', size: 32, color: BLUE })] });
}

function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 160 }, children: [new TextRun({ text, bold: true, font: 'Arial', size: 26, color: BLUE })] });
}

function h3(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 120 }, children: [new TextRun({ text, bold: true, font: 'Arial', size: 22, color: '333333' })] });
}

function para(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after || 120 },
    children: [new TextRun({ text, font: 'Arial', size: opts.size || 20, color: opts.color || '444444', bold: opts.bold || false, italics: opts.italics || false })],
  });
}

function richPara(runs, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after || 120 },
    children: runs.map(r => new TextRun({ font: 'Arial', size: 20, color: '444444', ...r })),
  });
}

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: 'bullets', level },
    spacing: { after: 80 },
    children: [new TextRun({ text, font: 'Arial', size: 20, color: '444444' })],
  });
}

function richBullet(runs, level = 0) {
  return new Paragraph({
    numbering: { reference: 'bullets', level },
    spacing: { after: 80 },
    children: runs.map(r => new TextRun({ font: 'Arial', size: 20, color: '444444', ...r })),
  });
}

function numberedItem(text, level = 0) {
  return new Paragraph({
    numbering: { reference: 'numbers', level },
    spacing: { after: 80 },
    children: [new TextRun({ text, font: 'Arial', size: 20, color: '444444' })],
  });
}

function codePara(text) {
  return new Paragraph({
    spacing: { after: 40 },
    indent: { left: 360 },
    shading: { fill: GRAY, type: ShadingType.CLEAR },
    children: [new TextRun({ text, font: 'Courier New', size: 17, color: '333333' })],
  });
}

function makeTable(headers, rows, colWidths) {
  const totalW = colWidths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalW, type: WidthType.DXA },
    columnWidths: colWidths,
    rows: [
      new TableRow({ children: headers.map((h, i) => headerCell(h, colWidths[i])) }),
      ...rows.map((row, ri) => new TableRow({
        children: row.map((c, ci) => cell(c, colWidths[ci], { shading: ri % 2 === 1 ? GRAY : undefined })),
      })),
    ],
  });
}

// ============================================================
// Document
// ============================================================

const doc = new Document({
  styles: {
    default: { document: { run: { font: 'Arial', size: 20 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 32, bold: true, font: 'Arial', color: BLUE }, paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 26, bold: true, font: 'Arial', color: BLUE }, paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { size: 22, bold: true, font: 'Arial' }, paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: 'bullets', levels: [
        { level: 0, format: LevelFormat.BULLET, text: '\u2022', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        { level: 1, format: LevelFormat.BULLET, text: '\u25E6', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1440, hanging: 360 } } } },
      ]},
      { reference: 'numbers', levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
      ]},
    ],
  },
  sections: [
    // ====== COVER PAGE ======
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } },
      },
      children: [
        new Paragraph({ spacing: { before: 2400 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: 'CS PULSE', font: 'Arial', size: 56, bold: true, color: BLUE })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: 'Qualitative Signal Ingestion Module', font: 'Arial', size: 40, color: '666666' })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [new TextRun({ text: '(QSIM)', font: 'Arial', size: 36, color: '666666' })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [new TextRun({ text: 'Engineering Specification \u2014 V2 (Revised)', font: 'Arial', size: 28, color: '888888' })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: BLUE, space: 1 } } }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [new TextRun({ text: 'Date: March 21, 2026', font: 'Arial', size: 22, color: '666666' })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [new TextRun({ text: 'Status: REVISED DRAFT \u2014 Anchored to CS Pulse Codebase', font: 'Arial', size: 22, color: '999999' })] }),
        new Paragraph({ spacing: { before: 1200 } }),

        // Version table
        makeTable(
          ['Field', 'Value'],
          [
            ['Version', '2.0'],
            ['Date', 'March 21, 2026'],
            ['Status', 'REVISED DRAFT'],
            ['Changes from v0.1', 'Added CG pre-emption (Section 5), structural urgency classifier, Phase 1 scoping to existing codebase, removed Redis dependency, added vertical-aware enrichment, cold-start ramp, cost guardrails'],
            ['Related Code', 'models.py (QualitativeSignal), context_graph.py, playbook_webhook_engine.py, integration_api.py, event_system.py'],
          ],
          [2500, 6860]
        ),
      ],
    },

    // ====== MAIN CONTENT ======
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } },
      },
      headers: {
        default: new Header({ children: [new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC', space: 4 } }, children: [new TextRun({ text: 'CS Pulse \u2014 QSIM Engineering Specification V2', font: 'Arial', size: 16, color: '888888', italics: true })] })] }),
      },
      footers: {
        default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Page ', font: 'Arial', size: 16, color: '888888' }), new TextRun({ children: [PageNumber.CURRENT], font: 'Arial', size: 16, color: '888888' })] })] }),
      },
      children: [

        // ========================================
        // 1. OVERVIEW
        // ========================================
        h1('1. Overview (Revised)'),
        para('This document defines the engineering specification for the Qualitative Signal Ingestion Module (QSIM) \u2014 a capability layer for CS Pulse that ingests unstructured communication data from Slack, email, and meeting transcripts, enriches it using an LLM pipeline, and fuses the resulting qualitative signals with existing quantitative KPI data.'),
        para(''),
        richPara([
          { text: 'V2 CHANGES: ', bold: true, color: 'C0392B' },
          { text: 'This revision anchors all design decisions to the existing CS Pulse codebase, eliminates redundant infrastructure (Redis, parallel connectors), and defines a minimal Phase 1 that can ship in 4\u20136 weeks by extending existing models and APIs.' },
        ]),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 2. DESIGN PRINCIPLES
        // ========================================
        h1('2. Design Principles (NEW)'),
        numberedItem('EXTEND, DON\u2019T DUPLICATE \u2014 Use existing QualitativeSignal model, existing webhook engine, existing event system. No parallel infrastructure.'),
        numberedItem('VERTICAL-AWARE FROM DAY 1 \u2014 LLM prompts include vertical context (DC2_S vs SaaS Premium). Intent enums are vertical-specific.'),
        numberedItem('CONTEXT GRAPH IS AUTHORITATIVE \u2014 CG signals pre-empt composite analysis for high-impact events. QSIM enriches CG nodes, never overrides them.'),
        numberedItem('COLD-START SAFE \u2014 Qualitative weight ramps from 0% to target over first 30 days. No health score crashes on day 1.'),
        numberedItem('COST-BOUNDED \u2014 LLM calls are batched, cached, and capped per customer per day.'),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 3. SYSTEM ARCHITECTURE
        // ========================================
        h1('3. System Architecture'),

        h2('3.1 High-Level Data Flow'),
        para('The QSIM pipeline processes signals through six sequential stages:'),
        para(''),
        richBullet([{ text: 'Stage 1 \u2014 Ingestion: ', bold: true }, { text: 'Raw communication data pulled from source connectors (Slack, Email, Transcript) and normalized into RawSignal objects.' }]),
        richBullet([{ text: 'Stage 2 \u2014 LLM Enrichment: ', bold: true }, { text: 'Each RawSignal passed through LLM extraction pipeline to produce EnrichedSignal with sentiment, intent, stakeholder, urgency, and confidence scores.' }]),
        richBullet([{ text: 'Stage 3 \u2014 Cross-Channel Deduplication: ', bold: true }, { text: 'EnrichedSignals from same account within configurable time window evaluated for dedup.' }]),
        richBullet([{ text: 'Stage 4 \u2014 Context Graph Collision Check: ', bold: true }, { text: 'Each CompositeSignal checked against existing CG nodes to prevent double-alerting.' }]),
        richBullet([{ text: 'Stage 5 \u2014 Composite Score Fusion: ', bold: true }, { text: 'CompositeSignals fused with quantitative KPI data to produce composite health modifier.' }]),
        richBullet([{ text: 'Stage 6 \u2014 Alert Routing: ', bold: true }, { text: 'Based on signal type, urgency, and RBAC rules, alerts dispatched to appropriate channels.' }]),

        para(''),
        h2('3.2 Technology Stack (REVISED \u2014 Anchored to Codebase)'),
        makeTable(
          ['Component', 'CS Pulse Existing Code', 'Extension Needed'],
          [
            ['Signal Store', 'models.py: QualitativeSignal', 'Add enrichment columns (sentiment_score, intent_signals, confidence, etc.)'],
            ['Context Graph', 'utils/context_graph.py', 'Add QUALITATIVE_SIGNAL node subtype, collision check function'],
            ['Alert Routing', 'playbook_webhook_engine.py', 'Add signal-type triggers (not just health threshold triggers)'],
            ['Webhook Delivery', 'integration_api.py', 'Already supports Slack/Email via n8n webhooks \u2014 reuse'],
            ['Event Bus', 'event_system.py', 'Add context_graph_node_created event'],
            ['Config Store', 'CustomerConfig model', 'Add qsim_config JSON column (fusion weights, dedup windows)'],
            ['Ingestion API', 'integration_api.py webhook endpoint', 'Extend /api/integrations/webhook/{provider} for slack/email'],
            ['Health Scoring', 'utils/vertical_health.py', 'Add composite modifier to get_health_calculator output'],
          ],
          [2000, 3200, 4160]
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 4. DATA MODELS
        // ========================================
        h1('4. Data Models (REVISED)'),

        h2('4.1 Extended QualitativeSignal Model'),
        richPara([
          { text: 'Design decision: ', bold: true },
          { text: 'Instead of creating RawSignal + EnrichedSignal + CompositeSignal as 3 new tables, extend the existing QualitativeSignal model with new columns. This preserves backward compatibility with existing CSV-ingested signals.' },
        ]),
        para(''),

        makeTable(
          ['New Column', 'Type', 'Description'],
          [
            ['source_type', 'Enum', 'slack, email, transcript, manual, kpi_derived (existing signals)'],
            ['raw_text', 'Text (nullable)', 'Original unstructured text (encrypted at rest)'],
            ['sentiment_score', 'Float', 'Continuous sentiment -1.0 to +1.0'],
            ['relationship_sentiment', 'Float', 'Sentiment toward vendor relationship'],
            ['product_sentiment', 'Float', 'Sentiment toward product'],
            ['urgency_score', 'Float', 'Time-sensitivity 0.0 to 1.0'],
            ['escalation_probability', 'Float', 'Likelihood of executive escalation 0.0 to 1.0'],
            ['intent_signals', 'JSONB', 'List of detected intent codes'],
            ['stakeholder_roles', 'JSONB', 'List of {role, name} objects'],
            ['suggested_action', 'String', 'LLM-recommended next action'],
            ['confidence', 'JSONB', 'Per-field confidence scores'],
            ['requires_review', 'Boolean', 'True if any confidence < 0.6'],
            ['llm_model_version', 'String', 'Model ID for audit trail'],
            ['composite_signal_id', 'UUID (nullable)', 'Links to parent composite if deduped'],
            ['dedup_confidence', 'Float (nullable)', 'Confidence that this was correctly deduped'],
            ['cg_node_id', 'Integer (nullable)', 'Linked context graph node if collision detected'],
            ['alert_suppressed', 'Boolean', 'True if alert suppressed due to CG collision'],
            ['structural_urgency', 'Enum (nullable)', 'critical, high, medium, low \u2014 from structural classifier'],
            ['effective_urgency', 'Enum', 'max(structural_urgency, llm_urgency) \u2014 used for routing'],
          ],
          [2500, 2000, 4860]
        ),

        para(''),
        h2('4.2 Intent Signal Enum (Vertical-Aware)'),
        makeTable(
          ['Intent Code', 'DC2_S Meaning', 'SaaS Premium Meaning', 'Typical Source'],
          [
            ['renewal_risk', 'Contract renewal uncertainty', 'Subscription churn signal', 'Email, Transcript'],
            ['expansion_interest', 'Additional rack/GPU capacity', 'Seat expansion, tier upgrade', 'Transcript, Slack'],
            ['champion_change', 'Infra team lead departing', 'Product champion role change', 'Slack, Email'],
            ['product_frustration', 'Hardware failures, thermal issues', 'UX bugs, performance complaints', 'Slack, Transcript'],
            ['feature_request', 'Firmware/driver capability request', 'Product feature request', 'Slack, Email'],
            ['executive_escalation', 'CTO/VP Infra escalation', 'CTO/VP Product escalation', 'Email, Transcript'],
            ['pricing_concern', 'CapEx budget constraints', 'Subscription pricing objection', 'Transcript, Email'],
            ['competitor_mention', 'Alternative DC vendor evaluation', 'Competing SaaS platform mentioned', 'Transcript'],
            ['deployment_blocker', 'Rack commissioning blocked', 'Onboarding/integration blocked', 'Slack, Transcript'],
            ['nps_drop_indicator', 'Declining satisfaction language', 'Declining satisfaction language', 'Email, Transcript'],
          ],
          [2200, 2400, 2400, 2360]
        ),

        para(''),
        h2('4.3 AlertRecord'),
        para('Alert records track every notification fired by the system. Each alert includes: alert_id, signal_ref (composite_signal_id or cg_node_id), account_id, customer_id, alert_type (tier_1_preemption, tier_2_composite), channel (slack, email, crm_task), recipient, urgency, delivery_status, created_at, delivered_at, acknowledged_at, and suppression_reason (nullable).'),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 5. CONTEXT GRAPH PRE-EMPTION
        // ========================================
        h1('5. Context Graph Pre-emption (NEW)'),

        h2('5.1 Two-Tier Alert Architecture'),
        richBullet([{ text: 'Tier 1 \u2014 Immediate (Context Graph Pre-emption): ', bold: true }, { text: 'Context graph signals with known high-impact patterns fire alerts instantly, bypassing composite fusion. These are structural events, not sentiment.' }]),
        richBullet([{ text: 'Tier 2 \u2014 Composite (Day-to-Day QSIM): ', bold: true }, { text: 'All other signals go through the 6-stage pipeline. Product sentiment drift, gradual relationship cooling, recurring feature requests benefit from dedup, fusion, and composite scoring.' }]),

        para(''),
        h2('5.2 Tier 1 Pre-emption Rules'),
        makeTable(
          ['Condition', 'Action', 'Bypass Fusion?'],
          [
            ['CG node created with subtype in [champion_loss, executive_escalation, churn_risk]', 'Immediate Tier 1 alert via playbook_webhook_engine.py', 'Yes'],
            ['CG node with revenue_impact > $500K AND health_delta < -15', 'Immediate Tier 1 alert', 'Yes'],
            ['KPI cliff detected (any pillar drops >20 points in 7 days)', 'Immediate Tier 1 alert + auto-trigger playbook', 'Yes'],
            ['QSIM signal matches Tier 1 CG node (collision)', 'Enrich existing alert thread, don\u2019t fire new', 'N/A'],
            ['All other signals', 'Normal Tier 2 pipeline \u2014 composite \u2014 alert routing', 'No'],
          ],
          [4000, 3500, 1860]
        ),

        para(''),
        h2('5.3 Structural Urgency Classifier'),
        para('A deterministic, business-logic-driven classifier that pre-empts LLM urgency scoring for known high-impact patterns:'),
        para(''),
        codePara('def classify_structural_urgency(signal, account):'),
        codePara('    """Pre-empt LLM urgency with business-logic urgency.'),
        codePara('    Returns urgency level or None (fall through to LLM)."""'),
        codePara('    TIER_1_SUBTYPES = {\'champion_loss\', \'executive_escalation\', \'churn_risk\'}'),
        codePara('    if signal.node_subtype in TIER_1_SUBTYPES:'),
        codePara('        return \'critical\''),
        codePara('    if account.days_to_renewal <= 30 and signal.health_delta < -10:'),
        codePara('        return \'critical\''),
        codePara('    if account.arr > ARR_HIGH_THRESHOLD and signal.health_delta < -5:'),
        codePara('        return \'high\''),
        codePara('    if signal.health_delta < -15:'),
        codePara('        return \'high\''),
        codePara('    return None  # fall through to LLM-based urgency'),

        para(''),
        h2('5.4 Effective Urgency Resolution'),
        para('The effective urgency is the maximum of structural and perceived urgency:'),
        para(''),
        codePara('structural_urgency = f(signal_type, ARR_at_risk, days_to_renewal, health_delta)'),
        codePara('perceived_urgency  = f(LLM_urgency_score, escalation_probability)'),
        codePara('effective_urgency  = max(structural_urgency, perceived_urgency)'),
        para(''),
        richPara([
          { text: 'Example: ', bold: true },
          { text: 'A calm email from a CTO saying "we\'re evaluating alternatives" has low perceived urgency (polite tone) but critical structural urgency (competitor eval + CTO involvement + high ARR). The structural classifier overrides to critical.' },
        ]),

        para(''),
        h2('5.5 Integration with Existing Event System'),
        richPara([
          { text: 'File: ', bold: true },
          { text: 'backend/event_system.py' , italics: true },
          { text: ' \u2014 add new event type:' },
        ]),
        bullet('Event: context_graph_node_created'),
        bullet('Subscriber: QSIMPreemptionSubscriber'),
        bullet('Logic: On CG node creation, check if subtype is in TIER_1_SUBTYPES. If yes, fire immediate alert via playbook_webhook_engine.py, bypassing the QSIM composite pipeline.'),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 6. LLM ENRICHMENT PIPELINE
        // ========================================
        h1('6. LLM Enrichment Pipeline (REVISED)'),

        h2('6.1 Vertical-Aware Enrichment Prompt'),
        richPara([
          { text: 'V2 CHANGE: ', bold: true, color: 'C0392B' },
          { text: 'The v0.1 prompt was generic. This version injects vertical context so the LLM understands that "deployment_blocker" means GPU rack commissioning in DC2_S but onboarding integration in SaaS Premium.' },
        ]),
        para(''),
        para('System Prompt Template:', { bold: true }),
        codePara('You are a B2B Customer Success signal extraction engine'),
        codePara('for the {vertical_name} vertical.'),
        codePara('Industry context: {vertical_description}'),
        codePara('Key pillars: {pillar_names_and_descriptions}'),
        codePara('Return ONLY valid JSON. No preamble. No markdown.'),
        codePara('Confidence scores reflect explicitness:'),
        codePara('  1.0=stated directly, 0.5=implied, 0.0=not determinable.'),
        codePara('If confidence for any field < 0.6, set requires_review=true.'),

        para(''),
        h2('6.2 Expected Response Schema'),
        para('The LLM returns a JSON object with: sentiment_score (float), relationship_sentiment (float), product_sentiment (float), urgency_score (float), escalation_probability (float), intent_signals (array of intent codes), stakeholder_roles (array of {role, name}), suggested_action (string), confidence (object with per-field scores), and requires_review (boolean).'),

        para(''),
        h2('6.3 Cost Guardrails (NEW)'),
        makeTable(
          ['Guard', 'Default', 'Configurable?'],
          [
            ['Max LLM calls per customer per day', '200', 'Yes, via CustomerConfig'],
            ['Max LLM calls per account per day', '50', 'Yes'],
            ['Batch size for bulk historical ingestion', '10 signals per LLM call', 'Yes'],
            ['Cache TTL for near-identical signals', '1 hour (cosine similarity > 0.95)', 'Yes'],
            ['Cost cap per customer per month', '$500', 'Yes'],
            ['Estimated cost per signal (Claude Sonnet)', '~$0.003', 'N/A'],
          ],
          [4000, 3000, 2360]
        ),

        para(''),
        h2('6.4 Error Handling'),
        makeTable(
          ['Error Type', 'Handling Strategy'],
          [
            ['Invalid JSON response from LLM', 'Retry once with stricter prompt. If still invalid, mark requires_review=true and store raw response.'],
            ['LLM timeout (>30s)', 'Retry with exponential backoff (1s, 2s, 4s). After 3 failures, queue for batch retry.'],
            ['Low confidence on critical fields', 'Route to human review queue. Do not include in composite scoring until reviewed.'],
            ['Partial JSON (some fields missing)', 'Fill missing fields with null. Set confidence for missing fields to 0.0. Set requires_review=true.'],
          ],
          [3000, 6360]
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 7. CROSS-CHANNEL DEDUPLICATION
        // ========================================
        h1('7. Cross-Channel Deduplication (REVISED)'),

        h2('7.1 Dedup Engine \u2014 PostgreSQL-Based'),
        richPara([
          { text: 'V2 CHANGE: ', bold: true, color: 'C0392B' },
          { text: 'v0.1 specified Redis for dedup. At CS Pulse scale (hundreds of accounts, not millions), PostgreSQL handles dedup windows with a simple query. Add Redis only if query latency exceeds 100ms at scale (unlikely before 10K signals/day).' },
        ]),
        para(''),
        codePara('SELECT * FROM qualitative_signals'),
        codePara('WHERE account_id = :acct'),
        codePara('  AND created_at > now() - interval :dedup_window'),
        codePara('  AND intent_signals && ARRAY[:intent_codes]'),

        para(''),
        h2('7.2 Dedup Window Configuration'),
        makeTable(
          ['Intent Category', 'Default Window', 'Rationale'],
          [
            ['executive_escalation, champion_change', '72 hours', 'Fast-moving relationship events'],
            ['renewal_risk, expansion_interest', '7 days', 'Strategic signals evolve over days'],
            ['product_frustration, deployment_blocker', '48 hours', 'Operational issues need fast dedup'],
            ['competitor_mention, pricing_concern', '7 days', 'Evaluation cycles are multi-day'],
          ],
          [3500, 2000, 3860]
        ),

        para(''),
        h2('7.3 Merge Rules'),
        bullet('unified_sentiment_score: Weighted average (recent signals weighted higher via exponential decay)'),
        bullet('unified_urgency: Highest urgency across all child signals'),
        bullet('merged_intent_signals: Union of all detected intents'),
        bullet('merged_participants: Deduplicated union of all stakeholder_roles'),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 8. CONTEXT GRAPH COLLISION & INTEGRATION
        // ========================================
        h1('8. Context Graph Collision & Integration (REVISED)'),

        h2('8.1 Collision Check'),
        para('Before any CompositeSignal fires an alert, the system queries the Context Graph for matching nodes by account_id + subtype within a configurable collision window. If a match is found, QSIM enriches the existing CG node with qualitative fields (sentiment, stakeholder details). If no match is found, a new QUALITATIVE_SIGNAL node is created.'),

        para(''),
        h2('8.2 Intent-to-Node Mapping'),
        makeTable(
          ['QSIM Intent', 'CG Node Subtypes', 'Window', 'Action'],
          [
            ['executive_escalation', 'champion_loss, executive_escalation', '72h', 'Enrich CG, suppress QSIM'],
            ['champion_change', 'champion_loss, stakeholder_change', '72h', 'Enrich CG, suppress QSIM'],
            ['renewal_risk', 'churn_risk, renewal_signal', '7d', 'Enrich CG, suppress QSIM'],
            ['product_frustration', 'kpi_change, ticket (recurring)', '48h', 'Enrich CG, suppress QSIM'],
            ['expansion_interest', 'expansion_signal', '7d', 'Enrich CG, suppress QSIM'],
            ['deployment_blocker', 'ticket, kpi_change (P1)', '48h', 'Enrich CG, suppress QSIM'],
            ['competitor_mention', '(no CG equivalent)', 'N/A', 'New QUALITATIVE_SIGNAL node'],
            ['pricing_concern', '(no CG equivalent)', 'N/A', 'New QUALITATIVE_SIGNAL node'],
            ['feature_request', '(no CG equivalent)', 'N/A', 'New QUALITATIVE_SIGNAL node'],
          ],
          [2200, 3000, 800, 3360]
        ),

        para(''),
        h2('8.3 New QUALITATIVE_SIGNAL Node Type'),
        para('When a QSIM signal has no matching CG node, it creates a new context graph node:'),
        makeTable(
          ['Attribute', 'Value'],
          [
            ['node_type', 'SIGNAL'],
            ['node_subtype', 'qualitative_signal'],
            ['source_types', 'List of contributing source types'],
            ['sentiment_score', 'Unified sentiment from CompositeSignal'],
            ['intent_signals', 'Merged intent tags'],
            ['urgency', 'effective_urgency (structural or LLM)'],
            ['revenue_impact', 'null (SIGNAL nodes never carry revenue)'],
          ],
          [2500, 6860]
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 9. COMPOSITE SCORE FUSION
        // ========================================
        h1('9. Composite Score Fusion (REVISED)'),

        h2('9.1 Fusion Formula'),
        para('The composite health score blends quantitative KPI health with qualitative signal analysis:'),
        para(''),
        codePara('qual_score = (relationship_sentiment_norm x 0.40)'),
        codePara('           + (product_sentiment_norm     x 0.30)'),
        codePara('           + (urgency_score_norm_inv     x 0.20)'),
        codePara('           + (escalation_prob_norm_inv   x 0.10)'),
        codePara(''),
        codePara('composite = (quant_health x quant_weight) + (qual_score x qual_weight)'),
        para(''),
        para('Default weights: quant_weight=0.70, qual_weight=0.30. Configurable per customer via CustomerConfig.'),

        para(''),
        h2('9.2 Cold-Start Ramp (NEW)'),
        richPara([
          { text: 'V2 ADDITION: ', bold: true, color: 'C0392B' },
          { text: 'When QSIM is first enabled for a customer, there are zero historical qualitative signals. Without a ramp, 30% of health score would be zero. The ramp prevents health score crashes on day 1.' },
        ]),
        para(''),
        codePara('def get_qual_weight(account_id, target_qual_weight=0.30):'),
        codePara('    signal_count = QualitativeSignal.query.filter_by('),
        codePara('        account_id=account_id,'),
        codePara('        source_type__in=[\'slack\',\'email\',\'transcript\']'),
        codePara('    ).count()'),
        codePara('    MIN_SIGNALS_FOR_FULL_WEIGHT = 100'),
        codePara('    ramp = min(1.0, signal_count / MIN_SIGNALS_FOR_FULL_WEIGHT)'),
        codePara('    return target_qual_weight * ramp'),
        para(''),
        para('This ramps qual_weight from 0% to 30% over the first 100 signals per account.'),

        para(''),
        h2('9.3 Vertical-Specific Fusion Weights (NEW)'),
        richPara([
          { text: 'V2 ADDITION: ', bold: true, color: 'C0392B' },
          { text: 'Fixed fusion sub-weights are wrong for different verticals. DC2_S cares more about product/infra reliability; SaaS Premium is more relationship-driven.' },
        ]),
        para(''),
        makeTable(
          ['Dimension', 'DC2_S Weight', 'SaaS Premium Weight', 'Rationale'],
          [
            ['relationship_sentiment', '0.30', '0.45', 'SaaS renewals are relationship-driven'],
            ['product_sentiment', '0.40', '0.25', 'DC2_S cares more about infra reliability'],
            ['urgency (inverted)', '0.20', '0.20', 'Same across verticals'],
            ['escalation (inverted)', '0.10', '0.10', 'Same across verticals'],
          ],
          [2500, 1800, 2200, 2860]
        ),

        para(''),
        h2('9.4 Pillar Contribution Mapping'),
        para('Qualitative dimensions map to specific health pillars as score modifiers:'),
        makeTable(
          ['Qualitative Dimension', 'Pillar', 'Mechanism'],
          [
            ['relationship_sentiment', 'P4 Channel & Partner Health', 'Modifier on P4 score'],
            ['product_sentiment', 'P3 (AI Workload Perf / Customer Sentiment)', 'Modifier on P3 score'],
            ['intent: deployment_blocker', 'P1 Deployment Velocity', 'Negative modifier on P1'],
            ['intent: expansion_interest', 'P5 Expansion Readiness', 'Positive modifier on P5'],
            ['escalation_probability', 'All pillars (global)', 'Scales down composite proportionally'],
          ],
          [2800, 3500, 3060]
        ),

        para(''),
        h2('9.5 Score Velocity'),
        para('Score velocity measures the rate of change in composite health:'),
        codePara('signal_delta = composite_score_today - composite_score_7d_ago'),
        para(''),
        bullet('Delta < -10: Rapid deterioration \u2014 immediate alert'),
        bullet('Delta -5 to -10: Slow decline \u2014 flag for CSM review'),
        bullet('Delta > +10: Recovery \u2014 positive signal, track for ROI attribution'),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 10. ALERT ROUTING
        // ========================================
        h1('10. Alert Routing (REVISED)'),

        h2('10.1 Route Through Existing Webhook Engine'),
        richPara([
          { text: 'V2 CHANGE: ', bold: true, color: 'C0392B' },
          { text: 'v0.1 specified building new Slack SDK + SMTP connectors. CS Pulse already has playbook_webhook_engine.py and integration_api.py with n8n webhook support. QSIM alerts route through the existing infrastructure:' },
        ]),
        para(''),
        bullet('Slack alerts: via n8n Slack connector (already configured in integration registry)'),
        bullet('Email alerts: via n8n Email connector'),
        bullet('CRM tasks: via n8n Salesforce/HubSpot connector'),
        bullet('No new connectors needed. Alert routing rules map to webhook trigger configurations.'),

        para(''),
        h2('10.2 Routing Rules'),
        makeTable(
          ['Condition', 'Recipients', 'Channel', 'Urgency'],
          [
            ['sentiment < -0.5 + urgency high', 'CSM + CS Leader', 'Slack DM + Email', 'Critical'],
            ['executive_escalation detected', 'CS Leader + VP CS', 'Slack #cs-alerts + Email', 'Critical'],
            ['champion_change detected', 'CSM', 'Slack DM', 'High'],
            ['renewal_risk + ARR > $1M', 'CSM + CS Leader + VP CS', 'Slack + Email + CRM Task', 'Critical'],
            ['competitor_mention', 'CSM + Product', 'Slack #competitive-intel', 'Medium'],
            ['expansion_interest', 'CSM + Sales', 'Slack DM + CRM Task', 'Medium'],
            ['product_frustration (recurring, >3 signals)', 'CSM + Product', 'Slack + JIRA ticket', 'High'],
            ['score_velocity < -10 (7-day delta)', 'CSM + CS Leader', 'Slack + Email', 'High'],
          ],
          [3000, 2200, 2300, 1860]
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 11. RBAC & SENSITIVITY
        // ========================================
        h1('11. RBAC & Sensitivity'),

        h2('11.1 Role-Based Access'),
        makeTable(
          ['Role', 'Signal Access', 'Raw Text Access', 'Review Queue', 'Config'],
          [
            ['CSM', 'Own accounts only', 'Redacted', 'Own accounts', 'No'],
            ['CS Leader', 'All accounts', 'Full', 'All accounts', 'Read-only'],
            ['VP CS / Admin', 'All accounts', 'Full', 'All accounts', 'Full'],
            ['Product', 'product_frustration + feature_request only', 'Redacted', 'No', 'No'],
            ['Sales', 'expansion_interest + renewal_risk only', 'Redacted', 'No', 'No'],
          ],
          [1500, 2200, 1600, 2000, 2060]
        ),

        para(''),
        h2('11.2 Sensitivity Overrides'),
        bullet('Signals containing PII are auto-flagged and raw_text is encrypted at rest.'),
        bullet('Admin can set per-customer sensitivity level: standard, elevated, restricted.'),
        bullet('Restricted mode: raw_text purged after enrichment; only extracted fields retained.'),
        bullet('Auto-purge: raw_text deleted after 90 days regardless of sensitivity level.'),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 12. HUMAN-IN-THE-LOOP REVIEW
        // ========================================
        h1('12. Human-in-the-Loop Review (REVISED)'),

        h2('12.1 Review Queue Triggers'),
        bullet('Any confidence score < 0.6 on a critical field (sentiment, intent, urgency)'),
        bullet('enrichment_failed status (LLM returned invalid/partial response)'),
        bullet('consent_verified=false (transcript source without verified consent)'),
        bullet('dedup_confidence < 0.7 (uncertain merge decision)'),

        para(''),
        h2('12.2 Feedback Loop \u2014 Practical Implementation'),
        richPara([
          { text: 'V2 CHANGE: ', bold: true, color: 'C0392B' },
          { text: 'v0.1 mentioned "future fine-tuning" with no implementation path. V2 specifies a statistical approach:' },
        ]),
        para(''),
        numberedItem('Store all corrections in qualitative_signal_corrections table (original vs corrected values, tagged by vertical + intent type).'),
        numberedItem('Monthly: compute correction rates per intent type per vertical. If correction rate > 20% for an intent type, adjust confidence threshold upward for that type.'),
        numberedItem('Quarterly: update system prompt with top-5 most common correction patterns as few-shot examples.'),
        numberedItem('Skip fine-tuning entirely for v1. Statistical threshold adjustment gives 80% of the benefit at 1% of the cost.'),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 13. API CONTRACTS
        // ========================================
        h1('13. API Contracts (REVISED)'),

        h2('13.1 Ingestion Endpoint'),
        richPara([
          { text: 'V2 CHANGE: ', bold: true, color: 'C0392B' },
          { text: 'Uses the existing integration_api.py webhook endpoint, extended with QSIM field mapping.' },
        ]),
        para(''),
        para('POST /api/integrations/webhook/slack  (or /email, /transcript)', { bold: true }),
        para(''),
        para('Request body:', { bold: true }),
        codePara('{'),
        codePara('  "source_type": "slack",'),
        codePara('  "account_id": 301,'),
        codePara('  "customer_id": 407,'),
        codePara('  "timestamp": "2026-03-21T10:30:00Z",'),
        codePara('  "raw_text": "Hey team, we\'re evaluating ...",'),
        codePara('  "participant_list": ['),
        codePara('    {"name": "Jane Doe", "role": "VP Infrastructure"}'),
        codePara('  ],'),
        codePara('  "thread_or_channel_id": "C04ABCD1234",'),
        codePara('  "consent_verified": true'),
        codePara('}'),
        para(''),
        para('Response 202:', { bold: true }),
        codePara('{ "raw_signal_id": "uuid-here", "status": "queued" }'),

        para(''),
        h2('13.2 Review Queue Endpoint'),
        para('GET /api/v1/review-queue', { bold: true }),
        para('Returns paginated list of signals requiring human review. Filterable by account_id, intent_type, urgency.'),
        para(''),
        para('POST /api/v1/review-queue/{signal_id}/action', { bold: true }),
        para('Actions: approve (accept enrichment as-is), correct (provide corrected values), dismiss (mark as noise/irrelevant).'),

        para(''),
        h2('13.3 Composite Score Endpoint'),
        para('GET /api/v1/accounts/{account_id}/composite-score', { bold: true }),
        para('Returns current composite health score with breakdown: quant_health, qual_score, qual_weight (with ramp factor), composite_score, score_velocity (7-day delta), contributing_signals (recent QSIM signals), and fusion_weights.'),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 14. IMPLEMENTATION PHASES
        // ========================================
        h1('14. Implementation Phases (REVISED)'),

        h2('Phase 1 \u2014 Foundation (4\u20136 weeks) \u2014 SHIP THIS'),
        makeTable(
          ['Task', 'Existing Code to Extend', 'New Code', 'Effort'],
          [
            ['Extend QualitativeSignal model with enrichment columns', 'models.py', 'Alembic migration', '2 days'],
            ['Slack + Email webhook ingest via integration_api.py', 'integration_api.py', 'Field mapping for slack/email payloads', '3 days'],
            ['LLM enrichment service (vertical-aware prompts)', 'NEW', 'qsim_enrichment.py (~300 lines)', '5 days'],
            ['Structural urgency classifier', 'NEW', 'qsim_urgency.py (~100 lines)', '2 days'],
            ['CG collision check', 'utils/context_graph.py', 'Add collision_check() function', '3 days'],
            ['CG pre-emption subscriber', 'event_system.py', 'QSIMPreemptionSubscriber', '2 days'],
            ['Composite score fusion (with cold-start ramp)', 'utils/score_calculator.py', 'Add qual_modifier to health calc', '3 days'],
            ['Alert routing via webhook engine', 'playbook_webhook_engine.py', 'Add signal-type triggers', '2 days'],
            ['Basic review queue API', 'NEW', 'review_queue_api.py (~200 lines)', '3 days'],
            ['PostgreSQL dedup queries', 'NEW', 'SQL in enrichment service', '2 days'],
            ['Total Phase 1', '', '', '~27 dev-days'],
          ],
          [3000, 2500, 2500, 1360]
        ),

        para(''),
        h2('Phase 2 \u2014 Polish (3\u20134 weeks)'),
        bullet('Review queue React UI component'),
        bullet('RBAC enforcement on all QSIM endpoints'),
        bullet('Feedback loop dataset collection and correction table'),
        bullet('Confidence threshold calibration per intent type'),
        bullet('Cost monitoring dashboard (LLM calls, monthly spend)'),

        para(''),
        h2('Phase 3 \u2014 Transcript Ingestion (2 weeks)'),
        richPara([
          { text: 'BLOCKED ', bold: true, color: 'C0392B' },
          { text: 'on legal consent model resolution.' },
        ]),
        bullet('Transcript source connector (Zoom, Gong, or similar)'),
        bullet('Consent verification flow (participant opt-in tracking)'),
        bullet('Participant identification and role mapping'),

        para(''),
        h2('Phase 4 \u2014 Hardening (2 weeks)'),
        bullet('Load testing (10K signals/day throughput validation)'),
        bullet('Monitoring and alerting on LLM costs'),
        bullet('Dedup accuracy metrics and tuning'),
        bullet('A/B test fusion weights (70/30 vs alternatives)'),
        para(''),
        richPara([
          { text: 'Total timeline: ', bold: true },
          { text: 'Phase 1 ships in 4\u20136 weeks. Full system in 11\u201314 weeks (down from 14\u201318 in v0.1).' },
        ]),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 15. OPEN QUESTIONS
        // ========================================
        h1('15. Open Questions (REVISED)'),
        makeTable(
          ['#', 'Question', 'Owner', 'Status', 'V2 Resolution'],
          [
            ['1', 'Vector DB or Redis for semantic dedup?', 'Eng Lead', 'RESOLVED', 'Use PostgreSQL for v1. Add Redis only if query latency > 100ms at scale.'],
            ['2', 'Which LLM for enrichment?', 'Eng Lead', 'RESOLVED', 'Claude Sonnet via Anthropic SDK. Already in codebase dependencies.'],
            ['3', 'Consent for transcripts', 'Legal', 'OPEN', 'Blocks Phase 3. Phase 1 ships without transcripts.'],
            ['4', 'Default quant/qual fusion weights', 'CS Leader', 'RESOLVED', '70/30 with cold-start ramp. Vertical-specific sub-weights.'],
            ['5', 'competitor_mention routing to Product?', 'Product', 'OPEN', 'Low priority for Phase 1.'],
            ['6', 'Dedup window for executive_escalation', 'CS Leader', 'RESOLVED', '72 hours default, configurable per customer.'],
            ['7', 'Review queue SLA', 'CS Leader', 'OPEN', 'Suggest 4-hour SLA for critical, 24-hour for others.'],
          ],
          [500, 2500, 1200, 1200, 3960]
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 16. RISK REGISTER
        // ========================================
        h1('16. Risk Register (NEW)'),
        makeTable(
          ['Risk', 'Severity', 'Mitigation'],
          [
            ['LLM cost overrun on noisy Slack channels', 'High', 'Signal volume throttle: max 50 signals/account/day, priority queue for high-urgency'],
            ['Health score crash on QSIM enable (cold start)', 'Critical', 'Cold-start ramp: qual_weight = min(target, signal_count / 100)'],
            ['Duplicate alerts from CG + QSIM', 'High', 'CG collision check + alert dedup registry (PostgreSQL, not Redis)'],
            ['Low LLM accuracy for vertical-specific intents', 'Medium', 'Vertical context in prompts + feedback loop threshold calibration'],
            ['PII in raw_text column', 'High', 'Encrypt at rest, RBAC access controls, auto-purge after 90 days'],
            ['n8n webhook reliability for alert delivery', 'Medium', 'Retry with exponential backoff, dead letter queue for failed deliveries'],
          ],
          [3200, 1200, 4960]
        ),

        para(''),
        para(''),
        para('\u2014 End of Document \u2014', { bold: true, color: '888888', size: 18 }),
      ],
    },
  ],
});

// ============================================================
// Generate
// ============================================================

const outputPath = '/Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard/docs/qsim_engg_spec_V2.docx';

Packer.toBuffer(doc).then(buffer => {
  const dir = require('path').dirname(outputPath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(outputPath, buffer);
  console.log(`Document generated: ${outputPath}`);
  console.log(`Size: ${(buffer.length / 1024).toFixed(1)} KB`);
}).catch(err => {
  console.error('Error generating document:', err);
  process.exit(1);
});
