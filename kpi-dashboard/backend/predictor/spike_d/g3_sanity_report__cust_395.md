# G3 — Sanity Report — Customer 395

*Generated 2026-05-07 15:18 UTC.*

Per PLAN_nrr_predictor_v3.md G3, reviewer gut-checks the 5 named 
accounts below for directional correctness. Pass = 5/5 directionally 
right. Fail on any account → diagnose feature / segment / arc misspec, 
fix, re-run; **never "ship anyway."**

## Step 1 — Trigger Wizard D (calibration pass)

- run_id: `wizard_d_63148edc10dd`
- status: **completed**
- sub_models_calibrated: 4
- fits_by_status: `{'converged': 3, 'insufficient_events': 1}`
- panel_summary: `{'n_rows': 500, 'n_accounts': 30, 'n_tenants': 1, 'tenant_ids': [395]}`
- duration_seconds: 31.176631

## Step 2 — Predictions for named accounts

## Antares Holdings

- ARR: $20,625,000
- arc_type: `expansion_champion`

### Antares Holdings (account_id=3906)

- **Horizon:** renewal (8 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_63148edc10dd__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-07T15:18:54.777581

**Expected NRR:** 1.006 (90% CI: 0.956 – 1.056)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.002 |
| `p_survive_at_horizon` | 0.998 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.026 |

**Top NRR drivers:**

- `health` → -12.4724
- `log_arr` → +8.7702
- `dtr_181-365` → +0.7729

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.338
- `expected_size_pct_given_event` = 0.077
- `expected_arr_lift` = $537,453 (CI: $268,727 – $806,180)
- `horizon_to_likely_event_months` = 20

**Top expansion drivers:**

- `health` → +10.7719
- `arc_expansion_champion` → +0.2323
- `arr_10M+` → +0.1288

### Antares Holdings (account_id=3906)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_63148edc10dd__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-07T15:18:54.777581

**Expected NRR:** 1.015 (90% CI: 0.965 – 1.065)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.003 |
| `p_survive_at_horizon` | 0.997 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.036 |

**Top NRR drivers:**

- `health` → -12.4724
- `log_arr` → +8.7702
- `dtr_181-365` → +0.7729

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.464
- `expected_size_pct_given_event` = 0.077
- `expected_arr_lift` = $737,607 (CI: $368,803 – $1,106,410)
- `horizon_to_likely_event_months` = 20

**Top expansion drivers:**

- `health` → +10.7719
- `arc_expansion_champion` → +0.2323
- `arr_10M+` → +0.1288

## Cassiopeia Insurance

- ARR: $0
- arc_type: `crisis_recovery`

### Cassiopeia Insurance (account_id=3915)

- **Horizon:** renewal (8 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_63148edc10dd__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-07T15:18:54.777581

**Expected NRR:** 0.561 (90% CI: 0.511 – 0.611)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.429 |
| `p_survive_at_horizon` | 0.571 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.000 |

**Top NRR drivers:**

- `log_arr` → +8.4522
- `health` → -6.5579
- `dtr_181-365` → +0.7729

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.003
- `expected_size_pct_given_event` = 0.000
- `expected_arr_lift` = $15 (CI: $8 – $23)
- `horizon_to_likely_event_months` = 2474

**Top expansion drivers:**

- `health` → +5.6638
- `arr_10M+` → +0.1288
- `health_slope_3mo` → +0.0843

### Cassiopeia Insurance (account_id=3915)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_63148edc10dd__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-07T15:18:54.777581

**Expected NRR:** 0.431 (90% CI: 0.381 – 0.481)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.562 |
| `p_survive_at_horizon` | 0.438 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.000 |

**Top NRR drivers:**

- `log_arr` → +8.4522
- `health` → -6.5579
- `dtr_181-365` → +0.7729

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.005
- `expected_size_pct_given_event` = 0.000
- `expected_arr_lift` = $23 (CI: $12 – $35)
- `horizon_to_likely_event_months` = 2429

**Top expansion drivers:**

- `health` → +5.6638
- `arr_10M+` → +0.1288
- `health_slope_3mo` → +0.0843

## Lyra Media

- ARR: $0
- arc_type: `crisis_recovery`

### Lyra Media (account_id=3918)

- **Horizon:** renewal (11 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_63148edc10dd__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-07T15:18:54.777581

**Expected NRR:** 0.201 (90% CI: 0.151 – 0.251)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.795 |
| `p_survive_at_horizon` | 0.205 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.000 |

**Top NRR drivers:**

- `log_arr` → +8.1358
- `health` → -5.4810
- `dtr_181-365` → +0.7729

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.002
- `expected_size_pct_given_event` = 0.000
- `expected_arr_lift` = $6 (CI: $3 – $9)
- `horizon_to_likely_event_months` = 4807

**Top expansion drivers:**

- `health` → +4.7337
- `health_slope_3mo` → +0.0763
- `health_slope_1mo` → +0.0188

### Lyra Media (account_id=3918)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_63148edc10dd__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-07T15:18:54.777581

**Expected NRR:** 0.176 (90% CI: 0.126 – 0.226)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.821 |
| `p_survive_at_horizon` | 0.179 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.000 |

**Top NRR drivers:**

- `log_arr` → +8.1358
- `health` → -5.4810
- `dtr_181-365` → +0.7729

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.003
- `expected_size_pct_given_event` = 0.000
- `expected_arr_lift` = $7 (CI: $3 – $10)
- `horizon_to_likely_event_months` = 4790

**Top expansion drivers:**

- `health` → +4.7337
- `health_slope_3mo` → +0.0763
- `health_slope_1mo` → +0.0188

## Deneb Pharma

- ARR: $8,900,000
- arc_type: `seasonal_surge`

### Deneb Pharma (account_id=3912)

- **Horizon:** renewal (8 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_63148edc10dd__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-07T15:18:54.777581

**Expected NRR:** 0.980 (90% CI: 0.930 – 1.030)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.003 |
| `p_survive_at_horizon` | 0.997 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.000 |

**Top NRR drivers:**

- `health` → -9.7509
- `log_arr` → +8.3326
- `volatility_3mo` → -0.9413

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.183
- `expected_size_pct_given_event` = 0.002
- `expected_arr_lift` = $2,946 (CI: $1,473 – $4,418)
- `horizon_to_likely_event_months` = 40

**Top expansion drivers:**

- `health` → +8.4214
- `health_slope_3mo` → +1.2000

### Deneb Pharma (account_id=3912)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_63148edc10dd__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-07T15:18:54.777581

**Expected NRR:** 0.979 (90% CI: 0.929 – 1.029)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.003 |
| `p_survive_at_horizon` | 0.997 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.001 |

**Top NRR drivers:**

- `health` → -9.7509
- `log_arr` → +8.3326
- `volatility_3mo` → -0.9413

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.331
- `expected_size_pct_given_event` = 0.002
- `expected_arr_lift` = $5,310 (CI: $2,655 – $7,965)
- `horizon_to_likely_event_months` = 30

**Top expansion drivers:**

- `health` → +8.4214
- `health_slope_3mo` → +1.2000

## Polaris Cloud

- ARR: $20,160,000
- arc_type: `expansion_champion`

### Polaris Cloud (account_id=3894)

- **Horizon:** renewal (8 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_63148edc10dd__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-07T15:18:54.777581

**Expected NRR:** 1.004 (90% CI: 0.954 – 1.054)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.002 |
| `p_survive_at_horizon` | 0.998 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.025 |

**Top NRR drivers:**

- `health` → -12.3708
- `log_arr` → +8.7583
- `dtr_181-365` → +0.7729

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.324
- `expected_size_pct_given_event` = 0.076
- `expected_arr_lift` = $496,192 (CI: $248,096 – $744,288)
- `horizon_to_likely_event_months` = 21

**Top expansion drivers:**

- `health` → +10.6842
- `arc_expansion_champion` → +0.2323
- `arr_10M+` → +0.1288

### Polaris Cloud (account_id=3894)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_63148edc10dd__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-07T15:18:54.777581

**Expected NRR:** 1.013 (90% CI: 0.963 – 1.063)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.003 |
| `p_survive_at_horizon` | 0.997 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.034 |

**Top NRR drivers:**

- `health` → -12.3708
- `log_arr` → +8.7583
- `dtr_181-365` → +0.7729

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.446
- `expected_size_pct_given_event` = 0.076
- `expected_arr_lift` = $683,233 (CI: $341,616 – $1,024,849)
- `horizon_to_likely_event_months` = 21

**Top expansion drivers:**

- `health` → +10.6842
- `arc_expansion_champion` → +0.2323
- `arr_10M+` → +0.1288

---

## Reviewer Checklist (5/5 required to pass G3)

- [ ] Antares Holdings — predicted NRR + decomposition direction matches gut?
- [ ] Cassiopeia Insurance — predicted NRR + decomposition direction matches gut?
- [ ] Lyra Media — predicted NRR + decomposition direction matches gut?
- [ ] Deneb Pharma — predicted NRR + decomposition direction matches gut?
- [ ] Polaris Cloud — predicted NRR + decomposition direction matches gut?

*Generated by `predictor/scripts/g3_sanity_report.py`.*