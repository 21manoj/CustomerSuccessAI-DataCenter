# Item 26/27 — revenue bucketing divergence: blast radius + decision

Reviewer independently confirmed both live on 390 (2026-08-24). Quantified
platform-wide before proposing a fix, because CFO-visible dollars move.

## The divergence (item 26)

Two hand-maintained bucketing maps in `utils/context_graph.py` disagree on **8
OUTCOME subtypes**:
- **per-account** (`get_revenue_at_risk._BUCKET_ALIASES`, ~:432) files them as **`lost`**
- **cross-account** (`_OUTCOME_RISK_TYPES`, :526) files them as **`at_risk`**

Same node, opposite label depending on which endpoint you ask. Node 124379
(Titan −$4.1M) is "Confirmed Risk" on the CFO dashboard but `lost` via
`get_revenue_at_risk` — the reviewer traced this exactly.

## Blast radius (live, all tenants)

**$91,742,000 flips at_risk↔lost depending on endpoint.** Only 5 of the 8
divergent subtypes carry live money:

| subtype | nodes | $ (conf-weighted) | correct bucket by its own name |
|---|---|---|---|
| `revenue_at_risk` | 20 | $53,700,000 | **at_risk** — the name literally says so |
| `capacity_constraint` | 16 | $16,479,000 | **at_risk** — a constraint is risk, not realized loss |
| `renewal_uncertainty` | 20 | $9,526,000 | **at_risk** — "uncertainty" is risk |
| `engagement_decline` | 27 | $8,277,000 | **at_risk** — a decline trajectory, not a closed loss |
| `partial_recovery` | 4 | $3,760,000 | **genuinely ambiguous** — some recovered, some not |

(`churn_lost`, `churn_risk`, `partner_friction` — in both maps but zero live nodes.)

390 is portfolio-wide, not just Titan: **7 of 12 accounts** carry divergent
nodes ($5.33M down to $270k).

## Recommendation — the per-account map is the bug, fix it (owner's call, not executed)

The evidence is near-dispositive: a subtype **named `revenue_at_risk` carrying
$53.7M is filed as realized `lost`** by the per-account map. Four of the five
money-bearing subtypes are risk-trajectory concepts that the cross-account map
already buckets correctly as `at_risk`. So the fix is to align
`_BUCKET_ALIASES` to `_OUTCOME_RISK_TYPES` — stop the per-account path recasting
these four as `lost`.

**Why flagged, not silently fixed:** it moves CFO-visible dollars (390's
account-level `lost` drops ~$10.67M, `at_risk` rises correspondingly), and one
subtype (`partial_recovery`, $3.76M) is a real judgment call — is a
partially-recovered account showing money-at-risk or money-lost? That's a
product-semantics decision the owner should make, not defaulted.

**Two questions for sign-off:**
1. Align the per-account map to at_risk for the 4 risk-named subtypes? (Recommend: yes.)
2. `partial_recovery` → at_risk, lost, or split? (No default; recommend at_risk since recovery-in-progress ≠ realized loss.)

Then the single fix is a small edit to one alias dict, and both endpoints agree.

## Item 27 — node_count overcount (bundled, smaller)

`get_revenue_at_risk` returns `node_count = len(outcome_nodes) + (1 if at_risk > 0)`.
The `+1` counts the health-model at_risk figure as if it were a node — it isn't
(it comes from `_calculate_at_risk_from_health`, no node behind it). Docstring
says "revenue-contributing nodes"; the count conflates real OUTCOME nodes with a
synthetic +1, so it matches neither the OUTCOME total nor the revenue-bearing
subset (reviewer: reported 7, actual revenue-bearing 5). Consumers:
`context_graph_api.py:479` → `ContextGraphView.tsx:602`. Fix: drop the +1 (or
return the health-derived contribution as separate metadata, not a fake node).
Also a rendered-number change — bundle the sign-off with item 26.
