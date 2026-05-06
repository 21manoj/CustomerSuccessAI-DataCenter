# G3 — Sanity Report — Customer 395

*Generated 2026-05-06 20:36 UTC.*

Per PLAN_nrr_predictor_v3.md G3, reviewer gut-checks the 5 named 
accounts below for directional correctness. Pass = 5/5 directionally 
right. Fail on any account → diagnose feature / segment / arc misspec, 
fix, re-run; **never "ship anyway."**

## Step 1 — Trigger Wizard D (calibration pass)

- run_id: `wizard_d_b3693a2c9322`
- status: **completed**
- sub_models_calibrated: 4
- fits_by_status: `{'converged': 2, 'insufficient_events': 2}`
- panel_summary: `{'n_rows': 500, 'n_accounts': 30, 'n_tenants': 1, 'tenant_ids': [395]}`
- duration_seconds: 21.717212

## Step 2 — Predictions for named accounts

## Antares Holdings

- ARR: $20,625,000
- arc_type: `expansion_champion`

### Antares Holdings (account_id=3906)

- **Horizon:** renewal (8 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_b3693a2c9322__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-06T20:36:53.037752

**Expected NRR:** 1.009 (90% CI: 0.959 – 1.059)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.001 |
| `p_survive_at_horizon` | 0.999 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.028 |

**Top NRR drivers:**

- `health` → -11.0468
- `tenure_in_panel` → +10.8721
- `log_arr` → -4.2688

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.155
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $577,033 (CI: $288,517 – $865,550)
- `horizon_to_likely_event_months` = 48

**Top expansion drivers:**

- `health` → +1.3171
- `arc_expansion_champion` → +0.5558
- `arr_10M+` → +0.1517

### Antares Holdings (account_id=3906)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_b3693a2c9322__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-06T20:36:53.037752

**Expected NRR:** 1.021 (90% CI: 0.971 – 1.071)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.001 |
| `p_survive_at_horizon` | 0.999 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.040 |

**Top NRR drivers:**

- `health` → -11.0468
- `tenure_in_panel` → +10.8721
- `log_arr` → -4.2688

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.224
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $831,667 (CI: $415,834 – $1,247,501)
- `horizon_to_likely_event_months` = 48

**Top expansion drivers:**

- `health` → +1.3171
- `arc_expansion_champion` → +0.5558
- `arr_10M+` → +0.1517

## Cassiopeia Insurance

- ARR: $0
- arc_type: `crisis_recovery`

### Cassiopeia Insurance (account_id=3915)

- **Horizon:** renewal (8 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_b3693a2c9322__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-06T20:36:53.037752

**Expected NRR:** 0.003 (90% CI: 0.000 – 0.053)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.997 |
| `p_survive_at_horizon` | 0.003 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.010 |

**Top NRR drivers:**

- `tenure_in_panel` → +10.8721
- `health` → -5.8084
- `dtr_181-365` → +0.1606

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.055
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $0 (CI: $0 – $0)
- `horizon_to_likely_event_months` = 143

**Top expansion drivers:**

- `health` → +0.6925
- `health_slope_3mo` → +0.0743

### Cassiopeia Insurance (account_id=3915)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_b3693a2c9322__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-06T20:36:53.037752

**Expected NRR:** 0.000 (90% CI: 0.000 – 0.050)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 1.000 |
| `p_survive_at_horizon` | 0.000 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.015 |

**Top NRR drivers:**

- `tenure_in_panel` → +10.8721
- `health` → -5.8084
- `dtr_181-365` → +0.1606

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.081
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $0 (CI: $0 – $0)
- `horizon_to_likely_event_months` = 142

**Top expansion drivers:**

- `health` → +0.6925
- `health_slope_3mo` → +0.0743

## Lyra Media

- ARR: $0
- arc_type: `crisis_recovery`

### Lyra Media (account_id=3918)

- **Horizon:** renewal (11 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_b3693a2c9322__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-06T20:36:53.037752

**Expected NRR:** 0.037 (90% CI: 0.000 – 0.087)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.963 |
| `p_survive_at_horizon` | 0.037 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.022 |

**Top NRR drivers:**

- `tenure_in_panel` → +8.8336
- `health` → -4.8545
- `dtr_181-365` → +0.1606

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.121
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $0 (CI: $0 – $0)
- `horizon_to_likely_event_months` = 86

**Top expansion drivers:**

- `health` → +0.5788
- `health_slope_3mo` → +0.0672
- `health_slope_1mo` → +0.0110

### Lyra Media (account_id=3918)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_b3693a2c9322__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-06T20:36:53.037752

**Expected NRR:** 0.028 (90% CI: 0.000 – 0.078)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.972 |
| `p_survive_at_horizon` | 0.028 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.024 |

**Top NRR drivers:**

- `tenure_in_panel` → +8.8336
- `health` → -4.8545
- `dtr_181-365` → +0.1606

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.131
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $0 (CI: $0 – $0)
- `horizon_to_likely_event_months` = 86

**Top expansion drivers:**

- `health` → +0.5788
- `health_slope_3mo` → +0.0672
- `health_slope_1mo` → +0.0110

## Deneb Pharma

- ARR: $8,900,000
- arc_type: `seasonal_surge`

### Deneb Pharma (account_id=3912)

- **Horizon:** renewal (8 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_b3693a2c9322__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-06T20:36:53.037752

**Expected NRR:** 0.990 (90% CI: 0.940 – 1.040)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.003 |
| `p_survive_at_horizon` | 0.997 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.011 |

**Top NRR drivers:**

- `tenure_in_panel` → +10.8721
- `health` → -8.6363
- `log_arr` → -4.0558

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.062
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $98,601 (CI: $49,301 – $147,902)
- `horizon_to_likely_event_months` = 126

**Top expansion drivers:**

- `health_slope_3mo` → +1.0583
- `health` → +1.0297

### Deneb Pharma (account_id=3912)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_b3693a2c9322__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-06T20:36:53.037752

**Expected NRR:** 0.996 (90% CI: 0.946 – 1.046)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.003 |
| `p_survive_at_horizon` | 0.997 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.017 |

**Top NRR drivers:**

- `tenure_in_panel` → +10.8721
- `health` → -8.6363
- `log_arr` → -4.0558

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.094
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $150,081 (CI: $75,040 – $225,121)
- `horizon_to_likely_event_months` = 122

**Top expansion drivers:**

- `health_slope_3mo` → +1.0583
- `health` → +1.0297

## Polaris Cloud

- ARR: $20,160,000
- arc_type: `expansion_champion`

### Polaris Cloud (account_id=3894)

- **Horizon:** renewal (8 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_b3693a2c9322__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-06T20:36:53.037752

**Expected NRR:** 1.011 (90% CI: 0.961 – 1.061)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.001 |
| `p_survive_at_horizon` | 0.999 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.030 |

**Top NRR drivers:**

- `health` → -10.9568
- `tenure_in_panel` → +10.8721
- `log_arr` → -4.2631

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.166
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $602,447 (CI: $301,224 – $903,671)
- `horizon_to_likely_event_months` = 45

**Top expansion drivers:**

- `health` → +1.3064
- `arc_expansion_champion` → +0.5558
- `arr_10M+` → +0.1517

### Polaris Cloud (account_id=3894)

- **Horizon:** 12mo (12 months)
- **Prediction method:** `calibrated`
- **Calibration:** `wizard_d_b3693a2c9322__saas_enterprise__hazard`
- **Calibrated at:** 2026-05-06T20:36:53.037752

**Expected NRR:** 1.024 (90% CI: 0.974 – 1.074)

**Term decomposition:**

| Term | Value |
|---|---|
| `p_churn_at_horizon` | 0.001 |
| `p_survive_at_horizon` | 0.999 |
| `e_contract_pct_given_survive` | 0.018 |
| `e_expand_pct_given_survive` | 0.043 |

**Top NRR drivers:**

- `health` → -10.9568
- `tenure_in_panel` → +10.8721
- `log_arr` → -4.2631

**A6 expansion outlook:**

- `p_expansion_event_horizon` = 0.239
- `expected_size_pct_given_event` = 0.180
- `expected_arr_lift` = $865,596 (CI: $432,798 – $1,298,394)
- `horizon_to_likely_event_months` = 45

**Top expansion drivers:**

- `health` → +1.3064
- `arc_expansion_champion` → +0.5558
- `arr_10M+` → +0.1517

---

## Reviewer Checklist (5/5 required to pass G3)

- [ ] Antares Holdings — predicted NRR + decomposition direction matches gut?
- [ ] Cassiopeia Insurance — predicted NRR + decomposition direction matches gut?
- [ ] Lyra Media — predicted NRR + decomposition direction matches gut?
- [ ] Deneb Pharma — predicted NRR + decomposition direction matches gut?
- [ ] Polaris Cloud — predicted NRR + decomposition direction matches gut?

*Generated by `predictor/scripts/g3_sanity_report.py`.*