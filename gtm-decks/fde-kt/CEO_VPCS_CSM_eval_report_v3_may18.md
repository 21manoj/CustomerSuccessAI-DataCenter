# CEO + VP CS + CSM Persona Eval — v3 (close-out delta, May 18)

> **Scope of this doc.** Delta on top of [`CEO_VPCS_CSM_eval_report_v2_cust334_may17.md`](CEO_VPCS_CSM_eval_report_v2_cust334_may17.md). v2 captured PM-v2 FINAL scores. v3 only carries forward what changed May 17 close → May 18 AM. **Full rubric, evidence and per-question scoring stay in v2.**

**Tenant**: still `customer_id 334`. No re-ingestion.

---

## TL;DR — what changed since v2

| Item | v2 status | v3 status |
|---|---|---|
| CEO Lens A | 18 / 20 ✅ | 18 / 20 ✅ (no rubric re-walk) |
| VP CS Lens A | 15 / 20 ✅ | 15 / 20 ✅ |
| CSM Lens A | 16 / 20 ✅ | 16 / 20 ✅ |
| 5-persona portfolio (Lens A) | 83 / 100 ✅ | 83 / 100 ✅ |
| 5-persona portfolio (Lens B) | 85 / 100 ✅ | 85 / 100 ✅ |
| Flask + MCP duplication-drift audit (v2 meta-finding) | chip in flight | **PR #37 OPEN** |
| Account-column drift baseline | shipped + drained | unchanged; **`filter_by(**kwargs)` gap** still open |
| Pending Decisions Queue (NEW, May 18) | not in v2 | shipped on **CRO + CFO only** — not the 3 personas in this report; cross-referenced for completeness only |

No persona in this report had its UI changed by today's work — Decision Queue v1 is CRO/CFO-only. Scores stay at v2 PM-FINAL.

---

## 1. State of v2's "Open threads for next session"

| v2 thread | May 18 state | Note |
|---|---|---|
| **#1 Single-tenant CEO eval — is it meaningful at all?** | **Still open** — product framing decision. Today's rubric still inherits a PE-fund framing that costs cust 334 4–6 points it can't recover. | Worth pinning before the next refresh. |
| #2 ~~File CR for B-4 / B-5~~ | ✅ closed at v2 (PR #26) | n/a |
| **#3 Close-loop attribution drift** (Mira account-level $1.36M churn averted vs. CSM scorecard $0 protected) | **Still open** — same cross-source-inconsistency from Apr 20 demo prep | Suspected shared root cause with `revenue_protected: 0` cold-start pattern. ~1 day to reconcile. |
| #4 ~~B-1 / B-4 / B-5 investment for VP CS surface~~ | ✅ closed at v2 (PRs #30, #33, #26) — VPCS lifted to 15 | n/a |
| #5 ~~CEO single-tenant polish sprint~~ | ✅ closed at v2 (PR #31) — CEO lifted to 18 | n/a |
| #6 ~~Re-run 5-persona eval after B-1/B-4/B-5 land~~ | ✅ closed — that's exactly what v2 PM-FINAL captures | n/a |
| **#7 Commit `gtm-decks/fde-kt/` to a branch** | **Still open** — directory still untracked in `elastic-knuth-039b58` | Same as v3 CRO/CFO Open Thread #8. |

---

## 2. Newer open items rolled forward

Same set as the v3 CRO/CFO report; not re-listing in full. The ones that touch these three personas specifically:

| Item | Persona impact | Status |
|---|---|---|
| Flask + MCP duplication-drift audit (PR #37) | VPCS Q1 + Q6 + CSM Q4 were all Flask+MCP drift instances. PR #37 institutionalises the catch. | OPEN |
| Apply Account-column audit pattern to other ORM models (HealthScore, PlaybookExecution, OutcomeNode, ContextNode) | CSM drill-drawer + VPCS team-capacity tile both lean on these models | Open |
| Real bootstrap CIs | CEO-7 (CI on board metrics) stays caveated until done | Open |
| Decision Queue write-back v2 | **Future expansion** could mirror the CRO/CFO panel for VPCS (capacity-rebalance approvals) and CSM (kanban-write decisions). Not in scope today. | Pre-decision |

---

## 3. Cross-reference: Pending Decisions Queue (shipped May 18)

The new right-sidebar panel ships on **CRO + CFO only**. Out of scope for the 3 personas in this report — but worth flagging so the engagement lead knows:

- A buyer walking from CRO → CFO → VPCS → CSM dashboards in sequence will see the new panel only on the first two. The visual asymmetry is intentional for v1 (decision-queue framing is exec-altitude; CSM already has a daily-actions queue at a different altitude).
- If the buyer asks "where's mine?" during a VPCS or CSM walk-through, the honest answer is: VPCS has the Action Queue (CSM-altitude rollup); CSM has the kanban + daily-actions. The exec-altitude Decision Queue is genuinely a different surface, not a missing copy of the same widget.
- **Future**: a VPCS-flavoured Decision Queue (approvals for book reassignment / capacity-rebalance — things VPCS does that need exec sign-off) is a sensible v2.5 if customer feedback asks. Not currently scoped.

See [`CRO_CFO_eval_report_v3_may18.md`](CRO_CFO_eval_report_v3_may18.md) §2 for full feature detail (data sources, verification status, persona behaviour).

---

## 4. Open threads for next session (this report's personas)

1. **Decide whether single-tenant CEO eval is meaningful** (v2 thread #1 carries forward). If yes, the rubric needs alternate questions that don't assume a portfolio-above layer.
2. **Reconcile close-loop attribution** — account-level outcome-roi-story vs. CSM scorecard `revenue_protected`. Likely shared root cause with `revenue_protected: 0` everywhere on cold-start tenants. Same chip from v2.
3. **Add an "Executive Action Queue" rubric category** if v4 wants to score the Decision Queue feature. Would touch CRO + CFO; uniform extension across all 5 personas recommended to keep totals comparable.
4. **VPCS Decision Queue** — pre-decision. Only do if customer feedback asks. ~3–4 days if approved.
5. **Cust 334 retention** — same decision as v3 CRO/CFO Open Thread #9. Affects all 5 personas' eval baselines.

---

## 5. PR ledger (deltas only since v2 close)

Same as v3 CRO/CFO §5 — only #37 OPEN + the local Decision Queue branch (CRO/CFO-only). Nothing exclusively touching this report's three personas has landed since v2 close.

---

*Generated 2026-05-18 · delta on top of [CEO_VPCS_CSM_eval_report_v2_cust334_may17.md](CEO_VPCS_CSM_eval_report_v2_cust334_may17.md) · companion to [CRO_CFO_eval_report_v3_may18.md](CRO_CFO_eval_report_v3_may18.md) · cust 334 (no re-ingestion) · Internal — NDA covered*
