const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "CS Pulse";
pres.title = "CS Pulse - CSM: Your Daily Command Center";

// ============================================================================
// COLOR PALETTE - Dark executive theme matching CS Pulse UI
// ============================================================================
const C = {
  bg:         "0F1419",
  bgCard:     "1A2332",
  bgCardAlt:  "1E2D3D",
  accent:     "10B981",  // emerald green
  accentAlt:  "3B82F6",  // blue
  accentWarm: "F59E0B",  // amber/gold
  accentRed:  "EF4444",  // red for risk
  accentPurple: "8B5CF6", // purple
  accentCyan: "06B6D4",  // cyan for CSM branding
  textWhite:  "FFFFFF",
  textLight:  "CBD5E1",
  textMuted:  "64748B",
  textGold:   "F59E0B",
  divider:    "334155",
  tagGreen:   "065F46",
  tagRed:     "7F1D1D",
  tagBlue:    "1E3A5F",
  tagAmber:   "78350F",
  tagCyan:    "083344",
};

const cardShadow = () => ({ type: "outer", blur: 8, offset: 3, angle: 135, color: "000000", opacity: 0.3 });

// ============================================================================
// SLIDE 1: TITLE — YOUR DAILY COMMAND CENTER
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accentCyan } });

  slide.addText("CS PULSE", {
    x: 0.6, y: 0.3, w: 3, h: 0.4,
    fontSize: 12, fontFace: "Arial", color: C.accentCyan, charSpacing: 4, bold: true, margin: 0
  });

  slide.addText("Your Daily Command Center", {
    x: 0.6, y: 0.9, w: 9, h: 0.8,
    fontSize: 40, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });
  slide.addText("Customer Success Manager Quick Start Guide", {
    x: 0.6, y: 1.65, w: 9, h: 0.5,
    fontSize: 20, fontFace: "Calibri", color: C.textLight, margin: 0
  });

  slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 2.35, w: 2.5, h: 0.04, fill: { color: C.accentCyan } });

  slide.addText("Two purpose-built layouts for your daily workflow. Process actions sequentially or manage your portfolio visually. AI handles the analysis \u2014 you focus on relationships.", {
    x: 0.6, y: 2.65, w: 5.5, h: 0.9,
    fontSize: 13, fontFace: "Calibri", color: C.textMuted, lineSpacingMultiple: 1.4, margin: 0
  });

  // CSM Persona Card
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.5, y: 0.55, w: 3.2, h: 2.6, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 6.5, y: 0.55, w: 0.07, h: 2.6, fill: { color: C.accentCyan } });

  slide.addText("CUSTOMER SUCCESS MANAGER", {
    x: 6.85, y: 0.7, w: 2.7, h: 0.35,
    fontSize: 10, fontFace: "Arial", color: C.accentCyan, bold: true, charSpacing: 1, margin: 0
  });
  slide.addText("Daily Command Center", {
    x: 6.85, y: 1.0, w: 2.7, h: 0.35,
    fontSize: 16, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });
  slide.addText([
    { text: "Daily prioritized actions", options: { bullet: true, breakLine: true, color: C.textLight } },
    { text: "Account health deep-dives", options: { bullet: true, breakLine: true, color: C.textLight } },
    { text: "Playbook execution & tracking", options: { bullet: true, breakLine: true, color: C.textLight } },
    { text: "Signal triage & notifications", options: { bullet: true, breakLine: true, color: C.textLight } },
    { text: "AI-powered email drafts", options: { bullet: true, color: C.textLight } }
  ], {
    x: 6.85, y: 1.4, w: 2.7, h: 1.5,
    fontSize: 10, fontFace: "Calibri", margin: 0, paraSpaceAfter: 3
  });

  // Two layout mode cards
  const layouts = [
    { name: "Focus Flow", desc: "Sequential task queue", icon: "\u25B6", accent: C.accentCyan },
    { name: "Cockpit", desc: "Kanban workflow board", icon: "\u25A6", accent: C.accentAlt },
  ];
  layouts.forEach((l, i) => {
    const x = 0.6 + i * 2.7;
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: 3.85, w: 2.4, h: 0.9, fill: { color: C.bgCard }, shadow: cardShadow()
    });
    slide.addShape(pres.shapes.RECTANGLE, { x, y: 3.85, w: 0.06, h: 0.9, fill: { color: l.accent } });
    slide.addText(l.icon + "  " + l.name, {
      x: x + 0.2, y: 3.92, w: 2, h: 0.3,
      fontSize: 14, fontFace: "Georgia", color: l.accent, bold: true, margin: 0
    });
    slide.addText(l.desc, {
      x: x + 0.2, y: 4.22, w: 2, h: 0.25,
      fontSize: 10, fontFace: "Calibri", color: C.textMuted, margin: 0
    });
  });

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.56, w: 10, h: 0.06, fill: { color: C.divider } });
  slide.addText("Navigate to  /dc-dashboard/csm  to access this view", {
    x: 0.6, y: 5.15, w: 5, h: 0.3,
    fontSize: 9, fontFace: "Calibri", color: C.textMuted, margin: 0
  });
})();

// ============================================================================
// SLIDE 2: FOCUS FLOW — SEQUENTIAL TASK QUEUE
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accentCyan } });

  slide.addText("FOCUS FLOW", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accentCyan, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("Sequential Task Queue", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });
  slide.addText("Inspired by Superhuman \u2014 one action at a time", {
    x: 6.0, y: 0.55, w: 3.7, h: 0.3,
    fontSize: 9, fontFace: "Calibri", color: C.textMuted, align: "right", margin: 0
  });

  // ---- LEFT: Icon Rail ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.1, w: 0.8, h: 3.8, fill: { color: C.bgCardAlt }, shadow: cardShadow()
  });
  const navIcons = [
    { icon: "\u2302", label: "Home", active: false },
    { icon: "\u26A1", label: "Actions", active: true },
    { icon: "\u2261", label: "Accounts", active: false },
    { icon: "\u2713", label: "Approvals", active: false },
    { icon: "\u23F0", label: "Renewals", active: false },
  ];
  navIcons.forEach((n, i) => {
    const y = 1.25 + i * 0.7;
    if (n.active) {
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 0.8, h: 0.55, fill: { color: C.bgCard } });
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y, w: 0.05, h: 0.55, fill: { color: C.accentCyan } });
    }
    slide.addText(n.icon, {
      x: 0.45, y, w: 0.7, h: 0.3,
      fontSize: 16, fontFace: "Calibri", color: n.active ? C.accentCyan : C.textMuted, align: "center", margin: 0
    });
    slide.addText(n.label, {
      x: 0.45, y: y + 0.28, w: 0.7, h: 0.2,
      fontSize: 7, fontFace: "Arial", color: n.active ? C.accentCyan : C.textMuted, align: "center", margin: 0
    });
  });

  // ---- CENTER: Current Action Card ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 1.4, y: 1.1, w: 5.0, h: 3.8, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 1.4, y: 1.1, w: 0.07, h: 3.8, fill: { color: C.accentRed } });

  // Action header
  slide.addText("ACTION 1 OF 10", {
    x: 1.65, y: 1.2, w: 2, h: 0.2,
    fontSize: 8, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });
  // Navigation
  slide.addText("\u2190 Prev    Next \u2192    Skip    Snooze", {
    x: 3.8, y: 1.2, w: 2.4, h: 0.2,
    fontSize: 8, fontFace: "Calibri", color: C.textMuted, align: "right", margin: 0
  });

  // Account info
  slide.addText("Drift Analytics", {
    x: 1.65, y: 1.55, w: 3, h: 0.35,
    fontSize: 18, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // Health badge
  slide.addShape(pres.shapes.RECTANGLE, { x: 4.8, y: 1.58, w: 0.7, h: 0.25, fill: { color: C.tagRed } });
  slide.addText("42", { x: 4.8, y: 1.58, w: 0.7, h: 0.25, fontSize: 10, fontFace: "Georgia", color: C.accentRed, bold: true, align: "center", valign: "middle", margin: 0 });
  slide.addText("Critical", { x: 5.55, y: 1.6, w: 0.7, h: 0.22, fontSize: 8, fontFace: "Arial", color: C.accentRed, margin: 0 });

  // Action description
  slide.addText("Emergency retention review \u2014 health dropped 16 points in 90 days. Silent churn pattern detected. Champion departed Q1.", {
    x: 1.65, y: 2.0, w: 4.5, h: 0.55,
    fontSize: 11, fontFace: "Calibri", color: C.textLight, lineSpacingMultiple: 1.3, margin: 0
  });

  // Action metadata
  const actionMeta = [
    { label: "Playbook", value: "PB-05 Emergency Retention", color: C.accentCyan },
    { label: "Urgency", value: "Critical", color: C.accentRed },
    { label: "Est. Hours", value: "8h", color: C.textLight },
    { label: "ARR at Risk", value: "$1.8M", color: C.accentWarm },
    { label: "Projected Impact", value: "$1.8M protected", color: C.accent },
  ];
  actionMeta.forEach((m, i) => {
    const y = 2.7 + i * 0.28;
    slide.addText(m.label, { x: 1.65, y, w: 1.5, h: 0.22, fontSize: 9, fontFace: "Calibri", color: C.textMuted, margin: 0 });
    slide.addText(m.value, { x: 3.2, y, w: 3, h: 0.22, fontSize: 9, fontFace: "Calibri", color: m.color, bold: true, margin: 0 });
  });

  // Action buttons
  slide.addShape(pres.shapes.RECTANGLE, { x: 1.65, y: 4.2, w: 1.8, h: 0.35, fill: { color: C.accent } });
  slide.addText("Start Playbook", { x: 1.65, y: 4.2, w: 1.8, h: 0.35, fontSize: 10, fontFace: "Arial", color: C.bg, bold: true, align: "center", valign: "middle", margin: 0 });

  slide.addShape(pres.shapes.RECTANGLE, { x: 3.65, y: 4.2, w: 1.4, h: 0.35, fill: { color: C.bgCardAlt } });
  slide.addText("Draft Email", { x: 3.65, y: 4.2, w: 1.4, h: 0.35, fontSize: 10, fontFace: "Arial", color: C.textLight, bold: true, align: "center", valign: "middle", margin: 0 });

  slide.addShape(pres.shapes.RECTANGLE, { x: 5.25, y: 4.2, w: 1.0, h: 0.35, fill: { color: C.bgCardAlt } });
  slide.addText("Ask AI", { x: 5.25, y: 4.2, w: 1.0, h: 0.35, fontSize: 10, fontFace: "Arial", color: C.accentCyan, bold: true, align: "center", valign: "middle", margin: 0 });

  // ---- RIGHT: Queue preview ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.6, y: 1.1, w: 3.1, h: 3.8, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("QUEUE", {
    x: 6.8, y: 1.2, w: 2, h: 0.2,
    fontSize: 8, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  const queue = [
    { rank: "1", acct: "Drift Analytics", urgency: "Critical", urgColor: C.accentRed, active: true },
    { rank: "2", acct: "Relay Healthcare", urgency: "Critical", urgColor: C.accentRed, active: false },
    { rank: "3", acct: "Canopy EdTech", urgency: "High", urgColor: C.accentWarm, active: false },
    { rank: "4", acct: "TechGrid Corp", urgency: "High", urgColor: C.accentWarm, active: false },
    { rank: "5", acct: "Apex Dynamics", urgency: "Medium", urgColor: C.accentAlt, active: false },
    { rank: "6", acct: "Horizon Labs", urgency: "Medium", urgColor: C.accentAlt, active: false },
    { rank: "7", acct: "Summit Data", urgency: "Medium", urgColor: C.accentAlt, active: false },
  ];
  queue.forEach((q, i) => {
    const y = 1.5 + i * 0.42;
    if (q.active) {
      slide.addShape(pres.shapes.RECTANGLE, { x: 6.6, y, w: 3.1, h: 0.38, fill: { color: C.bgCardAlt } });
      slide.addShape(pres.shapes.RECTANGLE, { x: 6.6, y, w: 0.05, h: 0.38, fill: { color: C.accentCyan } });
    }
    slide.addText(q.rank, { x: 6.8, y: y + 0.04, w: 0.25, h: 0.22, fontSize: 9, fontFace: "Georgia", color: C.textMuted, margin: 0 });
    slide.addText(q.acct, { x: 7.1, y: y + 0.04, w: 1.6, h: 0.22, fontSize: 9, fontFace: "Calibri", color: q.active ? C.textWhite : C.textLight, bold: q.active, margin: 0 });
    // Urgency dot
    slide.addShape(pres.shapes.OVAL, { x: 8.85, y: y + 0.1, w: 0.1, h: 0.1, fill: { color: q.urgColor } });
    slide.addText(q.urgency, { x: 9.0, y: y + 0.04, w: 0.65, h: 0.22, fontSize: 7, fontFace: "Arial", color: q.urgColor, margin: 0 });
  });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 5.05, w: 9.3, h: 0.35, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 5.05, w: 0.06, h: 0.35, fill: { color: C.accentCyan } });
  slide.addText("Process your highest-impact actions one at a time \u2014 never wonder what to do next", {
    x: 0.7, y: 5.05, w: 8.8, h: 0.35,
    fontSize: 11, fontFace: "Calibri", color: C.accentCyan, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 3: COCKPIT — KANBAN WORKFLOW BOARD
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accentAlt } });

  slide.addText("COCKPIT", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accentAlt, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("Kanban Workflow Board", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });
  slide.addText("Inspired by Linear \u2014 full visual portfolio", {
    x: 6.0, y: 0.55, w: 3.7, h: 0.3,
    fontSize: 9, fontFace: "Calibri", color: C.textMuted, align: "right", margin: 0
  });

  // ---- Three Kanban Columns ----
  const columns = [
    {
      title: "\uD83D\uDD25 FIRE", subtitle: "Critical urgency", color: C.accentRed, bgColor: C.tagRed, action: "Escalate",
      cards: [
        { acct: "Drift Analytics", score: "42", arr: "$1.8M", signal: "Silent churn" },
        { acct: "Relay Healthcare", score: "56", arr: "$3.8M", signal: "Champion departed" },
      ]
    },
    {
      title: "\u26A0 THIS WEEK", subtitle: "High urgency", color: C.accentWarm, bgColor: C.tagAmber, action: "Start Playbook",
      cards: [
        { acct: "Canopy EdTech", score: "57", arr: "$4.2M", signal: "QBR overdue" },
        { acct: "TechGrid Corp", score: "60", arr: "$2.6M", signal: "Deployment stall" },
      ]
    },
    {
      title: "\uD83D\uDE80 OPPORTUNITY", subtitle: "Growth", color: C.accent, bgColor: C.tagGreen, action: "Draft Proposal",
      cards: [
        { acct: "Apex Dynamics", score: "78", arr: "$6.1M", signal: "Expansion ready" },
        { acct: "Summit Data", score: "72", arr: "$5.4M", signal: "Usage spike" },
      ]
    },
  ];

  columns.forEach((col, ci) => {
    const colX = 0.4 + ci * 3.15;
    const colW = 2.95;

    // Column header
    slide.addShape(pres.shapes.RECTANGLE, {
      x: colX, y: 1.1, w: colW, h: 0.55, fill: { color: col.bgColor }
    });
    slide.addText(col.title, {
      x: colX + 0.12, y: 1.12, w: 2.5, h: 0.25,
      fontSize: 10, fontFace: "Arial", color: col.color, bold: true, margin: 0
    });
    slide.addText(col.subtitle, {
      x: colX + 0.12, y: 1.37, w: 2, h: 0.18,
      fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0
    });

    // Cards
    col.cards.forEach((card, i) => {
      const y = 1.75 + i * 1.15;
      slide.addShape(pres.shapes.RECTANGLE, {
        x: colX, y, w: colW, h: 1.0, fill: { color: C.bgCard }, shadow: cardShadow()
      });
      slide.addText(card.acct, {
        x: colX + 0.12, y: y + 0.05, w: 2.2, h: 0.25,
        fontSize: 11, fontFace: "Calibri", color: C.textWhite, bold: true, margin: 0
      });
      // Score badge
      let scoreColor = C.accent;
      let scoreBg = C.tagGreen;
      if (parseInt(card.score) < 50) { scoreColor = C.accentRed; scoreBg = C.tagRed; }
      else if (parseInt(card.score) < 70) { scoreColor = C.accentWarm; scoreBg = C.tagAmber; }
      slide.addShape(pres.shapes.RECTANGLE, { x: colX + colW - 0.65, y: y + 0.08, w: 0.5, h: 0.2, fill: { color: scoreBg } });
      slide.addText(card.score, { x: colX + colW - 0.65, y: y + 0.08, w: 0.5, h: 0.2, fontSize: 9, fontFace: "Georgia", color: scoreColor, bold: true, align: "center", valign: "middle", margin: 0 });

      slide.addText(card.arr + "  |  " + card.signal, {
        x: colX + 0.12, y: y + 0.32, w: 2.6, h: 0.2,
        fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0
      });

      // Action button
      slide.addShape(pres.shapes.RECTANGLE, { x: colX + 0.12, y: y + 0.62, w: 1.3, h: 0.25, fill: { color: C.bgCardAlt } });
      slide.addText(col.action, { x: colX + 0.12, y: y + 0.62, w: 1.3, h: 0.25, fontSize: 8, fontFace: "Arial", color: col.color, bold: true, align: "center", valign: "middle", margin: 0 });
    });
  });

  // ---- Drawer tabs preview ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 4.1, w: 9.3, h: 0.65, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("CONTEXTUAL DRAWER TABS:", {
    x: 0.6, y: 4.15, w: 2.5, h: 0.2,
    fontSize: 8, fontFace: "Arial", color: C.textMuted, charSpacing: 1, margin: 0
  });
  const drawerTabs = ["Overview", "Signals", "People", "Tickets", "History", "Notes"];
  drawerTabs.forEach((tab, i) => {
    const x = 0.6 + i * 1.5;
    const isFirst = i === 0;
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: 4.4, w: 1.2, h: 0.25, fill: { color: isFirst ? C.accentCyan : C.bgCardAlt }
    });
    slide.addText(tab, {
      x, y: 4.4, w: 1.2, h: 0.25,
      fontSize: 8, fontFace: "Arial", color: isFirst ? C.bg : C.textMuted, bold: isFirst, align: "center", valign: "middle", margin: 0
    });
  });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.95, w: 9.3, h: 0.35, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.95, w: 0.06, h: 0.35, fill: { color: C.accentAlt } });
  slide.addText("See your entire portfolio in one visual board \u2014 click any card to open the contextual drawer", {
    x: 0.7, y: 4.95, w: 8.8, h: 0.35,
    fontSize: 11, fontFace: "Calibri", color: C.accentAlt, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 4: ACCOUNT DEEP-DIVE
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent } });

  slide.addText("ACCOUNT DEEP-DIVE", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accent, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("Full Account Context in One Click", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // ---- LEFT: Health + Pillars ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.1, w: 3.0, h: 2.6, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("Drift Analytics", {
    x: 0.6, y: 1.18, w: 2.5, h: 0.3,
    fontSize: 14, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // Overall health
  slide.addText("42", {
    x: 0.6, y: 1.55, w: 1.0, h: 0.5,
    fontSize: 32, fontFace: "Georgia", color: C.accentRed, bold: true, margin: 0
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 1.65, y: 1.62, w: 0.7, h: 0.22, fill: { color: C.tagRed } });
  slide.addText("Critical", { x: 1.65, y: 1.62, w: 0.7, h: 0.22, fontSize: 8, fontFace: "Arial", color: C.accentRed, bold: true, align: "center", valign: "middle", margin: 0 });

  // Pillar breakdown
  slide.addText("5-PILLAR BREAKDOWN", {
    x: 0.6, y: 2.15, w: 2.5, h: 0.2,
    fontSize: 7, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  const pillars = [
    { name: "P1 Adoption", score: 38, color: C.accentRed },
    { name: "P2 Experience", score: 45, color: C.accentRed },
    { name: "P3 Support", score: 52, color: C.accentWarm },
    { name: "P4 Engagement", score: 35, color: C.accentRed },
    { name: "P5 Outcomes", score: 40, color: C.accentRed },
  ];
  pillars.forEach((p, i) => {
    const y = 2.4 + i * 0.24;
    slide.addText(p.name, { x: 0.6, y, w: 1.3, h: 0.18, fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0 });
    slide.addShape(pres.shapes.RECTANGLE, { x: 1.95, y: y + 0.02, w: 1.2, h: 0.12, fill: { color: C.bgCardAlt } });
    slide.addShape(pres.shapes.RECTANGLE, { x: 1.95, y: y + 0.02, w: 1.2 * (p.score / 100), h: 0.12, fill: { color: p.color } });
    slide.addText(String(p.score), { x: 3.2, y, w: 0.3, h: 0.18, fontSize: 8, fontFace: "Georgia", color: p.color, bold: true, margin: 0 });
  });

  // ---- CENTER: Champion + Contract ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 3.6, y: 1.1, w: 2.9, h: 2.6, fill: { color: C.bgCard }, shadow: cardShadow()
  });

  slide.addText("CHAMPION", {
    x: 3.8, y: 1.18, w: 2, h: 0.2,
    fontSize: 8, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 5.4, y: 1.2, w: 0.85, h: 0.18, fill: { color: C.tagRed } });
  slide.addText("Departed", { x: 5.4, y: 1.2, w: 0.85, h: 0.18, fontSize: 7, fontFace: "Arial", color: C.accentRed, bold: true, align: "center", valign: "middle", margin: 0 });

  const champInfo = [
    { label: "Name", value: "Lisa Chen" },
    { label: "Title", value: "VP Engineering" },
    { label: "Last Contact", value: "45 days ago" },
  ];
  champInfo.forEach((c, i) => {
    const y = 1.45 + i * 0.25;
    slide.addText(c.label, { x: 3.8, y, w: 1.2, h: 0.2, fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0 });
    slide.addText(c.value, { x: 5.0, y, w: 1.3, h: 0.2, fontSize: 8, fontFace: "Calibri", color: C.textLight, bold: true, margin: 0 });
  });

  slide.addShape(pres.shapes.RECTANGLE, { x: 3.8, y: 2.2, w: 2.5, h: 0.01, fill: { color: C.divider } });

  slide.addText("CONTRACT", {
    x: 3.8, y: 2.3, w: 2, h: 0.2,
    fontSize: 8, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });
  const contractInfo = [
    { label: "ARR", value: "$1.8M" },
    { label: "Renewal", value: "May 15, 2026" },
    { label: "Days Left", value: "29" },
  ];
  contractInfo.forEach((c, i) => {
    const y = 2.55 + i * 0.25;
    slide.addText(c.label, { x: 3.8, y, w: 1.2, h: 0.2, fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0 });
    let valColor = C.textLight;
    if (c.label === "Days Left") valColor = C.accentRed;
    slide.addText(c.value, { x: 5.0, y, w: 1.3, h: 0.2, fontSize: 8, fontFace: "Calibri", color: valColor, bold: true, margin: 0 });
  });

  // ---- RIGHT: Recent Signals ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.7, y: 1.1, w: 3.0, h: 2.6, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 6.7, y: 1.1, w: 0.07, h: 2.6, fill: { color: C.accentWarm } });

  slide.addText("RECENT SIGNALS", {
    x: 6.95, y: 1.18, w: 2.5, h: 0.2,
    fontSize: 8, fontFace: "Arial", color: C.accentWarm, charSpacing: 2, bold: true, margin: 0
  });

  const signals = [
    { type: "kpi_decline", date: "Apr 12", desc: "Adoption score dropped 12pts" },
    { type: "champion_loss", date: "Mar 28", desc: "VP Engineering departed" },
    { type: "ticket_spike", date: "Mar 15", desc: "5 P1 tickets in 2 weeks" },
    { type: "silent_churn", date: "Mar 01", desc: "No exec engagement 45d" },
    { type: "escalation", date: "Feb 20", desc: "CSM flagged for VP review" },
  ];
  const signalColors = {
    kpi_decline: C.accentRed, champion_loss: C.accentRed,
    ticket_spike: C.accentWarm, silent_churn: C.accentRed, escalation: C.accentWarm
  };
  signals.forEach((s, i) => {
    const y = 1.48 + i * 0.42;
    slide.addShape(pres.shapes.OVAL, { x: 6.95, y: y + 0.04, w: 0.1, h: 0.1, fill: { color: signalColors[s.type] || C.textMuted } });
    slide.addText(s.type.replace(/_/g, " "), {
      x: 7.15, y, w: 1.5, h: 0.18,
      fontSize: 7, fontFace: "Arial", color: signalColors[s.type] || C.textMuted, bold: true, margin: 0
    });
    slide.addText(s.date, {
      x: 8.7, y, w: 0.8, h: 0.18,
      fontSize: 7, fontFace: "Calibri", color: C.textMuted, align: "right", margin: 0
    });
    slide.addText(s.desc, {
      x: 7.15, y: y + 0.18, w: 2.4, h: 0.18,
      fontSize: 8, fontFace: "Calibri", color: C.textLight, margin: 0
    });
  });

  // ---- Bottom: Recommended Playbooks ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 3.9, w: 9.3, h: 0.85, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("RECOMMENDED PLAYBOOKS", {
    x: 0.6, y: 3.97, w: 3, h: 0.2,
    fontSize: 8, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  const recPlaybooks = [
    { name: "PB-05 Emergency Retention", impact: "$1.8M", hours: "48h", match: "95%" },
    { name: "PB-SYS-04 Champion Recovery", impact: "$1.2M", hours: "24h", match: "88%" },
    { name: "PB-06 QBR Engagement", impact: "$900K", hours: "24h", match: "72%" },
  ];
  recPlaybooks.forEach((pb, i) => {
    const x = 0.6 + i * 3.1;
    slide.addText(pb.name, { x, y: 4.22, w: 2.8, h: 0.18, fontSize: 8, fontFace: "Calibri", color: C.textWhite, bold: true, margin: 0 });
    slide.addText("Impact: " + pb.impact + "  |  " + pb.hours + "  |  Match: " + pb.match, { x, y: 4.42, w: 2.8, h: 0.18, fontSize: 7, fontFace: "Calibri", color: C.textMuted, margin: 0 });
  });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.95, w: 9.3, h: 0.35, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.95, w: 0.06, h: 0.35, fill: { color: C.accent } });
  slide.addText("Full account context in one click \u2014 health, champion, signals, and recommended actions", {
    x: 0.7, y: 4.95, w: 8.8, h: 0.35,
    fontSize: 11, fontFace: "Calibri", color: C.accent, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 5: PLAYBOOK EXECUTION — FROM SIGNAL TO RESOLUTION
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent } });

  slide.addText("PLAYBOOK EXECUTION", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accent, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("From Signal to Resolution", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // ---- Three-step flow ----
  const flowSteps = [
    {
      num: "1", title: "START", subtitle: "Launch with context",
      details: ["Confirmation modal with account health", "Playbook details + estimated hours", "ARR context and urgency level", "One-click launch"],
      accent: C.accentCyan, bgColor: C.tagCyan
    },
    {
      num: "2", title: "TRACK", subtitle: "Monitor progress",
      details: ["Active tracker on Home view", "Days active since trigger", "Health delta (before vs now)", "Progress bar (steps completed %)"],
      accent: C.accentWarm, bgColor: C.tagAmber
    },
    {
      num: "3", title: "CLOSE", subtitle: "Capture outcomes",
      details: ["Outcome: resolved / escalated / timeout", "Actual CSM hours spent", "Revenue protected ($ARR saved)", "Revenue expanded ($ARR upsold)"],
      accent: C.accent, bgColor: C.tagGreen
    },
  ];

  flowSteps.forEach((step, i) => {
    const x = 0.4 + i * 3.15;
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.1, w: 2.95, h: 2.8, fill: { color: C.bgCard }, shadow: cardShadow()
    });
    slide.addShape(pres.shapes.RECTANGLE, { x, y: 1.1, w: 2.95, h: 0.55, fill: { color: step.bgColor } });

    // Step number circle
    slide.addShape(pres.shapes.OVAL, { x: x + 0.12, y: 1.16, w: 0.35, h: 0.35, fill: { color: step.accent } });
    slide.addText(step.num, { x: x + 0.12, y: 1.16, w: 0.35, h: 0.35, fontSize: 14, fontFace: "Georgia", color: C.bg, bold: true, align: "center", valign: "middle", margin: 0 });

    slide.addText(step.title, {
      x: x + 0.55, y: 1.17, w: 2, h: 0.22,
      fontSize: 12, fontFace: "Arial", color: step.accent, bold: true, margin: 0
    });
    slide.addText(step.subtitle, {
      x: x + 0.55, y: 1.4, w: 2, h: 0.18,
      fontSize: 9, fontFace: "Calibri", color: C.textMuted, margin: 0
    });

    step.details.forEach((d, j) => {
      const y = 1.85 + j * 0.38;
      slide.addText("\u2022", { x: x + 0.2, y, w: 0.2, h: 0.2, fontSize: 10, fontFace: "Calibri", color: step.accent, margin: 0 });
      slide.addText(d, { x: x + 0.4, y, w: 2.3, h: 0.2, fontSize: 9, fontFace: "Calibri", color: C.textLight, margin: 0 });
    });

    // Arrows between steps
    if (i < 2) {
      slide.addText("\u2192", {
        x: x + 2.85, y: 2.3, w: 0.4, h: 0.3,
        fontSize: 18, fontFace: "Georgia", color: C.divider, align: "center", valign: "middle", margin: 0
      });
    }
  });

  // ---- Active Playbook Tracker Preview ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 4.1, w: 9.3, h: 0.65, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.1, w: 0.07, h: 0.65, fill: { color: C.accentWarm } });

  slide.addText("ACTIVE TRACKER:", {
    x: 0.65, y: 4.15, w: 1.5, h: 0.2,
    fontSize: 8, fontFace: "Arial", color: C.accentWarm, charSpacing: 1, bold: true, margin: 0
  });
  slide.addText("Drift Analytics \u2014 PB-05 Emergency Retention", {
    x: 2.2, y: 4.15, w: 3.5, h: 0.2,
    fontSize: 9, fontFace: "Calibri", color: C.textWhite, bold: true, margin: 0
  });
  slide.addText("Day 3 of 14  |  Health \u0394: +2  |  $1.8M ARR", {
    x: 2.2, y: 4.38, w: 3.5, h: 0.2,
    fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0
  });
  // Progress bar
  slide.addShape(pres.shapes.RECTANGLE, { x: 6.2, y: 4.3, w: 3.2, h: 0.12, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 6.2, y: 4.3, w: 3.2 * 0.25, h: 0.12, fill: { color: C.accentWarm } });
  slide.addText("25% complete", { x: 6.2, y: 4.45, w: 3.2, h: 0.18, fontSize: 7, fontFace: "Calibri", color: C.textMuted, align: "center", margin: 0 });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.95, w: 9.3, h: 0.35, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.95, w: 0.06, h: 0.35, fill: { color: C.accent } });
  slide.addText("Every intervention builds your success story \u2014 outcomes feed the ROI engine automatically", {
    x: 0.7, y: 4.95, w: 8.8, h: 0.35,
    fontSize: 11, fontFace: "Calibri", color: C.accent, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 6: SIGNAL TRIAGE & NOTIFICATIONS
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accentWarm } });

  slide.addText("SIGNAL TRIAGE", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accentWarm, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("Never Miss a Critical Signal", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // ---- Urgent Alert Banner ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.1, w: 9.3, h: 0.5, fill: { color: C.tagRed }
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.1, w: 0.07, h: 0.5, fill: { color: C.accentRed } });
  slide.addText("\u26A0  URGENT: Drift Analytics health dropped below 50 \u2014 champion departed, 29 days to renewal", {
    x: 0.65, y: 1.1, w: 8.5, h: 0.5,
    fontSize: 11, fontFace: "Calibri", color: C.accentRed, bold: true, valign: "middle", margin: 0
  });
  slide.addText("\u2715", {
    x: 9.2, y: 1.1, w: 0.4, h: 0.5,
    fontSize: 14, fontFace: "Calibri", color: C.textMuted, align: "center", valign: "middle", margin: 0
  });

  // ---- LEFT: Notification Bell ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.8, w: 4.5, h: 3.0, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.8, w: 0.07, h: 3.0, fill: { color: C.accentWarm } });

  slide.addText("\uD83D\uDD14 NOTIFICATIONS", {
    x: 0.65, y: 1.88, w: 3, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.accentWarm, charSpacing: 2, bold: true, margin: 0
  });
  slide.addShape(pres.shapes.OVAL, { x: 3.8, y: 1.9, w: 0.3, h: 0.22, fill: { color: C.accentRed } });
  slide.addText("5", { x: 3.8, y: 1.9, w: 0.3, h: 0.22, fontSize: 9, fontFace: "Arial", color: C.textWhite, bold: true, align: "center", valign: "middle", margin: 0 });

  const notifications = [
    { type: "urgent_alert", title: "Health Critical: Drift Analytics", sub: "Score dropped to 42 \u2014 action required", time: "2m", color: C.accentRed, bgColor: C.tagRed },
    { type: "playbook_triggered", title: "Playbook PB-05 auto-triggered", sub: "Emergency Retention for Drift Analytics", time: "5m", color: C.accentAlt, bgColor: C.tagBlue },
    { type: "signal_insight", title: "Champion departed: Relay Healthcare", sub: "VP Engineering Lisa Chen left the company", time: "1h", color: C.accentWarm, bgColor: C.tagAmber },
    { type: "signal_insight", title: "QBR overdue: Canopy EdTech", sub: "Last QBR was 120 days ago", time: "3h", color: C.accentWarm, bgColor: C.tagAmber },
    { type: "playbook_triggered", title: "Playbook PB-04 recommended", sub: "Expansion Opportunity for Apex Dynamics", time: "1d", color: C.accentAlt, bgColor: C.tagBlue },
  ];
  notifications.forEach((n, i) => {
    const y = 2.2 + i * 0.5;
    slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: y + 0.02, w: 0.14, h: 0.14, fill: { color: n.bgColor } });
    slide.addText(n.title, { x: 0.85, y, w: 3.2, h: 0.2, fontSize: 9, fontFace: "Calibri", color: n.color, bold: true, margin: 0 });
    slide.addText(n.time, { x: 4.1, y, w: 0.6, h: 0.2, fontSize: 8, fontFace: "Calibri", color: C.textMuted, align: "right", margin: 0 });
    slide.addText(n.sub, { x: 0.85, y: y + 0.2, w: 3.8, h: 0.18, fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0 });
  });

  // ---- RIGHT: Signal Types ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.8, w: 4.6, h: 3.0, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("SIGNAL TYPES", {
    x: 5.3, y: 1.88, w: 3, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  const signalTypes = [
    { name: "KPI Decline", desc: "Health pillar drops below threshold", icon: "\u2193", color: C.accentRed },
    { name: "Champion Loss", desc: "Key stakeholder departs company", icon: "\u2716", color: C.accentRed },
    { name: "Silent Churn", desc: "No executive engagement for 30+ days", icon: "\uD83D\uDD07", color: C.accentRed },
    { name: "Competitive Threat", desc: "Competitor evaluation detected", icon: "\u26A0", color: C.accentWarm },
    { name: "Ticket Spike", desc: "Unusual support volume increase", icon: "\uD83C\uDFAB", color: C.accentWarm },
    { name: "Expansion Signal", desc: "Usage growth + healthy scores", icon: "\uD83D\uDE80", color: C.accent },
  ];
  signalTypes.forEach((s, i) => {
    const y = 2.2 + i * 0.42;
    slide.addText(s.icon, { x: 5.3, y, w: 0.3, h: 0.25, fontSize: 12, fontFace: "Calibri", margin: 0 });
    slide.addText(s.name, { x: 5.65, y, w: 2.2, h: 0.2, fontSize: 10, fontFace: "Calibri", color: s.color, bold: true, margin: 0 });
    slide.addText(s.desc, { x: 5.65, y: y + 0.2, w: 3.8, h: 0.18, fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0 });
  });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.95, w: 9.3, h: 0.35, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.95, w: 0.06, h: 0.35, fill: { color: C.accentWarm } });
  slide.addText("Alerts find you \u2014 critical signals surface automatically via banner + notification bell", {
    x: 0.7, y: 4.95, w: 8.8, h: 0.35,
    fontSize: 11, fontFace: "Calibri", color: C.accentWarm, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 7: AI-POWERED EMAIL DRAFTS
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accentPurple } });

  slide.addText("AI EMAIL DRAFTS", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accentPurple, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("Personalized Emails in 10 Seconds", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // ---- Auto-Template Selection ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.1, w: 9.3, h: 0.9, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("AUTO-TEMPLATE SELECTION", {
    x: 0.6, y: 1.18, w: 3, h: 0.2,
    fontSize: 8, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  const templates = [
    { health: "< 50", template: "Health Drop", desc: "Urgent health review email", color: C.accentRed, bgColor: C.tagRed },
    { health: "50-69", template: "Renewal", desc: "Pre-renewal check-in", color: C.accentWarm, bgColor: C.tagAmber },
    { health: "70+", template: "Expansion", desc: "Growth opportunity outreach", color: C.accent, bgColor: C.tagGreen },
  ];
  templates.forEach((t, i) => {
    const x = 0.6 + i * 3.1;
    slide.addShape(pres.shapes.RECTANGLE, { x, y: 1.45, w: 0.65, h: 0.22, fill: { color: t.bgColor } });
    slide.addText(t.health, { x, y: 1.45, w: 0.65, h: 0.22, fontSize: 8, fontFace: "Georgia", color: t.color, bold: true, align: "center", valign: "middle", margin: 0 });
    slide.addText("\u2192", { x: x + 0.7, y: 1.45, w: 0.25, h: 0.22, fontSize: 10, fontFace: "Georgia", color: C.divider, margin: 0 });
    slide.addText(t.template, { x: x + 1.0, y: 1.45, w: 1.2, h: 0.22, fontSize: 9, fontFace: "Calibri", color: t.color, bold: true, margin: 0 });
    slide.addText(t.desc, { x: x + 1.0, y: 1.68, w: 1.8, h: 0.18, fontSize: 7, fontFace: "Calibri", color: C.textMuted, margin: 0 });
  });

  // ---- Email Preview ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 2.2, w: 5.5, h: 2.8, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 2.2, w: 0.07, h: 2.8, fill: { color: C.accentPurple } });

  slide.addText("EMAIL PREVIEW", {
    x: 0.65, y: 2.28, w: 3, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.accentPurple, charSpacing: 2, bold: true, margin: 0
  });

  slide.addText("To: sarah.johnson@driftanalytics.com", {
    x: 0.65, y: 2.58, w: 4.5, h: 0.2,
    fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0
  });
  slide.addText("Subject: Partnership Health Review \u2014 Drift Analytics", {
    x: 0.65, y: 2.8, w: 4.5, h: 0.2,
    fontSize: 9, fontFace: "Calibri", color: C.textWhite, bold: true, margin: 0
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.65, y: 3.05, w: 5.0, h: 0.01, fill: { color: C.divider } });

  slide.addText("Hi Sarah,\n\nI wanted to reach out regarding our partnership. Our platform intelligence has identified some areas where we can provide additional support to help maximize your investment...\n\nKey observations:\n\u2022 Adoption metrics trending below target\n\u2022 Recent leadership transition in your engineering org\n\u2022 Support ticket volume above normal\n\nI'd like to schedule a 30-minute health review this week to discuss a targeted action plan.", {
    x: 0.65, y: 3.12, w: 5.0, h: 1.7,
    fontSize: 8, fontFace: "Calibri", color: C.textLight, lineSpacingMultiple: 1.25, margin: 0
  });

  // ---- RIGHT: Features ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.1, y: 2.2, w: 3.6, h: 2.8, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("FEATURES", {
    x: 6.3, y: 2.28, w: 3, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  const features = [
    { title: "Context-Aware", desc: "Pulls health score, signals, champion status, ARR, and renewal date into the draft" },
    { title: "Auto-Template", desc: "Selects health_drop, renewal, or expansion based on current account health" },
    { title: "Fully Editable", desc: "Review and customize subject and body before sending" },
    { title: "One-Click Actions", desc: "Copy to clipboard or open directly in your mail client" },
    { title: "AI-Powered", desc: "Claude generates contextual, professional prose \u2014 not canned templates" },
  ];
  features.forEach((f, i) => {
    const y = 2.6 + i * 0.46;
    slide.addText(f.title, { x: 6.3, y, w: 3.2, h: 0.2, fontSize: 9, fontFace: "Calibri", color: C.accentPurple, bold: true, margin: 0 });
    slide.addText(f.desc, { x: 6.3, y: y + 0.2, w: 3.2, h: 0.22, fontSize: 8, fontFace: "Calibri", color: C.textMuted, lineSpacingMultiple: 1.2, margin: 0 });
  });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 5.15, w: 9.3, h: 0.35, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 5.15, w: 0.06, h: 0.35, fill: { color: C.accentPurple } });
  slide.addText("Personalized, context-aware emails in 10 seconds \u2014 not canned templates", {
    x: 0.7, y: 5.15, w: 8.8, h: 0.35,
    fontSize: 11, fontFace: "Calibri", color: C.accentPurple, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 8: HEALTH TRENDS & RENEWALS
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accentAlt } });

  slide.addText("HEALTH & RENEWALS", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accentAlt, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("Track Momentum, Spot Risk Early", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // ---- Account Health Trajectory ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.1, w: 5.5, h: 2.4, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("ACCOUNT HEALTH TRAJECTORY", {
    x: 0.6, y: 1.18, w: 4, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  // Month headers
  const months = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr"];
  months.forEach((m, i) => {
    slide.addText(m, {
      x: 1.8 + i * 0.65, y: 1.45, w: 0.6, h: 0.18,
      fontSize: 7, fontFace: "Arial", color: C.textMuted, align: "center", margin: 0
    });
  });

  const myAccounts = [
    { name: "Drift Analytics", scores: [58, 55, 52, 48, 45, 42], color: C.accentRed },
    { name: "Relay Healthcare", scores: [64, 62, 60, 58, 57, 56], color: C.accentWarm },
    { name: "Apex Dynamics", scores: [72, 74, 73, 76, 78, 80], color: C.accent },
    { name: "Summit Data", scores: [68, 65, 67, 70, 72, 75], color: C.accent },
    { name: "Horizon Labs", scores: [70, 71, 69, 72, 71, 73], color: C.accentAlt },
  ];
  myAccounts.forEach((a, i) => {
    const y = 1.7 + i * 0.33;
    slide.addText(a.name, { x: 0.6, y, w: 1.2, h: 0.2, fontSize: 8, fontFace: "Calibri", color: C.textWhite, bold: true, margin: 0 });
    a.scores.forEach((s, j) => {
      let dotColor = C.accent;
      if (s < 50) dotColor = C.accentRed;
      else if (s < 70) dotColor = C.accentWarm;
      slide.addText(String(s), {
        x: 1.85 + j * 0.65, y, w: 0.5, h: 0.2,
        fontSize: 8, fontFace: "Georgia", color: dotColor, align: "center", margin: 0
      });
    });
    // Trend arrow
    const diff = a.scores[5] - a.scores[0];
    const trend = diff > 0 ? `\u2191+${diff}` : `\u2193${diff}`;
    slide.addText(trend, { x: 5.3, y, w: 0.5, h: 0.2, fontSize: 8, fontFace: "Georgia", color: a.color, bold: true, margin: 0 });
  });

  // Threshold legend
  slide.addText("Critical < 50  |  At Risk 50-69  |  Healthy 70+", {
    x: 0.6, y: 3.2, w: 4, h: 0.18,
    fontSize: 7, fontFace: "Calibri", color: C.textMuted, margin: 0
  });

  // ---- Renewal Calendar ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.1, y: 1.1, w: 3.6, h: 2.4, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("MY RENEWALS", {
    x: 6.3, y: 1.18, w: 3, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  const myRenewals = [
    { acct: "Drift Analytics", days: "29", arr: "$1.8M", health: "42", daysColor: C.accentRed },
    { acct: "Relay Healthcare", days: "67", arr: "$3.8M", health: "56", daysColor: C.accentWarm },
    { acct: "Apex Dynamics", days: "116", arr: "$6.1M", health: "78", daysColor: C.accent },
  ];
  myRenewals.forEach((r, i) => {
    const y = 1.55 + i * 0.55;
    slide.addText(r.acct, { x: 6.3, y, w: 2, h: 0.2, fontSize: 9, fontFace: "Calibri", color: C.textWhite, bold: true, margin: 0 });
    slide.addText(r.arr, { x: 8.6, y, w: 0.9, h: 0.2, fontSize: 9, fontFace: "Georgia", color: C.textMuted, align: "right", margin: 0 });
    slide.addText(r.days + " days", { x: 6.3, y: y + 0.22, w: 1, h: 0.18, fontSize: 9, fontFace: "Georgia", color: r.daysColor, bold: true, margin: 0 });
    slide.addText("Health: " + r.health, { x: 7.4, y: y + 0.22, w: 1, h: 0.18, fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0 });
    // Progress bar for days
    const pct = Math.max(0, Math.min(1, (120 - parseInt(r.days)) / 120));
    slide.addShape(pres.shapes.RECTANGLE, { x: 6.3, y: y + 0.42, w: 3.1, h: 0.06, fill: { color: C.bgCardAlt } });
    slide.addShape(pres.shapes.RECTANGLE, { x: 6.3, y: y + 0.42, w: 3.1 * pct, h: 0.06, fill: { color: r.daysColor } });
  });

  // ---- Bottom: Portfolio Summary ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 3.7, w: 9.3, h: 1.0, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("MY PORTFOLIO SUMMARY", {
    x: 0.6, y: 3.78, w: 3, h: 0.2,
    fontSize: 8, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  const summaryItems = [
    { label: "Accounts", value: "5", color: C.accent },
    { label: "Total ARR", value: "$17.5M", color: C.accentAlt },
    { label: "Avg Health", value: "65.2", color: C.accentWarm },
    { label: "Improving", value: "2", color: C.accent },
    { label: "Declining", value: "2", color: C.accentRed },
    { label: "Stable", value: "1", color: C.accentAlt },
  ];
  summaryItems.forEach((s, i) => {
    const x = 0.6 + i * 1.55;
    slide.addText(s.label, { x, y: 4.05, w: 1.3, h: 0.18, fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0 });
    slide.addText(s.value, { x, y: 4.25, w: 1.3, h: 0.3, fontSize: 16, fontFace: "Georgia", color: s.color, bold: true, margin: 0 });
  });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.85, w: 9.3, h: 0.35, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.85, w: 0.06, h: 0.35, fill: { color: C.accentAlt } });
  slide.addText("Track account momentum \u2014 spot risk before it becomes churn", {
    x: 0.7, y: 4.85, w: 8.8, h: 0.35,
    fontSize: 11, fontFace: "Calibri", color: C.accentAlt, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 9: ASK AI — YOUR ACCOUNT CO-PILOT
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accentCyan } });

  slide.addText("ASK AI", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accentCyan, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("Your Account Co-Pilot", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // ---- LEFT: CSM Questions ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.1, w: 4.5, h: 4.1, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.1, w: 0.07, h: 4.1, fill: { color: C.accentCyan } });

  slide.addText("QUESTIONS YOU CAN ASK", {
    x: 0.65, y: 1.18, w: 4, h: 0.25,
    fontSize: 10, fontFace: "Arial", color: C.accentCyan, charSpacing: 1, bold: true, margin: 0
  });
  slide.addText("Natural language \u2192 grounded in live account data", {
    x: 0.65, y: 1.45, w: 4, h: 0.2,
    fontSize: 9, fontFace: "Calibri", color: C.textMuted, margin: 0
  });

  // Account Analysis
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.65, y: 1.8, w: 1.4, h: 0.22, fill: { color: C.tagCyan } });
  slide.addText("ACCOUNTS", { x: 0.65, y: 1.8, w: 1.4, h: 0.22, fontSize: 8, fontFace: "Arial", color: C.accentCyan, bold: true, align: "center", valign: "middle", margin: 0 });

  const accountQs = [
    "What's the story for Drift Analytics?",
    "Why did Relay Healthcare's health drop?",
    "Show me the context graph for Canopy EdTech.",
  ];
  accountQs.forEach((q, i) => {
    const y = 2.1 + i * 0.27;
    slide.addText("\u25B8", { x: 0.65, y, w: 0.2, h: 0.22, fontSize: 9, fontFace: "Georgia", color: C.accentCyan, margin: 0 });
    slide.addText(q, { x: 0.85, y, w: 3.8, h: 0.22, fontSize: 9, fontFace: "Calibri", color: C.textLight, italic: true, margin: 0 });
  });

  // Playbook & Actions
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.65, y: 3.0, w: 1.4, h: 0.22, fill: { color: C.tagGreen } });
  slide.addText("PLAYBOOKS", { x: 0.65, y: 3.0, w: 1.4, h: 0.22, fontSize: 8, fontFace: "Arial", color: C.accent, bold: true, align: "center", valign: "middle", margin: 0 });

  const pbQs = [
    "What playbook should I run for Drift?",
    "How did my last intervention perform?",
    "What's the projected ROI of PB-05?",
  ];
  pbQs.forEach((q, i) => {
    const y = 3.3 + i * 0.27;
    slide.addText("\u25B8", { x: 0.65, y, w: 0.2, h: 0.22, fontSize: 9, fontFace: "Georgia", color: C.accent, margin: 0 });
    slide.addText(q, { x: 0.85, y, w: 3.8, h: 0.22, fontSize: 9, fontFace: "Calibri", color: C.textLight, italic: true, margin: 0 });
  });

  // Communication
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.65, y: 4.15, w: 1.7, h: 0.22, fill: { color: C.tagBlue } });
  slide.addText("COMMUNICATION", { x: 0.65, y: 4.15, w: 1.7, h: 0.22, fontSize: 8, fontFace: "Arial", color: C.accentAlt, bold: true, align: "center", valign: "middle", margin: 0 });

  const commQs = [
    "Draft a QBR prep email for Summit Data.",
    "Write an escalation note for my VP.",
    "Summarize Relay's signals for my 1:1.",
  ];
  commQs.forEach((q, i) => {
    const y = 4.45 + i * 0.27;
    slide.addText("\u25B8", { x: 0.65, y, w: 0.2, h: 0.22, fontSize: 9, fontFace: "Georgia", color: C.accentAlt, margin: 0 });
    slide.addText(q, { x: 0.85, y, w: 3.8, h: 0.22, fontSize: 9, fontFace: "Calibri", color: C.textLight, italic: true, margin: 0 });
  });

  // ---- RIGHT: AI Response Example ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.1, w: 4.6, h: 2.6, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 5.1, y: 1.1, w: 0.07, h: 2.6, fill: { color: C.accentCyan } });

  slide.addText("AI RESPONSE EXAMPLE", {
    x: 5.35, y: 1.18, w: 4, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.accentCyan, charSpacing: 1, bold: true, margin: 0
  });

  slide.addText("You: \"What's the story for Drift Analytics?\"", {
    x: 5.35, y: 1.5, w: 4.1, h: 0.22,
    fontSize: 9, fontFace: "Calibri", color: C.textMuted, italic: true, margin: 0
  });

  slide.addText("CS Pulse analyzed 23 signals, 5 decisions, and 3 outcomes across the context graph...\n\nDrift Analytics is in a Silent Churn pattern. Health declined 16 points over 90 days driven by:\n\u2022 Champion departure (VP Engineering, Mar 28)\n\u2022 Adoption score drop to 38 (-12pts)\n\u2022 5 P1 support tickets in 14 days\n\nRecommended: PB-05 Emergency Retention\nEstimated impact: $1.8M ARR protected", {
    x: 5.35, y: 1.8, w: 4.1, h: 1.7,
    fontSize: 8, fontFace: "Calibri", color: C.textLight, lineSpacingMultiple: 1.25, margin: 0
  });

  // Stats bar
  slide.addShape(pres.shapes.RECTANGLE, { x: 5.35, y: 3.35, w: 4.1, h: 0.25, fill: { color: C.bgCardAlt } });
  slide.addText("23 signals  |  5 decisions  |  3 outcomes  |  3 tools used  |  1.2s", {
    x: 5.45, y: 3.35, w: 3.9, h: 0.25,
    fontSize: 7, fontFace: "Calibri", color: C.textMuted, valign: "middle", margin: 0
  });

  // ---- RIGHT: Suggested Follow-ups ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 3.85, w: 4.6, h: 1.35, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("SUGGESTED FOLLOW-UPS", {
    x: 5.3, y: 3.93, w: 4, h: 0.22,
    fontSize: 8, fontFace: "Arial", color: C.textMuted, charSpacing: 1, margin: 0
  });

  const followups = [
    "Show me the causal chain for the champion loss",
    "Draft an escalation email to my VP",
    "What happens if we don't intervene?",
  ];
  followups.forEach((f, i) => {
    const y = 4.22 + i * 0.3;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 5.3, y, w: 4.2, h: 0.25, fill: { color: C.bgCardAlt }
    });
    slide.addText(f, { x: 5.4, y, w: 4, h: 0.25, fontSize: 8, fontFace: "Calibri", color: C.accentCyan, valign: "middle", margin: 0 });
  });

  // Bottom tagline
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 5.3, w: 9.3, h: 0.3, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 5.3, w: 0.06, h: 0.3, fill: { color: C.accentCyan } });
  slide.addText("Ask any question about any account \u2014 AI does the analysis, you make the call", {
    x: 0.7, y: 5.3, w: 8.8, h: 0.3,
    fontSize: 11, fontFace: "Calibri", color: C.accentCyan, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// WRITE FILE
// ============================================================================
const outPath = process.argv[2] || "CS_Pulse_CSM_Tutorial.pptx";
pres.writeFile({ fileName: outPath }).then(() => {
  console.log(`Created: ${outPath}`);
}).catch(err => {
  console.error("Error:", err);
  process.exit(1);
});
