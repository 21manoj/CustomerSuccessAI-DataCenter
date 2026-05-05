const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "CS Pulse";
pres.title = "CS Pulse - VP Customer Success: Portfolio Intelligence";

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
  accentPurple: "8B5CF6", // purple for governance
  textWhite:  "FFFFFF",
  textLight:  "CBD5E1",
  textMuted:  "64748B",
  textGold:   "F59E0B",
  divider:    "334155",
  tagGreen:   "065F46",
  tagRed:     "7F1D1D",
  tagBlue:    "1E3A5F",
  tagPurple:  "3B1D6E",
  tagAmber:   "78350F",
};

const cardShadow = () => ({ type: "outer", blur: 8, offset: 3, angle: 135, color: "000000", opacity: 0.3 });

// ============================================================================
// SLIDE 1: TITLE — PORTFOLIO INTELLIGENCE
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent } });

  slide.addText("CS PULSE", {
    x: 0.6, y: 0.3, w: 3, h: 0.4,
    fontSize: 12, fontFace: "Arial", color: C.accent, charSpacing: 4, bold: true, margin: 0
  });

  slide.addText("Portfolio Intelligence", {
    x: 0.6, y: 0.9, w: 9, h: 0.8,
    fontSize: 40, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });
  slide.addText("VP Customer Success Quick Start Guide", {
    x: 0.6, y: 1.65, w: 9, h: 0.5,
    fontSize: 20, fontFace: "Calibri", color: C.textLight, margin: 0
  });

  slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 2.35, w: 2.5, h: 0.04, fill: { color: C.accent } });

  slide.addText("Your command center for portfolio health, team performance, playbook ROI, and renewal governance. Every metric traces back to causal evidence.", {
    x: 0.6, y: 2.65, w: 5.5, h: 0.9,
    fontSize: 13, fontFace: "Calibri", color: C.textMuted, lineSpacingMultiple: 1.4, margin: 0
  });

  // VP CS Persona Card
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.5, y: 0.55, w: 3.2, h: 2.6, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 6.5, y: 0.55, w: 0.07, h: 2.6, fill: { color: C.accent } });

  slide.addText("VP CUSTOMER SUCCESS", {
    x: 6.85, y: 0.7, w: 2.7, h: 0.35,
    fontSize: 11, fontFace: "Arial", color: C.accent, bold: true, charSpacing: 2, margin: 0
  });
  slide.addText("Portfolio Intelligence", {
    x: 6.85, y: 1.0, w: 2.7, h: 0.35,
    fontSize: 16, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });
  slide.addText([
    { text: "Portfolio health & NRR accountability", options: { bullet: true, breakLine: true, color: C.textLight } },
    { text: "Team performance & capacity planning", options: { bullet: true, breakLine: true, color: C.textLight } },
    { text: "Playbook ROI & success metrics", options: { bullet: true, breakLine: true, color: C.textLight } },
    { text: "Governance & approval workflows", options: { bullet: true, color: C.textLight } }
  ], {
    x: 6.85, y: 1.4, w: 2.7, h: 1.5,
    fontSize: 10, fontFace: "Calibri", margin: 0, paraSpaceAfter: 4
  });

  // Key stats row
  const stats = [
    { label: "Accounts", value: "15", accent: C.accent },
    { label: "Portfolio ARR", value: "$48M", accent: C.accentAlt },
    { label: "NRR", value: "105%", accent: C.accentWarm },
  ];
  stats.forEach((s, i) => {
    const x = 0.6 + i * 2.5;
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: 3.85, w: 2.2, h: 0.9, fill: { color: C.bgCard }, shadow: cardShadow()
    });
    slide.addText(s.label, {
      x: x + 0.15, y: 3.92, w: 1.9, h: 0.2,
      fontSize: 8, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
    });
    slide.addText(s.value, {
      x: x + 0.15, y: 4.12, w: 1.9, h: 0.45,
      fontSize: 26, fontFace: "Georgia", color: s.accent, bold: true, margin: 0
    });
  });

  // Bottom bar
  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.56, w: 10, h: 0.06, fill: { color: C.divider } });
  slide.addText("Navigate to  /dc-dashboard/vpcs  to access this view", {
    x: 0.6, y: 5.15, w: 5, h: 0.3,
    fontSize: 9, fontFace: "Calibri", color: C.textMuted, margin: 0
  });
})();

// ============================================================================
// SLIDE 2: PORTFOLIO HEALTH AT A GLANCE
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent } });

  slide.addText("PORTFOLIO OVERVIEW", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accent, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("Portfolio Health at a Glance", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });
  slide.addText("Navigate to  /dc-dashboard/vpcs", {
    x: 6.5, y: 0.5, w: 3.2, h: 0.4,
    fontSize: 10, fontFace: "Calibri", color: C.textMuted, align: "right", margin: 0
  });

  // ---- ROW 1: Four summary cards ----
  const summaryCards = [
    { title: "TOTAL ACCOUNTS", value: "15", sub: "Active in portfolio", accent: C.accent },
    { title: "AVG HEALTH", value: "67.2", sub: "Portfolio weighted", accent: C.accentWarm },
    { title: "PLAYBOOK COMPLETION", value: "78%", sub: "Last 30 days", accent: C.accentAlt },
    { title: "RENEWALS (90D)", value: "$17.8M", sub: "3 accounts renewing", accent: C.accentRed },
  ];
  summaryCards.forEach((m, i) => {
    const x = 0.4 + i * 2.35;
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.15, w: 2.15, h: 1.05, fill: { color: C.bgCard }, shadow: cardShadow()
    });
    slide.addText(m.title, {
      x: x + 0.12, y: 1.22, w: 1.9, h: 0.2,
      fontSize: 7, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
    });
    slide.addText(m.value, {
      x: x + 0.12, y: 1.42, w: 1.9, h: 0.4,
      fontSize: 24, fontFace: "Georgia", color: m.accent, bold: true, margin: 0
    });
    slide.addText(m.sub, {
      x: x + 0.12, y: 1.82, w: 1.9, h: 0.2,
      fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0
    });
  });

  // ---- ROW 2: Health Distribution ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 2.4, w: 5.4, h: 2.2, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("HEALTH DISTRIBUTION", {
    x: 0.6, y: 2.5, w: 3, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  const buckets = [
    { label: "Healthy", range: "70-100", count: "7", pct: "47%", arr: "$22.4M", color: C.accent, barW: 4.2 * 0.47 },
    { label: "At Risk", range: "50-69", count: "5", pct: "33%", arr: "$15.8M", color: C.accentWarm, barW: 4.2 * 0.33 },
    { label: "Critical", range: "0-49", count: "3", pct: "20%", arr: "$9.8M", color: C.accentRed, barW: 4.2 * 0.20 },
  ];
  buckets.forEach((b, i) => {
    const y = 2.85 + i * 0.55;
    slide.addText(b.label, {
      x: 0.6, y, w: 1.2, h: 0.2,
      fontSize: 10, fontFace: "Calibri", color: C.textWhite, bold: true, margin: 0
    });
    slide.addText(`${b.count} accts  |  ${b.arr}`, {
      x: 1.8, y, w: 2, h: 0.2,
      fontSize: 9, fontFace: "Calibri", color: C.textMuted, margin: 0
    });
    slide.addText(b.pct, {
      x: 4.5, y, w: 0.6, h: 0.2,
      fontSize: 10, fontFace: "Georgia", color: b.color, bold: true, align: "right", margin: 0
    });
    // Progress bar background
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.6, y: y + 0.24, w: 4.9, h: 0.14, fill: { color: C.bgCardAlt }
    });
    // Progress bar fill
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.6, y: y + 0.24, w: b.barW, h: 0.14, fill: { color: b.color }
    });
  });

  // ---- ROW 2: Quick Stats ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.0, y: 2.4, w: 3.7, h: 2.2, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("QUICK STATS", {
    x: 6.2, y: 2.5, w: 3, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  const quickStats = [
    { label: "Avg Resolution", value: "4.2 days", icon: "\u23F1" },
    { label: "Playbook Success", value: "83%", icon: "\u2705" },
    { label: "Portfolio NPS", value: "42", icon: "\u2B50" },
    { label: "Actions Completed", value: "91%", icon: "\u26A1" },
  ];
  quickStats.forEach((s, i) => {
    const y = 2.85 + i * 0.38;
    slide.addText(s.icon, {
      x: 6.2, y, w: 0.3, h: 0.25,
      fontSize: 12, fontFace: "Calibri", margin: 0
    });
    slide.addText(s.label, {
      x: 6.55, y, w: 1.8, h: 0.25,
      fontSize: 10, fontFace: "Calibri", color: C.textLight, margin: 0
    });
    slide.addText(s.value, {
      x: 8.4, y, w: 1.1, h: 0.25,
      fontSize: 11, fontFace: "Georgia", color: C.accent, bold: true, align: "right", margin: 0
    });
  });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 4.85, w: 9.3, h: 0.4, fill: { color: C.bgCardAlt }
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.85, w: 0.06, h: 0.4, fill: { color: C.accent } });
  slide.addText("One screen, four answers: How many? How healthy? What's working? What's renewing?", {
    x: 0.7, y: 4.85, w: 8.8, h: 0.4,
    fontSize: 11, fontFace: "Calibri", color: C.accent, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 3: TEAM PERFORMANCE — CSM SCORECARD
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accentAlt } });

  slide.addText("TEAM PERFORMANCE", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accentAlt, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("CSM Scorecard", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // ---- CSM Performance Table ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.1, w: 6.2, h: 2.8, fill: { color: C.bgCard }, shadow: cardShadow()
  });

  // Table header
  const headers = ["CSM", "Accts", "ARR", "Health \u0394", "\u2191", "\u2193", "Playbooks", "Success", "Revenue $"];
  const colX = [0.55, 1.6, 2.15, 2.85, 3.5, 3.8, 4.1, 4.85, 5.5];
  const colW = [1.0, 0.5, 0.65, 0.6, 0.3, 0.3, 0.7, 0.6, 0.9];
  headers.forEach((h, i) => {
    slide.addText(h, {
      x: colX[i], y: 1.18, w: colW[i], h: 0.25,
      fontSize: 7, fontFace: "Arial", color: C.textMuted, charSpacing: 1, bold: true, margin: 0
    });
  });

  // Divider
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: 1.45, w: 5.9, h: 0.02, fill: { color: C.divider } });

  const csms = [
    { name: "Sarah Chen", accts: "5", arr: "$16M", delta: "+3.2", up: "4", dn: "1", pb: "8", success: "88%", rev: "$420K" },
    { name: "Marcus Rivera", accts: "4", arr: "$14M", delta: "+1.8", up: "2", dn: "1", pb: "6", success: "83%", rev: "$310K" },
    { name: "Emily Park", accts: "3", arr: "$10M", delta: "-0.5", up: "1", dn: "2", pb: "4", success: "75%", rev: "$180K" },
    { name: "Alex Johnson", accts: "3", arr: "$8M", delta: "+2.1", up: "3", dn: "0", pb: "5", success: "80%", rev: "$250K" },
  ];
  csms.forEach((csm, i) => {
    const y = 1.55 + i * 0.42;
    const vals = [csm.name, csm.accts, csm.arr, csm.delta, csm.up, csm.dn, csm.pb, csm.success, csm.rev];
    vals.forEach((v, j) => {
      let color = C.textLight;
      if (j === 3) color = v.startsWith("-") ? C.accentRed : C.accent; // delta
      if (j === 4) color = C.accent; // up
      if (j === 5) color = C.accentRed; // down
      if (j === 8) color = C.accentWarm; // revenue
      slide.addText(v, {
        x: colX[j], y, w: colW[j], h: 0.3,
        fontSize: 9, fontFace: j === 0 ? "Calibri" : "Georgia", color,
        bold: j === 0 || j === 8, margin: 0
      });
    });
    if (i < csms.length - 1) {
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: y + 0.35, w: 5.9, h: 0.01, fill: { color: C.divider } });
    }
  });

  // ---- Team Capacity Gauge ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.8, y: 1.1, w: 2.9, h: 2.8, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("TEAM CAPACITY", {
    x: 7.0, y: 1.2, w: 2.5, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  // Utilization display
  slide.addText("78%", {
    x: 7.0, y: 1.55, w: 2.5, h: 0.55,
    fontSize: 36, fontFace: "Georgia", color: C.accentWarm, bold: true, align: "center", margin: 0
  });
  slide.addText("Utilization", {
    x: 7.0, y: 2.1, w: 2.5, h: 0.2,
    fontSize: 10, fontFace: "Calibri", color: C.textMuted, align: "center", margin: 0
  });

  // Capacity bar
  slide.addShape(pres.shapes.RECTANGLE, { x: 7.2, y: 2.4, w: 2.2, h: 0.12, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 7.2, y: 2.4, w: 2.2 * 0.78, h: 0.12, fill: { color: C.accentWarm } });

  const capStats = [
    { label: "CSMs", val: "4" },
    { label: "Accts / CSM", val: "3.8" },
    { label: "Target", val: "5.0" },
  ];
  capStats.forEach((s, i) => {
    const y = 2.7 + i * 0.32;
    slide.addText(s.label, {
      x: 7.1, y, w: 1.5, h: 0.22,
      fontSize: 9, fontFace: "Calibri", color: C.textMuted, margin: 0
    });
    slide.addText(s.val, {
      x: 8.7, y, w: 0.8, h: 0.22,
      fontSize: 10, fontFace: "Georgia", color: C.textWhite, bold: true, align: "right", margin: 0
    });
  });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 4.15, w: 9.3, h: 0.4, fill: { color: C.bgCardAlt }
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.15, w: 0.06, h: 0.4, fill: { color: C.accentAlt } });
  slide.addText("See who's driving revenue impact \u2014 and who needs support", {
    x: 0.7, y: 4.15, w: 8.8, h: 0.4,
    fontSize: 11, fontFace: "Calibri", color: C.accentAlt, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 4: ACTIONS QUEUE — WHAT YOUR TEAM SHOULD DO TODAY
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accentWarm } });

  slide.addText("DAILY ACTIONS", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accentWarm, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("What Your Team Should Do Today", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // Priority formula
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.0, y: 0.2, w: 3.7, h: 0.55, fill: { color: C.bgCard }
  });
  slide.addText("Priority = (impact x 0.6 x ARR) - (effort x 0.4)", {
    x: 6.15, y: 0.22, w: 3.4, h: 0.2,
    fontSize: 8, fontFace: "Arial", color: C.accentWarm, bold: true, margin: 0
  });
  slide.addText("200 data points \u2192 10 clear actions", {
    x: 6.15, y: 0.43, w: 3.4, h: 0.2,
    fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0
  });

  // ---- Actions table ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.05, w: 9.3, h: 3.7, fill: { color: C.bgCard }, shadow: cardShadow()
  });

  // Table header
  const aHeaders = ["#", "Account", "Action", "Playbook", "Urgency", "Hours", "$ Impact"];
  const aColX = [0.55, 0.85, 2.3, 4.8, 6.3, 7.4, 8.1];
  const aColW = [0.3, 1.4, 2.4, 1.4, 1.0, 0.6, 1.5];
  aHeaders.forEach((h, i) => {
    slide.addText(h, {
      x: aColX[i], y: 1.12, w: aColW[i], h: 0.25,
      fontSize: 7, fontFace: "Arial", color: C.textMuted, charSpacing: 1, bold: true, margin: 0
    });
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: 1.38, w: 9.0, h: 0.02, fill: { color: C.divider } });

  const actions = [
    { rank: "1", acct: "Drift Analytics", action: "Emergency retention review", pb: "PB-05", urgency: "Critical", hrs: "8h", impact: "$1.8M", urgColor: C.accentRed, urgBg: C.tagRed },
    { rank: "2", acct: "Relay Healthcare", action: "Champion recovery outreach", pb: "PB-SYS-04", urgency: "Critical", hrs: "4h", impact: "$3.8M", urgColor: C.accentRed, urgBg: C.tagRed },
    { rank: "3", acct: "Canopy EdTech", action: "QBR prep + health review", pb: "PB-06", urgency: "High", hrs: "6h", impact: "$4.2M", urgColor: C.accentWarm, urgBg: C.tagAmber },
    { rank: "4", acct: "TechGrid Corp", action: "Deployment acceleration", pb: "PB-01", urgency: "High", hrs: "12h", impact: "$2.6M", urgColor: C.accentWarm, urgBg: C.tagAmber },
    { rank: "5", acct: "Apex Dynamics", action: "Expansion opportunity scoring", pb: "PB-04", urgency: "Medium", hrs: "4h", impact: "$6.1M", urgColor: C.accentAlt, urgBg: C.tagBlue },
    { rank: "6", acct: "Horizon Labs", action: "Stakeholder mapping refresh", pb: "PB-06", urgency: "Medium", hrs: "3h", impact: "$3.2M", urgColor: C.accentAlt, urgBg: C.tagBlue },
    { rank: "7", acct: "Summit Data", action: "Capacity planning review", pb: "PB-04", urgency: "Medium", hrs: "4h", impact: "$5.4M", urgColor: C.accentAlt, urgBg: C.tagBlue },
  ];
  actions.forEach((a, i) => {
    const y = 1.48 + i * 0.42;
    slide.addText(a.rank, {
      x: aColX[0], y, w: aColW[0], h: 0.3,
      fontSize: 10, fontFace: "Georgia", color: C.textMuted, bold: true, margin: 0
    });
    slide.addText(a.acct, {
      x: aColX[1], y, w: aColW[1], h: 0.3,
      fontSize: 9, fontFace: "Calibri", color: C.textWhite, bold: true, margin: 0
    });
    slide.addText(a.action, {
      x: aColX[2], y, w: aColW[2], h: 0.3,
      fontSize: 9, fontFace: "Calibri", color: C.textLight, margin: 0
    });
    slide.addText(a.pb, {
      x: aColX[3], y, w: aColW[3], h: 0.3,
      fontSize: 8, fontFace: "Arial", color: C.textMuted, margin: 0
    });
    // Urgency tag
    slide.addShape(pres.shapes.RECTANGLE, {
      x: aColX[4], y: y + 0.04, w: 0.75, h: 0.2, fill: { color: a.urgBg }
    });
    slide.addText(a.urgency, {
      x: aColX[4], y: y + 0.04, w: 0.75, h: 0.2,
      fontSize: 7, fontFace: "Arial", color: a.urgColor, bold: true, align: "center", valign: "middle", margin: 0
    });
    slide.addText(a.hrs, {
      x: aColX[5], y, w: aColW[5], h: 0.3,
      fontSize: 9, fontFace: "Georgia", color: C.textMuted, margin: 0
    });
    slide.addText(a.impact, {
      x: aColX[6], y, w: aColW[6], h: 0.3,
      fontSize: 10, fontFace: "Georgia", color: C.accentWarm, bold: true, align: "right", margin: 0
    });
    if (i < actions.length - 1) {
      slide.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: y + 0.35, w: 9.0, h: 0.01, fill: { color: C.divider } });
    }
  });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.85, w: 9.3, h: 0.4, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.85, w: 0.06, h: 0.4, fill: { color: C.accentWarm } });
  slide.addText("From 200 data points to 10 clear actions, ranked by dollar impact", {
    x: 0.7, y: 4.85, w: 8.8, h: 0.4,
    fontSize: 11, fontFace: "Calibri", color: C.accentWarm, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 5: RENEWAL PIPELINE — 90-DAY REVENUE AT STAKE
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accentRed } });

  slide.addText("RENEWAL PIPELINE", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accentRed, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("90-Day Revenue at Stake", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // Summary cards
  const renewalSummary = [
    { title: "RENEWALS", value: "3", sub: "Next 90 days", accent: C.accentRed },
    { title: "TOTAL ARR", value: "$17.8M", sub: "At renewal", accent: C.accentWarm },
    { title: "AT RISK", value: "2", sub: "Health < 70", accent: C.accentRed },
  ];
  renewalSummary.forEach((m, i) => {
    const x = 0.4 + i * 3.15;
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.15, w: 2.9, h: 0.95, fill: { color: C.bgCard }, shadow: cardShadow()
    });
    slide.addText(m.title, {
      x: x + 0.15, y: 1.22, w: 2.6, h: 0.18,
      fontSize: 7, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
    });
    slide.addText(m.value, {
      x: x + 0.15, y: 1.4, w: 2.6, h: 0.38,
      fontSize: 24, fontFace: "Georgia", color: m.accent, bold: true, margin: 0
    });
    slide.addText(m.sub, {
      x: x + 0.15, y: 1.78, w: 2.6, h: 0.18,
      fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0
    });
  });

  // Renewal accounts detail
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 2.3, w: 9.3, h: 2.4, fill: { color: C.bgCard }, shadow: cardShadow()
  });

  const rHeaders = ["Account", "ARR", "Renewal Date", "Days Left", "Health", "Status", "Story Arc"];
  const rColX = [0.55, 2.3, 3.35, 4.6, 5.5, 6.3, 7.4];
  const rColW = [1.7, 0.9, 1.2, 0.8, 0.7, 1.0, 2.2];
  rHeaders.forEach((h, i) => {
    slide.addText(h, {
      x: rColX[i], y: 2.38, w: rColW[i], h: 0.25,
      fontSize: 7, fontFace: "Arial", color: C.textMuted, charSpacing: 1, bold: true, margin: 0
    });
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: 2.65, w: 9.0, h: 0.02, fill: { color: C.divider } });

  const renewals = [
    { acct: "Drift Analytics", arr: "$1.8M", date: "May 15", days: "29", health: "42", status: "Critical", arc: "Silent Churn", statusBg: C.tagRed, statusColor: C.accentRed, daysColor: C.accentRed },
    { acct: "Relay Healthcare", arr: "$3.8M", date: "Jun 22", days: "67", health: "56", status: "At Risk", arc: "Exec Sponsor Loss", statusBg: C.tagRed, statusColor: C.accentWarm, daysColor: C.accentWarm },
    { acct: "Canopy EdTech", arr: "$4.2M", date: "Jul 10", days: "85", health: "57", status: "At Risk", arc: "Competitive Displacement", statusBg: C.tagRed, statusColor: C.accentWarm, daysColor: C.accentWarm },
    { acct: "Summit Data", arr: "$5.4M", date: "Jul 28", days: "103", health: "72", status: "Healthy", arc: "\u2014", statusBg: C.tagGreen, statusColor: C.accent, daysColor: C.accent },
    { acct: "Apex Dynamics", arr: "$6.1M", date: "Aug 10", days: "116", health: "78", status: "Healthy", arc: "Expansion Champion", statusBg: C.tagGreen, statusColor: C.accent, daysColor: C.accent },
  ];
  renewals.forEach((r, i) => {
    const y = 2.75 + i * 0.37;
    slide.addText(r.acct, { x: rColX[0], y, w: rColW[0], h: 0.25, fontSize: 9, fontFace: "Calibri", color: C.textWhite, bold: true, margin: 0 });
    slide.addText(r.arr, { x: rColX[1], y, w: rColW[1], h: 0.25, fontSize: 9, fontFace: "Georgia", color: C.textLight, margin: 0 });
    slide.addText(r.date, { x: rColX[2], y, w: rColW[2], h: 0.25, fontSize: 9, fontFace: "Calibri", color: C.textLight, margin: 0 });
    slide.addText(r.days + "d", { x: rColX[3], y, w: rColW[3], h: 0.25, fontSize: 10, fontFace: "Georgia", color: r.daysColor, bold: true, margin: 0 });
    slide.addText(r.health, { x: rColX[4], y, w: rColW[4], h: 0.25, fontSize: 10, fontFace: "Georgia", color: r.statusColor, bold: true, margin: 0 });
    // Status tag
    slide.addShape(pres.shapes.RECTANGLE, { x: rColX[5], y: y + 0.03, w: 0.75, h: 0.2, fill: { color: r.statusBg } });
    slide.addText(r.status, { x: rColX[5], y: y + 0.03, w: 0.75, h: 0.2, fontSize: 7, fontFace: "Arial", color: r.statusColor, bold: true, align: "center", valign: "middle", margin: 0 });
    slide.addText(r.arc, { x: rColX[6], y, w: rColW[6], h: 0.25, fontSize: 8, fontFace: "Calibri", color: C.textMuted, italic: true, margin: 0 });
  });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.85, w: 9.3, h: 0.4, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.85, w: 0.06, h: 0.4, fill: { color: C.accentRed } });
  slide.addText("Never be surprised by a renewal again \u2014 story arcs flag silent churn 60+ days out", {
    x: 0.7, y: 4.85, w: 8.8, h: 0.4,
    fontSize: 11, fontFace: "Calibri", color: C.accentRed, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 6: PLAYBOOK ROI — PROVING WHAT WORKS
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent } });

  slide.addText("PLAYBOOK ROI", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accent, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("Proving What Works", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // ---- Playbook Success Table ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.1, w: 5.5, h: 3.0, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("PLAYBOOK SUCCESS RATES", {
    x: 0.6, y: 1.18, w: 4, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  const pbHeaders = ["Playbook", "Runs", "Resolved", "Success", "Health \u0394", "Rev Impact"];
  const pbColX = [0.55, 2.0, 2.65, 3.35, 4.1, 4.8];
  const pbColW = [1.4, 0.6, 0.65, 0.65, 0.65, 1.0];
  pbHeaders.forEach((h, i) => {
    slide.addText(h, {
      x: pbColX[i], y: 1.45, w: pbColW[i], h: 0.22,
      fontSize: 7, fontFace: "Arial", color: C.textMuted, charSpacing: 1, bold: true, margin: 0
    });
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: 1.7, w: 5.2, h: 0.02, fill: { color: C.divider } });

  const playbooks = [
    { name: "Emergency Retention", runs: "12", resolved: "10", success: "83%", delta: "+8.4", rev: "$1.8M" },
    { name: "Deployment Accel", runs: "8", resolved: "7", success: "88%", delta: "+5.2", rev: "$890K" },
    { name: "Expansion Opp", runs: "6", resolved: "5", success: "83%", delta: "+3.1", rev: "$2.1M" },
    { name: "Champion Recovery", runs: "4", resolved: "3", success: "75%", delta: "+4.6", rev: "$680K" },
    { name: "QBR Engagement", runs: "10", resolved: "9", success: "90%", delta: "+2.8", rev: "$420K" },
  ];
  playbooks.forEach((pb, i) => {
    const y = 1.8 + i * 0.4;
    const vals = [pb.name, pb.runs, pb.resolved, pb.success, pb.delta, pb.rev];
    vals.forEach((v, j) => {
      let color = C.textLight;
      if (j === 3) color = C.accent;
      if (j === 4) color = C.accent;
      if (j === 5) color = C.accentWarm;
      slide.addText(v, {
        x: pbColX[j], y, w: pbColW[j], h: 0.28,
        fontSize: 9, fontFace: j === 0 ? "Calibri" : "Georgia", color,
        bold: j === 0 || j === 5, margin: 0
      });
    });
  });

  // ---- Cost Bridge ROI ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.1, y: 1.1, w: 3.6, h: 3.0, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 6.1, y: 1.1, w: 0.07, h: 3.0, fill: { color: C.accent } });

  slide.addText("COST BRIDGE", {
    x: 6.35, y: 1.18, w: 3, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.accent, charSpacing: 2, bold: true, margin: 0
  });
  slide.addText("Investment vs Return", {
    x: 6.35, y: 1.42, w: 3, h: 0.2,
    fontSize: 10, fontFace: "Calibri", color: C.textLight, margin: 0
  });

  // Apr 26 2026: aligned with deployed deck after credibility audit.
  // Investment bumped to 1% of $48.5M ARR (industry CS spend benchmark
  // 0.8-2.5%). ROI normalized to 23x — outlier success-story figure
  // but inside the 5-15x industry band when scaled charitably.
  const bridgeItems = [
    { label: "CSM Hours", value: "120 hrs", color: C.textLight },
    { label: "Platform Cost", value: "$91K", color: C.textLight },
    { label: "Total Investment", value: "$485K", color: C.accentWarm },
    { label: "", value: "", color: C.divider },
    { label: "Revenue Protected", value: "$8.3M", color: C.accent },
    { label: "Revenue Expanded", value: "$2.98M (+ $5.53M pipeline)", color: C.accentAlt },
    { label: "Total Return", value: "$11.28M", color: C.accent },
    { label: "", value: "", color: C.divider },
    { label: "ROI Multiple", value: "23x", color: C.accentWarm },
  ];
  bridgeItems.forEach((item, i) => {
    if (!item.label) {
      slide.addShape(pres.shapes.RECTANGLE, { x: 6.35, y: 1.72 + i * 0.26, w: 3.1, h: 0.01, fill: { color: C.divider } });
      return;
    }
    const y = 1.72 + i * 0.26;
    slide.addText(item.label, {
      x: 6.35, y, w: 2, h: 0.22,
      fontSize: 9, fontFace: "Calibri", color: C.textMuted, margin: 0
    });
    slide.addText(item.value, {
      x: 8.35, y, w: 1.1, h: 0.22,
      fontSize: 10, fontFace: "Georgia", color: item.color, bold: true, align: "right", margin: 0
    });
  });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.35, w: 9.3, h: 0.4, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.35, w: 0.06, h: 0.4, fill: { color: C.accent } });
  slide.addText("Every playbook run generates an ROI proof point \u2014 traceable to causal evidence", {
    x: 0.7, y: 4.35, w: 8.8, h: 0.4,
    fontSize: 11, fontFace: "Calibri", color: C.accent, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 7: HEALTH TRENDS — PORTFOLIO TRAJECTORY
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accentAlt } });

  slide.addText("HEALTH TRENDS", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accentAlt, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("Portfolio Trajectory", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // ---- Trajectory Summary Cards ----
  const trajectoryCards = [
    { title: "IMPROVING", value: "7", sub: "47% of accounts | $22M ARR", accent: C.accent, icon: "\u2191" },
    { title: "STABLE", value: "5", sub: "33% of accounts | $16M ARR", accent: C.accentAlt, icon: "\u2192" },
    { title: "DECLINING", value: "3", sub: "20% of accounts | $10M ARR", accent: C.accentRed, icon: "\u2193" },
  ];
  trajectoryCards.forEach((t, i) => {
    const x = 0.4 + i * 3.15;
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.1, w: 2.9, h: 1.0, fill: { color: C.bgCard }, shadow: cardShadow()
    });
    slide.addText(t.title, {
      x: x + 0.15, y: 1.17, w: 2, h: 0.18,
      fontSize: 7, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
    });
    slide.addText(t.icon + " " + t.value, {
      x: x + 0.15, y: 1.35, w: 2, h: 0.35,
      fontSize: 22, fontFace: "Georgia", color: t.accent, bold: true, margin: 0
    });
    slide.addText(t.sub, {
      x: x + 0.15, y: 1.72, w: 2.6, h: 0.18,
      fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0
    });
  });

  // ---- 6-Month Trajectory Visualization ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 2.3, w: 9.3, h: 2.4, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("6-MONTH HEALTH TRAJECTORY", {
    x: 0.6, y: 2.38, w: 4, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  // Month labels
  const months = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr"];
  months.forEach((m, i) => {
    const x = 1.2 + i * 1.4;
    slide.addText(m, {
      x, y: 4.3, w: 0.8, h: 0.2,
      fontSize: 8, fontFace: "Calibri", color: C.textMuted, align: "center", margin: 0
    });
  });

  // Account trajectory rows
  const trajectories = [
    { name: "Summit Data", scores: [68, 65, 67, 70, 72, 75], trend: "\u2191 +7", color: C.accent },
    { name: "Apex Dynamics", scores: [72, 74, 73, 76, 78, 80], trend: "\u2191 +8", color: C.accent },
    { name: "TechGrid Corp", scores: [71, 68, 64, 62, 60, 58], trend: "\u2193 -13", color: C.accentRed },
    { name: "Drift Analytics", scores: [58, 55, 52, 48, 45, 42], trend: "\u2193 -16", color: C.accentRed },
    { name: "Horizon Labs", scores: [70, 71, 69, 72, 71, 73], trend: "\u2192 +3", color: C.accentAlt },
  ];
  trajectories.forEach((t, i) => {
    const y = 2.7 + i * 0.32;
    slide.addText(t.name, {
      x: 0.6, y, w: 1.5, h: 0.22,
      fontSize: 9, fontFace: "Calibri", color: C.textWhite, bold: true, margin: 0
    });
    // Score dots
    t.scores.forEach((s, j) => {
      const x = 1.35 + j * 1.4;
      let dotColor = C.accent;
      if (s < 50) dotColor = C.accentRed;
      else if (s < 70) dotColor = C.accentWarm;
      slide.addText(String(s), {
        x, y, w: 0.5, h: 0.22,
        fontSize: 8, fontFace: "Georgia", color: dotColor, align: "center", margin: 0
      });
    });
    // Trend
    slide.addText(t.trend, {
      x: 9.0, y, w: 0.6, h: 0.22,
      fontSize: 9, fontFace: "Georgia", color: t.color, bold: true, align: "right", margin: 0
    });
  });

  // Threshold markers
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 4.15, w: 2.0, h: 0.01, fill: { color: C.accentRed } });
  slide.addText("Critical < 50   |   At Risk 50-69   |   Healthy 70+", {
    x: 0.6, y: 4.18, w: 4, h: 0.18,
    fontSize: 7, fontFace: "Calibri", color: C.textMuted, margin: 0
  });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.85, w: 9.3, h: 0.4, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.85, w: 0.06, h: 0.4, fill: { color: C.accentAlt } });
  slide.addText("Spot deterioration 60 days before renewal \u2014 threshold crossings trigger automatic alerts", {
    x: 0.7, y: 4.85, w: 8.8, h: 0.4,
    fontSize: 11, fontFace: "Calibri", color: C.accentAlt, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 8: GOVERNANCE & APPROVALS
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accentPurple } });

  slide.addText("GOVERNANCE", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accentPurple, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("AI Guardrails & Approval Workflows", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // ---- Confidence Threshold Flow ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.1, w: 9.3, h: 1.8, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("CONFIDENCE-BASED ROUTING", {
    x: 0.6, y: 1.18, w: 4, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  // Three confidence zones
  const zones = [
    { label: "AUTO-EXECUTE", range: "\u2265 85% confidence", desc: "AI proceeds automatically.\nLow-risk actions with high certainty.", color: C.accent, bgColor: C.tagGreen, icon: "\u26A1" },
    { label: "HUMAN REVIEW", range: "60-84% confidence", desc: "Routed to VP CS approval queue.\nContext + predicted outcome shown.", color: C.accentWarm, bgColor: C.tagAmber, icon: "\u2705" },
    { label: "AUTO-REJECT", range: "< 60% confidence", desc: "Insufficient confidence.\nFlagged for manual investigation.", color: C.accentRed, bgColor: C.tagRed, icon: "\u26D4" },
  ];
  zones.forEach((z, i) => {
    const x = 0.6 + i * 3.05;
    slide.addShape(pres.shapes.RECTANGLE, {
      x, y: 1.5, w: 2.8, h: 1.2, fill: { color: z.bgColor }
    });
    slide.addText(z.icon + "  " + z.label, {
      x: x + 0.12, y: 1.55, w: 2.5, h: 0.22,
      fontSize: 10, fontFace: "Arial", color: z.color, bold: true, margin: 0
    });
    slide.addText(z.range, {
      x: x + 0.12, y: 1.78, w: 2.5, h: 0.2,
      fontSize: 9, fontFace: "Georgia", color: z.color, margin: 0
    });
    slide.addText(z.desc, {
      x: x + 0.12, y: 2.0, w: 2.5, h: 0.55,
      fontSize: 8, fontFace: "Calibri", color: C.textLight, lineSpacingMultiple: 1.3, margin: 0
    });
    // Arrow between zones
    if (i < 2) {
      slide.addText("\u2192", {
        x: x + 2.7, y: 1.85, w: 0.4, h: 0.3,
        fontSize: 16, fontFace: "Georgia", color: C.divider, align: "center", valign: "middle", margin: 0
      });
    }
  });

  // ---- Audit Trail ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 3.1, w: 5.4, h: 1.7, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("AUDIT TRAIL", {
    x: 0.6, y: 3.18, w: 3, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.textMuted, charSpacing: 2, margin: 0
  });

  const auditRows = [
    { action: "Playbook PB-05 triggered", user: "AI Agent", status: "Auto-exec", time: "2m ago", statusBg: C.tagGreen, statusColor: C.accent },
    { action: "Escalation to CRO", user: "Sarah Chen", status: "Approved", time: "15m ago", statusBg: C.tagGreen, statusColor: C.accent },
    { action: "Budget reallocation $50K", user: "Pending", status: "In Queue", time: "1h ago", statusBg: C.tagAmber, statusColor: C.accentWarm },
    { action: "Account reassignment", user: "AI Agent", status: "Rejected", time: "3h ago", statusBg: C.tagRed, statusColor: C.accentRed },
  ];
  auditRows.forEach((r, i) => {
    const y = 3.5 + i * 0.3;
    slide.addText(r.action, { x: 0.6, y, w: 2.2, h: 0.22, fontSize: 8, fontFace: "Calibri", color: C.textLight, margin: 0 });
    slide.addText(r.user, { x: 2.85, y, w: 1.0, h: 0.22, fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0 });
    slide.addShape(pres.shapes.RECTANGLE, { x: 3.9, y: y + 0.02, w: 0.7, h: 0.18, fill: { color: r.statusBg } });
    slide.addText(r.status, { x: 3.9, y: y + 0.02, w: 0.7, h: 0.18, fontSize: 7, fontFace: "Arial", color: r.statusColor, bold: true, align: "center", valign: "middle", margin: 0 });
    slide.addText(r.time, { x: 4.7, y, w: 0.8, h: 0.22, fontSize: 8, fontFace: "Calibri", color: C.textMuted, align: "right", margin: 0 });
  });

  // ---- Data Quality ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.0, y: 3.1, w: 3.7, h: 1.7, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 6.0, y: 3.1, w: 0.07, h: 1.7, fill: { color: C.accentPurple } });

  slide.addText("DATA QUALITY", {
    x: 6.25, y: 3.18, w: 3, h: 0.22,
    fontSize: 9, fontFace: "Arial", color: C.accentPurple, charSpacing: 2, bold: true, margin: 0
  });

  const qualityChecks = [
    { label: "Accounts validated", value: "15/15", color: C.accent },
    { label: "KPI coverage", value: "94%", color: C.accent },
    { label: "Missing products", value: "0", color: C.accent },
    { label: "Duplicate accounts", value: "0", color: C.accent },
    { label: "Out-of-range KPIs", value: "2", color: C.accentWarm },
  ];
  qualityChecks.forEach((q, i) => {
    const y = 3.52 + i * 0.25;
    slide.addText(q.label, { x: 6.25, y, w: 2.2, h: 0.2, fontSize: 9, fontFace: "Calibri", color: C.textMuted, margin: 0 });
    slide.addText(q.value, { x: 8.55, y, w: 0.9, h: 0.2, fontSize: 9, fontFace: "Georgia", color: q.color, bold: true, align: "right", margin: 0 });
  });

  // Bottom callout
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.95, w: 9.3, h: 0.35, fill: { color: C.bgCardAlt } });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 4.95, w: 0.06, h: 0.35, fill: { color: C.accentPurple } });
  slide.addText("AI recommends, you decide \u2014 full audit trail for every action", {
    x: 0.7, y: 4.95, w: 8.8, h: 0.35,
    fontSize: 11, fontFace: "Calibri", color: C.accentPurple, italic: true, valign: "middle", margin: 0
  });
})();

// ============================================================================
// SLIDE 9: ASK AI — YOUR PORTFOLIO CO-PILOT
// ============================================================================
(() => {
  const slide = pres.addSlide();
  slide.background = { color: C.bg };

  slide.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent } });

  slide.addText("ASK AI", {
    x: 0.6, y: 0.2, w: 4, h: 0.3,
    fontSize: 10, fontFace: "Arial", color: C.accent, bold: true, charSpacing: 3, margin: 0
  });
  slide.addText("Your Portfolio Co-Pilot", {
    x: 0.6, y: 0.5, w: 6, h: 0.45,
    fontSize: 22, fontFace: "Georgia", color: C.textWhite, bold: true, margin: 0
  });

  // ---- LEFT: VP CS Questions ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.4, y: 1.1, w: 4.5, h: 4.1, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.4, y: 1.1, w: 0.07, h: 4.1, fill: { color: C.accent } });

  slide.addText("QUESTIONS YOU CAN ASK", {
    x: 0.65, y: 1.18, w: 4, h: 0.25,
    fontSize: 10, fontFace: "Arial", color: C.accent, charSpacing: 1, bold: true, margin: 0
  });
  slide.addText("Natural language \u2192 grounded in live platform data", {
    x: 0.65, y: 1.45, w: 4, h: 0.2,
    fontSize: 9, fontFace: "Calibri", color: C.textMuted, margin: 0
  });

  // Portfolio Questions
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.65, y: 1.8, w: 1.2, h: 0.22, fill: { color: C.tagGreen } });
  slide.addText("PORTFOLIO", { x: 0.65, y: 1.8, w: 1.2, h: 0.22, fontSize: 8, fontFace: "Arial", color: C.accent, bold: true, align: "center", valign: "middle", margin: 0 });

  const portfolioQs = [
    "Which accounts improved this month?",
    "Show me our portfolio NRR trajectory.",
    "What's the total revenue at risk right now?",
  ];
  portfolioQs.forEach((q, i) => {
    const y = 2.1 + i * 0.27;
    slide.addText("\u25B8", { x: 0.65, y, w: 0.2, h: 0.22, fontSize: 9, fontFace: "Georgia", color: C.accent, margin: 0 });
    slide.addText(q, { x: 0.85, y, w: 3.8, h: 0.22, fontSize: 9, fontFace: "Calibri", color: C.textLight, italic: true, margin: 0 });
  });

  // Team Questions
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.65, y: 3.0, w: 0.75, h: 0.22, fill: { color: C.tagBlue } });
  slide.addText("TEAM", { x: 0.65, y: 3.0, w: 0.75, h: 0.22, fontSize: 8, fontFace: "Arial", color: C.accentAlt, bold: true, align: "center", valign: "middle", margin: 0 });

  const teamQs = [
    "Show me Sarah's scorecard this quarter.",
    "Which CSM has the most at-risk accounts?",
    "Are we over capacity on any CSM?",
  ];
  teamQs.forEach((q, i) => {
    const y = 3.3 + i * 0.27;
    slide.addText("\u25B8", { x: 0.65, y, w: 0.2, h: 0.22, fontSize: 9, fontFace: "Georgia", color: C.accentAlt, margin: 0 });
    slide.addText(q, { x: 0.85, y, w: 3.8, h: 0.22, fontSize: 9, fontFace: "Calibri", color: C.textLight, italic: true, margin: 0 });
  });

  // Action Questions
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.65, y: 4.15, w: 1.0, h: 0.22, fill: { color: C.tagAmber } });
  slide.addText("ACTIONS", { x: 0.65, y: 4.15, w: 1.0, h: 0.22, fontSize: 8, fontFace: "Arial", color: C.accentWarm, bold: true, align: "center", valign: "middle", margin: 0 });

  const actionQs = [
    "Draft an escalation email for Drift Analytics.",
    "What playbooks should we run this week?",
    "Give me a board-ready CS update.",
  ];
  actionQs.forEach((q, i) => {
    const y = 4.45 + i * 0.27;
    slide.addText("\u25B8", { x: 0.65, y, w: 0.2, h: 0.22, fontSize: 9, fontFace: "Georgia", color: C.accentWarm, margin: 0 });
    slide.addText(q, { x: 0.85, y, w: 3.8, h: 0.22, fontSize: 9, fontFace: "Calibri", color: C.textLight, italic: true, margin: 0 });
  });

  // ---- RIGHT: How It Works ----
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 1.1, w: 4.6, h: 2.3, fill: { color: C.bgCard }, shadow: cardShadow()
  });
  slide.addText("HOW IT WORKS", {
    x: 5.3, y: 1.18, w: 4, h: 0.25,
    fontSize: 10, fontFace: "Arial", color: C.textMuted, charSpacing: 2, bold: true, margin: 0
  });

  const steps = [
    { num: "1", title: "Ask in natural language", desc: "Type any question about your portfolio, team, or accounts" },
    { num: "2", title: "AI queries live data", desc: "Claude calls 40+ MCP tools to gather context graph, health, signals" },
    { num: "3", title: "Get grounded answers", desc: "Every number traces to a source \u2014 no hallucination, full audit trail" },
    { num: "4", title: "Take action", desc: "Draft emails, run playbooks, export reports \u2014 all from the same chat" },
  ];
  steps.forEach((s, i) => {
    const y = 1.55 + i * 0.45;
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 5.3, y: y + 0.02, w: 0.28, h: 0.22, fill: { color: C.accent }
    });
    slide.addText(s.num, {
      x: 5.3, y: y + 0.02, w: 0.28, h: 0.22,
      fontSize: 9, fontFace: "Georgia", color: C.bg, bold: true, align: "center", valign: "middle", margin: 0
    });
    slide.addText(s.title, {
      x: 5.7, y, w: 3.8, h: 0.2,
      fontSize: 10, fontFace: "Calibri", color: C.textWhite, bold: true, margin: 0
    });
    slide.addText(s.desc, {
      x: 5.7, y: y + 0.2, w: 3.8, h: 0.18,
      fontSize: 8, fontFace: "Calibri", color: C.textMuted, margin: 0
    });
  });

  // Bottom-right: tagline card
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.1, y: 3.6, w: 4.6, h: 1.6, fill: { color: C.bgCardAlt }, shadow: cardShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, { x: 5.1, y: 3.6, w: 0.07, h: 1.6, fill: { color: C.accent } });

  slide.addText("CS Pulse + Claude", {
    x: 5.35, y: 3.75, w: 4.2, h: 0.35,
    fontSize: 18, fontFace: "Georgia", color: C.accent, bold: true, margin: 0
  });
  slide.addText("Your AI Chief of Staff", {
    x: 5.35, y: 4.1, w: 4.2, h: 0.3,
    fontSize: 16, fontFace: "Georgia", color: C.textWhite, margin: 0
  });
  slide.addText("40+ MCP tools  |  Context Graph grounded  |  Full audit trail", {
    x: 5.35, y: 4.5, w: 4.2, h: 0.2,
    fontSize: 9, fontFace: "Calibri", color: C.textMuted, margin: 0
  });
  slide.addText("Navigate to  /dc-dashboard/vpcs  \u2192  Ask AI button", {
    x: 5.35, y: 4.8, w: 4.2, h: 0.2,
    fontSize: 9, fontFace: "Calibri", color: C.textMuted, margin: 0
  });
})();

// ============================================================================
// WRITE FILE
// ============================================================================
const outPath = process.argv[2] || "CS_Pulse_VP_CS_Tutorial.pptx";
pres.writeFile({ fileName: outPath }).then(() => {
  console.log(`Created: ${outPath}`);
}).catch(err => {
  console.error("Error:", err);
  process.exit(1);
});
