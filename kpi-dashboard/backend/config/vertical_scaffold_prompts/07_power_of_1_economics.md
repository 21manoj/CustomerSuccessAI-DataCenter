# Prompt 07: Power of 1 Economics (ROI Model)

## Input Variables
- `{VERTICAL_ID}`, `{VERTICAL_NAME}`, `{INDUSTRY_DESCRIPTION}`
- `{KPI_DEFINITIONS}`: Full KPI list from Prompt 01
- `{PLAYBOOK_DEFINITIONS}`: Playbook list from Prompt 02
- `{ARR_BASELINE}`: Typical ARR for target customer segment (e.g., $10M)

## Prompt

```
You are a CS operations economist modeling the ROI of customer success
initiatives for {VERTICAL_NAME} ({INDUSTRY_DESCRIPTION}). Generate a
complete Power of 1 economics model that quantifies the dollar impact
of a 1% improvement in each key metric.

CONTEXT:
- ARR baseline: {ARR_BASELINE}
- All dollar values auto-scale by arr_scale = actual_arr / baseline_arr
- The model must connect: Metrics → Work Packages → Playbooks → ROI

GENERATE:

1. METRICS (6-8 key metrics):
   For each metric:
   - metric_id: Short identifier (e.g., "TTFV", "NRR", "GRR")
   - display_name: Human-readable name
   - baseline: Current typical value
   - unit: %, days, hours, score, etc.
   - direction: "higher_is_better" or "lower_is_better"
   - one_pct_move: What 1% improvement means in absolute terms
   - annual_impact_per_pct: Dollar impact of 1% improvement at baseline ARR
   - total_investment: Cost to achieve 1% improvement (CS + platform)
   - cs_initiative_cost: Portion from CS team effort
   - platform_cost: Portion from platform/tooling
   - roi_at_1_pct: (annual_impact - total_investment) / total_investment
   - payback_months: Months to break even
   - linked_playbooks: Which PB codes drive this metric
   - linked_kpis: Which KPI codes this metric maps to

   METRIC SELECTION RULES:
   - Must include: time-to-value, net retention, gross retention
   - Must include at least 1 operational metric (support, adoption)
   - Must include at least 1 expansion metric
   - ROI should range from -0.2 (hard metrics) to 3.5 (easy wins)

2. WORK_PACKAGES (4-5 per metric):
   For each work package:
   - wp_id: "WP-{metric}-{n}"
   - name: Specific deliverable
   - hours: Total hours to deliver
   - roles: Dict of role → hours (csm, cs_ops, product, platform, leadership)
   - description: One sentence

3. METRIC_CASCADES:
   Which metrics amplify each other. Format:
   { "NRR": {"GRR": 0.3, "expansion_rate": 0.4} }
   Meaning: 1% NRR improvement → 0.3% GRR lift + 0.4% expansion lift

4. SCALING_SCENARIOS:
   Three improvement levels (1%, 4%, 6%) with:
   - Total annual impact at baseline ARR
   - Total investment required
   - Net ROI
   - Months to positive ROI

5. TIME_ECONOMICS:
   Year 1 / Year 2 / Year 3 projections with compounding

OUTPUT FORMAT:
JSON matching the structure of config/power_of_1_economics.json.

CRITICAL:
- All dollar amounts must be realistic for the industry
- ROI math must be internally consistent (impact - investment = net)
- Work package hours must sum to total_investment / blended_rate
- Blended hourly rate ~ $100 (weighted across roles)
- At least 2 metrics should have negative or near-zero ROI (honest model)
```
