# G3 — Sanity Report — Customer 393

*Generated 2026-05-06 20:00 UTC.*

Per PLAN_nrr_predictor_v3.md G3, reviewer gut-checks the 5 named 
accounts below for directional correctness. Pass = 5/5 directionally 
right. Fail on any account → diagnose feature / segment / arc misspec, 
fix, re-run; **never "ship anyway."**

## Step 1 — Trigger Wizard D (calibration pass)

- run_id: `wizard_d_7e4c6470e359`
- status: **completed**
- sub_models_calibrated: 4
- fits_by_status: `{'insufficient_events': 4}`
- panel_summary: `{'n_rows': 90, 'n_accounts': 30, 'n_tenants': 1, 'tenant_ids': [393]}`
- duration_seconds: 0.184704

## Step 2 — Predictions for named accounts

## Zermatt Analytics

- ARR: $17,250,000
- arc_type: `competitive_displacement`

### Zermatt Analytics (account_id=3834)

- **Horizon:** renewal (4 months)
- **Prediction method:** `cold_start`
- **Calibration:** `cdi_seed__saas_enterprise__hazard`
- **Calibrated at:** (CDI seed only — no tenant fit yet)

**Expected NRR:** 0.990 (90% CI: 0.890 – 1.090)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.024 |
| `p_survive_at_horizon` | 0.976 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.033 |

**Top NRR drivers:**


**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.181
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $561,058 (CI: $280,529 – $841,587)
- `horizon_to_likely_event_months` = 21

**Top expansion drivers:**

- (none — all expansion-positive coefficients are zero or absent)

### Zermatt Analytics (account_id=3834)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `cold_start`
- **Calibration:** `cdi_seed__saas_enterprise__hazard`
- **Calibrated at:** (CDI seed only — no tenant fit yet)

**Expected NRR:** 0.989 (90% CI: 0.889 – 1.089)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.070 |
| `p_survive_at_horizon` | 0.930 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.081 |

**Top NRR drivers:**


**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.450
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $1,397,297 (CI: $698,649 – $2,095,946)
- `horizon_to_likely_event_months` = 21

**Top expansion drivers:**

- (none — all expansion-positive coefficients are zero or absent)

## Bernina Health Systems

- ARR: $10,500,000
- arc_type: `competitive_displacement`

### Bernina Health Systems (account_id=3838)

- **Horizon:** renewal (6 months)
- **Prediction method:** `cold_start`
- **Calibration:** `cdi_seed__saas_enterprise__hazard`
- **Calibrated at:** (CDI seed only — no tenant fit yet)

**Expected NRR:** 0.992 (90% CI: 0.892 – 1.092)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.036 |
| `p_survive_at_horizon` | 0.964 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.047 |

**Top NRR drivers:**


**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.258
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $488,375 (CI: $244,188 – $732,563)
- `horizon_to_likely_event_months` = 21

**Top expansion drivers:**

- (none — all expansion-positive coefficients are zero or absent)

### Bernina Health Systems (account_id=3838)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `cold_start`
- **Calibration:** `cdi_seed__saas_enterprise__hazard`
- **Calibrated at:** (CDI seed only — no tenant fit yet)

**Expected NRR:** 0.989 (90% CI: 0.889 – 1.089)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.070 |
| `p_survive_at_horizon` | 0.930 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.081 |

**Top NRR drivers:**


**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.450
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $850,529 (CI: $425,264 – $1,275,793)
- `horizon_to_likely_event_months` = 21

**Top expansion drivers:**

- (none — all expansion-positive coefficients are zero or absent)

## Pilatus Enterprise

- ARR: $9,750,000
- arc_type: `expansion_champion`

### Pilatus Enterprise (account_id=3839)

- **Horizon:** renewal (8 months)
- **Prediction method:** `cold_start`
- **Calibration:** `cdi_seed__saas_enterprise__hazard`
- **Calibrated at:** (CDI seed only — no tenant fit yet)

**Expected NRR:** 0.992 (90% CI: 0.892 – 1.092)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.047 |
| `p_survive_at_horizon` | 0.953 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.059 |

**Top NRR drivers:**


**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.329
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $576,926 (CI: $288,463 – $865,389)
- `horizon_to_likely_event_months` = 21

**Top expansion drivers:**

- (none — all expansion-positive coefficients are zero or absent)

### Pilatus Enterprise (account_id=3839)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `cold_start`
- **Calibration:** `cdi_seed__saas_enterprise__hazard`
- **Calibrated at:** (CDI seed only — no tenant fit yet)

**Expected NRR:** 0.989 (90% CI: 0.889 – 1.089)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.070 |
| `p_survive_at_horizon` | 0.930 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.081 |

**Top NRR drivers:**


**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.450
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $789,777 (CI: $394,888 – $1,184,665)
- `horizon_to_likely_event_months` = 21

**Top expansion drivers:**

- (none — all expansion-positive coefficients are zero or absent)

## Matterhorn Digital

- ARR: $13,200,000
- arc_type: `land_and_expand`

### Matterhorn Digital (account_id=3837)

- **Horizon:** renewal (6 months)
- **Prediction method:** `cold_start`
- **Calibration:** `cdi_seed__saas_enterprise__hazard`
- **Calibrated at:** (CDI seed only — no tenant fit yet)

**Expected NRR:** 0.992 (90% CI: 0.892 – 1.092)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.036 |
| `p_survive_at_horizon` | 0.964 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.047 |

**Top NRR drivers:**


**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.258
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $613,957 (CI: $306,979 – $920,936)
- `horizon_to_likely_event_months` = 21

**Top expansion drivers:**

- (none — all expansion-positive coefficients are zero or absent)

### Matterhorn Digital (account_id=3837)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `cold_start`
- **Calibration:** `cdi_seed__saas_enterprise__hazard`
- **Calibrated at:** (CDI seed only — no tenant fit yet)

**Expected NRR:** 0.989 (90% CI: 0.889 – 1.089)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.070 |
| `p_survive_at_horizon` | 0.930 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.081 |

**Top NRR drivers:**


**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.450
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $1,069,236 (CI: $534,618 – $1,603,855)
- `horizon_to_likely_event_months` = 21

**Top expansion drivers:**

- (none — all expansion-positive coefficients are zero or absent)

## Denali Cloud Platform

- ARR: $5,557,707
- arc_type: `competitive_displacement`

### Denali Cloud Platform (account_id=3854)

- **Horizon:** renewal (7 months)
- **Prediction method:** `cold_start`
- **Calibration:** `cdi_seed__saas_enterprise__hazard`
- **Calibrated at:** (CDI seed only — no tenant fit yet)

**Expected NRR:** 0.992 (90% CI: 0.892 – 1.092)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.041 |
| `p_survive_at_horizon` | 0.959 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.053 |

**Top NRR drivers:**


**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.295
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $294,556 (CI: $147,278 – $441,834)
- `horizon_to_likely_event_months` = 21

**Top expansion drivers:**

- (none — all expansion-positive coefficients are zero or absent)

### Denali Cloud Platform (account_id=3854)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `cold_start`
- **Calibration:** `cdi_seed__saas_enterprise__hazard`
- **Calibrated at:** (CDI seed only — no tenant fit yet)

**Expected NRR:** 0.989 (90% CI: 0.889 – 1.089)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.070 |
| `p_survive_at_horizon` | 0.930 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.081 |

**Top NRR drivers:**


**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.450
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $450,190 (CI: $225,095 – $675,284)
- `horizon_to_likely_event_months` = 21

**Top expansion drivers:**

- (none — all expansion-positive coefficients are zero or absent)

---

## Reviewer Checklist (5/5 required to pass G3)

- [ ] Zermatt Analytics — predicted NRR + decomposition direction matches gut?
- [ ] Bernina Health Systems — predicted NRR + decomposition direction matches gut?
- [ ] Pilatus Enterprise — predicted NRR + decomposition direction matches gut?
- [ ] Matterhorn Digital — predicted NRR + decomposition direction matches gut?
- [ ] Denali Cloud Platform — predicted NRR + decomposition direction matches gut?

*Generated by `predictor/scripts/g3_sanity_report.py`.*