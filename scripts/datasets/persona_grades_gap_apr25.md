# Persona Grading — Gap Analysis (Apr 25 2026)

*Target: every persona at A (4.0). Current: a mix of C+ → B+. This document quantifies the gap rigorously: per persona, per question, by driver category. Companion to `persona_grades_recovery_plan_apr25.md`.*

## Top-line gap

| Persona | Current | Target | Gap (numeric) | Gap (letters) |
|---|---|---|---|---|
| CRO   | **C+ (2.49)** | A (4.0) | **1.51** | -4 (C+ → B → B+ → A- → A) |
| CFO   | **B  (2.98)** | A (4.0) | **1.02** | -3 (B → B+ → A- → A) |
| CEO   | **B+ (3.32)** | A (4.0) | **0.68** | -2 (B+ → A- → A) |
| VP CS | **B- (2.54)** | A (4.0) | **1.46** | -4 (B- → B → B+ → A- → A) |
| CSM   | **B  (2.93)** | A (4.0) | **1.07** | -3 (B → B+ → A- → A) |

Total gap-points to close across all 29 questions, weighted: **39.4 grade-points** (sum of `(4.0 - q.numeric) × q.weight` over all questions).

## What "A grade" actually means (high bar disclosure)

Per the grader system prompt:

> *"Reserve A for responses that would make you confident handing them to your board / your CSM team / your CFO. A 15-yr veteran in your role would not give an A to a response that's merely 'fine'."*

This is intentionally strict. "A" means a 15-yr veteran would deploy the answer **as-is**. "A-" means "very good — minor polish needed." Most current responses sit between "missing 1 medium item" (B) and "multiple gaps" (C+) — both perfectly defensible product states, just below the A bar.

**Implication:** reaching A on every question requires the AI to consistently produce expert-deployable output. That's not the same as "no bugs" — it requires polish, completeness, correct framing, AND honest data sourcing on every single answer.

## Gap decomposition per persona

### CRO — gap 1.51 (largest tied with VP CS)

| Q | Current | Target | Gap | Primary driver |
|---|---|---|---|---|
| q01-revenue-at-risk | C+ (2.3) | A (4.0) | **1.7** | Process failure: gave $ amounts without calling `get_revenue_at_risk`. CRO won't trust unsourced numbers. |
| q02-worst-accounts-why | A- (3.7) | A (4.0) | 0.3 | Polish: already strong; minor sharpening of framing. |
| q03-expansion-upside | **F (0.0)** | A (4.0) | **4.0** | Generation aborted/empty. Single biggest leverage point. |
| q04-causal-chain | A- (3.7) | A (4.0) | 0.3 | Polish: solid causal traversal; tighter narrative. |
| q05-nrr-trajectory | B- (2.7) | A (4.0) | 1.3 | Assumed 105% target without asking; CRO would deduct. |
| q06-playbook-roi | C+ (2.3) | A (4.0) | 1.7 | Tool returned sparse data; AI didn't deliver the comparative ranking. |

**Driver categories for CRO gap:**
- **Process failures** (didn't call required tools): q01, q06 → 2 questions
- **Catastrophic failures** (truncation/abort): q03 → 1 question, ~0.5 grade-pts of persona avg alone
- **Missing-context handling** (assumed instead of asked): q05 → 1 question
- **Polish on otherwise-strong answers**: q02, q04 → 2 questions

The F on q03 is the single most impactful issue: closing it from F to A- would lift the persona average from 2.49 to ~3.1 (B). All other CRO improvements stack on top.

### CFO — gap 1.02 (mostly polish, no F's)

| Q | Current | Target | Gap | Primary driver |
|---|---|---|---|---|
| q01-portfolio-roi | B- (2.7) | A (4.0) | 1.3 | "Critical issues for CFO review" — likely missing benchmark or transparency. |
| q02-cost-per-saved | C+ (2.3) | A (4.0) | 1.7 | Misinterpreted question (gave totals, not per-save). Question-comprehension gap. |
| q03-actual-vs-projected | B+ (3.3) | A (4.0) | 0.7 | Missing explicit variance % calculation. |
| q04-payback-period | B+ (3.3) | A (4.0) | 0.7 | Solid output; missing supporting context. |
| q05-power-of-1 | A- (3.7) | A (4.0) | 0.3 | Already best CFO answer (dedicated tool). Minor polish. |
| q06-benchmark-comparison | B- (2.7) | A (4.0) | 1.3 | Used too-narrow industry benchmark range. |

**Driver categories for CFO gap:**
- **Question-comprehension misalignment**: q02 → 1 question
- **Missing precision** (no variance %, narrow benchmarks): q01, q03, q06 → 3 questions
- **Polish on already-good answers**: q04, q05 → 2 questions

CFO is the most stable persona (no F's, no C-'s). The gap to A is mostly precision and clarification habits, not big rewrites. Likely the easiest to close.

### CEO — gap 0.68 (smallest, single weakness)

| Q | Current | Target | Gap | Primary driver |
|---|---|---|---|---|
| q01-30-second-summary | C+ (2.3) | A (4.0) | **1.7** | Verbosity: "far too long" — failed core requirement. |
| q02-strategic-risk | A- (3.7) | A (4.0) | 0.3 | Polish: strong concentration-risk synthesis. |
| q03-cascade-exposure | A- (3.7) | A (4.0) | 0.3 | Polish: strong cascade thinking. |
| q04-board-headline | A- (3.7) | A (4.0) | 0.3 | Polish: headline + 3 bullets + risk flag. |
| q05-vs-market | A- (3.7) | A (4.0) | 0.3 | Polish: honest both-ways framing. |

**Driver categories for CEO gap:**
- **Length budget violation**: q01 → 1 question (the only major issue)
- **Polish on already-A- answers**: q02-q05 → 4 questions

CEO has the tightest grade band (4 of 5 questions at A-, only 1 weakness). Closing the verbosity gap on q01 is a single prompt rule.

### VP CS — gap 1.46 (worst-performing on operational details)

| Q | Current | Target | Gap | Primary driver |
|---|---|---|---|---|
| q01-csms-need-help | C+ (2.3) | A (4.0) | 1.7 | "Completely failed to identify specific CSM names." Cross-CSM aggregation gap. |
| q02-playbook-effectiveness | A- (3.7) | A (4.0) | 0.3 | Polish: best VP CS answer. |
| q03-daily-action-queue | C  (2.0) | A (4.0) | **2.0** | Empty queue identified but no VP-level operational view delivered. |
| q04-uncovered-risk | C+ (2.3) | A (4.0) | 1.7 | Names + health but missing duration-since-last-touch. |
| q05-team-capacity | C- (1.7) | A (4.0) | **2.3** | **No tools called.** Process failure. |
| q06-early-predictors | B+ (3.3) | A (4.0) | 0.7 | Solid signal-types analysis; missing false-positive context. |

**Driver categories for VP CS gap:**
- **Cross-CSM aggregation gap** (existing tools don't surface per-CSM workload): q01, q03 → 2 questions
- **Missing data dimensions** (last-touch, capacity metrics): q04, q05 → 2 questions
- **Process failures** (no tools called): q05 → 1 question
- **Polish on strong answers**: q02, q06 → 2 questions

VP CS is structurally hardest. The aggregation gaps suggest **a missing tool** — an explicit `get_csm_team_workload` or similar that aggregates workload + outcomes per CSM. Without that tool, lifting q01/q03/q05 to A may require new product capability, not just prompts.

### CSM — gap 1.07 (held back by 2 specific tool dependencies)

| Q | Current | Target | Gap | Primary driver |
|---|---|---|---|---|
| q01-today-priority | A- (3.7) | A (4.0) | 0.3 | Best CSM answer. Polish only. |
| q02-why-health-dropped | A- (3.7) | A (4.0) | 0.3 | Polish: strong investigation. |
| q03-recommend-playbook | C- (1.7) | A (4.0) | **2.3** | Failed to deliver actual playbook recommendation. Tool data gap. |
| q04-qbr-prep | A- (3.7) | A (4.0) | 0.3 | Strong QBR talking points. Polish only. |
| q05-open-playbooks | C- (1.7) | A (4.0) | **2.3** | "Fails to answer the core question." Tool data gap. |
| q06-untouched-accounts | B- (2.7) | A (4.0) | 1.3 | Correct identification but underdelivered narrative. |

**Driver categories for CSM gap:**
- **`get_playbook_recommendations` data sparsity on cust 331**: q03, q05 → 2 questions, both at C-
- **Polish on strong answers**: q01, q02, q04 → 3 questions
- **Narrative depth**: q06 → 1 question
- **Missing CSM persona prompt** (falls back to vpcs): all 6 questions affected at the margin

CSM has a clear bimodal distribution: 4 questions at A-/B-, 2 questions at C-. The C- pair both depend on `get_playbook_recommendations`. Fixing that one tool's data state on cust 331 closes ~30% of the CSM gap.

## Cross-persona gap pattern analysis

### How many questions need to improve, by current grade

| Current grade | Count | What they need |
|---|---|---|
| F  | 1 | Total recovery (CRO q03) — biggest single leverage point |
| C- | 3 | Re-do — process or tool failure |
| C  | 1 | Significant rework |
| C+ | 5 | Process fixes (force tool calls, ask user for context) |
| B- | 4 | Precision improvements (variance %, benchmarks, narrative) |
| B  | 0 | (none currently) |
| B+ | 3 | Polish + minor framing |
| A- | 12 | Polish; already very close to A |

**12 of 29 questions are already at A-** — within polish-distance of A. The hard work is the 10 questions at C+ or below.

### Categorized gap drivers (across all 29 questions)

| Driver | Q count | Estimated grade-points to close |
|---|---|---|
| Process failures (didn't call required tools) | 4 | ~6 grade-pts |
| Catastrophic failure (F on CRO q03) | 1 | ~4 grade-pts |
| Tool data sparsity on cust 331 | 4 | ~8 grade-pts |
| Question-comprehension misalignment | 1 | ~1.7 grade-pts |
| Missing aggregation surfaces (CSM, capacity) | 3 | ~6 grade-pts |
| Missing-context-handling (assumed vs asked) | 1 | ~1.3 grade-pts |
| Length budget violation (CEO verbosity) | 1 | ~1.7 grade-pts |
| Persona prompt missing (no 'csm') | 6 (CSM all) | ~3 grade-pts (margin lift) |
| Polish on already-strong answers | 13 | ~5 grade-pts |
| **Total** | **29** (with overlap) | **~36-40 grade-pts** |

### Where the gap is fixable now vs requires real product work

| Fixable Tier | Driver | Rough effort | Grade-points closable |
|---|---|---|---|
| **Tier 1 — prompt engineering** | Force tool calls, length budgets, missing-context handling, csm persona prompt | 1-2 days | ~12 grade-pts |
| **Tier 2 — tool quality fixes** | Debug CRO q03 abort, improve `get_playbook_recommendations` empty-state | 3-5 days | ~10 grade-pts |
| **Tier 3 — new tools/surfaces** | `get_csm_team_workload` aggregation tool, last-touch tracking | 2-3 weeks | ~8 grade-pts |
| **Tier 4 — UI grade extension** | Claude-in-Chrome browser automation for second axis | 1 week | doubles measurement coverage; doesn't directly close Ask AI gap |
| **Polish** | Sharpening 12-13 already-A- answers | ongoing | ~5 grade-pts |

**Sum of Tiers 1-3: ~30 grade-points fixable.** That's ~75% of the total 36-40 gap. The remaining 25% is polish work that accumulates over many releases.

## Reaching A on every persona — what each needs

| Persona | Path to A |
|---|---|
| **CRO** | Tier 1 (force tools) + Tier 2 (fix q03) → C+ to B+. Then polish q05, q06 → B+ to A-. Then sharpen q02, q04 to A → A. **Sprint 1 gets to B+; Sprint 2-3 gets to A.** |
| **CFO** | Tier 1 (clarification habits) + precision-on-units → B to A-. Then polish across all → A. **Sprint 1 gets to B+; Sprint 2 gets to A-.** |
| **CEO** | Tier 1 (length budget) → B+ to A-. Then sharpen 4 already-A- answers to A → A. **Sprint 1 lifts to A-; reaching A is sustained polish.** |
| **VP CS** | Tier 1 + Tier 3 (NEW aggregation tool). **Without Tier 3, VP CS structurally cannot reach A.** Sprint 1 gets to B; new tool sprint gets to B+; full polish to A. |
| **CSM** | Tier 1 (csm persona prompt) + Tier 2 (`get_playbook_recommendations`) → B to B+. Then polish q01/q02/q04 to A → A-. Sprint 2 lifts to A-; sustained polish to A. |

## Honest caveats

1. **A is genuinely hard on this rubric.** The grader is explicitly anti-inflation. Reaching consistent A on every question is more aspirational than tactical. **B+ to A- across the board is a more realistic target.**
2. **Some grade movement requires customer-data improvements.** If cust 331's `playbook_executions_v2` is sparse, CSM grades will be capped regardless of prompt or tool changes. Running on cust 382 may produce different (likely higher) grades simply from richer data.
3. **Single-shot grading has variance.** Re-running the same questions tomorrow with the same code may produce avg grades ±0.2 points different. Set acceptance criteria as 3-run averages, not single runs.
4. **VP CS structural gap is real.** Without a per-CSM aggregation tool, q01/q03/q05 can't reach A no matter how good the AI is at framing. Either build the tool OR replace those 3 questions with ones that don't depend on aggregation.

## What this gap analysis does NOT include

- **UI grade gap.** The Apr 14-15 audit had two surfaces. Today's framework only grades Ask AI. Closing the UI gap is orthogonal work via Claude-in-Chrome browser automation.
- **Cross-customer comparison.** Grades are cust 331 only. Running on 318 / 382 may surface customer-data dependencies that this single-run can't see.
- **Robustness check.** No multi-run averaging. Some grade movement next time may be noise, not progress.

See `persona_grades_recovery_plan_apr25.md` for the sprint-by-sprint plan to close this gap.
