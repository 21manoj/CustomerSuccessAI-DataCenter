# PortCo CEO Dashboard — Business Case Review

**Audience:** PE PortCo CEO / portfolio operator  
**Purpose:** Gap analysis of the PortCo CEO dashboard and ROI calculations from a business standpoint. No feature implementation; TBD items are captured in the product roadmap.

---

## What Exists Today

### Dashboard Tabs
- **Overview:** Portfolio-level KPIs (companies, total ARR, standalone vs. synergy impact, portfolio ROI, payback), synergy waterfall, standalone vs. portfolio impact bar, shared investment model.
- **Power of 1:** Six independent levers (TTFV, NRR, GRR, ticket resolution, product adoption, expansion rate) with per-lever improvement % sliders; portfolio impact, ROI, investment, and payback recalc from lever settings; per-lever impact breakdown.
- **Synergy Engine:** Five synergy types (shared playbooks, shared resources, vendor leverage, cross-sell, benchmarking) with $ impact and diminishing-returns curve by company.
- **Company Detail:** Per-company ARR, standalone impact, synergy impact, total impact; expandable synergy breakdown per company.
- **Settings:** Portfolio companies (add/remove), cost inputs, role rates, synergy overrides.

### ROI Calculation Engine
- **Power of 1:** Six metrics with configurable economics (baseline, annual impact per 1%, investment scaling +50% per additional 1% improvement); direct + compounding impact; per-metric and portfolio-level.
- **Multi-lever:** Each lever can have a different improvement %; investment and impact aggregate correctly across levers and scale by company ARR.
- **Synergy:** Position-based (company order) geometric decay curves; cost reduction (shared resources, vendor leverage) and impact lift (playbooks, cross-sell, benchmarking); synergy-adjusted investment and portfolio ROI.

### Data Used
- Portfolio membership (which customers are in which portfolio).
- Company-level **ARR** (sum of account revenue per customer).
- No product-level or SKU-level revenue; no customer/account overlap across portfolios; no explicit upsell/cross-sell attribution.

---

## Strengths (From a PE PortCo CEO Lens)

1. **Portfolio-level ROI and payback** — Single view of “we invest X, we get Y impact and Z synergy uplift” with a clear payback period.
2. **Six levers not locked in step** — Realistic modeling (e.g. NRR and TTFV can move at different rates).
3. **Synergy narrative** — Five synergy types with $ impact and diminishing returns; supports board/operator storytelling.
4. **Company ordering and position-based synergy** — Reflects “first platform company vs. subsequent” and shared playbooks/resources.
5. **Configurable costs and synergy curves** — Settings allow tuning to a specific fund or sector.

---

## Gaps and Missing Elements

### 1. **Product / Revenue Dimension**
- **Gap:** All economics are at **company ARR** or **portfolio total ARR**. There is no:
  - Product/SKU or line-of-business revenue breakdown per company.
  - View of which products drive retention vs. expansion.
  - Product-level margin or unit economics.
- **Implication:** Hard to answer “which products we should push across the portfolio” or “where expansion is coming from (upsell vs. cross-sell).”
- **Roadmap:** **[TBD] Product revenues dimension** — Add product/SKU revenue (and optionally cost) per company/portfolio; support product-level views and filters in PortCo CEO dashboard and ROI context. *(See COMPLETE_FEATURE_LIST_AND_SAAS_ROADMAP.md.)*

### 2. **Upsell / Cross-Sell Correlation and Attribution**
- **Gap:** Cross-sell is modeled as a **synergy type** (lift %) with no link to:
  - Actual product adoption or revenue by product.
  - Distinction between upsell (same product, more $) vs. cross-sell (new product).
  - Correlation of CS actions (playbooks, health) to revenue expansion.
- **Implication:** Synergy $ is model-based, not evidence-based; difficult to tie ROI to “we did X playbook and saw Y uplift in product Z.”
- **Roadmap:** **[TBD] Upsell and cross-sell correlation** — Introduce product-level revenue and, where possible, link to playbooks/health; flag correlation (or proxy) for upsell and cross-sell to support evidence-based synergy and ROI storytelling. *(See COMPLETE_FEATURE_LIST_AND_SAAS_ROADMAP.md.)*

### 3. **Customer Overlap Across Portfolios**
- **Gap:** A given **customer** can belong to only one portfolio in the UI; there is no:
  - View of the same account/customer appearing in multiple portfolios (e.g. different funds, co-invest).
  - Aggregate “customer overlap” view across portfolios with product/revenue per company.
- **Implication:** Multi-fund or co-invest structures cannot see shared names and avoid double-counting or conflicting strategies.
- **Roadmap:** **[TBD] Customer overlap across portfolios** — View showing customer/account overlap across portfolios with product and revenue view per company; support multi-portfolio membership and clear attribution of ARR/revenue by portfolio/context. *(See COMPLETE_FEATURE_LIST_AND_SAAS_ROADMAP.md.)*

### 4. **Other Notable Gaps (No TBD Added Yet)**
- **Time dimension:** No explicit quarter/period selector; impact is “annual” and payback in months but no time-series of actual vs. projected.
- **Variance vs. plan:** No “plan vs. actual” for lever improvements or synergy realization.
- **Benchmarking:** No peer or industry benchmark (e.g. “portfolio NRR vs. sector”) on the dashboard.
- **Exits / hold period:** No explicit hold period or exit assumptions in ROI (e.g. 3–5 year horizon).
- **Risk/confidence:** All outputs are point estimates; no ranges or confidence intervals for impact or payback.

---

## Summary

The PortCo CEO dashboard and ROI engine are strong for **single-portfolio, company-level ARR and synergy storytelling** and for **what-if lever analysis**. The main business-case gaps are: (1) **no product/revenue dimension**, (2) **no evidence-based upsell/cross-sell correlation**, and (3) **no customer overlap view across portfolios**. The first two are captured as TBD in the product roadmap (product revenues dimension; upsell/cross-sell correlation). The third is captured as TBD (customer overlap across portfolios with product/revenue view). No feature changes were made in this review; roadmap TBDs only.
