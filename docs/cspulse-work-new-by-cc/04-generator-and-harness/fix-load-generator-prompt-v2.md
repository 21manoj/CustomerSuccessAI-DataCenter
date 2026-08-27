# Load generator rewrite — build prompt v2

**Supersedes `fix-load-generator-prompt.md`.** Move v1 to `_superseded/`. The
architecture in v1 was right and survives here; what changed is *why* this is being
built and therefore what it must emit.

**Companion:** `generator-ground-truth-spec.md` — the `ground_truth.json` contract.
§1, §4 and §5 below add fields to it; treat those as amendments to the spec.

---

## What changed since v1 — read this if you know the old prompt

**1 · The purpose inverted.** v1 framed this as a discovery-validation harness (does
FCI beat PC on confounded pairs). That is now the *secondary* purpose. The primary
purpose is **calibrating and validating abstention**, because Wizard A's redesign turns
on refusing to write edges it can't support, and:

> A threshold set too strict and an abstainer that crashes produce identical empty
> graphs. There is no internal signal that distinguishes them.

Abstention is the one behaviour in the platform that **cannot be validated without
ground truth**. That makes this generator a prerequisite for Track C's abstention work,
not a parallel nice-to-have.

**2 · Absence needs a taxonomy** (§4, new). "No edge" has four distinct causes and the
product promise depends on telling them apart. The generator must produce each kind
deliberately and label it, or abstention *reasons* can't be scored — only the binary.

**3 · The generator must feed the admission ratchet** (§5, new). `edge_admission.yaml`
and its conformance tests currently rely on hand-authored golden cases. Those should be
generated, which means `ground_truth.json` must emit the exact inputs the admission
function will see.

**4 · Item 24 — revenue is unscaled to ARR** (§6, new). Tenant 391 emits $95.7M of
outcome dollars against $35.9M of ARR. This is a generator defect, and it's the reason
no invariant relating node revenue to ARR exists anywhere.

**5 · `data_origin` shipped.** v1 proposed it. It now exists in WS-2 2a's schema. The
requirement changes from "add a column" to "use the canonical value" — see §7, and note
that five non-canonical source literals have already been found in this codebase.

---

```text
# Task: rewrite the manifest load generator as a two-profile generator that emits
#       ground truth, controlled messiness, and scoreable absence

## Read first

./generator-ground-truth-spec.md  — the ground_truth.json contract and knob semantics.
Sections 1, 4 and 5 of this prompt AMEND that spec; where they differ, this prompt wins.

## Profiles

    --profile demo   current behaviour, exactly. Messiness knobs at zero, no latents,
                     no ground_truth.json. Manifests keep working.
    --profile eval   worlds with known causal structure, messiness live, ground truth
                     and run manifest emitted.

## PRECONDITION — determinism. Do this before writing any code.

Two runs of the same manifest must produce byte-identical output. Verify this on the
CURRENT generator first.

If it is not deterministic, STOP and say so. Determinism is a smaller, separate piece of
work (usually an unseeded RNG and a wall-clock timestamp) and everything below is
unbuildable without it — AT-0 is impossible, and no two runs can be compared.

## AT-0 — the safety property. Establish before changing anything.

  1. Run the current generator against 3 representative manifests. Archive the output
     CSVs as golden files.
  2. Write a test asserting --profile demo reproduces them byte-for-byte.
  3. Confirm it passes on the UNMODIFIED generator.
  4. Run it after every commit, not just at the end.

This converts "refactoring the thing that provisions all our demos" from a risky change
into a bounded one.

## THE ARCHITECTURAL CHANGE — arc_types as input

The manifest format accepts `arc_types` as an input. That is the circularity: worlds are
generated FROM arcs, so any discovery result run against the output recovers the arcs.

  demo profile   `arc_types` keeps working exactly as now. No change.
  eval profile   `arc_types` in a manifest is a HARD ERROR. Eval worlds are generated
                 from a world DAG, never from an arc name.

Do not silently ignore it in eval profile. Raise, and say why.

## §4 (NEW) — THE ABSENCE TAXONOMY

Four different worlds produce "no edge between A and B," and they demand four different
sentences to a customer:

  no_relationship          nothing to find. Correct abstention, nothing to instrument.
  unobserved_intermediate  real link; the mediating event was dropped. INSTRUMENT THIS.
  latent_common_cause      real association via a hidden variable. No instrumentation
                           will fix it; this is what FCI must mark.
  beyond_lag_window        real link at a lag the admission window excludes. Our model
                           is wrong, not their data.

The generator must produce all four deliberately, and record them:

    "absences": [
      { "pair": ["champion_change", "gpu_utilization_drop"],
        "kind": "no_relationship" },

      { "pair": ["champion_change", "engagement_gap"],
        "kind": "unobserved_intermediate",
        "hidden_event": "expansion_review_cancelled",
        "dropped_by": "per_type_observation_rate" },

      { "pair": ["exec_sponsor_change", "renewal_risk"],
        "kind": "latent_common_cause",
        "via": "L_org_restructure" },

      { "pair": ["capacity_alert", "contract_reduction"],
        "kind": "beyond_lag_window",
        "true_lag_days": 41 }
    ]

Every generated world must contain at least one of each kind. A world with only
`no_relationship` absences cannot exercise the interesting half of abstention.

This is what makes AT-4 meaningful. Checking "did it abstain" is nearly free; checking
"did it abstain FOR THE RIGHT REASON" is the test that matters, because the reason is
what becomes a customer recommendation.

## §5 (NEW) — ADMISSION INPUTS, so the ratchet's fixtures are generated

`config/edge_admission.yaml` gates edge writes on six knobs. Its conformance tests
currently use hand-authored golden cases. Emit the real thing instead — per candidate
pair, the exact values the admission function will be handed:

    "admission_inputs": {
      "3535:champion_change->engagement_gap": {
        "supporting_events": 1,
        "lag_days": 8,
        "separation_hours": 40,
        "outcome_in_window": true,
        "distinct_sources": 1,
        "edge_stability": 0.72,
        "truth": "REAL_EDGE"          // or NO_EDGE — from the world DAG
      }
    }

Two knobs need generator features that do not exist yet:

  distinct_sources   the world must model more than one source system, with events
                     appearing in one or several. Today everything has one source, so
                     min_distinct_sources can never be exercised above 1.
  edge_stability     requires bootstrap resampling over the generated events. If the
                     scorer computes it, record the value it computed.

Without these two the ratchet has knobs nothing can test.

## §6 (NEW) — REVENUE REALISM (item 24)

Tenant 391 emits $95.7M of outcome dollars against $35.9M of ARR — 2.7x. Nothing
anywhere checks this, which is why it went unnoticed.

The generator must scale outcome dollars to account ARR and record the model:

    "revenue_model": {
      "account_arr_total": 35900000,
      "outcome_dollars_total": 12400000,
      "ratio_to_arr": 0.35,
      "per_account_bound": 1.5,
      "note": "no account's outcome dollars exceed 1.5x its own ARR in the window"
    }

Pick the bound deliberately and state the reasoning — gross flows across churn,
renewal and expansion can legitimately exceed 1.0x, but not by much within one TTM
window. Whatever you choose becomes a platform invariant (AT-8) and a tracer probe.

Also: DECISION nodes must never carry `revenue_impact`. A decision has a proposal, an
outcome has realised money. If a manifest figure needs preserving, emit it as
`proposed_value`, which nothing sums.

## §7 (REVISED) — data_origin

The column now exists (WS-2 2a). Use the canonical value; do not mint a new literal.

Five non-canonical source literals have already been found in this codebase, the most
recent (`wizard_a` instead of `synthetic`) bypassing a trust gate for months. Add the
generator to `test_provenance_writers`' guard list in the same commit that writes the
value, so this isn't the sixth.

## THE INDEPENDENCE GUARD

The generator must not import, read, parse, or derive from `ARC_TEMPLATES`, and world
files must not be authored from it.

Enforce structurally:
  - a test failing if arc_edge_generator or ARC_TEMPLATES appears in the generator's
    import graph
  - a test failing if any world file contains an arc-name string lifted from it

If the generated world is "the templates plus noise," discovery recovering the templates
proves nothing. These tests are what keep the harness capable of failing.

## GENERATION ORDER — most likely thing to get wrong

Build the TRUE event sequence from the world DAG FIRST. THEN apply observation dropout
to decide what reaches the platform.

If the generator only ever creates observed events, there are no hidden events for the
`unobserved_intermediate` absences to reference, and §4 becomes decorative. The dropped
events are the whole point.

Record every drop in ground_truth.json.

## World definitions

Data files, not code. 3-5 per vertical.

    worlds/datacenter_v1/world_a.json
    worlds/datacenter_v1/world_b.json        <- contradicts ARC_TEMPLATES
    worlds/saas_premium/world_a.json

Each declares: observed vocabulary, latents, the true DAG with lag distributions,
absences per §4, and template_disagreements.

At least one world per vertical MUST contradict ARC_TEMPLATES — an asserted edge
reversed, an asserted edge absent, a real edge no template contains. That is the world
that proves the harness can fail.

## Vertical vocabularies — CHECK FIRST, IT IS FIVE MINUTES

Determine whether the existing generator emits the SAME signal types across
datacenter_v1, dc2_s, saas_premium and healthcare_provider.

If it does, report it immediately — that invalidates any cross-vertical analysis run on
existing data, independent of this refactor.

Source vocabularies from the taxonomy overlays (config/taxonomy_<vertical>.json), which
are already config-driven and correct.

## Knobs

observation_rate · per_type_observation_rate · lag_distribution · latent_count ·
vocabulary_tail · no_arc_fraction · selection_bias · account_count ·
source_system_count (new, §5) · revenue_ratio_to_arr (new, §6)

All settable per run, all recorded in run_manifest.json. Defaults in the spec.

Per-type rates matter as much as the global rate: incidents get logged (~0.9),
disengagement does not (~0.15). That asymmetry produces the long unexplained gaps this
is modelling.

## Determinism

Every run reproducible from (world_id, seed, knobs), all three in run_manifest.json.
Test it.

## Output contract

Unchanged for demo. For eval, the same CSVs plus:

    ground_truth.json    the answer key — spec + §4/§5/§6 amendments
    run_manifest.json    world_id, generator_version, seed, every knob value

Same CSV shapes process_data() already ingests. Do not write to a parallel path or a
mock schema — the point is to exercise the real pipeline.

## Acceptance tests

  AT-0  --profile demo reproduces the archived goldens byte-for-byte.
  AT-1  Discovery against a world whose DAG CONTRADICTS ARC_TEMPLATES produces a schema
        matching the world, not the templates.
        If it matches the templates, the harness is a mirror. Stop and fix.
  AT-4  Accounts in ground_truth.accounts.with_no_arc receive no arc.
  AT-4b Abstention REASONS match the absence taxonomy. For each absence, the recorded
        reason and would_admit_if correspond to its `kind`:
          unobserved_intermediate -> names missing evidence, suggests instrumentation
          latent_common_cause     -> does NOT suggest instrumentation would fix it
          beyond_lag_window       -> names the window, not the data
          no_relationship         -> abstains without proposing a fix
        A right answer for a wrong reason fails. This is the most important test here.
  AT-8  No account's outcome dollars exceed the declared per_account_bound x its ARR.
        (Fails today on tenant 391 at 2.7x — item 24.)
  AT-2  PC asserts a direct causal edge on at least one confounded_pair; FCI does not.
        (If both are right, the latents are too weak to be a test.)
  AT-3  Sweeping observation_rate 0.9 -> 0.1 degrades recovery smoothly.
        (If it doesn't, the knobs aren't wired into generation.)
  AT-5  The no-ARC_TEMPLATES-import test passes.
  AT-6  Identical (world_id, seed, knobs) -> identical output.
  AT-7  arc_types in an eval-profile manifest raises.
  AT-9  Golden cases for tests/test_admission_ratchet.py are generated from
        ground_truth.admission_inputs, and the generated set still turns the ratchet red
        when a threshold is loosened.

AT-0 protects what already works. AT-1 is why the project exists. AT-4b is what makes
abstention shippable.

## Scoring harness

Provide score_run.py taking a generated tenant plus ground_truth.json, reporting per
spec section 3, plus: abstention-reason accuracy against the absence taxonomy, and the
revenue-to-ARR ratio per account.

causal_discovery_proto.py already implements most structure-recovery scoring against a
hardcoded DAG. Adapt it to read ground_truth.json rather than rewriting it.

## Non-goals

- Do not change demo-profile behaviour. AT-0 enforces this.
- Do not write to any production tenant.
- Do not tune world parameters so results look better. If the pipeline struggles on
  realistically messy data, that is the finding.
- Do not build a second generator.
- Do not let any output of this harness reach a customer conversation, a white paper, or
  a benchmark. It validates CODE, never CLAIMS.

## Working discipline

Verify claims against the code before stating them. Where something cannot be
determined, say so rather than assuming.
```

---

## Three notes for the build

**AT-4b is the reason to do this at all.** Everything else here has some other partial
substitute — discovery can be eyeballed, determinism can be spot-checked. But scoring
whether abstention refused *for the right reason* has no substitute, and the reason is
the thing that reaches the customer as "instrument this account." A system that abstains
correctly and explains wrongly produces a confidently wrong roadmap.

**The two missing knob features (§5) are small but load-bearing.** `distinct_sources`
and `edge_stability` are in the admission config today with nothing able to exercise
them. Until the generator models multiple source systems and the scorer computes
bootstrap stability, two of six admission knobs are untested — and the ratchet protecting
them is protecting nothing.

**Re-baseline the goldens after 1f1916333.** Population 2 was deleted, templates
regenerated, NULL-source edges cleared. The generator's own output shouldn't have
changed, but archive goldens from a current run and confirm against the last known state
rather than assuming continuity.
