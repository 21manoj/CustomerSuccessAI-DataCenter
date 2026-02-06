# Onboarding Wizard UI Design - Open Questions

## Summary of User Requirements

Based on your answers, here's what we need to implement:

1. **num_months**: Option B - Show "12 months (fixed)" as read-only info
2. **industry**: Use the industry selected by user in onboarding wizard first screen
3. **vertical**: Option B - Show "DC2_S (Data Center)" as read-only (from user selecting "Data Center" vertical)
4. **company_name**: Show as read-only from user input on first/second screen
5. **customer_id**: Show as system-generated, but allow override with validation (check if exists)

---

## Open Questions

### 1. KPI and Pillar Initial Weights

**Context Found:**
- Bootstrap weights are defined in `bootstrap_weights_config.json` files
- Default DC2_S pillar weights (from `onboarding_api.py`):
  - P1_deployment_velocity: 15%
  - P2_operational_stability: 20%
  - P3_ai_workload_performance: 25%
  - P4_channel_partner_health: 15%
  - P5_expansion_readiness: 25%

**Questions:**
1. **Should we show pillar weights in the UI?**
   - Option A: Show as read-only with default DC2_S weights
   - Option B: Allow user to adjust weights (with sliders/sum to 100%)
   - Option C: Hide completely (use defaults automatically)

2. **Should we show KPI weights within pillars?**
   - The bootstrap config has L1 (KPI-level) weights within each pillar
   - Example: P3 has `gpu_utilization_rate: 0.22`, `training_job_completion: 0.20`, etc.
   - Option A: Show top 5 KPIs per pillar with weights
   - Option B: Hide KPI weights (too detailed for onboarding)
   - Option C: Show as advanced/collapsible section

3. **When should weights be applied?**
   - During synthetic data generation? (affects health scores in generated data)
   - After data upload? (affects health score calculation)
   - Both?

4. **Should weights be saved to `CustomerConfig` during onboarding?**
   - Or saved later when customer is created?

---

### 2. Demo Manifest and Preplanned Journeys

**Context Found:**
- `DEMO_MANIFEST.md` includes predefined health scenarios:
  - **improving**: Critical → At-Risk → Healthy (55 → 88)
  - **declining**: Healthy → At-Risk → Critical (90 → 60)
  - **stable_healthy**: Consistently Healthy (88 → 92)
  - **stable_at_risk**: Persistently At-Risk (68 → 72)
  - **volatile**: Unpredictable swings
  - **plateau_breakthrough**: Plateau → Breakthrough (70 → 86)
  - **high_churn_risk**: Critical with declining engagement (58 → 45)
  - **new_onboarding**: Recently onboarded, improving (62 → 82)

- Each scenario has:
  - `name`: Display name
  - `description`: What it represents
  - `start_health` / `end_health`: Health score range
  - `progression`: How health changes over time
  - `use_case`: Demo scenario description

**Questions:**
1. **Are these scenarios the "preplanned journeys" you mentioned?**
   - Or are journeys something different (like Wizard A narrative outputs)?

2. **Should the UI show these scenarios during file generation?**
   - Option A: Show scenario selection (user picks which scenarios to include)
   - Option B: Auto-assign scenarios to accounts (current behavior)
   - Option C: Show scenario distribution after generation (info only)

3. **Should DEMO_MANIFEST.md be shown in the UI?**
   - Option A: Show preview/read-only in wizard
   - Option B: Download only (current behavior)
   - Option C: Show after generation with "View Demo Guide" button

4. **How many accounts per scenario should be generated?**
   - Currently: Cyclically assigned (account 1 = improving, account 2 = declining, etc.)
   - Should user control this distribution?

---

### 3. Wizard A and Wizard B Usage

**Context Found:**
- Wizard A: Journey Generator (creates journey narratives from account data)
- Wizard B: Pattern Analyzer (analyzes patterns in journey data)
- Both are in `backend/verticals/{customer}/journey/wizard_a/` and `wizard_b/`

**Questions:**
1. **When does Wizard A run?**
   - After CSV files are uploaded?
   - After data is loaded into database?
   - Manually triggered by user?
   - Automatically during onboarding completion?

2. **Does Wizard A use the synthetic data we generate?**
   - Does it read from `kpi_measurements.csv`?
   - Does it use health scenarios from DEMO_MANIFEST?
   - Does it use bootstrap weights?

3. **What does Wizard A output?**
   - Journey JSON files per account?
   - Narrative text?
   - Timeline of events?

4. **When does Wizard B run?**
   - After Wizard A completes?
   - On-demand analysis?
   - Scheduled?

5. **What does Wizard B analyze?**
   - Patterns across accounts?
   - Patterns in health trajectories?
   - Patterns in KPI correlations?

6. **Should the onboarding wizard show Wizard A/B status?**
   - Option A: Show "Journey generation pending" status
   - Option B: Trigger Wizard A automatically after data upload
   - Option C: Show as separate step in wizard
   - Option D: Hide completely (happens in background)

7. **Do Wizard A/B results appear in the portal?**
   - In Executive Dashboard?
   - In Journey view?
   - In AI Insights tab?

---

### 4. Customer ID Generation and Validation

**Questions:**
1. **How should system-generated customer_id be determined?**
   - Option A: Next available ID (query database for max customer_id + 1)
   - Option B: Use formula based on timestamp/random
   - Option C: Use account_id_start formula in reverse (if account_id_start = 28000, customer_id = 18)

2. **Where should customer_id validation happen?**
   - Frontend (before API call)?
   - Backend API (during generation)?
   - Both?

3. **What should happen if user overrides with existing ID?**
   - Show error immediately?
   - Suggest next available ID?
   - Allow but warn about overwriting existing customer?

4. **Should account IDs be recalculated if customer_id changes?**
   - If user changes customer_id from 18 to 19, should account IDs change from 28001-28010 to 29001-29010?
   - Or keep original account IDs?

---

### 5. Industry Parameter

**Questions:**
1. **How should industry be used in data generation?**
   - Option A: Filter INDUSTRIES list to only use selected industry
   - Option B: Prefer selected industry but allow some variation
   - Option C: Use selected industry for all accounts (no randomness)

2. **Should industry affect KPI values?**
   - Different industries might have different KPI ranges
   - Example: Healthcare might have different uptime requirements than E-commerce

---

### 6. Company Name Usage

**Questions:**
1. **Should company_name appear in generated data?**
   - In `customers.csv`?
   - In account names?
   - In DEMO_MANIFEST.md?

2. **Should it be used for customer record creation?**
   - When customer is created in database, use this name?

---

### 7. UI Layout and Flow

**Questions:**
1. **Where should these options appear in Step 5?**
   - Above "Generate Sample Files" button?
   - In a collapsible "Advanced Options" section?
   - In a modal dialog when clicking "Generate Sample Files"?

2. **Should we show a preview/summary before generation?**
   - "You're about to generate: 10 accounts, 12 months, Industry: Healthcare, Customer ID: 18"
   - With option to adjust before generating?

3. **Should we show generation progress?**
   - Progress bar during ZIP file generation?
   - Or just loading spinner?

---

## Recommended Next Steps

1. **Answer questions 1-7 above** to finalize requirements
2. **Update `generate_synthetic_customer_data.py`** to accept:
   - `industry` parameter (filter/prefer selected industry)
   - `customer_id` parameter (already accepts, but need validation)
   - `company_name` parameter (for customers.csv and manifest)
3. **Update onboarding API** to:
   - Generate customer_id if not provided
   - Validate customer_id if provided
   - Pass industry, company_name to generator
4. **Update UI (Step5Sources.tsx)** to:
   - Show read-only fields (num_months: 12, vertical: DC2_S, company_name)
   - Show customer_id with override option
   - Show industry from business context
   - Add validation for customer_id

---

## Files to Update

1. **Frontend:**
   - `src/components/onboarding/Step5Sources.tsx` - Add UI controls
   - `src/components/onboarding/OnboardingWizard.tsx` - Pass business context

2. **Backend:**
   - `backend/onboarding_api.py` - Update generate-sample-files endpoint
   - `backend/generate_synthetic_customer_data.py` - Add industry, company_name parameters
   - `backend/onboarding_api.py` - Add customer_id validation

3. **New Files (if needed):**
   - API endpoint for customer_id validation
   - API endpoint for next available customer_id
