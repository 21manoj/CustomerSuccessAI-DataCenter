const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageNumber, PageBreak,
  ExternalHyperlink,
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
const TABLE_WIDTH = 9360;

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

function codeCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: GRAY, type: ShadingType.CLEAR },
    margins: cellMargins,
    children: [new Paragraph({
      children: [new TextRun({ text, font: 'Courier New', size: 16, color: '333333' })],
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

function bullet(text, level = 0) {
  return new Paragraph({
    numbering: { reference: 'bullets', level },
    spacing: { after: 80 },
    children: [new TextRun({ text, font: 'Arial', size: 20, color: '444444' })],
  });
}

function codePara(text) {
  return new Paragraph({
    spacing: { after: 80 },
    indent: { left: 360 },
    children: [new TextRun({ text, font: 'Courier New', size: 18, color: '333333' })],
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
// Document Content
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
        new Paragraph({ spacing: { before: 3000 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: 'CS PULSE', font: 'Arial', size: 56, bold: true, color: BLUE })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 }, children: [new TextRun({ text: 'Integration Framework', font: 'Arial', size: 44, color: '666666' })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [new TextRun({ text: 'Technical Knowledge Transfer Document', font: 'Arial', size: 24, color: '888888' })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 }, border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: BLUE, space: 1 } } }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [new TextRun({ text: 'Version 1.0 \u2014 March 20, 2026', font: 'Arial', size: 22, color: '666666' })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [new TextRun({ text: 'Classification: Internal / Contractor', font: 'Arial', size: 22, color: '999999' })] }),
        new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: 'Branch: feature/integration-framework', font: 'Courier New', size: 20, color: '888888' })] }),
        new Paragraph({ spacing: { before: 1200 } }),
        para('Prepared for: n8n Integration Contractor', { bold: true }),
        para('Prepared by: CS Pulse Engineering Team'),
        para('E2E Test Status: 15/15 PASS', { bold: true, color: '2E7D32' }),
      ],
    },
    // ====== MAIN CONTENT ======
    {
      properties: {
        page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } },
      },
      headers: {
        default: new Header({ children: [new Paragraph({ border: { bottom: { style: BorderStyle.SINGLE, size: 1, color: 'CCCCCC', space: 4 } }, children: [new TextRun({ text: 'CS Pulse Integration Framework \u2014 Knowledge Transfer', font: 'Arial', size: 16, color: '888888', italics: true })] })] }),
      },
      footers: {
        default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Page ', font: 'Arial', size: 16, color: '888888' }), new TextRun({ children: [PageNumber.CURRENT], font: 'Arial', size: 16, color: '888888' })] })] }),
      },
      children: [
        // ========================================
        // 1. EXECUTIVE SUMMARY
        // ========================================
        h1('1. Executive Summary'),
        para('This document describes the CS Pulse Integration Framework \u2014 a complete system for connecting external data sources (Salesforce, HubSpot, Zendesk) and workflow orchestrators (n8n) to the CS Pulse platform.'),
        para('The framework provides:'),
        bullet('Inbound data ingestion from CRM, support, and marketing tools via webhooks'),
        bullet('Outbound playbook triggers that fire n8n workflows when health conditions are met'),
        bullet('Field mapping engine that transforms external schemas to CS Pulse entities'),
        bullet('CS Ops monitoring dashboard with real-time sync health and audit trails'),
        bullet('MCP tools enabling Claude AI to manage integrations and trigger workflows'),
        para('All features are tested end-to-end with loopback stubs (15/15 tests passing).', { bold: true }),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 2. ARCHITECTURE
        // ========================================
        h1('2. Architecture Overview'),
        h2('2.1 Three-Layer Design'),
        para('The integration framework uses a three-layer architecture separating concerns:'),

        makeTable(
          ['Layer', 'Role', 'Technology', 'Responsibility'],
          [
            ['Layer 1: CS Pulse Backend', 'Data Platform', 'Flask + PostgreSQL', 'Webhook ingest, field mapping, dedup, audit trail'],
            ['Layer 2: n8n Cloud', 'Orchestration', 'n8n Workflow Engine', 'Scheduled syncs, multi-step playbooks, retry logic'],
            ['Layer 3: Claude MCP', 'AI Agent', 'MCP Protocol', 'Real-time queries, trigger workflows, health checks'],
          ],
          [2000, 1500, 2000, 3860]
        ),

        para(''),
        h2('2.2 Data Flow'),
        para('Inbound (External \u2192 CS Pulse):'),
        bullet('n8n fetches records from SFDC/HubSpot/Zendesk on schedule'),
        bullet('n8n POSTs normalized data to CS Pulse webhook endpoint'),
        bullet('CS Pulse applies field mapping, deduplicates, and upserts into PostgreSQL'),
        bullet('WebhookEvent table stores raw payload for replay/debugging'),
        para(''),
        para('Outbound (CS Pulse \u2192 n8n):'),
        bullet('Health score engine recalculates scores (after KPI ingest)'),
        bullet('Trigger engine evaluates all active PlaybookWebhookTriggers'),
        bullet('If condition met (e.g., health drops below 50): fires webhook to n8n'),
        bullet('n8n workflow executes multi-step playbook (Slack + email + SFDC task)'),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 3. DATABASE SCHEMA
        // ========================================
        h1('3. Database Schema'),
        para('Five new tables support the integration framework. All tables use customer_id for tenant isolation.'),
        para('Migration script: backend/migrations/add_integration_tables.py', { italics: true }),
        para(''),

        h2('3.1 integration_connectors'),
        para('Registry of configured external data connectors per customer.'),
        makeTable(
          ['Column', 'Type', 'Description'],
          [
            ['connector_id', 'Integer PK', 'Auto-increment primary key'],
            ['customer_id', 'Integer FK', 'Tenant isolation (FK to customers)'],
            ['connector_type', 'String(50)', 'sfdc | hubspot | zendesk | n8n | csv_upload | custom_webhook'],
            ['connector_name', 'String(255)', 'Human label (e.g., "Production Salesforce")'],
            ['auth_type', 'String(30)', 'oauth2 | api_key | webhook_secret | basic_auth'],
            ['auth_config_encrypted', 'Text', 'Encrypted JSON credentials (encrypt at rest in prod)'],
            ['webhook_url', 'String(500)', 'Inbound webhook URL (for n8n push mode)'],
            ['webhook_secret_hash', 'String(64)', 'SHA-256 hash of HMAC secret for signature verification'],
            ['sync_direction', 'String(20)', 'inbound | outbound | bidirectional'],
            ['sync_frequency_minutes', 'Integer', 'Sync interval (0 = webhook/real-time only)'],
            ['sync_enabled', 'Boolean', 'Master toggle for sync'],
            ['field_mapping', 'JSON', 'External field \u2192 CS Pulse field mapping per entity type'],
            ['entity_mapping', 'JSON', 'External objects \u2192 CS Pulse entities (Account, Case, etc.)'],
            ['status', 'String(30)', 'pending_setup | active | paused | error | disabled | expired'],
            ['last_sync_at', 'DateTime', 'Timestamp of last successful sync'],
            ['last_sync_records', 'Integer', 'Records processed in last sync'],
            ['consecutive_errors', 'Integer', 'Error streak counter (reset on success)'],
          ],
          [2200, 1800, 5360]
        ),

        para(''),
        h2('3.2 integration_sync_logs'),
        para('Audit trail of every sync operation. One row per sync attempt.'),
        makeTable(
          ['Column', 'Type', 'Description'],
          [
            ['log_id', 'Integer PK', 'Auto-increment primary key'],
            ['connector_id', 'Integer FK', 'Which connector ran this sync'],
            ['sync_type', 'String(30)', 'full | incremental | webhook_push | manual'],
            ['sync_status', 'String(20)', 'started | success | partial | error'],
            ['records_fetched', 'Integer', 'Total records received from source'],
            ['records_created', 'Integer', 'New records created in CS Pulse'],
            ['records_updated', 'Integer', 'Existing records updated'],
            ['records_errored', 'Integer', 'Records that failed processing'],
            ['error_details', 'JSON', 'Array of per-record errors [{field, error, row}]'],
            ['watermark_value', 'String', 'High-water mark for incremental sync (last modified)'],
            ['duration_seconds', 'Float', 'Wall clock time for sync operation'],
          ],
          [2200, 1800, 5360]
        ),

        para(''),
        h2('3.3 webhook_events'),
        para('Raw inbound webhook payloads stored before processing. Enables replay and debugging.'),
        makeTable(
          ['Column', 'Type', 'Description'],
          [
            ['event_id', 'Integer PK', 'Auto-increment primary key'],
            ['event_type', 'String(100)', 'e.g., account.updated, ticket.created, deal.won'],
            ['source_system', 'String(50)', 'sfdc | hubspot | zendesk | n8n'],
            ['source_event_id', 'String(255)', 'Dedup key from source system'],
            ['payload', 'JSON', 'Complete raw request body'],
            ['headers', 'JSON', 'Request headers (for signature replay)'],
            ['processing_status', 'String(20)', 'pending | processing | processed | failed | skipped'],
            ['target_entity', 'String(50)', 'What was created: accounts | context_nodes | etc.'],
            ['target_id', 'Integer', 'ID of created/updated record'],
            ['retry_count', 'Integer', 'Number of processing retries'],
          ],
          [2200, 1800, 5360]
        ),

        para(''),
        h2('3.4 playbook_webhook_triggers'),
        para('Configuration for outbound webhooks fired when playbook conditions are met.'),
        makeTable(
          ['Column', 'Type', 'Description'],
          [
            ['trigger_id', 'Integer PK', 'Auto-increment primary key'],
            ['trigger_name', 'String(255)', 'Human label (e.g., "Critical Health Alert")'],
            ['trigger_type', 'String(50)', 'health_drop | health_critical | signal_detected | renewal_approaching | expansion_ready'],
            ['trigger_condition', 'JSON', '{"metric": "health_score", "operator": "drops_below", "threshold": 50}'],
            ['webhook_url', 'String(500)', 'n8n webhook URL to POST to'],
            ['webhook_secret_hash', 'String(64)', 'HMAC secret for signing outbound payloads'],
            ['cooldown_minutes', 'Integer', 'Minimum time between fires for same account'],
            ['max_fires_per_day', 'Integer', 'Daily rate limit per trigger'],
            ['account_filter', 'JSON', 'Scope: null=all, {"account_ids":[...]}, {"min_arr":500000}'],
            ['enabled', 'Boolean', 'Master toggle'],
          ],
          [2200, 1800, 5360]
        ),

        para(''),
        h2('3.5 playbook_webhook_logs'),
        para('Audit trail of every outbound webhook fire.'),
        makeTable(
          ['Column', 'Type', 'Description'],
          [
            ['log_id', 'Integer PK', 'Auto-increment primary key'],
            ['trigger_id', 'Integer FK', 'Which trigger fired'],
            ['account_id', 'Integer FK', 'Which account triggered this'],
            ['fire_reason', 'Text', '"health_score changed from 62 to 44 for K2 Hyperscale"'],
            ['payload_sent', 'JSON', 'Complete payload sent to webhook'],
            ['response_status', 'Integer', 'HTTP response code from n8n'],
            ['duration_ms', 'Integer', 'Round-trip time in milliseconds'],
            ['status', 'String(20)', 'success | error | timeout | skipped_cooldown'],
          ],
          [2200, 1800, 5360]
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 4. API REFERENCE
        // ========================================
        h1('4. API Reference'),
        para('All endpoints require X-Customer-ID header for tenant isolation. Public webhook endpoint uses HMAC-SHA256 signature verification.'),
        para('Base URL: http://localhost:5059 (dev) or https://your-domain.com (prod)', { italics: true }),
        para(''),

        h2('4.1 Connector Management'),
        makeTable(
          ['Method', 'Endpoint', 'Description', 'Auth'],
          [
            ['GET', '/api/integrations/connector-types', 'Available connector types with metadata', 'Public'],
            ['GET', '/api/integrations/connectors', 'List all connectors for customer', 'X-Customer-ID'],
            ['POST', '/api/integrations/connectors', 'Create new connector (returns secret once)', 'X-Customer-ID'],
            ['PUT', '/api/integrations/connectors/<id>', 'Update connector config (name, freq, mapping)', 'X-Customer-ID'],
            ['DELETE', '/api/integrations/connectors/<id>', 'Soft-delete (status=disabled)', 'X-Customer-ID'],
            ['POST', '/api/integrations/connectors/<id>/test', 'Loopback connectivity test', 'X-Customer-ID'],
          ],
          [1000, 3500, 3360, 1500]
        ),

        para(''),
        h2('4.2 Data Ingestion'),
        makeTable(
          ['Method', 'Endpoint', 'Description', 'Auth'],
          [
            ['POST', '/api/integrations/ingest', 'Ingest single record with field mapping', 'X-Customer-ID'],
            ['POST', '/api/integrations/ingest/batch', 'Batch ingest multiple records', 'X-Customer-ID'],
            ['POST', '/api/integrations/webhook/<cust_id>/<type>', 'Public webhook for n8n push', 'HMAC Signature'],
          ],
          [1000, 4000, 2860, 1500]
        ),

        para(''),
        h3('Single Ingest Payload'),
        codePara('{'),
        codePara('  "source": "sfdc",'),
        codePara('  "entity_type": "account",'),
        codePara('  "event_type": "created",'),
        codePara('  "data": {'),
        codePara('    "Name": "Acme Corp",'),
        codePara('    "AnnualRevenue": 2500000,'),
        codePara('    "Industry": "Technology"'),
        codePara('  },'),
        codePara('  "source_id": "sfdc_001_acme"'),
        codePara('}'),

        para(''),
        h3('Batch Ingest Payload'),
        codePara('{'),
        codePara('  "source": "hubspot",'),
        codePara('  "records": ['),
        codePara('    {"entity_type": "company", "data": {"name": "Globex", "annualrevenue": 1800000}},'),
        codePara('    {"entity_type": "deal", "data": {"dealname": "Expansion", "amount": 450000}}'),
        codePara('  ]'),
        codePara('}'),

        para(''),
        h2('4.3 Monitoring'),
        makeTable(
          ['Method', 'Endpoint', 'Description'],
          [
            ['GET', '/api/integrations/health', 'Overall integration health (status, 24h stats, errors)'],
            ['GET', '/api/integrations/sync-logs', 'Recent sync activity (limit param)'],
            ['GET', '/api/integrations/connectors/<id>/logs', 'Sync history for specific connector'],
          ],
          [1000, 4000, 4360]
        ),

        para(''),
        h2('4.4 Playbook Webhook Triggers'),
        makeTable(
          ['Method', 'Endpoint', 'Description'],
          [
            ['GET', '/api/integrations/playbook-triggers', 'List all outbound triggers'],
            ['POST', '/api/integrations/playbook-triggers', 'Create trigger (returns secret)'],
            ['PUT', '/api/integrations/playbook-triggers/<id>', 'Update trigger config'],
            ['DELETE', '/api/integrations/playbook-triggers/<id>', 'Disable trigger (soft-delete)'],
            ['POST', '/api/integrations/playbook-triggers/<id>/test', 'Test-fire with mock context'],
            ['GET', '/api/integrations/playbook-triggers/fire-log', 'Recent webhook fire history'],
          ],
          [1000, 4500, 3860]
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 5. FIELD MAPPING
        // ========================================
        h1('5. Field Mapping Engine'),
        para('The field mapping engine transforms external data schemas to CS Pulse entities. Default mappings are pre-configured for SFDC, HubSpot, and Zendesk. Custom mappings can be set per connector.'),
        para(''),

        h2('5.1 Default SFDC Mapping'),
        makeTable(
          ['SFDC Field (Account)', 'CS Pulse Field', 'Target Entity'],
          [
            ['Name', 'account_name', 'accounts'],
            ['AnnualRevenue', 'revenue', 'accounts'],
            ['Industry', 'industry', 'accounts'],
            ['BillingCountry', 'region', 'accounts'],
            ['Id', 'external_account_id', 'accounts'],
            ['AccountStatus__c', 'account_status', 'accounts'],
          ],
          [3000, 3000, 3360]
        ),

        para(''),
        h2('5.2 Default HubSpot Mapping'),
        makeTable(
          ['HubSpot Field (companies)', 'CS Pulse Field', 'Target Entity'],
          [
            ['name', 'account_name', 'accounts'],
            ['annualrevenue', 'revenue', 'accounts'],
            ['industry', 'industry', 'accounts'],
            ['country', 'region', 'accounts'],
            ['hs_object_id', 'external_account_id', 'accounts'],
          ],
          [3000, 3000, 3360]
        ),

        para(''),
        h2('5.3 Default Zendesk Mapping'),
        makeTable(
          ['Zendesk Field (tickets)', 'CS Pulse Field', 'Target Entity'],
          [
            ['subject', 'title', 'context_nodes (SIGNAL)'],
            ['priority', 'properties.priority', 'context_nodes (SIGNAL)'],
            ['status', 'properties.status', 'context_nodes (SIGNAL)'],
            ['created_at', 'occurred_at', 'context_nodes (SIGNAL)'],
            ['satisfaction_rating.score', 'properties.csat_score', 'context_nodes (SIGNAL)'],
          ],
          [3000, 3000, 3360]
        ),

        para(''),
        h2('5.4 Entity Type Routing'),
        para('The ingest engine routes entities to the correct CS Pulse model:'),
        makeTable(
          ['External Entity', 'CS Pulse Target', 'Node Type'],
          [
            ['account / company / companies', 'accounts table', 'N/A (direct model)'],
            ['ticket / case / signal', 'context_nodes', 'SIGNAL'],
            ['opportunity / deal', 'context_nodes', 'DECISION or OUTCOME (by stage)'],
            ['contact / stakeholder / user', 'context_nodes', 'STAKEHOLDER'],
            ['kpi / metric', 'dc2s_kpis table', 'N/A (direct model)'],
            ['(anything else)', 'context_nodes', 'EXTERNAL_CONTEXT'],
          ],
          [3000, 3000, 3360]
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 6. TRIGGER ENGINE
        // ========================================
        h1('6. Playbook Trigger Engine'),
        para('The trigger engine evaluates conditions against health score changes and fires outbound webhooks to n8n for playbook execution.'),
        para(''),

        h2('6.1 Trigger Condition Operators'),
        makeTable(
          ['Operator', 'Description', 'Example'],
          [
            ['drops_below', 'Previous >= threshold AND current < threshold', 'Health drops from 65 to 42 (threshold 50)'],
            ['rises_above', 'Previous <= threshold AND current > threshold', 'Health rises from 48 to 72 (threshold 70)'],
            ['less_than', 'Current < threshold (no previous needed)', 'Health = 42 < 50'],
            ['greater_than', 'Current > threshold', 'NRR = 115 > 100'],
            ['equals', 'Current == threshold (within 0.01)', 'Metric exactly matches target'],
            ['changed_by', 'abs(current - previous) >= threshold', 'Health changed by 15+ points'],
          ],
          [2000, 4000, 3360]
        ),

        para(''),
        h2('6.2 Loopback Stub Mode'),
        para('In development, the engine uses an in-memory loopback stub instead of making real HTTP calls. This enables full E2E testing without external services.'),
        bullet('Toggle: _USE_LOOPBACK_STUB = True (dev) / False (production)'),
        bullet('Stub log: _LOOPBACK_STUB_LOG stores all "fired" webhooks in memory'),
        bullet('Access via: get_loopback_log() and clear_loopback_log()'),
        bullet('Production: Set _USE_LOOPBACK_STUB = False and configure real n8n webhook URLs'),

        para(''),
        h2('6.3 Webhook Payload Structure'),
        para('Every outbound webhook fire sends this JSON payload:'),
        codePara('{'),
        codePara('  "event": "playbook_trigger",'),
        codePara('  "trigger_id": 3,'),
        codePara('  "trigger_name": "Critical Health Alert",'),
        codePara('  "trigger_type": "health_critical",'),
        codePara('  "customer_id": 396,'),
        codePara('  "account_id": 301,'),
        codePara('  "account_name": "K2 Hyperscale",'),
        codePara('  "account_arr": 4200000,'),
        codePara('  "timestamp": "2026-03-20T19:00:00Z",'),
        codePara('  "context": {'),
        codePara('    "health_score": 42,'),
        codePara('    "previous_health_score": 65'),
        codePara('  }'),
        codePara('}'),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 7. MCP TOOLS
        // ========================================
        h1('7. MCP Tools for Claude'),
        para('Nine MCP tools allow Claude to manage integrations conversationally. These are in backend/mcp_server/cs_pulse_integrations.py.'),
        para(''),

        makeTable(
          ['MCP Tool', 'Purpose', 'Example Prompt'],
          [
            ['list_integration_connectors', 'Show all configured connectors', '"What integrations are set up?"'],
            ['create_integration_connector', 'Register new external source', '"Connect our Salesforce instance"'],
            ['get_integration_health', 'Overall sync health dashboard', '"How are our integrations doing?"'],
            ['get_sync_logs', 'Recent sync activity', '"Show me recent sync failures"'],
            ['test_connector', 'Verify connectivity (loopback)', '"Test the Zendesk connector"'],
            ['trigger_n8n_workflow', 'Fire n8n workflow via webhook', '"Run re-engagement playbook for K2"'],
            ['list_playbook_webhook_triggers', 'Show outbound trigger configs', '"What playbook triggers are active?"'],
            ['create_playbook_webhook_trigger', 'Set up new outbound trigger', '"Alert me when health drops below 50"'],
            ['fire_playbook_webhook', 'Manually fire a trigger', '"Fire the escalation trigger for K2"'],
          ],
          [3000, 2800, 3560]
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 8. CS OPS DASHBOARD
        // ========================================
        h1('8. CS Ops Dashboard (Frontend)'),
        para('Route: /dc-dashboard/ops'),
        para('Component: src/components/ops/CSOpsIntegrationDashboard.tsx (1,011 lines)'),
        para(''),

        h2('8.1 Tab Structure'),
        makeTable(
          ['Tab', 'Content', 'Actions Available'],
          [
            ['Overview', 'Health cards (active/records/errors/pending) + connector grid + recent sync', 'Test connector, pause/resume'],
            ['Connectors', 'Detailed cards per connector (mapping, errors, config)', 'Test, pause, delete, view mapping'],
            ['Activity', 'Full sync log with record breakdowns', 'View error details'],
            ['Triggers', 'Playbook trigger cards with condition + fire history', 'Test-fire, create trigger'],
          ],
          [1500, 4500, 3360]
        ),

        para(''),
        h2('8.2 API Calls'),
        para('The dashboard makes 5 parallel fetch calls on mount:'),
        bullet('GET /api/integrations/health'),
        bullet('GET /api/integrations/connectors'),
        bullet('GET /api/integrations/sync-logs?limit=30'),
        bullet('GET /api/integrations/playbook-triggers'),
        bullet('GET /api/integrations/connector-types'),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 9. FILE REFERENCE
        // ========================================
        h1('9. File Reference'),
        makeTable(
          ['File', 'Lines', 'Purpose'],
          [
            ['backend/integration_models.py', '468', '5 DB models + default field mappings + connector type metadata'],
            ['backend/integration_api.py', '1,023', '12 REST endpoints: CRUD, ingest, health, testing'],
            ['backend/playbook_webhook_engine.py', '591', 'Trigger engine + condition evaluation + webhook fire + 6 API endpoints'],
            ['backend/mcp_server/cs_pulse_integrations.py', '523', '9 MCP tools for Claude agent integration management'],
            ['backend/migrations/add_integration_tables.py', '76', 'DB migration script (idempotent, safe to re-run)'],
            ['backend/tests/test_integration_framework.py', '594', '15 E2E tests with loopback stubs'],
            ['src/components/ops/CSOpsIntegrationDashboard.tsx', '1,011', 'React UI: 4-tab ops dashboard with modals'],
            ['backend/auth_middleware.py', 'Modified', 'Added X-Customer-ID header auth for integration endpoints'],
            ['backend/app_v3_minimal.py', 'Modified', 'Registered integration_api + playbook_webhook_api blueprints'],
            ['src/App.tsx', 'Modified', 'Added /dc-dashboard/ops route + CSOpsIntegrationDashboard import'],
          ],
          [4000, 800, 4560]
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 10. n8n SETUP GUIDE
        // ========================================
        h1('10. n8n Integration Setup Guide'),
        para('This section describes how to connect n8n Cloud to CS Pulse for the contractor.'),
        para(''),

        h2('10.1 Inbound: n8n \u2192 CS Pulse'),
        para('Step 1: Create a connector in CS Pulse (via UI or MCP tool)'),
        codePara('POST /api/integrations/connectors'),
        codePara('{ "connector_type": "n8n", "connector_name": "n8n Production" }'),
        para('Save the returned webhook_secret and webhook_endpoint.', { bold: true }),
        para(''),
        para('Step 2: In n8n, create an HTTP Request node:'),
        bullet('Method: POST'),
        bullet('URL: https://your-cs-pulse.com/api/integrations/webhook/<customer_id>/n8n'),
        bullet('Header: X-Webhook-Signature = sha256=<HMAC of body with secret>'),
        bullet('Body: { "entity_type": "account", "data": { ... mapped fields ... } }'),
        para(''),
        para('Step 3: Connect n8n trigger (SFDC/HubSpot/Zendesk node) \u2192 field mapping \u2192 HTTP Request node'),

        para(''),
        h2('10.2 Outbound: CS Pulse \u2192 n8n'),
        para('Step 1: In n8n, create a Webhook trigger node (get the URL)'),
        para('Step 2: Create a playbook trigger in CS Pulse:'),
        codePara('POST /api/integrations/playbook-triggers'),
        codePara('{ "trigger_name": "Health Alert",'),
        codePara('  "trigger_type": "health_critical",'),
        codePara('  "trigger_condition": {"metric":"health_score","operator":"drops_below","threshold":50},'),
        codePara('  "webhook_url": "https://your-n8n.com/webhook/health-alert" }'),
        para(''),
        para('Step 3: n8n workflow receives the payload and executes:'),
        bullet('Parse account_name, health_score, account_arr from payload'),
        bullet('Create Slack alert in #cs-alerts channel'),
        bullet('Create SFDC Task for account owner'),
        bullet('Send email to VP CS with risk summary'),
        bullet('Log action back to CS Pulse via ingest endpoint'),

        para(''),
        h2('10.3 Production Checklist'),
        bullet('Set _USE_LOOPBACK_STUB = False in playbook_webhook_engine.py'),
        bullet('Configure real HMAC secrets (generated on connector creation)'),
        bullet('Set up n8n error handling (retry on 5xx, alert on persistent failure)'),
        bullet('Configure webhook timeout (default 30s \u2014 increase for complex workflows)'),
        bullet('Set up monitoring: alert if consecutive_errors > 3 on any connector'),
        bullet('Encrypt auth_config_encrypted column (use ENCRYPTION_KEY env var)'),
        bullet('Rate limit public webhook endpoint in nginx/cloudfront'),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 11. TESTING
        // ========================================
        h1('11. E2E Test Suite'),
        para('Run: python3 tests/test_integration_framework.py', { bold: true }),
        para('Requires: Flask server running on port 5059 with DATABASE_URL set.'),
        para(''),
        makeTable(
          ['#', 'Test', 'What It Verifies'],
          [
            ['01', 'Connector Types', 'GET returns all 6 types (sfdc, hubspot, zendesk, n8n, csv, custom)'],
            ['02', 'Create Connectors', 'POST creates 4 connectors, returns secrets + endpoints'],
            ['03', 'List Connectors', 'GET returns \u22654 connectors'],
            ['04', 'Test Connector', 'Loopback creates/verifies/deletes test account'],
            ['05', 'Ingest SFDC Account', 'Field mapping: SFDC Name\u2192account_name, AnnualRevenue\u2192revenue'],
            ['06', 'Ingest Zendesk Ticket', 'Creates SIGNAL context node from ticket data'],
            ['07', 'Batch Ingest HubSpot', '3 records: 2 companies + 1 deal (Closed Won \u2192 OUTCOME)'],
            ['08', 'Create Trigger', 'Playbook webhook trigger with health_critical condition'],
            ['09', 'Test-Fire Trigger', 'Fires trigger with mock context, loopback confirms'],
            ['10', 'Engine Evaluation', 'Direct engine call: evaluates triggers programmatically'],
            ['11', 'Integration Health', 'GET /health returns overall status + connector counts'],
            ['12', 'Sync Logs', 'GET /sync-logs returns batch ingest log entry'],
            ['13', 'Fire Log', 'GET /fire-log returns webhook fire history'],
            ['14', 'Update Connector', 'PUT changes name + sync frequency'],
            ['15', 'Deactivate Connector', 'DELETE sets status=disabled, sync_enabled=false'],
          ],
          [500, 2500, 6360]
        ),

        new Paragraph({ children: [new PageBreak()] }),

        // ========================================
        // 12. SECURITY
        // ========================================
        h1('12. Security Considerations'),
        bullet('Webhook secrets are returned only once on creation (never stored in plaintext)'),
        bullet('HMAC-SHA256 signature verification on all public webhook endpoints'),
        bullet('Tenant isolation: every query filters by customer_id'),
        bullet('X-Customer-ID header auth is temporary \u2014 replace with API key auth for production'),
        bullet('auth_config_encrypted column must use AES-256 encryption with ENCRYPTION_KEY env var'),
        bullet('Rate limiting needed on /api/integrations/webhook/* (add nginx or CloudFront rule)'),
        bullet('Webhook payload size limit: add max_content_length check (recommended: 1MB)'),
        bullet('HMAC secret rotation: add endpoint to regenerate secret (invalidates old one)'),

        para(''),
        h1('13. Known Limitations'),
        bullet('Loopback stub mode is ON by default \u2014 must toggle for production'),
        bullet('No OAuth2 flow implemented yet \u2014 connectors use webhook_secret auth only'),
        bullet('Field mapping is static per connector \u2014 no per-record dynamic transforms'),
        bullet('No incremental sync watermarking \u2014 n8n handles this via its own scheduling'),
        bullet('No webhook retry queue \u2014 failed inbound events stay in "failed" status (manual replay)'),
        bullet('Daily fire counter (fire_count_today) does not auto-reset at midnight yet'),
      ],
    },
  ],
});

// ============================================================
// Generate
// ============================================================

const outputPath = process.argv[2] || '/Users/manojgupta/CustomerSuccessAI-DataCenter/.claude/worktrees/focused-poincare/kpi-dashboard/docs/CS_Pulse_Integration_Framework_KT.docx';

Packer.toBuffer(doc).then(buffer => {
  const dir = require('path').dirname(outputPath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(outputPath, buffer);
  console.log(`Document generated: ${outputPath}`);
  console.log(`Size: ${(buffer.length / 1024).toFixed(1)} KB`);
});
