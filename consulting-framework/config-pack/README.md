# Config Pack

The **Config layer** an FDE authors per engagement — the client-specific
parameterization that rides on top of the fixed Engine the 13 modules regenerate.
This is a **manifest + authoring guide, not a module**: it inventories the real
config artifacts (all of which already exist in the codebase), states the exact
Config-vs-Engine split for each, and gives the two authoring flows. Every path is
real and cited in [Provenance](#provenance).

Base path for all artifacts: `kpi-dashboard/backend/`.

## The layered Config model (lowest → highest priority)

A client's configuration resolves through three layers; higher layers override
lower ones, and the top layer hot-reloads with no restart:

1. **The vertical JSON catalog** — `config/{vertical}_kpi_catalog.json`. The
   source of truth for the KPI set, pillars, weights, ranges, and targets. (The
   `verticals/{vertical}/kpi_definitions.py` files are thin *loaders* — Engine —
   not the source of truth.)
2. **Per-customer bootstrap weights** — `verticals/customer{id}-{vertical}/journey/config/bootstrap_weights_config.json`
   (calibrated L1/L2 weights from a per-client simulation; canonical template at
   `verticals/_template/…`). There is **no** single central bootstrap file.
3. **The `CustomerConfig` DB row** — per-client overrides, highest priority,
   hot-reload (Wizard C writes calibrated weights here). Fields:
   `dc2s_pillar_weights`, `dc2s_kpi_weights`, `dc2s_kpi_overrides`,
   `dc2s_enabled_kpis`, `dc2s_kpi_definitions`, `nomenclature_overrides`,
   `category_weights` (`models.py:82-91`).

This chain is what Module 00's weight resolver (`resolve_weights`) and Module 03's
scoring read — see Module 00 Gotcha 7 (one resolver, ordered fallthrough).

## Artifact inventory

All under `kpi-dashboard/backend/config/` unless noted. **C** = Config (FDE edits
per client/vertical), **E** = Engine (fixed).

| Artifact | Path | Purpose | Consumed by (module) | C/E |
|----------|------|---------|----------------------|:---:|
| **DC KPI catalog** | `config/dc2s_kpi_catalog.json` (v3.0, **38 KPIs**, 5 pillars) | KPI set, `weight_l1`, pillar `weight_l2`, ranges, targets, direction | 02 (taxonomy), 03 (scoring), 00 (weights) | **C** |
| **SaaS KPI catalog** | `config/saas_premium_kpi_catalog.json` (v3.1, **43 KPIs**) | same, SaaS vertical | 02/03/00 | **C** |
| **Healthcare catalog** | `config/healthcare_provider_kpi_catalog.json` (10 KPIs) | the JSON-only-vertical example (no Python) | 02 | **C** |
| **Catalog loaders** | `verticals/{dc2_s,saas_premium}/kpi_definitions.py` | load the JSON, expose `*_PILLARS`/`*_KPIS`, scoring helpers | 03 | **E** |
| **Pillar weights** | `verticals/dc2_s/pillar_weights.py` (`BOOTSTRAP_L2_WEIGHTS`, `WeightConfig`) | L2 defaults + override management | 00 | **E**+default **C** |
| **Bootstrap weights (per-customer)** | `verticals/{customer}/journey/config/bootstrap_weights_config.json`; template `verticals/_template/…` | calibrated L1/L2 from per-client sim (0.70→0.85) | 00 (weight hierarchy) | **C** |
| **Bootstrap loader** | `verticals/{customer}/services/bootstrap_weights_loader.py` | reads the above, tolerant of key spellings | 00 | **E** |
| **Health thresholds** | `config/health_thresholds.json` (healthy 70 / at_risk 50 / critical 0 + colors) | band cutoffs, global (not per-vertical) | 03/00/08/08-UI/10 | **C** |
| **Taxonomy base** | `config/taxonomy_base.json` | polarity-ambiguous subtypes, revenue buckets, auto-recovery subtypes | 02, 04 (graph subtypes) | **C** |
| **Taxonomy overlays** | `config/taxonomy_{dc2_s,saas_premium,healthcare_provider}.json` (`extends:"base"`, additive) | per-vertical taxonomy deltas | 02/04 | **C** |
| **Taxonomy schema** | `config/taxonomy_schema.json` (draft-07, additive-only) | validates overlays | 02/10 | **E** |
| **Story arcs** | `config/story_arcs/*.json` (8 arcs) + `schema.json` | demo-data narratives (phases, causal chains, KPI trajectories) | 04, 11 | **C** (+schema **E**) |
| **Arc→playbook map** | `config/arc_playbook_map.json` | canonical arc → prioritized playbook IDs (Layer-B auto-trigger) | 05 | **C** |
| **Playbook config** | `verticals/{vertical}/vertical_config.py` (`PLAYBOOK_CONFIG`, `PHASE_CONFIG`, `should_trigger_playbook`) | playbook defs + trigger evaluation | 05 | dicts **C**, logic **E** |
| **SaaS KPI tiers** | `config/saas_kpi_tiers.json` (starter_9 / predictive_11 / growth_15 / full_43) | tiered onboarding presets → manifests | 02, 11 | **C** |
| **DC tiering** | (no JSON) — `CustomerConfig.dc2s_enabled_kpis` (a KPI-code list) | restrict the DC catalog per client | 02 | **C** |
| **Nomenclature** | `config/vertical_nomenclature/{dc2_s,saas_premium}.json` | per-vertical UI terminology (entities, pillars, health labels) | 08, 08-UI | **C** |
| **Industry benchmarks** | `config/industry_benchmarks/{dc2_s,saas_premium}.csv` | benchmark comparisons | 03/08 | **C** |
| **ROI economics** | `config/power_of_1_economics.json`, `config/resource_rates.json` | Power-of-1 / ROI benchmarks | 05/08 (CFO) | **C** |
| **CSV ingest schemas** | `config/csv_schemas.json` | the upload/onboarding CSV contracts | 09 (ingestion) | **C** |
| **MCP system prompt** | `config/mcp_system_prompt.md` (+ `_public.md`) | the copilot persona/instructions | 07 | **C** |
| **Vertical registry** | `utils/vertical_registry.py` (`VERTICAL_ALIASES`, auto-discovery) | resolves + registers verticals | 00/02 | **E** |
| **Scaffolder** | `verticals/provision_dc_customer.py` + `verticals/_template/` | copies the template → `customer{id}-{vertical}/` | 00 (bootstrap) | **E** |
| **New-vertical authoring guide** | `config/vertical_scaffold_prompts/*.md` (10 numbered steps) | the existing FDE playbook for a brand-new vertical | — | ref |

## Authoring flow A — onboard on an existing vertical (dc2_s / saas_premium)

Nothing to author in the pack — you're parameterizing, not building a vertical:
1. Pick the **vertical** and the **KPI tier** — SaaS: a tier from
   `config/saas_kpi_tiers.json`; DC: set `CustomerConfig.dc2s_enabled_kpis`.
2. Scaffold the customer's data dir: `python verticals/provision_dc_customer.py`
   (copies `_template/` → `customer{id}-{vertical}/`, remaps placeholders/IDs).
3. Set any per-client overrides on the `CustomerConfig` row (weights, targets,
   nomenclature) — these hot-reload and win over the catalog.
4. Proceed to the [Onboarding Runbook] flow (create_customer → load → process_data
   → verify). *(Onboarding Runbook not yet written — see the framework README.)*

## Authoring flow B — a brand-new vertical

The Engine is vertical-agnostic: "DC2_S is not special. Any vertical can be
defined via JSON catalog without Python code" (`vertical_registry.py`). To add a
vertical, drop these Config files (the registry auto-discovers a new catalog):
1. **`config/{vertical}_kpi_catalog.json`** — the KPI set, pillars, `weight_l1`/
   `weight_l2`, ranges, targets. (Model this on `dc2s_kpi_catalog.json`; the
   `healthcare_provider` catalog is the minimal 10-KPI example.)
2. **`config/taxonomy_{vertical}.json`** overlay (`extends:"base"`, additive).
3. **`config/vertical_nomenclature/{vertical}.json`** — UI terminology.
4. Optional: `config/industry_benchmarks/{vertical}.csv`, story arcs, an
   `arc_playbook_map` entry, a `vertical_config.py` playbook set, a tier JSON.
5. Add an alias in `vertical_registry.VERTICAL_ALIASES` if the short code differs.

**Use the existing step-by-step guide** rather than reinventing it:
`config/vertical_scaffold_prompts/` is a 10-part FDE authoring playbook
(`01_kpi_definitions` … `10_onboarding_prompt`). This Config Pack manifest tells
you *what* the artifacts are and *who consumes them*; that directory tells you
*how* to author each one.

## Nuances to know (from the code study — some contradict older docs)

- **SaaS is 43 KPIs (catalog v3.1)** — the `saas_premium/kpi_definitions.py`
  docstring still says "41"; trust the JSON catalog, not the docstring. DC is 38.
- **No central `bootstrap_weights_config.json`.** It is per-customer (two paths
  inside each customer dir); `verticals/_template/journey/config/…` is canonical.
- **DC has no committed tier JSON.** DC tiering rides entirely on
  `CustomerConfig.dc2s_enabled_kpis`; only SaaS has `saas_kpi_tiers.json`.
- **Playbook ID drift:** `vertical_config.py` uses `PB-0#`; `mcp_system_prompt.md`
  uses `PB-DC-0#`. Reconcile per client, or Module 10's drift auditor will (rightly) flag it.
- **The `.py` catalog files are loaders, not source** — edit the JSON catalog,
  not the Python, to change a client's KPIs.

## What "packaging the Config Pack" would add beyond this manifest

This manifest makes the Config layer explicit and consumable. To make it a true
drop-in bundle you would additionally: (a) snapshot a **reference client's** full
Config set (catalog + overlays + nomenclature + bootstrap template) into a single
versioned directory, and (b) add a validator that checks a Config set against the
schemas (`taxonomy_schema.json`, `story_arcs/schema.json`) and the KPI-code format
before onboarding — which is naturally Module 10's (Governance) job. Both are
follow-ons; the inventory + split + authoring flows above are the deliverable.

## Provenance

Verified 2026-08-07 against HEAD `25397567e` by listing `kpi-dashboard/backend/config/`
and `.../verticals/` and reading the cited catalogs, loaders, and `CustomerConfig`
(`models.py:82-91`). Catalog versions and KPI counts read from the JSON headers
(`dc2s_kpi_catalog.json` v3.0/38; `saas_premium_kpi_catalog.json` v3.1/43). Weight
hierarchy cross-checked against `utils/score_calculator.py`, `vertical_registry.py`,
and `services/bootstrap_weights_loader.py`. The new-vertical path and
auto-discovery verified in `utils/vertical_registry.py`; the scaffolder in
`verticals/provision_dc_customer.py` + `verticals/_template/`.
