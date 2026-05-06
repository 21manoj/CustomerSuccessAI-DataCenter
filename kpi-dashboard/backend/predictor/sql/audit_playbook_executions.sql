-- ============================================================================
-- NRR Predictor v3 — Block 1 — PlaybookExecutionV2 audit
-- ----------------------------------------------------------------------------
-- Closes Q3 action item from nrr_predictor_v3_design_notes.md.
-- Verifies the structured artifact we'll use as the treatment definition for
-- Phase 4 attribution is populated completely enough to reconstruct
-- treatment retrospectively.
--
-- Audit findings (run 2026-05-06):
--   total_rows:            1712 across 74 customers
--   triggered_at populated: 100% (1712/1712) — start time is reliable
--   closed_at populated:    96.1% (1646/1712) — end time mostly reliable;
--                           67 in_progress rows correctly have NULL
--   outcome populated:      96.1% (1645/1712) — 1 stale row with closed_at
--                           but no outcome (data-ops fix candidate, low priority)
--   account_id, customer_id: 100% (NOT NULL columns, hard-enforced)
--   status vocabulary:     {completed, in_progress}
--   outcome vocabulary:    {resolved, escalated, timeout}
--
-- Treatment definition for Phase 4 (per design notes Q3, with vocab corrected):
--   eligible IF status='completed' AND closed_at IS NOT NULL AND outcome IS NOT NULL
--   excluded: 67 in_progress rows (ongoing treatments) + 1 stale closed-no-outcome row
-- ============================================================================

SELECT
    COUNT(*)                                                  AS total_rows,
    COUNT(*) FILTER (WHERE triggered_at IS NOT NULL)          AS with_triggered_at,
    COUNT(*) FILTER (WHERE closed_at    IS NOT NULL)          AS with_closed_at,
    COUNT(*) FILTER (WHERE outcome      IS NOT NULL)          AS with_outcome,
    COUNT(*) FILTER (WHERE account_id   IS NOT NULL)          AS with_account_id,
    COUNT(*) FILTER (WHERE customer_id  IS NOT NULL)          AS with_customer_id,
    COUNT(DISTINCT customer_id)                               AS distinct_customers,
    COUNT(*) FILTER (WHERE status = 'completed')              AS completed_count,
    COUNT(*) FILTER (WHERE status = 'in_progress')            AS in_progress_count,
    COUNT(*) FILTER (WHERE outcome = 'resolved')              AS outcome_resolved,
    COUNT(*) FILTER (WHERE outcome = 'escalated')             AS outcome_escalated,
    COUNT(*) FILTER (WHERE outcome = 'timeout')               AS outcome_timeout,
    COUNT(*) FILTER (WHERE closed_at IS NOT NULL AND outcome IS NULL)
                                                              AS closed_without_outcome
FROM playbook_executions_v2;

-- Distribution by (status, outcome):
--   completed   | resolved   | 1555
--   completed   | escalated  |   77
--   in_progress | (NULL)     |   67
--   completed   | timeout    |   13
