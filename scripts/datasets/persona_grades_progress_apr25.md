# Persona Grading Progress Report — Apr 14-15 → Apr 25, 2026

*Run: 2026-04-25 22:48 UTC. Customer 331 (Slide Deck SaaS Demo). Methodology: LLM-as-judge with persona role-play. Grader: claude-sonnet-4-20250514. Same approach as the Apr 14-15 audit (LLM grader assuming N-yr experienced profile).*

## Headline grades — Ask AI (Claude.ai surface only)

| Persona | Apr 14-15 (Claude.ai) | Apr 25 (this framework) | Δ | Direction |
|---|---|---|---|---|
| CRO   | A      | **C+** (2.49) | -1.5 letter grades | regression |
| CFO   | A      | **B**  (2.98) | -1.0 letter grade  | regression |
| CEO   | n/a    | **B+** (3.32) | first measurement  | n/a |
| VP CS | A      | **B-** (2.54) | -1.3 letter grades | regression |
| CSM   | A      | **B**  (2.93) | -1.0 letter grade  | regression |

(Apr 14-15 also had separate "UI" grades — B+/B+/C+/B respectively. This framework doesn't grade UI yet, so we compare against the Claude.ai column only. Apr 14-15 VP Products grade D+ excluded — out of scope.)

## How to read this

**The regressions are real on the framework, but the methodology may not be apples-to-apples.** The Apr 14-15 grader prompt and question set aren't checked into the repo. Today's framework defines its own canonical 29 questions. Same approach (LLM role-play), but the question-set may be tougher and the grader is explicitly anti-inflation. Treat the Apr 25 numbers as the new baseline going forward; the Apr 14-15 numbers are an indicator of "we used to grade ourselves higher."

That said — the per-question rationales reveal **specific real issues** that would have lowered any reasonable grader's verdict, and those are actionable.

## Per-question deep dive — what dragged each persona down

### CRO — C+ avg (2.49), driven by 1 F + 1 C+

| Q | Grade | Issue (from grader rationale) |
|---|---|---|
| `cro-q01-revenue-at-risk` | C+ | Provided dollar amounts but **failed to call required tools** (`get_revenue_at_risk` / `get_at_risk_accounts`) to validate. CRO will not trust unsourced numbers. |
| `cro-q02-worst-accounts-why` | A- | Strong: specific account names + ARR + traceable signals + chronological framing. **Best CRO answer.** |
| `cro-q03-expansion-upside` | **F** | "Completely unusable — just an opening statement with no actual analysis, data, or insights." Likely truncation or generation aborted. **Single F drops the persona avg by ~0.5 grade points.** |
| `cro-q04-causal-chain` | A- | Strong: Drift Analytics, $1.8M ARR, $720K at risk, chronological causal chain. |
| `cro-q05-nrr-trajectory` | B- | Cited current NRR (99%) and variance ($1.2M shortfall), but **assumed 105% target without asking** the user. CRO would deduct for that. |
| `cro-q06-playbook-roi` | C+ | Correctly flagged "no active playbooks" but didn't deliver the comparative ranking the question asked for. |

**Top 2 fixes for CRO grade:** (a) Force `get_revenue_at_risk` / `get_at_risk_accounts` to be called when the question is foundational like q01 — this is a system-prompt tweak, not a model change. (b) Investigate the q03 truncation/abort.

### CFO — B avg (2.98), most stable

| Q | Grade | Issue |
|---|---|---|
| `cfo-q01-portfolio-roi` | B- | Solid metrics but "critical issues for a CFO review" — likely missing benchmark context or numerator/denominator transparency. |
| `cfo-q02-cost-per-saved-account` | C+ | "Misinterprets the question" — gave total cost / total saves, not cost-per-individual-save. |
| `cfo-q03-actual-vs-projected` | B+ | Clear actual vs projected; missing explicit variance %. |
| `cfo-q04-payback-period` | B+ | Strong (8.5 months payback, $1.2M cost, breakdown). |
| `cfo-q05-power-of-1` | A- | Strong: $509K per pp NRR, $48.5M ARR basis, 9.2x ROI math. **Best CFO answer.** |
| `cfo-q06-benchmark-comparison` | B- | Cited 2.47% $/ARR but used a tighter industry benchmark range (1.0-1.5%) than warranted. |

**CFO is the best-performing persona** by floor (no F's). Power-of-1 is consistently strong because there's a dedicated tool for it. Most CFO regressions are about answer precision (unit-of-measure confusion) rather than process failure.

### CEO — B+ avg (3.32), best persona; first measurement

| Q | Grade | Notes |
|---|---|---|
| `ceo-q01-30-second-summary` | C+ | "Far too long — failed the core requirement of being a 30-second summary." |
| `ceo-q02-strategic-risk` | A- | Strong concentration-risk synthesis: $13M+ ARR, 27% of portfolio. |
| `ceo-q03-cascade-exposure` | A- | Strong: $7.2M Horizon Fintech identified, board-ready framing. |
| `ceo-q04-board-headline` | A- | Headline + 3 bullets + risk flag. Honest both ways. |
| `ceo-q05-vs-market` | A- | Honest about both upside and weakness with metrics. |

**Only CEO weakness is verbosity** (q01). Once the AI knows it's allowed to be tight, the strategic synthesis lands well. Worth establishing CEO baseline at B+ (3.32) for future comparisons.

### VP CS — B- avg (2.54), worst-performing persona on operational details

| Q | Grade | Issue |
|---|---|---|
| `vpcs-q01-csms-need-help` | C+ | Provided account-level data but **completely failed to identify specific CSM names**. Operational view requires names. |
| `vpcs-q02-playbook-effectiveness` | A- | Strong analysis, specific failure patterns. **Best VP CS answer.** |
| `vpcs-q03-daily-action-queue` | C | Identified empty queue but didn't deliver a VP-level operational view. |
| `vpcs-q04-uncovered-risk` | C+ | Names + health scores but **completely missing duration-since-last-touch**. |
| `vpcs-q05-team-capacity` | C- | **No tools called.** Process failure. |
| `vpcs-q06-early-predictors` | B+ | Specific signal types, lead times, examples. |

**VP CS pattern**: questions that require *cross-account aggregation by CSM* (q01, q03, q05) consistently underperform. Suggests `get_csm_daily_actions` either returns sparse data on this customer or the prompt isn't surfacing CSM-specific framing well.

### CSM — B avg (2.93), held back by 2 C-'s

| Q | Grade | Issue |
|---|---|---|
| `csm-q01-today-priority` | A- | 3 specific actions, account names, ARR impact, action verbs. **Best CSM answer.** |
| `csm-q02-why-health-dropped` | A- | Drift Analytics + August 2025 timeline + investigative tone. |
| `csm-q03-recommend-playbook` | C- | Identified the account but **failed to deliver the actual playbook recommendation**. |
| `csm-q04-qbr-prep` | A- | Specific account, concrete metrics, wins/risks balance. |
| `csm-q05-open-playbooks` | C- | "Fails to answer the core question about open playbook executions and progress." |
| `csm-q06-untouched-accounts` | B- | Correctly identified no untouched accounts but underdelivered on the gap-detection narrative. |

**CSM pattern**: question types that depend on `get_playbook_recommendations` returning useful results (q03, q05) consistently underperform. Same root cause as VP CS — likely a tool/data gap, not a prompt issue.

## Top 5 actionable findings

1. **`get_playbook_recommendations` underperforms** on this customer. Drives 3 low grades (CSM q03/q05, CRO q06). Investigate whether the tool returns empty/sparse results for cust 331 and what's needed to fix.
2. **`get_csm_daily_actions` doesn't surface specific CSM names well** (VP CS q01, q03, q05). May return generic data without per-CSM breakdown.
3. **The CRO `cro-q03-expansion-upside` F is a process failure**, not content quality. Worth investigating: did Claude run out of tokens? Did it hit a tool error? One F drops a persona's avg by ~0.5 grade points so this single failure is high-leverage.
4. **Tool-call gaps drag grades down predictably**: when the system gives a numeric answer without calling the tool that would source it, the grader correctly penalizes. Tightening the system prompt to FORCE tool calls for foundational questions (revenue at risk, ROI, payback period) would lift the floor.
5. **Verbosity costs CEO grades**. The `30-second summary` question got C+ for being too long. A length cap in the persona prompt for CEO-style questions would help.

## What changed between Apr 14-15 and Apr 25 that *should* have helped grades

- **Wizard B taxonomy migration** (commit `c80c628a`) — Pipeline-bucket separation + correct expansion subtype recognition. **Expected impact:** CRO/CFO grades on revenue/ROI questions should be more accurate. (CFO held its B avg, CRO regressed — net flat.)
- **I17 + future-signal filter** (commit `2c41fee0`) — Cleaner causal evidence in the context graph. **Expected impact:** Causal-chain question grades should improve. (CRO q04 causal-chain landed A-, consistent with this.)
- **Backtest harness shipped** — Indirect benefit (knowing accuracy bounds). No direct grade impact.

## What didn't change between Apr 14-15 and Apr 25

- `PERSONA_PROMPTS` in `ask_ai_endpoint.py` — identical. Tone/focus framing unchanged.
- `TOOL_DEFINITIONS` — same 17 tools.
- Customer 331 itself (data shape, OUTCOMEs, signals).

So most of the Ask AI grade differences come from the framework's stricter rubric + question-set difference, not product regression. The product is essentially performing as it did Apr 14-15; the harder question set (with explicit `must_call_tools` checks) reveals process failures the prior audit may not have penalized.

## Recommendations

**Immediate (post-Monday):**
1. Add a system-prompt rule: "For foundational questions about revenue, ROI, or payback, ALWAYS call the relevant tool before answering." Should lift CRO floor from ~2.5 to ~2.8.
2. Investigate why `get_playbook_recommendations` underperforms on this customer — could be data state, query design, or output formatting.
3. Run framework on customer 382 too — see if grades differ on a fresher / better-populated demo customer.

**Sprint 1:**
4. Add `'csm'` entry to `PERSONA_PROMPTS` with frontline-operator tone (currently CSM falls back to `vpcs`). Will lift CSM floor.
5. Add a length budget by persona to system prompt (CEO → ≤4 sentences for "summary" questions).
6. Extend the framework to also grade UI surface via Claude-in-Chrome (would let us track the second axis the Apr 14-15 audit had).

**Ongoing:**
7. Re-run this framework after every commit to `ask_ai_endpoint.py` or `ask_ai_tools.py`. Track grade trajectory across releases.
8. If grades stay below 3.0 on any persona for 3+ runs, escalate to roadmap (sub-3.0 = "B-", which is below "ship to a CFO" bar).

## Files

- Framework code: `kpi-dashboard/backend/tests/persona_grading/`
- Run results: `scripts/datasets/persona_grades_2026-04-25.json`
- This report: `scripts/datasets/persona_grades_progress_apr25.md`
