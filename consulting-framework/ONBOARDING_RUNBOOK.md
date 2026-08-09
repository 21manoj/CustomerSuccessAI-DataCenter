# Onboarding Runbook

The ordered procedure an FDE follows to onboard a **new end-customer (tenant)**
into an already-running CS Pulse instance. This is the third operational
deliverable — it sits after [Deployment](DEPLOYMENT_RUNBOOK.md) and
[Config Pack](config-pack/README.md), and it stitches the create → load → process
→ verify steps that today live scattered across Modules 00, 07, 09, and 11 into
one checklist. Every tool and path below is real and cited in
[Provenance](#provenance).

> Scope: onboarding a **customer into a running platform**. Standing up the
> platform itself is the [Deployment Runbook](DEPLOYMENT_RUNBOOK.md); authoring a
> new *vertical's* config is the [Config Pack](config-pack/README.md).

## Decision tree (settle these first)

| Decision | Options | Notes |
|----------|---------|-------|
| **Vertical** | `dc2_s` / `saas_premium` / a custom one | Existing verticals need no new config; a new one is a Config Pack job first. |
| **KPI tier** | SaaS: `saas_starter_9` / `saas_predictive_11` / `saas_growth_15` / `saas_full_43`; DC: set `dc2s_enabled_kpis` | "4 CSVs × 11 KPIs" = the 4-CSV onboarding at the **Predictive-11** tier, not a universal default. |
| **Data source** | Real client CSVs / a synthetic manifest | Synthetic (a `load-driver` manifest) sidesteps the client-data mapping — best for demos/first-run. |
| **LLM enrichment** | on / off | `FEATURE_WITH_LLM` + `ANTHROPIC_API_KEY`. Off = deterministic signals only (Module 06). |
| **New tenant vs extend** | fresh `create_customer` / `--extend` an existing one | `--extend` continues an arc into a later phase; mutually exclusive with `--register`. |

## The ordered steps

### 1. Create the customer *(Module 00 bootstrap sequence)*
`create_customer(name, domain, vertical, admin_email, admin_name, tier=None)`
(MCP tool, `mcp_server/cs_pulse_onboarding.py:536`). In one transaction it creates
`Customer` + admin `User` + `CustomerConfig` (vertical + KPI tier) + a
`CustomerApiKey` + the data-dir scaffold + the default feature-toggle rows.

> **Capture the API key now — it is returned exactly once.** (Module 07.)

The admin logs in via **magic link**: `POST /api/auth/magic-link`; in dev/no-email
mode the token prints to stdout — read it with `docker logs cspulse-platform`
(15-min, single-use).

### 2. Confirm config *(Config Pack)*
- Vertical is written to **both** `Customer.vertical` and `CustomerConfig.vertical`
  from one value at create — verify they agree (Module 00 Gotcha 6: if they later
  diverge you score one vertical while loading data from another's folder).
- Apply any per-client overrides on the `CustomerConfig` row (weights, targets,
  nomenclature) — they hot-reload and win over the catalog.

### 3. Get the 4 Month-1 CSVs in *(Module 09 ingestion)*
The canonical onboarding shape is **4 CSVs**: `account_details.csv`,
`kpi_measurements.csv`, `qualitative_signals.csv`, `outcomes.csv` (contracts in
`config/csv_schemas.json`). Two ways:

- **Real data:** map the client's data to those four schemas, then `upload_csv`
  (`cs_pulse_onboarding.py:1033`) — or drop the files in
  `verticals/customer{id}-{vertical}/data/`. *(The scaffold is created by
  `verticals/provision_dc_customer.py`.)* This mapping is the one genuinely manual
  step; there is no automated adapter for an arbitrary source.
- **Synthetic / demo:** run an existing manifest end-to-end — it registers,
  generates, uploads, and processes for you:
  ```bash
  python load-driver/cs_pulse_driver.py --manifest load-driver/manifests/predictive_11_saas.json
  ```
  (`--phase baseline|intervention` and `--extend` drive multi-phase scenarios;
  Module 11.)

> Shift-left validation runs here: types/enums at upload, FK/temporal at ingest
> (Module 09). CSV file mtimes must be UTC or an incremental reload is silently
> skipped.

### 4. Process the data *(Module 00 sequencer)*
`process_data(customer_id, mode="auto")` (`cs_pulse_onboarding.py:2227` →
`_process_data_impl:1089`). Runs the ordered, fault-isolated, idempotent pipeline:
score → publish health → signal scan → Wizard A → (LLM tier-1, if enabled) →
Wizard B → roi/index/record. Re-running is safe (no duplicate rows).

> **Wizard B silently no-ops below 5 journeys** (`MIN_ACCOUNTS_FOR_WIZARD_B`) — a
> small onboard won't get the trailing-NRR counterfactual (Module 00 Gotcha 4 / 11).

### 5. Post-load steps *(don't skip — Module 11 Gotchas 4, 5)*
- **Wizard D recalibration** (`trigger_wizard` → Wizard D, or the driver's
  `trigger_wizard_d_recalibration()`) — else the predictor stays
  `prediction_method="cold_start"`.
- **Attribution backfill** (`backfill_playbook_attribution()`,
  `cs_pulse_driver.py:301`) — else CFO "Revenue Protected" / "Portfolio ROI" read
  **$0 / 0x**. *(The synthetic driver runs both automatically after a successful
  load.)*

### 6. Confirm onboarding complete
`complete_onboarding(customer_id, check_only=True)` (`cs_pulse_onboarding.py:2397`)
verifies the tenant reached a usable state.

### 7. Verify the numbers *(Module 11 acceptance + the surfaces)*
- Synthetic path self-validates via `_validate_post_process` (health distribution
  vs manifest classification, tolerance-based, **discovered** platform IDs — not
  the manifest's).
- Real data: run `tests/test_onboarding_e2e.py` and the persona-CI tests; eyeball
  the persona dashboards (Modules 08 / 08-UI).
- Governance baseline: `backend/scripts/audit_context_graph.py --customer-id <id>`.

## Onboarding gotchas (quick reference)

| Symptom | Cause | Fix / step |
|---------|-------|-----------|
| Lost the API key | returned once by `create_customer` | re-issue from the Admin UI (Module 07) |
| Scored `dc2_s` but data in a `saas_premium` folder | the two vertical columns diverged | step 2 — keep them equal |
| No NRR counterfactual | < 5 journeys → Wizard B no-ops | load ≥ 5 accounts, or expect it absent |
| Predictor shows `cold_start` | Wizard D never recalibrated | step 5a |
| CFO tiles read $0 / 0x | attribution not backfilled | step 5b |
| Incremental reload "did nothing" | CSV mtime not UTC | re-touch files in UTC (Module 09) |
| Synthetic arc looks wrong | manifest `story_arc` has no template → silent fallback | use a templated arc (Module 11 Gotcha 1) |
| Everything classifies healthy | a real 50 vs no-data confusion | `None` ≠ `50` (Modules 08/08-UI/10) |

## Fast paths

- **Demo tenant in one command:** `python load-driver/cs_pulse_driver.py --manifest
  load-driver/manifests/predictive_11_saas.json` — steps 1–5 in one run, then
  verify (step 7).
- **Scripted onboard:** `simple_onboard_customer.py` / `quick_onboard.py` seed the
  `CustomerConfig` + KPI data programmatically (the latter defaults to all 38 DC
  KPIs).

## Provenance

Origin tools/paths (verified to exist): `mcp_server/cs_pulse_onboarding.py`
(`create_customer:536`, `upload_csv:1033`, `_process_data_impl:1089`,
`process_data:2227`, `complete_onboarding:2397`); `mcp_server/process_data_pipeline.py`
(`MIN_ACCOUNTS_FOR_WIZARD_B`); `load-driver/cs_pulse_driver.py` (manifest flow,
`--phase`/`--extend`, `trigger_wizard_d_recalibration`, `backfill_playbook_attribution`);
`load-driver/manifests/predictive_11_saas.json`; `verticals/provision_dc_customer.py`;
`config/csv_schemas.json`, `config/saas_kpi_tiers.json`; `simple_onboard_customer.py`,
`quick_onboard.py`; `kpi-dashboard/backend/tests/test_onboarding_e2e.py`;
`kpi-dashboard/backend/scripts/audit_context_graph.py`. Module ownership: creation
+ sequencing (00), API key/auth (07), ingestion (09), synthetic + acceptance (11),
dashboards (08/08-UI). Mapped 2026-08-07 against HEAD `278b02cf7`.
