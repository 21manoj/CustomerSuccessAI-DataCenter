# Persona Grading — Recovery Plan to A (Apr 25 2026)

*Goal: every persona's average grade ≥ A (4.0) on the framework. Realistic intermediate target: B+ → A- across all 5 personas within 4 sprints.*

*Companion to `persona_grades_gap_apr25.md`. Read that first for the gap quantification — this document is execution.*

## Acceptance criteria (what counts as "back to A")

For each persona, the 3-run rolling average grade must be:
- **≥ 3.7 (A-)** — provisional pass; re-evaluate next sprint
- **≥ 4.0 (A)** — sustained for 2 consecutive runs

Single-run grades have ±0.2 noise (single-shot LLM-as-judge at temp=0.3). Use 3-run averages for sprint-end checkpoints.

Per persona, additional gates:
- No question scoring below B- (2.7)
- No catastrophic failures (F or D-grade outputs)
- All `must_call_tools` checks passing on foundational questions

## Sprint roadmap

### Sprint 1 (Week 1) — Prompt engineering + small fixes

**Theme: lift the floor.** No new tools, no UI work — just pure prompt-engineering changes to `ask_ai_endpoint.py`. Target: every persona ≥ B (3.0).

| # | Change | Persona impact | File | Effort |
|---|---|---|---|---|
| 1 | Add `csm` to `PERSONA_PROMPTS` | CSM (lifts margin) | `ask_ai_endpoint.py:42-71` | 1h |
| 2 | Add tool-call enforcement rule for foundational queries | CRO q01, CFO q01, q02; CRO q06 | system prompt | 2h |
| 3 | Add length budget for CEO summary-style questions | CEO q01 | system prompt | 1h |
| 4 | Add "ask user when target/projection unspecified" rule | CRO q05, CFO q03 | system prompt | 1h |
| 5 | Add explicit benchmark-range guidance for CFO | CFO q06 | system prompt | 1h |
| 6 | Add ranking-deliverable enforcement for "which X is best/worst" | CRO q06, VP CS q01 | system prompt | 1h |
| 7 | Investigate + fix CRO q03 expansion-upside F | CRO (closes F → A-) | runtime debug | 2-3h |
| 8 | Re-deploy + re-run framework + commit results | All | n/a | 2h |

**Total Sprint 1 effort: 1-1.5 days.**

**Predicted grade movement:**

| Persona | Sprint 0 (today) | Sprint 1 target |
|---|---|---|
| CRO   | C+ (2.49) | **B (3.0)** — lifted by tool-call enforcement + q03 fix |
| CFO   | B  (2.98) | **B+ (3.3)** — clarification habits + benchmark guidance |
| CEO   | B+ (3.32) | **A- (3.7)** — single length-budget rule fix |
| VP CS | B- (2.54) | **B (3.0)** — tool-call enforcement; q05 cap remains |
| CSM   | B  (2.93) | **B+ (3.3)** — csm persona prompt + improved framing |

**Acceptance criteria for Sprint 1:** each persona's 3-run avg ≥ B (3.0), with CEO ≥ A- (3.7).

### Sprint 2 (Week 2) — Tool quality + data audit

**Theme: fix tool data sparsity.** Three tier-2 driver fixes that lift the persistent C-grade questions.

| # | Change | Persona impact | Effort |
|---|---|---|---|
| 9 | Audit `get_playbook_recommendations` on cust 331 — backfill data OR improve empty-state response | CSM q03, q05, CRO q06, VP CS q02 | 1d |
| 10 | Audit `get_csm_daily_actions` — verify per-CSM aggregation surfaces in tool output | VP CS q01, q03, q05 | 1d |
| 11 | Add `last_touch_at` field to account journey timeline output | VP CS q04, CSM q06 | 1d |
| 12 | Verify `get_revenue_at_risk` returns context-graph evidence (not just account totals) | CRO q01 | 0.5d |
| 13 | Re-run framework on cust 331 + cust 382 (compare cross-customer variance) | All | 0.5d |
| 14 | Update gap analysis based on new data | All | 0.5d |

**Total Sprint 2 effort: ~4-5 days.**

**Predicted grade movement:**

| Persona | Sprint 1 | Sprint 2 target |
|---|---|---|
| CRO   | B (3.0) | **B+ (3.3)** — q06 tool fix + q01 evidence |
| CFO   | B+ (3.3) | **A- (3.5+)** — sustained quality across all questions |
| CEO   | A- (3.7) | **A- (3.7)** — already there, hold |
| VP CS | B (3.0) | **B+ (3.3)** — partial recovery on q01/q03; q05 still capped |
| CSM   | B+ (3.3) | **A- (3.6)** — q03 + q05 lifted by playbook tool fix |

**Acceptance criteria for Sprint 2:** CFO and CEO at A- avg; CRO/VP CS/CSM at B+ avg.

### Sprint 3 (Week 3-4) — New aggregation surfaces

**Theme: structural product additions.** This sprint addresses VP CS's structural gap (per-CSM aggregation is a missing tool, not a missing prompt).

| # | Change | Persona impact | Effort |
|---|---|---|---|
| 15 | Build `get_csm_team_workload` MCP tool — returns per-CSM (account_count, open_playbooks, last_touched_avg, capacity_utilization, outcomes_qtd) | VP CS q01, q03, q05 | 2-3d |
| 16 | Add `get_account_last_touch` to ContextNode index | VP CS q04, CSM q06 | 1d |
| 17 | Add `get_csm_capacity_utilization` derived metric | VP CS q05 | 1d |
| 18 | Update `TOOL_DEFINITIONS` in `ask_ai_tools.py` + executor mapping | All | 0.5d |
| 19 | Update VP CS persona system prompt to reference new tools | VP CS | 0.5d |
| 20 | Re-run framework, gap-update | All | 0.5d |

**Total Sprint 3 effort: ~5-6 days.**

**Predicted grade movement:**

| Persona | Sprint 2 | Sprint 3 target |
|---|---|---|
| CRO   | B+ (3.3) | **A- (3.7)** — polish on q05, q06 to A; q03 stable at A- |
| CFO   | A- (3.5) | **A- (3.7)** — precision improvements |
| CEO   | A- (3.7) | **A (3.9+)** — first persona to consistently A |
| VP CS | B+ (3.3) | **A- (3.6)** — new aggregation tool unlocks q01/q03/q05 |
| CSM   | A- (3.6) | **A- (3.7)** — `last_touch` data lifts q06 |

**Acceptance criteria for Sprint 3:** CEO at A; all other personas at A-.

### Sprint 4 (Week 5-6) — Polish + UI grade extension

**Theme: close the last 0.3 grade-points + add second measurement axis.**

| # | Change | Persona impact | Effort |
|---|---|---|---|
| 21 | Sharpen 12 currently-A- answers across all personas (case-by-case prompt tweaks) | All (fractional A- → A) | 3d |
| 22 | Build Claude-in-Chrome UI grading runner (browses dashboards, takes screenshots, grades via vision-LLM-as-judge) | All (new UI-grade axis) | 3-5d |
| 23 | Re-run with multi-shot averaging (3 runs per question, report mean ± stddev) | Robustness | 1d |
| 24 | Per-customer baseline runs (cust 318, 331, 382) | Cross-customer variance | 1d |

**Total Sprint 4 effort: ~7-10 days.**

**Predicted grade movement:**

| Persona | Sprint 3 | Sprint 4 target (Ask AI) | UI grade target |
|---|---|---|---|
| CRO   | A- (3.7) | **A (4.0)** | A- (3.7) |
| CFO   | A- (3.7) | **A (4.0)** | A- (3.7) |
| CEO   | A (3.9) | **A (4.0)** | A- (3.7) |
| VP CS | A- (3.6) | **A (4.0)** | A- (3.7) |
| CSM   | A- (3.7) | **A (4.0)** | A- (3.7) |

**Acceptance criteria for Sprint 4 (final):** all 5 personas at A on Ask AI surface, all at A- on UI surface, sustained across 3 consecutive runs.

## Per-persona recovery snapshot (TL;DR)

| Persona | Path to A | First A run (estimate) | Hardest residual gap |
|---|---|---|---|
| **CRO** | S1 fixes process/F → S2 polishes data → S3 sharpens q05/q06 → S4 polish | Sprint 4 | q03 expansion-upside F is unstable; need robust generation handling |
| **CFO** | S1 + S2 close most; S3-S4 polish | Sprint 3-4 | Question-comprehension on q02 — may need rephrasing or prompt clarification |
| **CEO** | S1 length-budget closes 90% of gap | **Sprint 3** (fastest) | None major; mostly polish across already-A- answers |
| **VP CS** | Structurally needs Sprint 3 new tool; S4 polishes | Sprint 4 | Cross-CSM aggregation tool is the linchpin; cannot reach A without it |
| **CSM** | S1 persona prompt + S2 playbook tool fix → S3 polish → S4 close | Sprint 4 | `get_playbook_recommendations` data state on cust 331 |

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Single-shot grade variance masks improvements | High | Medium | Switch to 3-run averaging in Sprint 4 (item 23); use trend lines, not point estimates |
| R2 | Customer 331 data state is unrepresentatively sparse → grades are pessimistic | Medium | Medium | Run cross-customer in Sprint 2 (item 13); if cust 382 grades higher, primary baseline shifts |
| R3 | Tool fixes (Sprint 2) require backfilling data, which requires customer cooperation | Medium | High | Where data backfill isn't possible, improve empty-state responses (AI explicitly says "no playbook data available") so grader doesn't penalize |
| R4 | New `get_csm_team_workload` tool (Sprint 3) requires schema additions or new aggregation logic | Medium | High | Scope tightly: start with read-only aggregation over existing tables; defer advanced features |
| R5 | LLM-as-judge grader drift over time (model updates, behavior changes) | Low (medium-term) | Medium | Pin grader model version in `runner.py`; document the version in each result file |
| R6 | "Reaching A" becomes a goodhart's-law metric (gaming the rubric instead of improving the product) | Medium | Medium | Cross-reference grades against actual user feedback; if grades go up but users don't benefit, rubric is wrong |
| R7 | Sprint 3's new tools introduce bugs that regress other grades | Low | High | Always re-run all 5 personas after any tool change; flag any regression > 0.3 grade-pts immediately |
| R8 | `expansion_upside` F (CRO q03) is intermittent — fixed once, comes back | Medium | High | Add a stable repro test before declaring fix; monitor across 3+ runs |

## Success metrics — what to track every sprint

1. **Per-persona avg grade** (numeric + letter) — primary
2. **Question count by grade tier** — secondary; tracks distribution shape
3. **`must_call_tools` pass rate** — process metric
4. **`anti_hallucination_pass` rate** — quality floor metric
5. **Cost per run** ($) — operational metric, target $3-5
6. **Run wall-clock time** (min) — operational metric, target ≤15 min
7. **Cross-customer variance** (cust 331 vs 382 grade delta) — added in Sprint 2

## Anti-patterns to avoid during recovery

1. **Don't optimize one persona at the expense of others.** Always re-run all 5 after any change. A change that lifts CSM by 0.3 but drops CRO by 0.2 is net negative.
2. **Don't tune the rubric to game the grades.** The fixtures + grader are the contract. If a question's rubric is wrong, change it deliberately and document the change. Don't silently soften it.
3. **Don't ship a fix without re-running the framework.** Every commit to `ask_ai_endpoint.py` or `ask_ai_tools.py` should trigger a re-grade.
4. **Don't conflate "passes ≥3.0" with "ready to demo".** A persona at B avg has at least one question at B- or below — those are the rough edges users will hit.
5. **Don't outsource to "just better prompts".** Some gaps (VP CS aggregation, CSM playbook data sparsity) are real product issues. Prompt-only fixes will plateau before A.

## Operational plan

**Cadence:**
- Re-run framework after every sprint demo
- Update gap doc with new numbers
- Commit results to `scripts/datasets/persona_grades_<YYYYMMDD>.json`
- Track 4-week trend: `scripts/datasets/persona_grades_trend.json` (one row per run)

**Owner:** Whoever owns Ask AI (likely the same person who owns `ask_ai_endpoint.py`)

**Reviewer:** Original Apr 14-15 audit reviewer (the one who pushed the predictive feedback). They've offered to spec the label builder; once labels exist, they can also re-grade independently as a sanity check on our LLM-as-judge.

**Communication:** Each sprint-end checkpoint produces a 1-page update — current grades, delta from baseline, what changed, what's next. Don't bury results; share them with whoever cares about quality.

## End-state vision

When this plan is complete (~6 weeks):

- **All 5 personas at A on Ask AI surface**, sustained across 3 runs
- **All 5 personas at A- on UI surface** (new dimension Sprint 4 adds)
- **Multi-customer baselines** (318, 331, 382) showing consistent grades within ±0.2 across customers
- **Multi-shot robustness check** (3 runs per question) showing stddev ≤ 0.3
- **Framework as a CI artifact** — every release runs grading, results land in dashboards
- **Reviewer's label-builder spec** integrated → grades against real customer outcomes, not just synthetic methodology

That's the bar. It's hard, but every step has a defined gate.
