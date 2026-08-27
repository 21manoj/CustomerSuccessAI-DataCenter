# Load generator: ground-truth emission and controlled messiness

**Purpose.** Turn the manifest generator from a demo-data producer into a **pipeline test harness** — a world where the true causal structure is known, so the discovery and provenance pipeline can be scored rather than argued about.

**Explicit non-purpose.** This validates *code*, never *claims*. No result from this harness is evidence that escalation precedes churn in the real world. Nothing produced here belongs in a customer conversation, a white paper, or a benchmark. It answers "does our pipeline work," not "what is true."

---

## 0. The discipline that decides whether this is worth building

**The generator's ground-truth DAG must not be authored by whoever wrote `ARC_TEMPLATES`, and must not be derived from it.**

If the generator's world is "the templates, plus noise," then discovery recovering the templates proves nothing — you've built a mirror with extra steps, and it will produce a confident, meaningless validation.

Three ways to break the circularity, in order of strength:

1. **Generate several worlds, not one.** Ship 3–5 ground-truth DAGs per vertical. At least one should deliberately contradict the templates — reversed edges, edges the templates assert that don't exist, real edges the templates miss. If the pipeline only recovers structure in the world that happens to match your templates, that is itself the finding.
2. **Source the DAG independently** — published CS churn research, or interviews with CSMs who did not write the templates.
3. **Have someone other than the template author write it**, blind to the template file.

A harness whose world was written by the thing under test cannot fail. Build it so it can.

---

## 1. `ground_truth.json` — the contract

Emitted alongside the CSVs, one per generated tenant. This is the answer key; the pipeline must never read it.

```json
{
  "schema_version": "1.0",
  "tenant": { "customer_id": 9001, "vertical": "datacenter_v1", "world_id": "dc_world_b" },

  "signal_vocabulary": {
    "observed": ["critical_incident", "support_escalation", "reserved_cluster_idle", "..."],
    "latent":   ["L_org_restructure", "L_business_decline"]
  },

  "true_dag": [
    { "from": "L_org_restructure", "to": "champion_change",
      "lag_days": { "median": 14, "iqr": [7, 30] }, "strength": 0.72 },
    { "from": "champion_change", "to": "engagement_gap",
      "lag_days": { "median": 47, "iqr": [21, 89] }, "strength": 0.61 }
  ],

  "confounded_pairs": [
    { "a": "champion_change", "b": "exec_sponsor_change", "via": "L_org_restructure" }
  ],

  "observation": {
    "rate": 0.35,
    "per_type_rate": { "critical_incident": 0.90, "engagement_gap": 0.15 },
    "note": "fraction of TRUE events that reach the platform"
  },

  "selection_bias": {
    "mechanism": "churned accounts stop emitting",
    "post_churn_drop_rate": 0.40
  },

  "accounts": {
    "total": 400,
    "with_no_arc": [9001042, 9001077],
    "arc_assignment": { "9001001": "champion_loss", "9001002": null }
  },

  "template_disagreements": [
    { "template_edge": ["support_escalation", "reserved_cluster_idle"],
      "reality": "no_direct_edge",
      "note": "templates assert this; this world does not contain it" }
  ]
}
```

**Key fields and why they exist:**

| field | what it lets you score |
|---|---|
| `true_dag` with `lag_days.iqr` | whether learned lags match reality — and whether a scalar `lag_days` can represent a real distribution at all |
| `latent` + `confounded_pairs` | whether FCI marks confounding where it exists and PC fails to. Without latents, FCI has nothing to prove |
| `observation.rate` | whether the system's coverage estimate is accurate; whether hypothesised nodes land in the real gaps |
| `accounts.with_no_arc` | whether the abstention path fires. If every account fits an arc, abstention is never exercised |
| `template_disagreements` | pre-computed answer key for the template-vs-reality comparison |

---

## 2. Generator knobs

All must be settable per run and recorded in `ground_truth.json`.

| knob | why | realistic default |
|---|---|---|
| `observation_rate` | Not every event reaches the platform — the core objection to sequence-only edges | 0.30–0.40 |
| `per_type_observation_rate` | Capture is uneven. Incidents are logged; disengagement is not | incidents 0.9, soft signals 0.15 |
| `lag_distribution` | Real gaps at Titan were 7, 97, 16, 10, 10 days. A fixed 30-day lag builds a world where the templates are right | lognormal, wide IQR |
| `latent_count` | Gives FCI something to find | 2–3 per vertical |
| `vocabulary_tail` | Customer 390 has 54% of types in exactly one account. An even 15-type vocabulary makes the feasibility gate pass on synthetic and fail on real | Zipf-like |
| `no_arc_fraction` | Tests abstention | 0.10–0.20 |
| `selection_bias` | Churned accounts truncate | on |
| `account_count` | Lets you sweep the "how much data do I need" question | 100 / 250 / 500 / 1000 |

**Vertical-correct vocabularies are mandatory.** If the generator emits the same signal types across `datacenter_v1`, `saas_premium`, and `healthcare_provider`, any cross-vertical analysis will find spurious universal structure that is really just the generator's shared word list. Check this before anything else — it is a five-minute look and it invalidates Phase 5 of the discovery spike if wrong.

---

## 3. What the eval scores

Run the full pipeline against a generated tenant, then score:

**Structure recovery**
- adjacency precision / recall / F1 vs `true_dag`
- orientation: correct / wrong / abstained
- confounded pairs: did FCI mark them? did PC wrongly assert a direct cause?

**Provenance discipline**
- every edge carries a non-null `evidence_tier`
- zero edges with a non-null `confidence` on an inferred tier
- Evidence Density and Derivation Completeness computed and non-null

**Abstention**
- accounts in `with_no_arc`: did the system decline to assign an arc, or force one?
- gaps exceeding the hypothesis threshold: was a hypothesised node inserted?

**Coverage estimation**
- system's estimated observation coverage vs the true `observation.rate`

**Template comparison**
- classification of every `ARC_TEMPLATES` edge as SUPPORTED / UNSUPPORTED / REVERSED / CONFOUNDED / UNTESTABLE, scored against `template_disagreements`

---

## 4. What this unlocks — design decisions made empirically

Every parameter argued about in design review becomes a sweep with an answer:

| question | sweep |
|---|---|
| At what gap length should a hypothesised node be inserted instead of a direct edge? | vary the threshold, score against `true_dag` — find where precision peaks |
| What bootstrap stability threshold separates real edges from spurious? | vary it, plot precision/recall |
| How many accounts before discovery is worth running? | sweep `account_count` at 100/250/500/1000 |
| At what observation rate does the pipeline break? | sweep `observation_rate` from 0.9 down to 0.1 |
| How coarse must signal-type aggregation be? | sweep `vocabulary_tail` |

That last group is the real payoff. Right now those are opinions. With this harness they are measurements, and they can be re-measured whenever the pipeline changes.

---

## 5. Acceptance criteria for the harness itself

The harness is working when:

1. Running discovery on a world whose DAG **contradicts** `ARC_TEMPLATES` produces a schema that matches the world, not the templates. *(If it matches the templates, the harness is a mirror — stop and fix it.)*
2. PC asserts a direct causal edge on at least one `confounded_pair`, and FCI does not. *(If both are right, the latents are too weak to be a test.)*
3. Sweeping `observation_rate` downward degrades recovery smoothly and visibly. *(If it doesn't, the messiness knobs aren't connected.)*
4. Accounts in `with_no_arc` receive no arc. *(If they all get one, abstention isn't implemented.)*

Criterion 1 is the important one. It is the check that this harness can fail.

---

## 6. What it still cannot do

- It cannot tell you the real causal structure of customer success.
- It cannot produce a schema to ship to a customer.
- It cannot validate Wizard D's NRR predictions — those need realised outcomes from real accounts.
- It cannot substitute for a real production tenant with 200+ accounts, which the learned-schema project ultimately depends on.

What it *can* do is let the entire provenance, abstention, and discovery redesign be built, tuned, and regression-tested now — so that the day real data arrives at scale, the pipeline is already correct and the only new thing is the answer.
