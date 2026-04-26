# Persona Grading Progress Report — Apr 14-15 → Apr 25, 2026

*Methodology: LLM-as-judge with persona role-play (15-yr veteran for senior personas; 5-yr for CSM). Both runs used Claude Sonnet class. The Apr 14-15 audit's exact question list and rubric weren't checked into the repo, so today's framework defines its own canonical set. The Apr 14-15 grades remain the public reference point even if individual questions differ — we treat the framework as a forward-going apples-to-apples basis from this date.*

## Headline grades

| Persona | Apr 14-15 (UI) | Apr 14-15 (Claude.ai) | Apr 25 (this framework) | Δ vs Apr 14-15 Claude.ai |
|---|---|---|---|---|
| CRO | B+ | A | TBD | TBD |
| CFO | B+ | A | TBD | TBD |
| CEO | n/a | n/a | TBD (first run) | first measurement |
| VP CS | C+ | A | TBD | TBD |
| CSM | B | A | TBD | TBD |
| VP Products | D+ | B | not graded (out of scope) | n/a |

## What changed between Apr 14-15 and Apr 25 that should affect persona grades

### Backend / data quality (positive impact expected)

- **Wizard B taxonomy migration** (commit `c80c628a`, Apr 25) — `_DEFINITIVE_LOST` / `_DEFINITIVE_EXPANSION` now load from `taxonomy_base.json`. Pipeline-bucket separation prevents double-counting `expansion_approved`. Real prod customers (318/331/382) saw ~+2pp upward NRR-forecast correction. **Expected impact:** CRO/CFO grades on revenue-related questions should be more accurate.
- **I17 + future-signal filter** (commit `2c41fee0`, Apr 25) — playbook closes no longer create reverse-time causal edges. Cleaner causal evidence in context graph. **Expected impact:** CRO `cro-q04-causal-chain` and CSM `csm-q02-why-health-dropped` grades should improve.
- **Backtest harness shipped** (commit `7a25dc22`) — the framework that exposed taxonomy drift in the first place. Indirect: gives us measurable accuracy claims to cite.

### UI / surface (mixed impact expected)

- **Journey Intelligence overlays** (commit `93af9110`, Apr 25) — 5 new toggle layers (Wizard A arcs, forecast lines, OUTCOME events, DECISION nodes). **Expected impact:** UI-grade improvements for personas that use the journey view (CSM, VP CS) — but our framework doesn't grade UI yet. Would need Claude-in-Chrome browser automation extension.

### Persona prompts (unchanged)

`PERSONA_PROMPTS` in `ask_ai_endpoint.py` hasn't been modified between Apr 14-15 and Apr 25. Tone/focus framing is identical. So any Ask AI grade improvements come from data/tool-output quality, not from prompt changes.

## Per-question deep-dive

(Filled in after the run lands.)

| Persona | Question ID | Apr 25 Grade | Rationale (concerns) |
|---|---|---|---|
| ... | ... | ... | ... |

## Known framework limitations (be honest)

1. **One-shot, no robustness.** Each question runs once with `temperature=0.3`. Stochastic — same question on a different day might grade B+ instead of A-. Mitigation: re-run on each release; trends matter more than point grades.
2. **No UI grade.** The Apr 14-15 audit graded "UI" and "Claude.ai" separately. This framework only does the latter. Adding UI grading via Claude-in-Chrome is a future enhancement.
3. **CSM persona prompt missing.** `PERSONA_PROMPTS` doesn't include `csm`; framework falls back to `vpcs`. CSM grades will be artificially capped until a real CSM persona prompt is added.
4. **Customer dependence.** Grades are tied to customer 331's data state (account count, signal density, OUTCOME coverage). Same framework on a sparse customer would grade lower simply because tools return less.
5. **Grader bias.** The grader is Claude grading Claude. Inherent risk that the grader sympathizes with the assistant's framing. Mitigation built in: explicit "avoid grade inflation" instruction in the grader system prompt.

## Recommendations after this run

(Filled in after results land.)
