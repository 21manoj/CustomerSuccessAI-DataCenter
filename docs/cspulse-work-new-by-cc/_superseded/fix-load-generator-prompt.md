# Fix the existing load generator in place — build prompt

**Supersedes** the "build alongside" instruction in `synthetic-worldgen-prompt.md`. That document's *architecture* section was right (one generator, two profiles); its *non-goals* section contradicted it by saying to build a second tool. This prompt resolves that in favour of refactoring what exists.

**Reference:** `generator-ground-truth-spec.md` — the `ground_truth.json` schema and knob semantics. Unchanged; still the design input.

---

## Why in place rather than alongside

The existing manifest generator already emits the correct CSV shapes and is wired into provisioning. Two generators means two code paths producing tenant data, drifting apart, with nobody sure which produced a given tenant. One generator with two profiles is the same amount of capability and half the surface.

The demo profile must come out of this refactor **behaviourally identical**. That is the safety property, and it is testable.

---

```text
# Task: refactor the manifest load generator into a two-profile generator that
#       emits ground truth and controlled messiness

## Read first

./generator-ground-truth-spec.md — the ground_truth.json schema and the knob
semantics. This prompt covers the refactor; that file covers the contract.

## What changes

The generator gains an eval profile. It keeps doing everything it does today
under a demo profile, unchanged.

    --profile demo   current behaviour, exactly. Messiness knobs at zero, no
                     latents, no ground_truth.json. Manifests keep working.
    --profile eval   worlds with known causal structure, messiness knobs live,
                     ground_truth.json + run_manifest.json emitted.

## THE SAFETY PROPERTY — establish this before changing anything

Before touching generator code:

  1. Run the current generator against 3 representative manifests. Archive the
     output CSVs as golden files.
  2. Write a test asserting --profile demo reproduces those files byte-for-byte.
  3. Confirm the test passes on the UNMODIFIED generator.

That test is the seatbelt for every subsequent step. If demo output drifts, the
refactor broke something, and you will know which commit.

Note: this requires the generator to be deterministic today. If it is not —
if two runs of the same manifest differ — say so and STOP. Determinism has to
come first, and that is a different (smaller) piece of work.

## THE ARCHITECTURAL CHANGE — arc_types as input

The manifest format currently accepts `arc_types` as an input. That is the
circularity: worlds are generated FROM arcs, so any causal-discovery result run
against the output recovers the arcs. Fixing this is the point of the exercise.

Resolution — different rules per profile:

  demo profile   `arc_types` keeps working exactly as now. Demos want clean,
                 legible arcs. No change.
  eval profile   `arc_types` in a manifest is a HARD ERROR. Eval worlds are
                 generated from a world DAG (see below), never from an arc name.

Do not silently ignore arc_types in eval profile. Raise, and say why.

## World definitions — eval profile input

Worlds are data files, not code. 3-5 per vertical.

    worlds/datacenter_v1/world_a.json
    worlds/datacenter_v1/world_b.json        <- contradicts ARC_TEMPLATES
    worlds/saas_premium/world_a.json

Each declares: observed signal vocabulary, latent variables, the true DAG with
lag distributions, and template_disagreements. Schema in the spec.

At least one world per vertical MUST contradict ARC_TEMPLATES — an asserted edge
reversed, an asserted edge absent, a real edge no template contains. That is the
world that proves the harness can fail.

## THE INDEPENDENCE GUARD

The generator must not import, read, parse, or derive from ARC_TEMPLATES, and
world definition files must not be authored from it.

Enforce structurally:
  - a test that fails if arc_edge_generator or ARC_TEMPLATES appears anywhere in
    the generator's import graph
  - a test that fails if any world file contains an arc-name string lifted from
    ARC_TEMPLATES

If the generated world is "the templates plus noise," discovery recovering the
templates proves nothing. These tests are what keep the harness capable of
failing.

## Generation order — the thing most likely to be got wrong

Build the TRUE event sequence from the world's DAG FIRST. THEN apply observation
dropout to decide what reaches the platform.

If the generator only ever creates observed events, there are no hidden events
for hypothesised nodes to recover, and the acceptance tests for abstention and
coverage become vacuous. The dropped events are the whole point.

Record what was dropped in ground_truth.json.

## Knobs (defaults in the spec)

observation_rate · per_type_observation_rate · lag_distribution · latent_count ·
vocabulary_tail · no_arc_fraction · selection_bias · account_count

All settable per run, all recorded in run_manifest.json.

Per-type observation rates matter as much as the global rate: incidents get
logged (~0.9), disengagement does not (~0.15). That asymmetry is what produces
long unexplained gaps, which is the phenomenon being modelled.

## Vertical vocabularies — CHECK THIS FIRST, IT IS FIVE MINUTES

Determine whether the existing generator emits the SAME signal types across
datacenter_v1, dc2_s, saas_premium and healthcare_provider.

If it does, report it immediately — that would invalidate any cross-vertical
analysis run on existing data, and it is a finding independent of this refactor.

Each vertical needs its own vocabulary in eval profile. Source it from the
taxonomy overlays (config/taxonomy_<vertical>.json), which are already
config-driven and correct.

## Determinism

Every run reproducible from (world_id, seed, knobs), all three in
run_manifest.json. Two runs with identical inputs produce identical output.
Test it.

## Provenance tagging

Every tenant the generator creates records data_origin = "synthetic_worldgen"
(or the demo equivalent). Today there is no way to distinguish a generated
tenant from a real one in the database, which means no analysis can exclude
synthetic data. One column, and it gates a lot.

## Output contract

Unchanged for demo. For eval, the same CSVs plus:

    ground_truth.json    the answer key — schema in the spec
    run_manifest.json    world_id, generator_version, seed, every knob value

Same CSV shapes process_data() already ingests. Do not write to a parallel path
or a mock schema — the point is to exercise the real pipeline.

## Acceptance tests

  AT-0  --profile demo reproduces the archived golden files byte-for-byte.
        (Run this after every commit, not just at the end.)
  AT-1  Discovery against a world whose DAG CONTRADICTS ARC_TEMPLATES produces a
        schema matching the world, not the templates.
        If it matches the templates, the harness is a mirror. Stop and fix.
  AT-2  PC asserts a direct causal edge on at least one confounded_pair; FCI does
        not. (If both are right, the latents are too weak to be a test.)
  AT-3  Sweeping observation_rate 0.9 → 0.1 degrades structure recovery smoothly.
        (If it doesn't, the knobs are not wired into generation.)
  AT-4  Accounts in ground_truth.accounts.with_no_arc receive no arc from
        Wizard A. (If they all get one, abstention is not implemented — that is a
        finding about the pipeline. Report it; do not change the test.)
  AT-5  The no-ARC_TEMPLATES-import test passes.
  AT-6  Identical (world_id, seed, knobs) → identical output.
  AT-7  arc_types in an eval-profile manifest raises.

AT-0 protects what already works. AT-1 is the reason the project exists.

## Scoring harness

Provide score_run.py taking a generated tenant plus ground_truth.json, reporting
per spec section 3: structure recovery, confounded-pair handling, provenance
discipline, abstention, coverage estimate vs true rate, template classification.

causal_discovery_proto.py already implements most of the structure-recovery
scoring against a hardcoded DAG. Adapt it to read ground_truth.json rather than
rewriting it.

## Non-goals

- Do not change demo-profile behaviour. AT-0 enforces this.
- Do not write to any production tenant.
- Do not tune world parameters so results look better. If the pipeline struggles
  on realistically messy data, that is the finding.
- Do not build a second generator.

## Working discipline

Verify claims against the code before stating them. Where something cannot be
determined, say so rather than assuming.
```

---

## Two notes for the build

**AT-0 is the whole safety story.** Archive golden files from the *unmodified* generator and run that test after every commit. It converts "refactoring the thing that provisions all our demos" from a risky change into a bounded one.

**If the current generator isn't deterministic, stop and fix that first.** AT-0 is impossible without it, and so is any meaningful comparison between runs. It is also probably a smaller job than it sounds — usually an unseeded RNG and a timestamp.
