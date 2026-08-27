# `tracer` — build prompt for the external due-diligence app

**Companion inputs:**

| file | role |
|---|---|
| `due-diligence-checklist.md` | **the probe list** — this prompt covers the app, that file covers what it checks |
| `synthetic-worldgen-prompt.md` | build prompt for `synthetic_worldgen_v1`, the generator that emits `ground_truth.json` |
| `generator-ground-truth-spec.md` | the `ground_truth.json` schema tracer reads as its third source |

**Suggested name:** `tracer`. Short, and it names the organizing concept.

---

## Relationship to `synthetic_worldgen_v1` — optional, not a prerequisite

**Do not block tracer on worldgen.** They are independent builds with a one-way, optional data dependency.

| mode | sources available | what works | what doesn't |
|---|---|---|---|
| **Two-source** (no worldgen) | `via_api` · `via_db` | Stages 2–9. Catalog mismatch, constant-detector, row reconciliation, dashboard consistency, tracer passports | Stage 10 ground-truth scoring; `via_truth` on every probe |
| **Three-source** (with worldgen) | `via_api` · `via_db` · `via_truth` | everything | — |

**AT-4 and AT-5 — the two criteria that prove tracer finds real bugs — need only two-source mode.** Both fire against customer 390 as it exists now. Build tracer in two-source mode first, prove it catches those, then add `via_truth` when worldgen lands.

**Stage 1 (generate) behaves differently by mode:**
- worldgen configured → tracer shells out to it, records `world_id` / `seed` / knobs from `run_manifest.json`, and loads `ground_truth.json`
- not configured → tracer records the CSVs it was pointed at and marks every `via_truth` probe `SKIPPED (no ground truth)`, never `MATCH`

A probe with no ground truth must never report MATCH on the strength of api-and-db agreeing. Two wrong sources can agree — that is exactly what `get_kpi_catalog` and the CFO dashboard did. Mark it `UNSOURCED`.

---

## The two design decisions that make this worth building

**1. It must be independent of CS Pulse.** An auditor sharing code with the system it audits inherits that system's bugs. If `tracer` imports `utils.vertical_registry` to learn what pillars to expect, it will agree with whatever the platform says — including when the platform is wrong. That is exactly how `get_kpi_catalog` served dc2_s pillars for months without anyone noticing.

**2. It must lock the expectation before revealing the actual.** A human who sees the value first will rationalise it. Software can make that impossible: prompt, write the expectation with a timestamp, *then* fetch. A markdown checklist can ask for this; an app can enforce it.

Everything below follows from those two.

---

```text
# Task: build `tracer` — an external due-diligence harness for CS Pulse

## What this is

A standalone application that walks a CS Pulse tenant from CSV generation through
executive dashboards and back, recording what every value is and where it came
from. It produces an immutable run record that can be diffed against previous runs.

It is an AUDITOR. It answers "why is that number what it is," not "did it run."

## What this is NOT

- Not part of the CS Pulse codebase. Separate repo, separate venv, separate deps.
- Not a test suite. Tests assert known-correct behaviour; this discovers what the
  behaviour actually is.
- Never writes to CS Pulse's database. Read-only, always, enforced at the
  connection level (read-only user or a connection flag — not by convention).

## HARD CONSTRAINT — independence

`tracer` must NOT import any CS Pulse module. No `from utils...`, no
`from verticals...`, no shared config loader.

Enforce structurally: a test that fails if any CS Pulse package appears in
tracer's import graph.

Everything tracer knows about what SHOULD be true comes from:
  - its own config, authored independently
  - ground_truth.json emitted by synthetic_worldgen_v1
  - CS Pulse's own PUBLIC surface (API/MCP), treated as a black box

If tracer and CS Pulse share a source of truth, tracer cannot detect when that
source is wrong. That is the entire point.

## The three-source model — the core mechanic

For every observable, tracer collects up to three independent views:

  via_api    what the MCP tool / REST endpoint returns
  via_db     what a direct read-only SQL query returns
  via_truth  what ground_truth.json says (where applicable)

A check passes only when all AVAILABLE sources agree. Disagreement is
automatically logged as a finding — no human judgment required.

This alone would have caught the headline bug: get_kpi_catalog (via_api) returns
5 dc2_s pillars while customer_config (via_db) holds 6 datacenter_v1 weights.
Neither view is suspicious alone. The disagreement is the finding.

Where only one source exists, record which — a single-sourced value is weaker
evidence and the report must say so.

## Expectation locking — the enforced discipline

For every probe:

  1. tracer states the question and shows CONTEXT ONLY (what was uploaded, what
     stage just ran) — never the value being checked
  2. it prompts for the expected value
  3. it writes {expected, locked_at} to the ledger
  4. ONLY THEN does it fetch the actual
  5. it records {actual, fetched_at, sources, verdict}

Schema constraint: locked_at < fetched_at. A row violating it is invalid.

For automatic probes with a deterministic expectation (row counts must reconcile,
sums must equal 1.0), tracer writes its own expectation from config and skips the
prompt. Reserve the prompt for probes where the expectation is a genuine
prediction.

## Probe types — automate everything mechanizable

  AUTO       runs unattended, self-verifying
             row-count reconciliation · weight sums · ratio detection ·
             three-source agreement · null checks · duplicate triples ·
             hand-recomputation of a pillar score
  JUDGMENT   pauses and asks a human
             does this edge label describe the nodes it connects? ·
             provenance verdict on a dashboard field ·
             is this movement proportional to what I did?

Most of the checklist is AUTO. If a full run needs more than ~15 human
judgments, nobody will run it twice — and the second run is where the value is.

Report the AUTO/JUDGMENT split at the end of each run.

## Tracer records

Config registers tracers by kind:

    account · signal · kpi_reading · outcome · edge

At every stage, tracer resolves each one automatically and records where it
now lives: which table, which row, which node_id, which edges reference it,
what its provenance fields say.

Output per stage: a "tracer passport" — one row per tracer showing its identity
in each layer and what changed since the previous stage. This is what makes it a
trace rather than a series of spot checks.

## Data model (SQLite, append-only)

    run            id, started_at, git_rev, db_url, vertical, customer_id,
                   world_id, seed, fixes_present[]
    tracer         run_id, kind, identifier, label
    observation    run_id, stage, probe_id, expected, locked_at,
                   actual, fetched_at, sources{api,db,truth}, verdict, notes
    finding        run_id, probe_id, severity, title, detail, auto_detected
    passport       run_id, stage, tracer_id, layer, row_ref, provenance_json

Append-only. Never update a row — a correction is a new observation referencing
the old one. The ledger is evidence; evidence does not get edited.

## Verdicts

    MATCH        expected == actual
    MISMATCH     differs — always a finding
    UNKNOWN      could not determine the value's basis — ALWAYS a finding
    UNSOURCED    only one of three sources available
    SKIPPED      probe not applicable to this vertical/stage (state why)

UNKNOWN is not a pass. It means the system cannot explain itself.

## Stages

Implement the stages in due-diligence-checklist.md: environment → generate →
create tenant → upload → process_data (8 sub-stages) → dashboards → partner
portal → intervention → hot load → recheck → ground-truth scoring.

Each stage is a module exporting a probe list. Adding a probe must not require
touching the runner.

Honour the checklist's STOP CONDITIONS: halt the run, write the finding, exit
non-zero. Do not continue past a catalog mismatch — everything downstream is
invalid and continuing produces findings that are artefacts of the first one.

## Run diffing — the second-most-important feature

    tracer diff <run_a> <run_b>

Reports, per probe: verdict changed · actual value changed · new findings ·
findings that disappeared.

This is how you prove a fix did something. Run once before the three fixes land,
once after; the diff is the evidence. Without it you are asserting improvement.

## Report

Generate a self-contained HTML file per run:
  - header: run metadata, fixes present, AUTO/JUDGMENT split
  - findings first, severity-ordered
  - tracer passports — one section per tracer, its journey across stages
  - full observation ledger, filterable by verdict
  - the surprise log (see below)

Self-contained: no CDN, no external assets. It gets emailed and archived.

## Surprise log

At the end of each stage, one free-text prompt: "anything you did not predict?"

Verbatim capture, no structure imposed. This is the highest-value output of the
whole exercise — every finding in the prior audit began as something that would
have gone here.

## Config

    tracer.yaml
      cs_pulse:
        api: {base_url, auth}
        db:  {dsn, read_only: true}     # read-only enforced at connection
      ground_truth: path
      tracers: [{kind, identifier, label}, ...]
      expectations:                      # for AUTO probes with fixed expectations
        pillar_weights_sum: 1.0
        max_distinct_nrr_values: 1
        max_distinct_roi_values: 1

## Acceptance criteria

  AT-1  Import-independence test passes: no CS Pulse module in the import graph.
  AT-2  Any attempted write to the CS Pulse DB fails at the connection layer,
        not by convention.
  AT-3  An observation with locked_at >= fetched_at is rejected by the schema.
  AT-4  Given a tenant where the API reports one pillar set and the DB holds
        another, tracer flags it automatically with no human input.
        (Reproducible against customer 390 today.)
  AT-5  The constant-detector probe flags a per-account metric that is a fixed
        multiple of ARR. (Should fire on roi_pct: 427 today.)
  AT-6  `tracer diff` on two runs of the same build reports zero changes.
  AT-7  A full run on a 12-account tenant completes in under 10 minutes of
        wall-clock, excluding human judgment time.

AT-4 and AT-5 are the ones that matter — they prove tracer finds real bugs that
exist right now, not just that it runs.

## Non-goals

- Do not fix anything found. Report only.
- Do not modify CS Pulse in any way.
- Do not build a live dashboard. Discrete runs, diffable.
- Do not tune probes so runs come out clean. A noisy run is a working auditor.

## Working discipline

Verify claims against the data before stating them. Show the query behind every
number. Where something cannot be determined, record UNKNOWN — do not estimate.
```

---

## Notes for the build

**Start with three probes, not a hundred.** Implement the runner, the ledger and the expectation lock, then exactly three probes: the catalog three-source check (AT-4), the constant-detector (AT-5), and row-count reconciliation. Both AT-4 and AT-5 should fire against customer 390 today. If they don't, the harness is wrong and no number of additional probes will fix that.

**The read-only enforcement should be a database user**, not an application flag. An app that promises not to write is one bug away from writing.

**Resist the live dashboard.** The value is in discrete, immutable, diffable runs. A live view invites glancing at it instead of walking it, and glancing is what this exists to replace.
