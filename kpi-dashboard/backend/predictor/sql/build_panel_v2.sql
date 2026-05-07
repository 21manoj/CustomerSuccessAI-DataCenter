-- ============================================================================
-- NRR Predictor v3 — Block 1 — Panel Construction (V2: time-varying ARR)
-- ----------------------------------------------------------------------------
-- v2 differs from v1 in exactly one structural change: the `arr` column is
-- now time-varying (start-of-month ARR), reconstructed from
-- accounts.revenue (current ARR) and the cumulative revenue_impact deltas
-- on OUTCOME context_nodes.
--
-- Convention (locked here so we don't drift):
--   accounts.revenue                = ARR after all OUTCOME events have applied
--   revenue_impact on OUTCOME node  = signed delta the event applied
--                                     (+ for expansion_closed/new_logo,
--                                      - for contraction/churn_lost)
--   arr_at_month(account, T)        = accounts.revenue
--                                       − SUM(revenue_impact)
--                                         WHERE event_month >= T
--
-- This means a panel row for the month an event occurs in carries the
-- PRE-event ARR (what was at risk going into that month). The next
-- month's row carries the post-event ARR. This matches the prediction
-- semantic: condition the model on the state going into the event,
-- not the state after.
--
-- arr_band is recomputed per-row from arr_at_month so accounts that
-- cross a band boundary via expansion/contraction get correct band
-- one-hots throughout their history.
--
-- Outputs columns: identical schema to v1 build_panel.sql.
-- ============================================================================

WITH
-- ----------------------------------------------------------------------------
-- 1. Auto-detect saas_profile per tenant (A5 — unchanged from v1)
-- ----------------------------------------------------------------------------
tenant_profile AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.vertical,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY a.revenue) AS median_arr,
        CASE
            WHEN PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY a.revenue) >= 250000
                THEN 'saas_enterprise'
            ELSE 'saas_smb'
        END AS saas_profile
    FROM customers c
    JOIN accounts a ON a.customer_id = c.customer_id
    WHERE c.customer_id = ANY(:target_customer_ids)
      AND c.vertical = 'saas_premium'
      AND a.account_status NOT IN ('cancelled', 'inactive')
    GROUP BY c.customer_id, c.customer_name, c.vertical
),

-- ----------------------------------------------------------------------------
-- 2. Per-account metadata — note `arr_current` (renamed from v1's `arr` for
--    clarity); segment is still derived from current ARR (segment is a
--    relatively stable classification, not re-banded per event).
-- ----------------------------------------------------------------------------
account_meta AS (
    SELECT
        a.account_id,
        a.customer_id,
        a.account_name,
        a.revenue AS arr_current,
        a.arc_type,
        DATE(a.profile_metadata->>'renewal_date') AS renewal_date,
        tp.saas_profile,
        CASE
            WHEN tp.saas_profile = 'saas_enterprise' THEN
                CASE
                    WHEN a.revenue >= 50000000 THEN 'strategic'
                    WHEN a.revenue >= 5000000  THEN 'enterprise'
                    WHEN a.revenue >= 250000   THEN 'mid_market'
                    ELSE 'below_floor'
                END
            WHEN tp.saas_profile = 'saas_smb' THEN
                CASE
                    WHEN a.revenue >= 250000 THEN 'enterprise'
                    WHEN a.revenue >= 25000  THEN 'mid_market'
                    ELSE 'smb'
                END
        END AS segment
    FROM accounts a
    JOIN tenant_profile tp ON tp.customer_id = a.customer_id
    WHERE a.account_status NOT IN ('cancelled', 'inactive')
),

-- ----------------------------------------------------------------------------
-- 3. Calendar-month spine (unchanged from v1)
-- ----------------------------------------------------------------------------
account_month_range AS (
    SELECT
        am.account_id,
        DATE_TRUNC('month', MIN(hs.measurement_month))::date AS first_month,
        DATE_TRUNC('month', MAX(hs.measurement_month))::date AS last_month
    FROM account_meta am
    JOIN health_scores hs ON hs.account_id = am.account_id
    GROUP BY am.account_id
),
panel_skeleton AS (
    SELECT
        am.account_id,
        am.customer_id,
        am.saas_profile,
        am.segment,
        am.arr_current,
        am.arc_type,
        am.renewal_date,
        gs.month_start::date AS month
    FROM account_meta am
    JOIN account_month_range amr ON amr.account_id = am.account_id
    CROSS JOIN LATERAL generate_series(
        amr.first_month,
        amr.last_month,
        interval '1 month'
    ) AS gs(month_start)
),

-- ----------------------------------------------------------------------------
-- 4. NEW: outcome deltas per (account, event_month). Sums revenue_impact
--    across all OUTCOME nodes whose revenue_impact_type lands in the
--    definitive lifecycle subtypes. NULL revenue_impact rows are excluded
--    so a malformed event can't poison the cumulative sum.
-- ----------------------------------------------------------------------------
account_outcome_deltas AS (
    SELECT
        cn.account_id,
        DATE_TRUNC('month', cn.occurred_at)::date AS event_month,
        SUM(cn.revenue_impact) AS month_arr_delta
    FROM context_nodes cn
    WHERE cn.node_type = 'OUTCOME'
      AND cn.account_id IN (SELECT account_id FROM account_meta)
      AND cn.revenue_impact IS NOT NULL
      AND cn.revenue_impact_type IN (
          'expansion_closed', 'new_logo', 'contraction', 'churn_lost'
      )
    GROUP BY cn.account_id, DATE_TRUNC('month', cn.occurred_at)::date
),

-- ----------------------------------------------------------------------------
-- 5. NEW: time-varying arr_at_month per (account, month).
--    arr_at_month(T) = arr_current − SUM(month_arr_delta WHERE event_month >= T)
--    i.e., subtract everything that hasn't happened yet from T's perspective.
-- ----------------------------------------------------------------------------
account_arr_by_month AS (
    SELECT
        ps.account_id,
        ps.month,
        ps.arr_current
          - COALESCE((
                SELECT SUM(d.month_arr_delta)
                FROM account_outcome_deltas d
                WHERE d.account_id = ps.account_id
                  AND d.event_month >= ps.month
            ), 0) AS arr_at_month
    FROM panel_skeleton ps
),

-- ----------------------------------------------------------------------------
-- 6. Health joined per (account, month) — unchanged from v1
-- ----------------------------------------------------------------------------
health_panel AS (
    SELECT
        ps.*,
        ab.arr_at_month AS arr,
        hs.health_score AS health,
        LAG(hs.health_score, 1) OVER (
            PARTITION BY ps.account_id ORDER BY ps.month
        ) AS h_lag1,
        LAG(hs.health_score, 3) OVER (
            PARTITION BY ps.account_id ORDER BY ps.month
        ) AS h_lag3,
        STDDEV_SAMP(hs.health_score) OVER (
            PARTITION BY ps.account_id
            ORDER BY ps.month
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS volatility_3mo
    FROM panel_skeleton ps
    JOIN account_arr_by_month ab
      ON ab.account_id = ps.account_id AND ab.month = ps.month
    LEFT JOIN health_scores hs
      ON hs.account_id = ps.account_id
     AND DATE_TRUNC('month', hs.measurement_month)::date = ps.month
),

-- ----------------------------------------------------------------------------
-- 7. Outcome event flags + signed revenue impact per (account, month).
--    Adds two SUM columns over revenue_impact split by event type so the
--    panel can emit fractional event sizes (expansion_size_pct,
--    contraction_size_pct) which the glmm.py size sub-models consume.
--    Expansion impacts are sign-positive in context_nodes; contraction
--    impacts are sign-negative — we ABS the contraction sum so
--    contraction_size_pct is a positive magnitude (matching the
--    expansion_size_pct convention).
-- ----------------------------------------------------------------------------
outcome_panel AS (
    SELECT
        cn.account_id,
        DATE_TRUNC('month', cn.occurred_at)::date AS month,
        BOOL_OR(cn.revenue_impact_type = 'churn_lost')          AS is_churn_event,
        BOOL_OR(cn.revenue_impact_type = 'contraction')         AS is_contraction_event,
        BOOL_OR(cn.revenue_impact_type IN ('expansion_closed', 'new_logo')) AS is_expansion_event,
        SUM(CASE
                WHEN cn.revenue_impact_type IN ('expansion_closed', 'new_logo')
                THEN cn.revenue_impact ELSE 0
            END) AS expansion_revenue_impact,
        ABS(SUM(CASE
                WHEN cn.revenue_impact_type = 'contraction'
                THEN cn.revenue_impact ELSE 0
            END)) AS contraction_revenue_impact
    FROM context_nodes cn
    WHERE cn.node_type = 'OUTCOME'
      AND cn.account_id IN (SELECT account_id FROM account_meta)
    GROUP BY cn.account_id, DATE_TRUNC('month', cn.occurred_at)::date
),

-- ----------------------------------------------------------------------------
-- 8. Final panel — arr_band now derived per-row from time-varying arr
-- ----------------------------------------------------------------------------
panel_final AS (
    SELECT
        hp.account_id,
        hp.customer_id AS tenant_id,
        hp.saas_profile,
        hp.segment,
        CASE
            WHEN hp.arr >= 10000000 THEN '10M+'
            WHEN hp.arr >= 1000000  THEN '1M-10M'
            WHEN hp.arr >= 100000   THEN '100K-1M'
            WHEN hp.arr >= 10000    THEN '10K-100K'
            ELSE '<10K'
        END AS arr_band,
        hp.month,
        ROW_NUMBER() OVER (
            PARTITION BY hp.account_id ORDER BY hp.month
        ) - 1 AS month_idx,
        ROW_NUMBER() OVER (
            PARTITION BY hp.account_id ORDER BY hp.month
        ) - 1 AS tenure_in_panel,
        ROUND(hp.health::numeric, 2) AS health,
        ROUND((hp.health - hp.h_lag1)::numeric, 2) AS health_slope_1mo,
        CASE
            WHEN hp.h_lag3 IS NOT NULL
                THEN ROUND(((hp.health - hp.h_lag3) / 3.0)::numeric, 2)
            ELSE NULL
        END AS health_slope_3mo,
        ROUND(hp.volatility_3mo::numeric, 3) AS volatility_3mo,
        hp.arc_type,
        (hp.renewal_date - hp.month)::int AS days_to_renewal,
        CASE
            WHEN (hp.renewal_date - hp.month) IS NULL  THEN 'unknown'
            WHEN (hp.renewal_date - hp.month) <= 30    THEN '0-30'
            WHEN (hp.renewal_date - hp.month) <= 90    THEN '31-90'
            WHEN (hp.renewal_date - hp.month) <= 180   THEN '91-180'
            WHEN (hp.renewal_date - hp.month) <= 365   THEN '181-365'
            ELSE '>365'
        END AS days_to_renewal_band,
        COALESCE(op.is_churn_event,       FALSE) AS is_churn_event,
        COALESCE(op.is_contraction_event, FALSE) AS is_contraction_event,
        COALESCE(op.is_expansion_event,   FALSE) AS is_expansion_event,
        -- Fractional event sizes — NULL on non-event rows so glmm size
        -- sub-models can dropna() to the event-only fit panel. arr here
        -- is start-of-month (pre-event) under v2 convention, so the
        -- denominator matches "fraction of pre-event ARR added (or lost)."
        CASE
            WHEN COALESCE(op.is_expansion_event, FALSE)
                 AND hp.arr > 0
                 AND op.expansion_revenue_impact IS NOT NULL
            THEN ROUND((op.expansion_revenue_impact / hp.arr)::numeric, 6)
            ELSE NULL
        END AS expansion_size_pct,
        CASE
            WHEN COALESCE(op.is_contraction_event, FALSE)
                 AND hp.arr > 0
                 AND op.contraction_revenue_impact IS NOT NULL
            THEN ROUND((op.contraction_revenue_impact / hp.arr)::numeric, 6)
            ELSE NULL
        END AS contraction_size_pct,
        hp.arr
    FROM health_panel hp
    LEFT JOIN outcome_panel op
      ON op.account_id = hp.account_id
     AND op.month = hp.month
    WHERE hp.health IS NOT NULL
)

SELECT * FROM panel_final
ORDER BY tenant_id, account_id, month;
