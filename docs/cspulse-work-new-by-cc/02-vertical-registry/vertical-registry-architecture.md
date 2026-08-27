# Vertical registry — removing `dc2_s` as the root

**Problem:** `dc2_s` currently plays two incompatible roles — a concrete vertical with its own pillars, KPIs and customers, *and* the fallback root every other vertical lands on when its config fails. A peer cannot be a parent.

**Consequence, observed:** when `datacenter_v1` or `saas_premium` fails to resolve, the caller does not receive generic defaults. It receives **another real industry's configuration**, with plausible pillar names a human reads as correct. That is why the bug survived — the wrong answer looked like a right answer.

---

## 1. The sharp claim: there should be no fallback at all

The reason `dc2_s` became the root is that someone needed *something* to return when a vertical's config was missing. That instinct is wrong for this class of data.

**A customer's pillar structure is identity, not preference.** There is no sensible default answer to "what are this customer's pillars," in the same way there is no sensible default for their ARR. You either know, or you must refuse.

So the target is not "a better base vertical." It is **no base vertical, and fail-closed resolution**. What gets shared is a *schema*, not a *configuration*.

---

## 2. You already have the right pattern

The signal taxonomy layer does this correctly today:

```
config/taxonomy_base.json                 ← a genuine base: shared structure, no industry
config/taxonomy_dc2_s.json                ← overlay
config/taxonomy_datacenter_v1.json        ← overlay
config/taxonomy_saas_premium.json         ← overlay
config/taxonomy_healthcare_provider.json  ← overlay
```

`taxonomy_base.json` is a *base*, not a *vertical*. Nobody's customer is assigned to it. That is exactly the distinction missing everywhere else.

**Generalise this pattern. Do not invent a new one.**

---

## 3. Target architecture

Three layers, and the middle one is the whole point.

```
  CONTRACT          vertical_schema.json
                    what every vertical MUST declare. No values, only shape.
                        │
  REGISTRY          verticals/registry.py
                    loads · validates against contract · resolves by slug
                    FAIL-CLOSED: unknown or invalid slug raises. Never substitutes.
                        │
  VERTICALS         verticals/dc2_s/            ← peers. all equal.
                    verticals/datacenter_v1/       no vertical imports another.
                    verticals/saas_premium/
                    verticals/healthcare_provider/
```

`dc2_s` becomes an ordinary peer with no special status. Its config is extracted into the same shape everything else uses.

**The registry is the only path.** Today `get_vertical_config`, `ScoreCalculator` and most of the codebase already go through `utils.vertical_registry` correctly — the defect is that `get_kpi_catalog` bypasses it with a hardcoded `if/else`. So this is mostly *removing bypasses*, not building new machinery.

---

## 4. What is universal vs. what every vertical must declare

**Universal — lives in core, never in a vertical:**

- Node types: SIGNAL · DECISION · OUTCOME · STAKEHOLDER · EXTERNAL_CONTEXT
- Edge types: LED_TO · TRIGGERED · CAUSED_BY · RESULTED_IN
- The L1→L2→L3→L4 rollup *algorithm*
- `evidence_tier` vocabulary
- Health-band *concept* (thresholds themselves are per-vertical)
- **Pillar role vocabulary** — `revenue`, `reliability`, `capacity`, `partner`, `expansion`, `adoption`, `engagement`, `compliance`. The role names are universal; the mapping is not.

**Per-vertical — must be declared, never defaulted:**

| must declare | why it cannot default |
|---|---|
| pillar codes, names, **and roles** | P4 means Power & Facility in one vertical, Partner Health in another |
| KPI catalog + default L1 weights | 38 / 38 / 43 / 10 KPIs across the four |
| default L2 pillar weights | the missing `SAAS_PILLAR_WEIGHTS` is exactly this gap |
| signal taxonomy | already correct via overlays |
| arc vocabulary + templates | `champion_loss` differs by industry |
| arc classification rules | they reference signal types |
| outcome type vocabulary | `capacity_constraint` is not a SaaS concept |
| retention model composition | consumption vs subscription |
| Power-of-1 metric set | GPU utilisation ≠ product adoption |
| playbook catalog + economics constants | `csm_rate`, `effort_multiplier` |
| health thresholds | 22% GPU utilisation may be normal for a burst tenant |

---

## 5. The `pillar_roles` registry — the fix for the P4 class of bug

Each vertical declares which pillar plays which role. `null` where it has none.

```json
// verticals/datacenter_v1/vertical.json
{
  "slug": "datacenter_v1",
  "pillars": {
    "P1": { "name": "Revenue & Unit Economics",    "role": "revenue" },
    "P2": { "name": "Fleet Utilization & Goodput", "role": "utilization" },
    "P3": { "name": "Reliability & SLA Delivery",  "role": "reliability" },
    "P4": { "name": "Power & Facility",            "role": "facility" },
    "P5": { "name": "Commercial & Expansion",      "role": "expansion" },
    "P6": { "name": "Provisioning Velocity",       "role": "velocity" }
  },
  "pillar_roles": {
    "revenue": "P1", "utilization": "P2", "reliability": "P3",
    "facility": "P4", "expansion": "P5", "velocity": "P6",
    "partner": null
  }
}
```

Consumers ask by role:

```python
partner_pillar = registry.role(customer.vertical, 'partner')
if partner_pillar is None:
    raise VerticalCapabilityError(
        f"{customer.vertical} has no partner pillar; partner portal unavailable")
```

`partner_portal` then **refuses to serve** `datacenter_v1` rather than handing a partner the facility scores. Same for any "hide the revenue pillar" rule — revenue is P1 in one vertical, P5 in another; ask for the role.

---

## 6. Compose from a library, do not inherit from a peer

You will be tempted to let `datacenter_v1` extend `dc2_s` — they are both datacenter. **Don't.** Sibling inheritance is what produced this problem.

Instead, a shared library of *definitions* that verticals reference by id:

```
library/kpis/gpu_utilization_rate.json
library/kpis/mttr_hours.json
library/playbooks/health_monitoring.json
```

```json
"P2": { "name": "Fleet Utilization & Goodput",
        "kpis": ["lib:gpu_utilization_rate", "lib:goodput_ratio",
                 "local:power_headroom"] }
```

Reuse without hierarchy. No vertical is anyone's parent.

---

## 7. Refactor sequence

**No data migration is involved.** No rows move, no customer records are touched, no schema changes, no backfill, no rollback plan. This is entirely code and config: files written, imports deleted, exception handlers removed.

1. **Extract `dc2_s`** into the standard shape. It stops being importable as a base.
2. **Author the contract** — `vertical_schema.json`. Every vertical validates against it at load.
3. **Author three config files** that don't exist yet — `datacenter_v1`, `saas_premium` (this closes the missing `SAAS_PILLAR_WEIGHTS` properly rather than routing around it), `healthcare_provider`.
4. **Delete every bypass.** `get_kpi_catalog`'s `if/else` goes; it calls the registry like everything else.
5. **Fail-closed.** Remove every `except ImportError → fall through`. A vertical that will not load raises.
6. **Add `pillar_roles`** and convert positional consumers.

Steps 1–4 are the correctness fix. Steps 5–6 are what stops recurrence.

---

## 8. Guards — the part that makes it stick

- **No cross-vertical imports.** A test that fails if any module outside `verticals/dc2_s/` imports from it. Generalised: no vertical package may import another.
- **Contract conformance.** Every registered vertical validates against `vertical_schema.json` at load and in CI.
- **Round-trip identity.** For every vertical, `get_kpi_catalog`'s pillar names match `list_verticals`' description and `total_kpis` matches `kpi_count`. This single test catches both bugs found today.
- **No silent substitution.** Any code path that returns a config whose `slug` differs from the one requested raises. This is the general form of the defect and the most valuable guard of the six.

---

## 9. On the name

`CS-Pulse_vertical-Registry` will not work as a Python module — hyphens are invalid identifiers. Options that carry the same intent:

- `cs_pulse/verticals/registry.py` — package boundary makes the hierarchy visible in the import path
- keep `utils.vertical_registry` and simply make it authoritative

The name matters less than the boundary. What fixes this is that **exactly one module resolves verticals, it validates against a contract, and it raises rather than substitutes.** A registry with a better name and a surviving bypass is the same bug.

---

## Assumption to verify first

This design takes the coding agent's characterisation of `utils.vertical_registry` — "the generic, JSON-catalog-driven loader that `get_vertical_config`, `ScoreCalculator`, and everything else correctly use" — at face value. Before building on it, confirm its actual contract: what it loads, from where, what it does on a miss, and whether it already validates. If it silently returns `None` or falls back internally, that is the first thing to fix, and it changes step 4.
