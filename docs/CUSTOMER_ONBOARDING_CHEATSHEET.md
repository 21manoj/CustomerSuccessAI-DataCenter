# CS Pulse — Customer Onboarding Cheat Sheet

How a new customer gets their data in and lights up their dashboards.
**Accounts are created by uploading `accounts.csv`** — one row per account. You do
*not* create accounts one-by-one in a form.

---

## Who does what

| Role | Does |
|------|------|
| **Super-admin** (CS Pulse ops) | Creates your tenant in the Admin Console → you get an admin login, your vertical (saas_premium / dc2_s / datacenter_v1), and an **empty** account list. |
| **You** (customer admin) | Log in → the **Onboarding Wizard** opens → upload your CSVs → click Process. |

---

## The 5 steps

1. **Log in** at your CS Pulse URL with the admin email + password ops gave you.
   With no data yet, you land on **Onboarding** automatically (or go to `/onboarding`).
2. **Welcome** → click **Start Upload**.
3. **Month 1 Data** → upload the **4 required CSVs** (see below). Each card has a
   **Template** button (downloads the exact columns) and a **Columns** button (shows the
   schema). Upload each file; wait for the green ✓.
4. **Month 2+ (Optional)** → optionally add `engagement_events.csv` and
   `industry_benchmarks.csv`. Skip if you don't have them yet → **Process Data**.
5. **Process** → click **Calculate Health Scores**. Wait ~30s (health scoring, arc
   detection, signal analysis, ROI). You'll see **"Onboarding Complete!"** with buttons to
   the Executive Dashboard, CSM Cockpit, and Ask AI.

You can re-run onboarding later to add months/accounts — it's incremental and safe to
repeat (duplicate rows are skipped).

---

## The 4 required files (Month 1)

| File | What it is | Creates |
|------|-----------|---------|
| **`accounts.csv`** | Your accounts (enriched) — **one row per account** | The accounts themselves |
| **`kpi_measurements.csv`** | KPI time-series per account | Health scores |
| **`enhanced_qualitative_signals.csv`** | Signals feed (NPS, escalations, champion changes…) | Context-graph signal nodes |
| **`outcomes.csv`** | CRM renewal/churn/expansion history | Revenue-at-risk / protected / expansion |

Download each **Template** from the wizard to get the exact headers, then fill with your data.

---

## How accounts are created — `accounts.csv`

Each **row = one account**. The account is created from `account_name`. The most useful columns:

| Column | Required? | Notes |
|--------|-----------|-------|
| `source_account_id` | **Yes** | Your own id for the account (e.g. `1001`). **This is the join key** — the other 3 files reference it. |
| `account_name` | **Yes** | Creates the account; must be unique. |
| `arr` (or `revenue`) | Recommended | Annual recurring revenue — drives revenue-weighted rollups. |
| `industry`, `region` | Optional | Firmographics. |
| `tier` | Optional | e.g. Enterprise / Mid-Market. |
| `csm_name`, `csm_email` | Optional | Owning CSM. |
| `primary_champion_name` / `_title` / `_email` | Optional | Champion (feeds stakeholder map). |
| `contract_start`, `contract_end`, `renewal_date` | Optional | Dates (YYYY-MM-DD). |
| `account_status` | Optional | Defaults to `active`. |

> **The one rule that matters:** the `source_account_id` in `accounts.csv` must match the
> `source_account_id` used in `kpi_measurements.csv`, `enhanced_qualitative_signals.csv`,
> and `outcomes.csv`. That's how KPIs, signals, and outcomes attach to the right account.
> If they don't match, the account is created but shows no data.

Minimal example:

```csv
source_account_id,account_name,arr,industry,region,tier,csm_name,renewal_date
1001,Pinnacle HR Platform,3900000,Technology,North America,Mid-Market,Sarah Rivera,2026-10-01
1002,Atlas Retail Intelligence,4300000,Retail,North America,Enterprise,Alex Chen,2026-09-15
```

Then in `kpi_measurements.csv`, rows reference the same ids:

```csv
source_account_id,kpi_code,pillar,measured_at,value,target,unit
1001,P1-KPI1,P1,2026-01-01,79.5,60,percentage
1002,P1-KPI1,P1,2026-01-01,84.0,60,percentage
```

(Use **Get KPI catalog** / the wizard's **Columns** button to see the valid `kpi_code`
and `pillar` values for *your* vertical — they differ per vertical.)

---

## After onboarding

- **Executive / CRO dashboard** — portfolio health, revenue at risk/protected, expansion.
- **CSM Cockpit** — prioritized actions, per-account deep-dive, playbooks.
- **Ask AI** — "What are my top at-risk accounts and why?" (reasons over your data).

---

## Testing with Synthetic Data — create / upload / test (internal / demos)

For FDEs and demos: you don't need real customer CSVs. The **load-driver** generates a
full, self-consistent set (accounts + KPIs + signals + outcomes with matching
`source_account_id`s and coherent story arcs) that you upload through the same wizard.

### 1. Generate the CSVs (no server needed)

```bash
cd load-driver
python3.11 cs_pulse_driver.py \
  --manifest manifests/cascade_predictive_11_saas.json \
  --generate-only ./out_saas --seed 42
```

Pick a manifest matching the vertical you're testing:

| Vertical | Example manifests |
|----------|-------------------|
| **saas_premium** | `cascade_predictive_11_saas.json`, `e2e_eval_saas.json` |
| **dc2_s** | `dr1_ai_dc2s.json`, `Mount-Fuji_dc2.json` |
| **datacenter_v1** | `novagrid_datacenter_v1.json`, `hyperion_datacenter_v1.json` |

`--generate-only` writes these files (no API calls, nothing registered):
`account_details.csv`, `kpi_measurements.csv`, `qualitative_signals.csv`,
`outcomes.csv` (+ `engagement_events.csv`, `decisions.csv`, `signal_edges.csv`).

### 2. Create a matching test tenant

Super-admin → Admin Console → **New Customer**, with **vertical = the manifest's
vertical** (the vertical sets the KPI catalog/scoring — a mismatch produces wrong
scores). New tenants now start with **0 accounts**, so the upload defines the account
list cleanly.

### 3. Upload into the wizard (map file → slot)

Log in as the tenant → `/onboarding` → **Start Upload** → drop each generated file into
the matching card:

| Wizard slot | Upload this generated file |
|-------------|----------------------------|
| Accounts (Enriched) | `account_details.csv` |
| KPI Measurements | `kpi_measurements.csv` |
| Qualitative Signals | `qualitative_signals.csv` |
| Outcomes (CRM History) | `outcomes.csv` |

(The generator's filenames differ slightly from the slot labels — the slot is what
matters, not the filename.) Then **Process** → *Calculate Health Scores*.

### 4. Verify

- **Dashboards** populate (Exec/CRO revenue cards, CSM Cockpit accounts + health).
- **Ask AI**: "What are my top at-risk accounts and why?" — should cite real accounts,
  pillars, and context-graph nodes.
- Quick DB sanity (if you have shell access): accounts / KPIs / health rows > 0 for the
  customer, and KPI `pillar`s cover the vertical's full set (e.g. P1–P6 for datacenter_v1).

> **Headless / CI note:** the browser-automation panes have no OS file dialog, so a
> scripted test can't click the file picker. Either drive the underlying
> `POST /api/onboarding/upload` + `POST /api/onboarding/process-data` directly, or host the
> generated CSVs same-origin and inject them into the wizard's `<input type=file>` via a
> `DataTransfer` + `change` event. A human tester just uses the normal file picker.

---

## Common gotchas

- **Account shows up but is empty** → its `source_account_id` doesn't match the id used in
  the KPI/signals/outcomes files.
- **"Processing…" seems slow** → the pipeline runs LLM signal analysis; ~30s is normal.
- **Wrong KPI codes** → each vertical has its own KPI catalog; always start from the
  downloaded template / Columns list, don't guess codes.
- **Adding more accounts later** → just re-upload an `accounts.csv` with the new rows (plus
  their KPIs/signals/outcomes) and Process again; existing data is preserved.
