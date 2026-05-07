-- ============================================================================
-- NRR Predictor v3 — Block 1 — Panel Construction
-- ----------------------------------------------------------------------------
-- Produces one row per (account, month) for every month the account is at
-- risk for an event. At risk = active and not yet churned, censored at last
-- observed month.
--
-- Inputs:
--   :target_customer_ids — array of customer_ids to include
--                          (e.g. ARRAY[393, <new_customer_id>])
--
-- Outputs columns (matches design notes Part 2 panel structure):
--   account_id, tenant_id, saas_profile, segment, arr_band,
--   month, month_idx, tenure_in_panel,
--   health, health_slope_1mo, health_slope_3mo, volatility_3mo,
--   arc_type, days_to_renewal, days_to_renewal_band,
--   is_churn_event, is_contraction_event, is_expansion_event,
--   arr
--
-- Per Architecture Decision A5 in PLAN_nrr_predictor_v3.md:
--   - saas_profile auto-detected per tenant via median ARR
--   - Segment thresholds vary by profile
--
-- Phase 1 scope: vertical='saas_premium' only.
-- ============================================================================

WITH
-- ----------------------------------------------------------------------------
-- 1. Auto-detect saas_profile per tenant (A5)
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
-- 2. Per-account metadata, with profile-aware segment classification
-- ----------------------------------------------------------------------------
account_meta AS (
    SELECT
        a.account_id,
        a.customer_id,
        a.account_name,
        a.revenue AS arr,
        a.arc_type,
        DATE(a.profile_metadata->>'renewal_date') AS renewal_date,
        tp.saas_profile,
        CASE
            WHEN tp.saas_profile = 'saas_enterprise' THEN
                CASE
                    WHEN a.revenue >= 50000000 THEN 'strategic'
                    WHEN a.revenue >= 5000000  THEN 'enterprise'
                    WHEN a.revenue >= 250000   THEN 'mid_market'
                    ELSE 'below_floor'  -- A5 escape hatch; flagged at G1.5
                END
            WHEN tp.saas_profile = 'saas_smb' THEN
                CASE
                    WHEN a.revenue >= 250000 THEN 'enterprise'
                    WHEN a.revenue >= 25000  THEN 'mid_market'
                    ELSE 'smb'
                END
        END AS segment,
        CASE
            WHEN a.revenue >= 10000000 THEN '10M+'
            WHEN a.revenue >= 1000000  THEN '1M-10M'
            WHEN a.revenue >= 100000   THEN '100K-1M'
            WHEN a.revenue >= 10000    THEN '10K-100K'
            ELSE '<10K'
        END AS arr_band
    FROM accounts a
    JOIN tenant_profile tp ON tp.customer_id = a.customer_id
    WHERE a.account_status NOT IN ('cancelled', 'inactive')
),

-- ----------------------------------------------------------------------------
-- 3. Calendar-month spine, anchored to per-account observed range
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
        am.arr,
        am.arr_band,
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
-- 4. Health joined per (account, month), with lag/lead for slope/volatility
-- ----------------------------------------------------------------------------
health_panel AS (
    SELECT
        ps.*,
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
    LEFT JOIN health_scores hs
      ON hs.account_id = ps.account_id
     AND DATE_TRUNC('month', hs.measurement_month)::date = ps.month
),

-- ----------------------------------------------------------------------------
-- 5. Outcome events per (account, month)
--    Definitive lifecycle subtypes only (per design notes Q3, taxonomy_base.json):
--      churn_lost / contraction / expansion_closed / new_logo
--    Narrative outcomes (revenue_protected, churn_averted, etc.) excluded.
-- ----------------------------------------------------------------------------
outcome_panel AS (
    SELECT
        cn.account_id,
        DATE_TRUNC('month', cn.occurred_at)::date AS month,
        BOOL_OR(cn.revenue_impact_type = 'churn_lost')          AS is_churn_event,
        BOOL_OR(cn.revenue_impact_type = 'contraction')         AS is_contraction_event,
        BOOL_OR(cn.revenue_impact_type IN ('expansion_closed', 'new_logo')) AS is_expansion_event
    FROM context_nodes cn
    WHERE cn.node_type = 'OUTCOME'
      AND cn.account_id IN (SELECT account_id FROM account_meta)
    GROUP BY cn.account_id, DATE_TRUNC('month', cn.occurred_at)::date
),

-- ----------------------------------------------------------------------------
-- 6. Final panel — joins, derived covariates, censoring
-- ----------------------------------------------------------------------------
panel_final AS (
    SELECT
        hp.account_id,
        hp.customer_id AS tenant_id,
        hp.saas_profile,
        hp.segment,
        hp.arr_band,
        hp.month,
        ROW_NUMBER() OVER (
            PARTITION BY hp.account_id ORDER BY hp.month
        ) - 1 AS month_idx,
        ROW_NUMBER() OVER (
            PARTITION BY hp.account_id ORDER BY hp.month
        ) - 1 AS tenure_in_panel,  -- left-truncation handler
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
        hp.arr
    FROM health_panel hp
    LEFT JOIN outcome_panel op
      ON op.account_id = hp.account_id
     AND op.month = hp.month
    WHERE hp.health IS NOT NULL  -- drop synthetic months with no health observation
)

SELECT * FROM panel_final
ORDER BY tenant_id, account_id, month;
