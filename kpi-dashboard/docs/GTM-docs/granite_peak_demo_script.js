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
const GREEN = '2E7D32';
const RED = 'C62828';
const ORANGE = 'E65100';
const GRAY = 'F5F5F5';
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
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, color: WHITE, font: 'Arial', size: 20 })] })],
  });
}

function cell(text, width, opts = {}) {
  const fill = opts.fill || WHITE;
  const color = opts.color || '333333';
  const bold = opts.bold || false;
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill, type: ShadingType.CLEAR },
    margins: cellMargins,
    children: [new Paragraph({
      children: [new TextRun({ text, font: 'Arial', size: 20, color, bold })],
    })],
  });
}

function heading(text, level = HeadingLevel.HEADING_1) {
  return new Paragraph({ heading: level, children: [new TextRun({ text, font: 'Arial', bold: true })] });
}

function body(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 120 },
    children: [new TextRun({ text, font: 'Arial', size: 22, ...opts })],
  });
}

function bullet(text, ref = 'bullets') {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    children: [new TextRun({ text, font: 'Arial', size: 22 })],
  });
}

function highlight(label, value, color = BLUE) {
  return new Paragraph({
    spacing: { after: 80 },
    children: [
      new TextRun({ text: `${label}: `, font: 'Arial', size: 22, bold: true, color }),
      new TextRun({ text: value, font: 'Arial', size: 22 }),
    ],
  });
}

function spacer() {
  return new Paragraph({ spacing: { after: 200 }, children: [] });
}

// ============================================================
// Document
// ============================================================
const doc = new Document({
  styles: {
    default: { document: { run: { font: 'Arial', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 36, bold: true, font: 'Arial', color: BLUE },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: 'Arial', color: BLUE },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 24, bold: true, font: 'Arial', color: '444444' },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '\u2022', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: 'numbers', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1200, bottom: 1200, left: 1200 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: BLUE, space: 4 } },
          children: [
            new TextRun({ text: 'CS Pulse Demo Script', font: 'Arial', size: 18, color: BLUE, bold: true }),
            new TextRun({ text: '    |    Granite Peak Capital    |    Confidential', font: 'Arial', size: 18, color: '999999' }),
          ],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: 'Page ', font: 'Arial', size: 16, color: '999999' }),
            new TextRun({ children: [PageNumber.CURRENT], font: 'Arial', size: 16, color: '999999' }),
          ],
        })],
      }),
    },
    children: [
      // ============================================================
      // COVER
      // ============================================================
      spacer(), spacer(), spacer(),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 },
        children: [new TextRun({ text: 'CS PULSE', font: 'Arial', size: 56, bold: true, color: BLUE })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
        children: [new TextRun({ text: 'Revenue Intelligence Platform', font: 'Arial', size: 32, color: '666666' })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 40 },
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: BLUE, space: 8 } },
        children: [new TextRun({ text: 'DEMO NARRATIVE SCRIPT', font: 'Arial', size: 28, bold: true, color: '333333' })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 },
        children: [new TextRun({ text: 'Granite Peak Capital Portfolio', font: 'Arial', size: 24, color: '666666' })] }),

      // Portfolio summary box
      new Table({
        width: { size: 9840, type: WidthType.DXA },
        columnWidths: [2460, 2460, 2460, 2460],
        rows: [
          new TableRow({ children: [
            headerCell('Portfolio', 2460), headerCell('Total ARR', 2460),
            headerCell('Accounts', 2460), headerCell('Industries', 2460),
          ]}),
          new TableRow({ children: [
            cell('Granite Peak Capital', 2460, { bold: true }),
            cell('$68.7M', 2460, { bold: true, color: GREEN }),
            cell('18 portcos', 2460),
            cell('18 unique', 2460),
          ]}),
        ],
      }),
      spacer(),

      new Table({
        width: { size: 9840, type: WidthType.DXA },
        columnWidths: [3280, 3280, 3280],
        rows: [
          new TableRow({ children: [
            cell('3 Critical', 3280, { fill: 'FFEBEE', color: RED, bold: true }),
            cell('3 At-Risk', 3280, { fill: 'FFF3E0', color: ORANGE, bold: true }),
            cell('12 Healthy', 3280, { fill: 'E8F5E9', color: GREEN, bold: true }),
          ]}),
        ],
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // ============================================================
      // ACT 1: THE BURNING PLATFORM
      // ============================================================
      heading('Act 1: The Burning Platform', HeadingLevel.HEADING_1),
      body('Open the CRO Dashboard. Three accounts are in crisis. This is what the CRO sees Monday morning.'),
      spacer(),

      heading('Scene 1: Vertex Compute \u2014 Champion Loss', HeadingLevel.HEADING_2),
      highlight('ARR', '$8.2M \u2014 Largest account in portfolio'),
      highlight('Health', '35 \u2192 Critical', RED),
      highlight('Story Arc', 'Champion Loss'),
      highlight('Renewal', 'June 15, 2026 \u2014 92 days away'),
      spacer(),
      body('NARRATIVE (say this):'),
      new Paragraph({ spacing: { after: 120 }, indent: { left: 400 },
        children: [new TextRun({ text: '"Vertex Compute is our $8.2M flagship. Their CTO Alex Rivera \u2014 our champion who drove the original deal \u2014 resigned in January. The new CTO, Priya Sharma, favors competitor cloud solutions. GPU utilization crashed from 82% to 41%. We haven\'t had executive contact in 90 days. They\'ve issued an RFP to AWS and CoreWeave."', font: 'Arial', size: 22, italics: true })] }),
      spacer(),
      body('CLICK: Show the context graph for Vertex Compute.'),
      bullet('Point to the champion_change signal node (Jan 2026)'),
      bullet('Trace the causal chain: champion_loss \u2192 usage_decline \u2192 competitor_mention \u2192 engagement_gap'),
      bullet('Show revenue at risk: $8.2M ARR on this single account'),
      spacer(),
      body('TRANSITION:'),
      new Paragraph({ spacing: { after: 120 }, indent: { left: 400 },
        children: [new TextRun({ text: '"But this isn\'t just a health score. Watch what CS Pulse did automatically..."', font: 'Arial', size: 22, italics: true })] }),

      spacer(),
      heading('Scene 2: Ironridge Manufacturing \u2014 Infrastructure Meltdown', HeadingLevel.HEADING_2),
      highlight('ARR', '$5.8M'),
      highlight('Health', '32 \u2192 Critical', RED),
      highlight('Story Arc', 'Infrastructure Decay'),
      spacer(),
      body('NARRATIVE:'),
      new Paragraph({ spacing: { after: 120 }, indent: { left: 400 },
        children: [new TextRun({ text: '"Ironridge had a Sev-1 outage \u2014 Pod 3 went down, taking 40% of their production workloads offline for 6 hours. Their CEO called our VP of Sales directly. They\'ve started migrating 30% of capacity to a backup data center."', font: 'Arial', size: 22, italics: true })] }),
      bullet('Show the executive_escalation signal (CEO \u2192 VP Sales)'),
      bullet('Show the support_escalation \u2192 usage_decline causal chain'),

      spacer(),
      heading('Scene 3: Sentinel Cybersecurity \u2014 Budget Axe', HeadingLevel.HEADING_2),
      highlight('ARR', '$4.2M'),
      highlight('Health', '38 \u2192 Critical', RED),
      highlight('Story Arc', 'Budget Pressure'),
      spacer(),
      body('NARRATIVE:'),
      new Paragraph({ spacing: { after: 120 }, indent: { left: 400 },
        children: [new TextRun({ text: '"Sentinel missed Q4 earnings. The board mandated 15% IT budget cuts. Their CFO is requesting competitive bids from 3 vendors. This is a price war we can\'t win on price \u2014 we have to win on value."', font: 'Arial', size: 22, italics: true })] }),

      spacer(),
      body('PAUSE \u2014 Let the audience absorb: $18.2M ARR across 3 critical accounts.', { bold: true, color: RED }),

      new Paragraph({ children: [new PageBreak()] }),

      // ============================================================
      // ACT 2: THE INTERVENTION
      // ============================================================
      heading('Act 2: The Intervention', HeadingLevel.HEADING_1),
      body('Now switch to Phase 2 data. Show the "after" state \u2014 what happened when CS Pulse guided the response.'),
      spacer(),

      heading('Vertex Compute Recovery', HeadingLevel.HEADING_2),
      body('NARRATIVE:'),
      new Paragraph({ spacing: { after: 120 }, indent: { left: 400 },
        children: [new TextRun({ text: '"CS Pulse detected the champion loss within 24 hours. It auto-triggered PB-01 (Champion Loss Playbook) and escalated to our VP of Customer Success. Here\'s what happened..."', font: 'Arial', size: 22, italics: true })] }),
      spacer(),
      bullet('Senior CSM Sarah Chen assigned with executive mandate'),
      bullet('PB-03 Optimization Playbook deployed: GPU utilization 41% \u2192 68%'),
      bullet('New CTO Priya Sharma re-engaged after product roadmap preview'),
      spacer(),

      new Table({
        width: { size: 9840, type: WidthType.DXA },
        columnWidths: [4920, 2460, 2460],
        rows: [
          new TableRow({ children: [
            headerCell('Outcome', 4920), headerCell('Type', 2460), headerCell('Revenue Impact', 2460),
          ]}),
          new TableRow({ children: [
            cell('12-month commitment secured', 4920),
            cell('Churn Averted', 2460, { color: GREEN }),
            cell('$4.1M', 2460, { bold: true, color: GREEN }),
          ]}),
          new TableRow({ children: [
            cell('ARR protected via CSM + optimization', 4920),
            cell('Revenue Protected', 2460, { color: GREEN }),
            cell('$3.28M', 2460, { bold: true, color: GREEN }),
          ]}),
        ],
      }),

      spacer(),
      heading('Ironridge Manufacturing Recovery', HeadingLevel.HEADING_2),
      bullet('VP of Customer Success personally assigned as exec sponsor'),
      bullet('System uptime restored to 99.95% after infrastructure overhaul'),
      bullet('Retention: 18-month commitment + SLA credits ($2.9M protected)'),
      bullet('Full renewal secured ($5.8M)'),

      spacer(),
      heading('Sentinel Cybersecurity Recovery', HeadingLevel.HEADING_2),
      bullet('CFO presented with TCO analysis: 23% savings vs alternatives'),
      bullet('Budget cuts redirected to non-critical vendors'),
      bullet('Contract preserved: $2.1M protected'),

      new Paragraph({ children: [new PageBreak()] }),

      // ============================================================
      // ACT 3: THE NUMBERS
      // ============================================================
      heading('Act 3: The Revenue Impact', HeadingLevel.HEADING_1),
      body('Open the CFO Dashboard or Portfolio ROI view.'),
      spacer(),
      body('NARRATIVE:'),
      new Paragraph({ spacing: { after: 120 }, indent: { left: 400 },
        children: [new TextRun({ text: '"Let me show you the financial impact across the entire Granite Peak portfolio..."', font: 'Arial', size: 22, italics: true })] }),
      spacer(),

      new Table({
        width: { size: 9840, type: WidthType.DXA },
        columnWidths: [4920, 4920],
        rows: [
          new TableRow({ children: [
            headerCell('Metric', 4920), headerCell('Value', 4920),
          ]}),
          new TableRow({ children: [
            cell('Total Portfolio ARR', 4920), cell('$68.7M', 4920, { bold: true }),
          ]}),
          new TableRow({ children: [
            cell('Revenue Protected (churn averted)', 4920), cell('$15.6M', 4920, { bold: true, color: GREEN }),
          ]}),
          new TableRow({ children: [
            cell('Expansion Revenue (approved)', 4920), cell('$6.5M', 4920, { bold: true, color: GREEN }),
          ]}),
          new TableRow({ children: [
            cell('Accounts Rescued from Critical', 4920), cell('3 of 3', 4920, { bold: true }),
          ]}),
          new TableRow({ children: [
            cell('Avg Time to Intervention', 4920), cell('< 48 hours', 4920, { bold: true }),
          ]}),
          new TableRow({ children: [
            cell('Net Revenue Impact', 4920, { fill: LIGHT_BLUE }),
            cell('$22.1M protected + expanded', 4920, { fill: LIGHT_BLUE, bold: true, color: BLUE }),
          ]}),
        ],
      }),

      spacer(),
      heading('Expansion Highlights', HeadingLevel.HEADING_2),

      new Table({
        width: { size: 9840, type: WidthType.DXA },
        columnWidths: [3500, 3840, 2500],
        rows: [
          new TableRow({ children: [
            headerCell('Account', 3500), headerCell('Expansion', 3840), headerCell('Revenue', 2500),
          ]}),
          new TableRow({ children: [
            cell('Meridian Financial', 3500), cell('Compliance-certified GPU cluster', 3840), cell('$1.95M', 2500, { color: GREEN }),
          ]}),
          new TableRow({ children: [
            cell('Blackstone Analytics', 3500), cell('Training pipeline 100\u2192500 GPU hrs/day', 3840), cell('$1.9M', 2500, { color: GREEN }),
          ]}),
          new TableRow({ children: [
            cell('Clearwater Health', 3500), cell('Phase 2 HIPAA workload migration', 3840), cell('$1.53M', 2500, { color: GREEN }),
          ]}),
          new TableRow({ children: [
            cell('Quantum Edge Networks', 3500), cell('Edge computing \u2014 5G network sites', 3840), cell('$1.44M', 2500, { color: GREEN }),
          ]}),
          new TableRow({ children: [
            cell('Ridgeline Energy', 3500), cell('Edge computing \u2014 12 remote substations', 3840), cell('$1.38M', 2500, { color: GREEN }),
          ]}),
          new TableRow({ children: [
            cell('Crestline Logistics', 3500), cell('Real-time fleet tracking GPU cluster', 3840), cell('$1.05M', 2500, { color: GREEN }),
          ]}),
        ],
      }),

      new Paragraph({ children: [new PageBreak()] }),

      // ============================================================
      // ACT 4: THE CLOSE
      // ============================================================
      heading('Act 4: The Close', HeadingLevel.HEADING_1),
      body('NARRATIVE:'),
      new Paragraph({ spacing: { after: 200 }, indent: { left: 400 },
        children: [new TextRun({ text: '"Three accounts were burning. $18.2M at risk. CS Pulse detected every signal \u2014 the champion departure, the Sev-1 outage, the budget cuts \u2014 and triggered interventions within 48 hours. Result: zero churn, $15.6M protected, $6.5M in new expansion. That\'s a 32% revenue impact on a $68.7M portfolio."', font: 'Arial', size: 22, italics: true })] }),
      spacer(),

      heading('Key Differentiators to Emphasize', HeadingLevel.HEADING_2),
      bullet('Context Graph: Not just scores \u2014 causal chains that explain WHY'),
      bullet('Signal \u2192 Decision \u2192 Outcome: Every dollar traced to a specific intervention'),
      bullet('Multi-persona: CRO sees revenue, CFO sees ROI, CSM sees daily actions'),
      bullet('7 persona dashboards: CRO, CFO, CEO, VP CS, Sales, CSM, CS Ops'),
      bullet('Real accounts, real industries: 18 unique verticals from AI/ML to Aerospace'),
      spacer(),

      heading('Power-of-1 Talking Point', HeadingLevel.HEADING_2),
      new Paragraph({ spacing: { after: 120 }, indent: { left: 400 },
        children: [new TextRun({ text: '"A 1% improvement in NRR across this portfolio is worth $687K annually. CS Pulse doesn\'t just show you the number \u2014 it shows you exactly which accounts to focus on and which playbook to run."', font: 'Arial', size: 22, italics: true })] }),

      spacer(), spacer(),

      // ============================================================
      // QUICK REFERENCE
      // ============================================================
      heading('Quick Reference: Account Portfolio', HeadingLevel.HEADING_1),

      new Table({
        width: { size: 9840, type: WidthType.DXA },
        columnWidths: [2800, 1200, 900, 1800, 1700, 1440],
        rows: [
          new TableRow({ children: [
            headerCell('Account', 2800), headerCell('ARR', 1200), headerCell('Health', 900),
            headerCell('Industry', 1800), headerCell('Story Arc', 1700), headerCell('Renewal', 1440),
          ]}),
          ...([
            ['Vertex Compute', '$8.2M', '35', 'AI/ML', 'Champion Loss', 'Jun 15'],
            ['Ironridge Manufacturing', '$5.8M', '32', 'Manufacturing', 'Infra Decay', 'Jul 1'],
            ['Meridian Financial', '$6.5M', '52', 'Financial Svc', 'Competitor Eval', 'Sep 30'],
            ['Clearwater Health', '$5.1M', '55', 'Healthcare', 'Stalled Deploy', 'Jun 30'],
            ['Quantum Edge Networks', '$4.8M', '58', 'Telecom', 'Engagement Drop', 'Oct 15'],
            ['Blackstone Analytics', '$4.8M', '78', 'Data Analytics', 'Expansion Champ', 'Dec 15'],
            ['Sentinel Cybersecurity', '$4.2M', '38', 'Cybersecurity', 'Budget Pressure', 'Aug 15'],
            ['Ridgeline Energy', '$4.6M', '80', 'Energy', 'Steady Performer', 'Nov 30'],
            ['Oakwood Retail Tech', '$3.8M', '75', 'Retail', 'Steady Performer', 'Jan 15'],
            ['Crestline Logistics', '$3.5M', '77', 'Logistics', 'Expansion Champ', 'Dec 1'],
            ['Pinnacle Biotech', '$3.2M', '76', 'Life Sciences', 'Steady Performer', 'Feb 28'],
            ['Northstar Media', '$2.8M', '82', 'Media', 'Steady Performer', 'Mar 15'],
            ['Apex Robotics', '$2.5M', '80', 'Robotics', 'Steady Performer', 'Jan 30'],
            ['Vanguard Legal Tech', '$2.4M', '83', 'Legal', 'Steady Performer', 'Apr 15'],
            ['Terraforge Mining', '$2.1M', '79', 'Mining', 'Steady Performer', 'Feb 15'],
            ['Cascade Aerospace', '$1.8M', '81', 'Aerospace', 'Steady Performer', 'May 1'],
            ['Horizon EdTech', '$1.5M', '82', 'Education', 'Steady Performer', 'Mar 30'],
            ['Forge Financial', '$1.1M', '84', 'FinTech', 'Steady Performer', 'Jun 15'],
          ]).map(row => {
            const h = parseInt(row[2]);
            const hColor = h < 50 ? RED : h < 70 ? ORANGE : GREEN;
            const hFill = h < 50 ? 'FFEBEE' : h < 70 ? 'FFF3E0' : 'E8F5E9';
            return new TableRow({ children: [
              cell(row[0], 2800, { bold: true }),
              cell(row[1], 1200),
              cell(row[2], 900, { color: hColor, fill: hFill, bold: true }),
              cell(row[3], 1800),
              cell(row[4], 1700),
              cell(row[5], 1440),
            ]});
          }),
        ],
      }),

      spacer(),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 400 },
        border: { top: { style: BorderStyle.SINGLE, size: 2, color: 'CCCCCC', space: 8 } },
        children: [new TextRun({ text: 'CS Pulse \u2014 Revenue Intelligence Platform \u2014 Confidential', font: 'Arial', size: 18, color: '999999' })],
      }),
    ],
  }],
});

// Generate
Packer.toBuffer(doc).then(buffer => {
  const outPath = '/Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard/docs/Granite_Peak_Demo_Script.docx';
  fs.writeFileSync(outPath, buffer);
  console.log(`Generated: ${outPath} (${(buffer.length / 1024).toFixed(0)} KB)`);
});
