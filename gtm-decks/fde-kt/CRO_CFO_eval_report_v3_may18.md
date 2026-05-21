# CRO + CFO Persona Eval — v3 (close-out delta, May 18)

> **Scope of this doc.** This is a **delta report** on top of [`CRO_CFO_eval_report_v2_cust334_may17.md`](CRO_CFO_eval_report_v2_cust334_may17.md), not a full re-eval. v2 ended May 17 with PM-v2 FINAL scores (Lens A 83/100, Lens B 85/100). v3 captures: (a) state of v2's open threads as of May 18 AM, (b) the new **Pending Decisions Queue** v1 shipped today as a customer-feedback-driven feature, (c) follow-ups still owed. **All scoring tables and per-question evidence remain in v2 — read v2 for the audit substance.**

**Tenant**: still `customer_id 334` — `Predictor V3 Demo SaaS Co (Eval May17)`, $175.37M ARR, 30 accts. No re-ingestion since v2.
**Image at v3 close**: same as v2 close (`:latest` pointing to the May 17 PM rebuild; PR #37 not yet built into an image).

---

## TL;DR — what changed since v2

| Item | v2 status (May 17 close) | v3 status (May 18) |
|---|---|---|
| Lens A portfolio | **83 / 100 ✅** | **83 / 100 ✅** (no re-score; no UI shipped that touches the rubric) |
| Lens B portfolio | **85 / 100 ✅** | **85 / 100 ✅** |
| Flask + MCP duplication-drift audit | flagged as meta-pattern, chip in flight | **PR #37 OPEN** — mergeable, no checks queued |
| Account-column drift audit | shipped (PR #32) + baseline drained (PR #36) | unchanged; **gap noted**: audit doesn't walk `filter_by(**kwargs)` (see Open Threads #2) |
| Pending Decisions Queue (NEW) | not in v2 — customer feedback received post-v2 | **read-only v1 implemented today**: right-sidebar panel on CRO + CFO dashboards; new endpoint `GET /api/executive/pending-decisions` |
| All other open threads (CFO-2 product question, real bootstrap CIs, disclosure rendering, cust 334 retention) | open | open — no movement |

Buyer-acceptance gates: **still passing both lenses, all personas ≥ 14**. The new Decision Queue feature does not affect the rubric (it's an addition, not a rubric-question fix) — flagged here for traceability and because it changes the right-sidebar layout buyers will see in the next demo.

---

## 1. State of v2's "Open threads for next session"

Mapping each thread from v2's close to its May 18 state:

| v2 thread | May 18 state | Evidence / owner |
|---|---|---|
| #1 ~~7,652% ROI presentation~~ | ✅ closed at v2 (PR #20) | n/a |
| #2 ~~File CR for B-1/B-2/B-3~~ | ✅ closed at v2 (PRs #21/#18/#19) | n/a |
| #3 ~~Run CEO/VPCS/CSM evals~~ | ✅ closed at v2 (companion report) | n/a |
| **#4 CFO-2 — does realized defensive ROI surface from outcome CSVs at ingest?** | **Still open** — product decision pending | Open. Belongs in the next product-design slot, not next eval. |
| #5 ~~Cold-start sanity step in rebuild runbook~~ | ✅ closed at v2 (memory `principle_cold_start_sanity_rebuild.md`) | n/a |
| **#6 Commit `gtm-decks/fde-kt/` to a branch** | **Still open** — directory still untracked in `elastic-knuth-039b58` worktree | `git status` confirms 7 files untracked under `gtm-decks/` |
| **#7 cust 334 retention decision** | **Still open** — no roll-forward; cust 334 remains canonical | Worth deciding before the next ingestion cycle. |
| **#8 (newly explicit from v2 Appendix A)** PR #20 disclosure payload rendered in CFO tile | **Still open** — backend ships `disclosure.headline` + `disclosure.detail`; CFO tile still relies on the legacy narrative field | ~half day to wire. |

### Newer open items captured at v2 close but easy to miss

| Item | Source | State |
|---|---|---|
| Flask+MCP duplication-drift audit (PR #37) | v2 meta-pattern + in-flight agent at close | **PR #37 OPEN** — first audit-line landed. Mergeable, no CI gate yet. |
| Extend Account-column audit to `filter_by(**kwargs)` | PR #36 commit message + v2 Pattern 2 | Open; ~1 day chip. |
| Apply Account-column audit pattern to `HealthScore`, `PlaybookExecutionV2`, `OutcomeNode`, `ContextNode` | PR #32 follow-up | Open; ~2 day chip. |
| Real bootstrap CIs (replace `ci_method: placeholder_uncalibrated`) | Phase 1 task #4 in roadmap | Open — CRO-3/4/8 + CFO-10 remain "data present, defensibility caveated" until this lands. |

---

## 2. New surface shipped May 18 — Pending Decisions Queue (read-only v1)

### Why it's in this report

Customer feedback after the v2 walkthrough flagged that the **right area next to the Context Graph** on the CRO + CFO dashboards was empty and a natural slot for a "what needs my attention" surface. This is **not** a v2-rubric question — neither lens scores against a "pending action list" question for CRO/CFO. It is a feature delta that buyers will see in the next demo, and is the platform's first step toward an **Executive Decision Queue** (vs. CSM's tactical action queue).

### What shipped

| Layer | Surface | Notes |
|---|---|---|
| **Backend** | `GET /api/executive/pending-decisions?persona={cro\|cfo}&limit=5` | New route in `executive_dashboard_api.py`. Tenant-isolated via `get_current_customer_id()`. |
| **Data sources** | `PlaybookExecutionV2` (status='in_progress') + at-risk accounts without active playbook + `ContextNode` (revenue_impact_type='expansion') | Three sources merged into one ranked list. Re-uses existing helpers (`_get_customer_accounts`, `_get_latest_health_scores`, `ht.classify`). No new DB tables. |
| **Persona behaviour** | CRO sorts by **revenue at stake** desc; CFO sorts by **$ spend** desc. Headlines reframe per persona | "Decide intervention for X" (CRO) vs. "Approve continued spend on X" (CFO) for the same underlying decision item. |
| **Resilience** | Three nested try/except guards (HealthScore / PlaybookExecutionV2 / ContextNode) | Matches the existing defensive pattern at `executive_dashboard_api.py:567`. If one source 500s on schema drift, the queue degrades to the remaining sources instead of collapsing. Future Flask+MCP image rebuilds that change column shape won't blank the panel. |
| **Frontend** | `kpi-dashboard/src/components/dashboard/PendingDecisionsQueue.tsx` | Read-only card list. Urgency colour-coding (high/medium/low driven by revenue × time-open). Skeleton / empty / error states. |
| **Wiring** | Right sidebar of `CRODashboard.tsx` (above Power of 1) + `CFODashboard.tsx` (between InvestmentAllocation and Revenue Waterfall) | Position chosen to occupy the previously-empty area customer feedback called out. |

### Verification status (May 18 AM)

- ✅ TypeScript `tsc --noEmit -p .` clean — zero errors.
- ✅ Backend route registered and importable: `{GET, OPTIONS, HEAD} /api/executive/pending-decisions`.
- ✅ Frontend dev server compiles (warnings only).
- ✅ Logged-in preview confirms panel renders in both CRO and CFO sidebars with the correct persona badge.
- ✅ Error-state UX confirmed end-to-end — local deploy serves an older image without the route, component renders "Could not load — API 404" instead of crashing.
- ⏸️ **End-to-end happy-path data NOT verified locally** — local docker DB schema lags this worktree's `models.py` on `users.magic_link_token`, `health_scores.kpi_only_score`, and `context_nodes.source`. Pre-existing drift; will resolve once this branch is built into a fresh image and rehydrated.

### Rubric impact

**None for v3**, by design — the v2 rubric was written before this feature was scoped. If a future rubric adds an actionability question framed "Does the dashboard surface a prioritised action queue for the executive?", CRO + CFO would lift by +2 each on Lens A.

### Follow-up (write-back v2)

Read-only v1 ships the read path only. Customer feedback after the next demo will tell us whether to invest in **write-back v2**: approve / escalate / defer state transitions + `ContextNode` audit trail + Slack/email notification fan-out. Out of scope for this eval cycle. See [project memory] for design notes on the Decision Queue framing.

---

## 3. Lens-A re-walk delta (sidebar only)

A full re-walk wasn't done for v3 — the rubric didn't change and no rubric-relevant UI changed. The sidebar visual change is:

- **CRO right sidebar** (top to bottom): NRR Forecast → **Pending Decisions** (NEW) → Power of 1 ROI Engine → Revenue Timeline.
- **CFO right sidebar**: CS Investment → Investment Allocation Story → **Pending Decisions** (NEW) → Revenue Waterfall (conditional) → Quick Financial Ratios.

Buyers walking either dashboard at next demo will see the new panel above the fold on first paint. If the panel is showing the "Could not load — API 404" error during the demo, the deploy hasn't picked up this branch yet — run `rehydrate-ec2-ecr.sh` with `PLATFORM_TAG=:latest` and re-point per the v2 close runbook.

---

## 4. Open threads for next session

Numbered fresh — older numbering from v2 is resolved or rolled into items below.

1. **CFO-2 product decision** — does realized defensive ROI surface from outcome CSVs at ingest or only after closed playbook executions? Carries to v4 unaddressed; recommend scoping in a 30-min product session before the next demo.
2. **Extend Account-column audit to `filter_by(**kwargs)`** — gap discovered in PR #36. ~1 day chip.
3. **Apply ORM-column audit pattern to other tables** (HealthScore, PlaybookExecutionV2, OutcomeNode, ContextNode). ~2 days. Suggested in PR #32 description.
4. **Flask + MCP duplication-drift audit** — PR #37 is OPEN. Land it.
5. **Real bootstrap CIs** — replace `ci_method: placeholder_uncalibrated` (Phase 1 task #4). Until done, CRO-3 / CRO-4 / CRO-8 / CFO-10 remain partial-credit-with-caveat.
6. **Wire PR #20's `disclosure.headline` + `disclosure.detail` into the CFO ROI tile** — payload exists, UI doesn't render the structured warning. ~half day.
7. **Decision Queue write-back v2** — only if customer feedback after next demo says read-only isn't enough. State transitions + audit trail + notifications. ~3–5 days.
8. **Commit `gtm-decks/fde-kt/` to a branch** — still untracked in `elastic-knuth-039b58` worktree. Carries from v2 thread #6.
9. **Cust 334 retention decision** — keep as canonical, or roll forward to a freshly-registered tenant per eval cycle? Affects how persistent the audit baseline is. Carries from v2 thread #7.
10. **Add a 6th category to the next rubric for "Executive Action Queue / Pending Decisions"** — covers the gap the new surface fills. Treat as Lens-A only for v1; would require ~2 questions to materially score the feature (e.g. "Can the exec see top-3 awaiting decisions in < 5s?", "Is each decision tied to a $ at stake?"). If we add this, all five persona rubrics should grow uniformly to avoid asymmetric scoring.

---

## 5. PR ledger (deltas only since v2 close)

| PR | State | Theme |
|---|---|---|
| #37 | **OPEN** | ci(audit): static audit for Flask + MCP duplication drift (in-flight at v2 close, now reviewable) |
| *new — local branch, not yet pushed* | pre-PR | feat: Pending Decisions Queue read-only v1 (this v3's centerpiece). To be opened on `claude/agitated-murdock-feaac1`. |

All other PRs from this initiative (#18–#36) are merged and on `:latest`.

---

*Generated 2026-05-18 · delta on top of [CRO_CFO_eval_report_v2_cust334_may17.md](CRO_CFO_eval_report_v2_cust334_may17.md) · cust 334 (no re-ingestion) · Internal — NDA covered*
