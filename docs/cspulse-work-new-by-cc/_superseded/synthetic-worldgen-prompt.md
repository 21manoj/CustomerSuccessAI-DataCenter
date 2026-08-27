# `synthetic_worldgen_v1` — build prompt

**Reference:** `generator-ground-truth-spec.md` (the design spec this implements).

**Why the name matters:** this tool's name lands in `customer.data_origin`. `real_world_load_gen` would assert something false in exactly the place people look for provenance. `synthetic_worldgen_v1` reads correctly wherever it appears.

**Dependency:** none. Can proceed in parallel with WS-1 and WS-2. The FCI spike depends on *this*, not the other way round.

---

```text
# Task: build synthetic_worldgen_v1 — a ground-truth-emitting data generator
#       that doubles as the pipeline's eval harness

## Read first

./generator-ground-truth-spec.md contains the design. Read it fully before writing
code. This prompt covers construction and the acceptance tests; the spec covers
the ground_truth.json schema and the knob semantics.

## What this is

The existing manifest generator produces demo data. It takes `arc_types` as an
INPUT, which means any causal-discovery result run against its output recovers the
manifests — circular, and it looks like a successful validation.

synthetic_worldgen_v1 generates worlds with a KNOWN, INDEPENDENT causal structure,
emits the answer key alongside the data, and lets the whole provenance / abstention /
discovery pipeline be scored instead of argued about.

It validates CODE. It never validates CLAIMS. No output of this tool is evidence
about real customer success dynamics.

## THE CONSTRAINT THAT MATTERS MOST

The generator must not import, read, parse, or derive from ARC_TEMPLATES.

Enforce it structurally, not by discipline:
  - a test that fails if `arc_edge_generator` or ARC_TEMPLATES appears anywhere in
    the generator's import graph
  - a test that fails if any world definition file contains an arc name string
    lifted from ARC_TEMPLATES

If the generated world is "the templates plus noise", discovery recovering the
templates proves nothing. This test is what keeps the harness capable of failing.

## Architecture

ONE generator, TWO profiles. Do not build two tools — they drift within a quarter.

  --profile demo   all messiness knobs at zero, no latents, clean arcs.
                   Produces what the current manifest generator produces.
  --profile eval   knobs live, latents generated, ground_truth.json emitted.

Demo is the special case of eval with clean settings.

## Output contract

Write into the EXACT CSV shapes process_data() already ingests, so the real
pipeline runs unchanged:
    accounts.csv
    kpi_measurements.csv
    enhanced_qualitative_signals.csv
    outcomes.csv
    (optionally signal_edges.csv for hot-load testing)

Plus, eval profile only:
    ground_truth.json      # schema in the spec — the answer key
    run_manifest.json      # world_id, generator_version, seed, every knob value

Do NOT write into a parallel path or a mock schema. If the generator does not feed
the real ingestion, you are testing a mock.

## Worlds

Ship 3-5 world definitions per vertical, as data files, not code.

At least one world per vertical MUST contradict ARC_TEMPLATES — containing:
  - an edge the templates assert, reversed
  - an edge the templates assert, absent entirely
  - a real edge no template contains

Record these in ground_truth.json under `template_disagreements`. This is the world
that proves the harness can fail.

Worlds are versioned independently of the generator. A result must be attributable
to (world_id, generator_version, seed).

## Vertical correctness

Each vertical gets its own signal vocabulary. datacenter_v1, dc2_s, saas_premium,
and healthcare_provider must NOT share a signal-type list.

First, check whether the EXISTING generator shares vocabularies across verticals.
If it does, report it — it would invalidate any cross-vertical analysis run on
existing data.

## Determinism

Every run reproducible from (world_id, seed, knobs). All three recorded in
run_manifest.json. Two runs with identical inputs must produce byte-identical CSVs.
Add a test for this.

## Knobs (defaults in the spec)

observation_rate, per_type_observation_rate, lag_distribution, latent_count,
vocabulary_tail, no_arc_fraction, selection_bias, account_count.

Generation order matters: build the TRUE event sequence first from the world's DAG,
THEN apply observation dropout. The dropped events are what hypothesised nodes are
supposed to recover — if you generate only what's observed, the harness cannot test
that at all.

## ACCEPTANCE TESTS — the harness must prove it can fail

Implement these as runnable tests, not as documentation. If any fails, the harness
is not trustworthy and nothing should be built on top of it.

  AT-1  Discovery run against a world whose DAG CONTRADICTS ARC_TEMPLATES produces
        a schema matching the world, not the templates.
        (If it matches the templates, the harness is a mirror. Stop and fix.)

  AT-2  PC asserts a direct causal edge on at least one pair listed in
        `confounded_pairs`, and FCI does not.
        (If both are correct, the latent effects are too weak to be a test.)

  AT-3  Sweeping observation_rate from 0.9 down to 0.1 degrades structure recovery
        smoothly and measurably.
        (If it doesn't, the messiness knobs are not wired into generation.)

  AT-4  Accounts listed in `accounts.with_no_arc` receive no arc assignment from
        Wizard A.
        (If they all get one, abstention is not implemented — that is a finding
        about the pipeline, report it rather than changing the test.)

  AT-5  The no-ARC_TEMPLATES-import test passes.

  AT-6  Two runs with identical (world_id, seed, knobs) produce identical output.

AT-1 is the important one. Report its result prominently in whatever summary the
tool produces.

## Scoring harness

Provide `score_run.py` that takes a generated tenant plus ground_truth.json and
reports, per the spec section 3:
  - structure recovery (adjacency P/R/F1, orientation correct/wrong/abstained)
  - confounded-pair handling (PC vs FCI)
  - provenance discipline (every edge tiered; no confidence on inferred tier)
  - abstention (no-arc accounts, hypothesis insertion on long gaps)
  - coverage estimation vs true observation_rate
  - template classification vs template_disagreements

causal_discovery_proto.py already implements most of the structure-recovery scoring
against a hardcoded DAG. Adapt it to read ground_truth.json rather than rewriting.

## Non-goals

- Do not modify the existing manifest generator. Build alongside it.
- Do not write to any production tenant.
- Do not tune world parameters so results look better. If the pipeline struggles on
  realistically messy data, that is the finding.

## Working discipline

Verify claims against the code before stating them. Where something cannot be
determined, say so rather than assuming.
```

---

## Two notes on the build

**Generation order is the easy thing to get wrong.** Build the true event sequence from the world's DAG *first*, then drop events to hit `observation_rate`. If the generator only ever creates observed events, there are no hidden events for hypothesised nodes to recover, and AT-3 and AT-4 become meaningless.

**AT-1 is the whole point.** Everything else is hygiene. A harness whose world was authored by the thing under test cannot fail, and a test that cannot fail is not a test.
