const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, LevelFormat, ExternalHyperlink,
        HeadingLevel, BorderStyle, WidthType, ShadingType,
        PageNumber, PageBreak, TabStopType, TabStopPosition } = require('docx');

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

function headerCell(text, width) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    shading: { fill: "1a1f2e", type: ShadingType.CLEAR },
    margins: cellMargins,
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, font: "Arial", size: 20, color: "FFFFFF" })] })],
  });
}

function cell(text, width) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    margins: cellMargins,
    children: [new Paragraph({ children: [new TextRun({ text, font: "Arial", size: 20 })] })],
  });
}

function tipBox(text) {
  return new Paragraph({
    spacing: { before: 120, after: 120 },
    indent: { left: 360, right: 360 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: "06b6d4", space: 8 } },
    children: [
      new TextRun({ text: "Tip: ", bold: true, font: "Arial", size: 20, color: "06b6d4" }),
      new TextRun({ text, font: "Arial", size: 20, italics: true }),
    ],
  });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, font: "Arial", color: "1a1f2e" },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "2563eb" },
        paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: "374151" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
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
            new TextRun({ text: "CS Pulse", bold: true, font: "Arial", size: 18, color: "6B7280" }),
            new TextRun({ text: "\tSandalwood Capital (ID: 419) \u2014 User Guide", font: "Arial", size: 18, color: "6B7280" }),
          ],
          tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "D1D5DB", space: 4 } },
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "CS Pulse \u2014 Confidential \u2014 Page ", font: "Arial", size: 16, color: "9CA3AF" }),
            new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: "9CA3AF" }),
          ],
        })],
      }),
    },
    children: [
      // ─── TITLE PAGE ───
      new Paragraph({ spacing: { before: 2400 } }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "CS Pulse", bold: true, font: "Arial", size: 56, color: "1a1f2e" })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
        children: [new TextRun({ text: "Revenue Intelligence Platform", font: "Arial", size: 28, color: "6B7280" })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 400, after: 200 },
        border: { top: { style: BorderStyle.SINGLE, size: 2, color: "2563eb", space: 12 } },
        children: [new TextRun({ text: "User Guide", bold: true, font: "Arial", size: 40, color: "2563eb" })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Sandalwood Capital \u2014 Customer ID: 419", font: "Arial", size: 24, color: "374151" })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 600 },
        children: [new TextRun({ text: "18 Accounts  |  $68.7M Portfolio ARR  |  DC2_S Vertical", font: "Arial", size: 22, color: "6B7280" })],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 1200 },
        children: [new TextRun({ text: "March 2026", font: "Arial", size: 20, color: "9CA3AF" })],
      }),

      // ─── PAGE BREAK ───
      new Paragraph({ children: [new PageBreak()] }),

      // ─── 1. GETTING STARTED ───
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("1. Getting Started")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("1.1 Accessing CS Pulse")] }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun("Open your browser and navigate to:")] }),
      new Paragraph({
        spacing: { after: 200 },
        children: [new ExternalHyperlink({
          children: [new TextRun({ text: "https://d2oqfugrb2ltg9.cloudfront.net", style: "Hyperlink", font: "Arial", size: 22 })],
          link: "https://d2oqfugrb2ltg9.cloudfront.net",
        })],
      }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("1.2 Logging In")] }),
      new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun("Enter your email address and password provided by your CS Pulse administrator.")] }),
      new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun("Click "), new TextRun({ text: "Sign In", bold: true }), new TextRun(".")] }),
      new Paragraph({ numbering: { reference: "numbers", level: 0 }, children: [new TextRun("You will land on the Portfolio Overview page showing your 18 accounts.")] }),
      new Paragraph({ spacing: { after: 120 } }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("1.3 Navigation Overview")] }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun("CS Pulse has multiple persona-based dashboards accessible from the left sidebar:")] }),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2800, 3280, 3280],
        rows: [
          new TableRow({ children: [headerCell("Dashboard", 2800), headerCell("Persona", 3280), headerCell("Key Focus", 3280)] }),
          new TableRow({ children: [cell("CRO Overview", 2800), cell("Chief Revenue Officer", 3280), cell("Revenue at risk, expansion, story arcs", 3280)] }),
          new TableRow({ children: [cell("CFO View", 2800), cell("Chief Financial Officer", 3280), cell("ROI, investment efficiency, NRR/GRR", 3280)] }),
          new TableRow({ children: [cell("Accounts", 2800), cell("All users", 3280), cell("Account list, health scores, pillar heatmap", 3280)] }),
          new TableRow({ children: [cell("Playbooks", 2800), cell("CSM / VP CS", 3280), cell("Playbook status, recommended actions", 3280)] }),
          new TableRow({ children: [cell("Ask AI", 2800), cell("All users", 3280), cell("Natural language Q&A powered by Claude", 3280)] }),
        ],
      }),

      // ─── PAGE BREAK ───
      new Paragraph({ children: [new PageBreak()] }),

      // ─── 2. CRO DASHBOARD ───
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("2. CRO Dashboard (Revenue Intelligence)")] }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun("Navigate to "), new TextRun({ text: "CRO Overview", bold: true }), new TextRun(" from the left sidebar. This is your primary revenue intelligence view.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.1 Revenue Cards (Top Row)")] }),
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun("Three cards show revenue intelligence derived from the Context Graph:")] }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2400, 1800, 5160],
        rows: [
          new TableRow({ children: [headerCell("Card", 2400), headerCell("Value", 1800), headerCell("What It Means", 5160)] }),
          new TableRow({ children: [cell("Revenue at Risk", 2400), cell("~$23.5M", 1800), cell("ARR connected to negative context graph outcomes (churn signals, renewal risk). Backed by causal evidence chains.", 5160)] }),
          new TableRow({ children: [cell("Revenue Protected", 2400), cell("~$15.1M", 1800), cell("ARR where interventions (playbooks, CSM actions) have confirmed positive outcomes.", 5160)] }),
          new TableRow({ children: [cell("Expansion Pipeline", 2400), cell("~$5.9M", 1800), cell("ARR connected to expansion signals (upsell discussions, capacity growth).", 5160)] }),
        ],
      }),
      tipBox("These numbers come from the Context Graph, not from manual entry. They update automatically as new signals, decisions, and outcomes are recorded."),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.2 KPI Metrics Row")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Avg Health Score: ", bold: true }), new TextRun("Revenue-weighted average across all 18 accounts. Higher ARR accounts pull the average more.")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Playbook ROI: ", bold: true }), new TextRun("Return on CS investment. Calculated from real pillar score improvements over 6 months. Labeled as estimated (industry benchmarks).")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "NRR Projection: ", bold: true }), new TextRun("Net Revenue Retention forecast based on current health trajectory.")] }),
      new Paragraph({ spacing: { after: 80 } }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.3 Story Arcs")] }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun("Story arcs are narrative patterns detected across your accounts by the Context Graph. Each arc shows how many accounts are affected and the associated revenue impact. Click an arc to see the accounts involved.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("2.4 Highest Risk Accounts")] }),
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun("Shows accounts with health scores below 70 (at-risk threshold). For Sandalwood Capital, expect to see:")] }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3200, 1600, 1600, 2960],
        rows: [
          new TableRow({ children: [headerCell("Account", 3200), headerCell("Health", 1600), headerCell("ARR", 1600), headerCell("Status", 2960)] }),
          new TableRow({ children: [cell("Ironridge Manufacturing", 3200), cell("~59", 1600), cell("$5.8M", 1600), cell("At Risk \u2014 lowest health", 2960)] }),
          new TableRow({ children: [cell("Clearwater Health Platform", 3200), cell("~62", 1600), cell("$5.1M", 1600), cell("At Risk", 2960)] }),
          new TableRow({ children: [cell("Vertex Compute", 3200), cell("~64", 1600), cell("$8.2M", 1600), cell("At Risk \u2014 highest ARR at risk", 2960)] }),
          new TableRow({ children: [cell("Sentinel Cybersecurity", 3200), cell("~66", 1600), cell("$4.2M", 1600), cell("At Risk \u2014 borderline", 2960)] }),
        ],
      }),
      tipBox("Click any account card to see its detailed health breakdown across 5 pillars (P1-P5)."),

      // ─── PAGE BREAK ───
      new Paragraph({ children: [new PageBreak()] }),

      // ─── 3. CFO DASHBOARD ───
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("3. CFO Dashboard (Investment Intelligence)")] }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun("Click "), new TextRun({ text: "CFO View", bold: true }), new TextRun(" in the left sidebar. This view focuses on CS investment returns.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.1 Key Metrics")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Portfolio ROI: ", bold: true }), new TextRun("CS investment return. Shows historical ROI from pillar score improvements. Labeled as estimated based on industry benchmarks (TSIA, Gainsight Pulse).")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "NRR: ", bold: true }), new TextRun("Net Revenue Retention \u2014 target is >100%. Shows current rate with trend.")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "GRR: ", bold: true }), new TextRun("Gross Revenue Retention \u2014 measures churn excluding expansion.")] }),
      new Paragraph({ spacing: { after: 80 } }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.2 Power of 1 Table")] }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun("Shows the dollar impact of a 1% improvement in each business metric. This uses the Power of 1 framework: for every 1% improvement in NRR, TTFV, GRR, etc., how much revenue impact does that create at your $68.7M ARR scale?")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("3.3 ROI Scaling Scenarios")] }),
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun("Three investment tiers showing how ROI scales:")] }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [2800, 2200, 2200, 2160],
        rows: [
          new TableRow({ children: [headerCell("Scenario", 2800), headerCell("Investment", 2200), headerCell("Impact", 2200), headerCell("ROI", 2160)] }),
          new TableRow({ children: [cell("Budget (1%)", 2800), cell("~$653K", 2200), cell("~$2.8M", 2200), cell("~3.2x", 2160)] }),
          new TableRow({ children: [cell("Target (4%)", 2800), cell("~$1.7M", 2200), cell("~$11M", 2200), cell("~5.5x", 2160)] }),
          new TableRow({ children: [cell("Celebrate (6%)", 2800), cell("~$2.5M", 2200), cell("~$16.6M", 2200), cell("~5.5x", 2160)] }),
        ],
      }),
      tipBox("Investment amounts scale with the improvement target \u2014 they are NOT fixed. A 4% improvement requires proportionally more CSM hours, playbook executions, and platform investment than 1%."),

      // ─── PAGE BREAK ───
      new Paragraph({ children: [new PageBreak()] }),

      // ─── 4. ACCOUNTS VIEW ───
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("4. Accounts View")] }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun("Click "), new TextRun({ text: "Accounts", bold: true }), new TextRun(" in the left sidebar. This shows all 18 accounts with their health scores and pillar breakdown.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.1 Pillar Heatmap")] }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun("Each account shows scores across 5 pillars:")] }),
      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [1400, 3200, 4760],
        rows: [
          new TableRow({ children: [headerCell("Pillar", 1400), headerCell("Name", 3200), headerCell("What It Measures", 4760)] }),
          new TableRow({ children: [cell("P1", 1400), cell("Deployment Velocity", 3200), cell("Time-to-first-workload, installation completion, config accuracy", 4760)] }),
          new TableRow({ children: [cell("P2", 1400), cell("Operational Stability", 3200), cell("RMA rates, MTBF, critical incidents, SLA compliance", 4760)] }),
          new TableRow({ children: [cell("P3", 1400), cell("AI/ML Workload Performance", 3200), cell("GPU utilization, training completion, inference latency", 4760)] }),
          new TableRow({ children: [cell("P4", 1400), cell("Channel & Partner Health", 3200), cell("Partner engagement, VAR performance, QBR frequency", 4760)] }),
          new TableRow({ children: [cell("P5", 1400), cell("Expansion Readiness", 3200), cell("Capacity utilization, workload growth, expansion signals", 4760)] }),
        ],
      }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("4.2 Health Thresholds")] }),
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun("Accounts are classified by their overall health score:")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Healthy (70-100): ", bold: true, color: "22c55e" }), new TextRun("Account is in good standing. 14 of your 18 accounts.")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "At Risk (50-69): ", bold: true, color: "eab308" }), new TextRun("Account needs attention. 4 of your 18 accounts ($23.3M ARR).")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Critical (0-49): ", bold: true, color: "ef4444" }), new TextRun("Urgent intervention needed. Currently 0 accounts.")] }),

      // ─── PAGE BREAK ───
      new Paragraph({ children: [new PageBreak()] }),

      // ─── 5. ASK AI ───
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("5. Ask AI (Revenue Advisor)")] }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun("Click the "), new TextRun({ text: "Ask AI", bold: true }), new TextRun(" button in the bottom-right corner of any dashboard. This opens a conversational AI assistant powered by Claude.")] }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.1 What You Can Ask")] }),
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun("Ask AI has access to all your account data, health scores, context graph, and ROI engine. Example questions:")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "\"Which accounts have the highest churn risk?\"", italics: true }), new TextRun(" \u2014 Returns at-risk accounts with health scores and ARR")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "\"Show me the context graph for Vertex Compute\"", italics: true }), new TextRun(" \u2014 Renders a visual Mermaid diagram of signals, decisions, outcomes")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "\"What is the ROI impact of improving NRR by 1%?\"", italics: true }), new TextRun(" \u2014 Calls Power of 1 engine with your portfolio ARR")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "\"What should my CSMs focus on today?\"", italics: true }), new TextRun(" \u2014 Returns prioritized actions with playbook recommendations")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "\"Give me the board-ready portfolio summary\"", italics: true }), new TextRun(" \u2014 CEO-level synthesis with strategic risks")] }),
      new Paragraph({ spacing: { after: 80 } }),

      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("5.2 Rich Artifacts")] }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun("Ask AI renders structured data alongside its narrative response:")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Tables: ", bold: true }), new TextRun("Account lists, stakeholder maps, daily actions \u2014 sortable and expandable")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Metric Cards: ", bold: true }), new TextRun("Revenue at risk, Power of 1 impact \u2014 color-coded")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Mermaid Diagrams: ", bold: true }), new TextRun("Context graph flowcharts showing Signal \u2192 Decision \u2192 Outcome causal chains")] }),
      tipBox("Ask AI adapts to your persona. On the CRO dashboard it focuses on revenue impact. On CFO it focuses on ROI and investment efficiency."),

      // ─── PAGE BREAK ───
      new Paragraph({ children: [new PageBreak()] }),

      // ─── 6. KEY METRICS ───
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("6. Key Metrics Reference")] }),
      new Paragraph({ spacing: { after: 120 }, children: [new TextRun("Quick reference for the numbers you will see across dashboards for Sandalwood Capital:")] }),

      new Table({
        width: { size: 9360, type: WidthType.DXA },
        columnWidths: [3600, 2400, 3360],
        rows: [
          new TableRow({ children: [headerCell("Metric", 3600), headerCell("Value", 2400), headerCell("Source", 3360)] }),
          new TableRow({ children: [cell("Total Accounts", 3600), cell("18", 2400), cell("Accounts table", 3360)] }),
          new TableRow({ children: [cell("Total ARR", 3600), cell("$68,700,000", 2400), cell("Accounts table", 3360)] }),
          new TableRow({ children: [cell("Avg Health (rev-weighted)", 3600), cell("~73", 2400), cell("Health scores + ARR", 3360)] }),
          new TableRow({ children: [cell("At-Risk Accounts", 3600), cell("4", 2400), cell("Health < 70 threshold", 3360)] }),
          new TableRow({ children: [cell("At-Risk ARR", 3600), cell("$23,300,000", 2400), cell("Sum of at-risk account ARR", 3360)] }),
          new TableRow({ children: [cell("Revenue at Risk (CG)", 3600), cell("~$23.5M", 2400), cell("Context graph OUTCOME nodes", 3360)] }),
          new TableRow({ children: [cell("Revenue Protected (CG)", 3600), cell("~$15.1M", 2400), cell("Context graph OUTCOME nodes", 3360)] }),
          new TableRow({ children: [cell("Expansion Pipeline (CG)", 3600), cell("~$5.9M", 2400), cell("Context graph OUTCOME nodes", 3360)] }),
          new TableRow({ children: [cell("NRR Projection", 3600), cell("~109%", 2400), cell("ROI snapshot", 3360)] }),
          new TableRow({ children: [cell("GRR", 3600), cell("~88%", 2400), cell("ROI snapshot", 3360)] }),
          new TableRow({ children: [cell("Portfolio ROI", 3600), cell("~1,466%", 2400), cell("Pillar score improvements", 3360)] }),
          new TableRow({ children: [cell("Context Graph Nodes", 3600), cell("~720", 2400), cell("Signals + decisions + outcomes", 3360)] }),
        ],
      }),

      new Paragraph({ spacing: { before: 240 } }),
      tipBox("All numbers are derived from real data in the platform. The ROI percentage is labeled as estimated because it uses industry benchmark coefficients (TSIA, Gainsight Pulse) to translate pillar improvements into dollar impact."),

      // ─── 7. TROUBLESHOOTING ───
      new Paragraph({ spacing: { before: 240 }, heading: HeadingLevel.HEADING_1, children: [new TextRun("7. Troubleshooting")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Dashboard shows error state: ", bold: true }), new TextRun("Click Retry. If persistent, check your network connection or contact your CS Pulse administrator.")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Ask AI returns \"API key not configured\": ", bold: true }), new TextRun("The Anthropic API key needs to be set by your administrator.")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Health scores show 0: ", bold: true }), new TextRun("Data may not have been processed yet. Contact your administrator to run process-data.")] }),
      new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: [new TextRun({ text: "Pillar scores missing: ", bold: true }), new TextRun("KPI data may be incomplete for some accounts. Check the Accounts view for which pillars have data.")] }),
    ],
  }],
});

Packer.toBuffer(doc).then(buffer => {
  const outPath = '/Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard/docs/CS_Pulse_User_Guide_Sandalwood_419.docx';
  fs.writeFileSync(outPath, buffer);
  console.log(`Created: ${outPath}`);
});
