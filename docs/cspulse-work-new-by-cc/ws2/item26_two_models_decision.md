# Item 26 — the two revenue models, quantified. Owner decision, not applied.

**Retraction of my earlier "align the map" recommendation.** Reading the code
properly (2026-08-24): this is not a buggy alias map, it is **two different
definitions of what "at risk" means**, with different bucket structures. A
one-line map edit would double-count risk or drop nodes for every customer.
Here is the real decision, with live dollars.

## What each path actually computes (live, all tenants)

| cust | ARR | Model A (account drilldown) | Model B (CFO summary) |
|---|---|---|---|
| | | at_risk / lost | at_risk (no lost bucket) |
| 390 | $50.0M | **$9.13M** / $10.67M | **$10.67M** |
| 391 | $35.9M | $9.32M / $9.96M | $9.96M |
| 392 | $28.2M | $7.58M / $7.99M | $7.99M |
| 393 | $50.0M | $9.13M / $10.67M | $10.67M |
| 398 | $17.6M | $7.06M / $7.99M | $7.99M |
| 399 | $23.3M | $4.80M / $6.51M | $6.51M |
| 400 | $18.5M | $5.89M / $7.52M | $7.52M |
| 401 | $5.0M | $0.90M / $0.56M | $0.56M |

**The exact relationship, on every row:**
- **Model B's `at_risk` == Model A's `lost`** (390: both $10.67M). Same nodes, opposite label.
- **Model A's `at_risk` == the health prediction** (390: $9.13M, from `_calculate_at_risk_from_health`, 40/20/5% of ARR by health band). Not from nodes at all.

So the divergence is not cosmetic. On 390 a CFO sees **"$10.67M at risk"** on the
summary; drilling into accounts they see **"$9.13M at risk" + "$10.67M lost"** —
the same $10.67M is "at risk" on one screen and "lost" on the next, plus a third
number ($9.13M) that only exists at account level.

## The actual question

What do the risk-named OUTCOME nodes (`revenue_at_risk`, `renewal_uncertainty`,
`capacity_constraint`, `engagement_decline` — $53.7M/$9.5M/$16.5M/$8.3M
platform-wide) represent?

- **Money at risk (not yet lost)** → they belong in `at_risk`; their names say so; they're node-evidenced. This is Model B.
- **Realized/confirmed loss** → they belong in `lost`; this is Model A.

And separately: what is the **health prediction** ($9.13M on 390)? It's a
heuristic (ARR × band), not evidence — the same modeled-estimate class as the
benchmark items. It should not silently share a bucket label with node-evidenced
figures.

## Key fact that points to the fix: the CFO dashboard ALREADY separates them

The CFO surface shows **"Confirmed Risk (Context Graph)"** (node-based, = Model B
at_risk) AND a separate **"Modeled Cost of Inaction"** (health-based). It already
treats node-risk and health-risk as two different things. The **account-level
`get_revenue_at_risk` is the outlier** — it conflates by putting the health
prediction in `at_risk` and the nodes in `lost`.

## Recommended model (C) — but it's your call, and it moves account-level dollars

Align `get_revenue_at_risk` to the CFO's existing separation:
1. **`at_risk` = the risk-named OUTCOME nodes** (node-evidenced "confirmed risk") — matches the CFO "Confirmed Risk" number. On 390 this makes account-level at_risk = $10.67M (up from $9.13M), agreeing with the summary.
2. **health prediction → a separate `modeled_at_risk` field**, labeled as modeled — matches "Cost of Inaction". Never summed into the evidenced at_risk.
3. **`lost` = only genuinely-realized-loss subtypes** (`churn_lost`, `contraction`, `revenue_lost`) — not the risk-named ones. On current data this empties `lost` to ~$0 for most tenants (no realized-churn nodes exist yet), which is correct: these are demo tenants mid-story, nothing has actually churned.

**The one genuine sub-judgment inside C:** `partial_recovery` ($3.76M, 4 nodes) —
at_risk (recovery in progress), lost, or split? Recommend at_risk.

## Per-customer impact of adopting C (account-level at_risk → matches CFO)

Every account-level `at_risk` rises to its Model-B value (e.g. 390 $9.13M→$10.67M),
`lost` drops to realized-only (~$0 on current data), and a new `modeled_at_risk`
carries the old health figure. The CFO summary is unchanged (already Model B).
Net effect: **the two surfaces finally agree, and "lost" stops overstating
realized losses by $10.67M on 390** (nothing has actually been lost on a
mid-story demo tenant).

## Decision requested

1. Adopt Model C (align account-level to the CFO's node-vs-modeled separation)? (Recommend: yes.)
2. `partial_recovery` → at_risk / lost / split? (Recommend: at_risk.)
3. Keep `lost` as a bucket at all, or fold realized losses into a signed `net`? (Recommend: keep, but it'll be ~$0 until a tenant actually churns.)

On sign-off this is a focused rewrite of `get_revenue_at_risk`'s bucketing +
one new field + its tests — not a map edit, and node-count item 27 is already
shipped independently.
