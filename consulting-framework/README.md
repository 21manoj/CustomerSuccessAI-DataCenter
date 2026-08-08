# CS Pulse Consulting Framework

An internal FDE (Forward-Deployed Engineer) cookbook: a modular prompt library that
lets an engineer stand up a working instance of this system — in whole or in part —
for a new client engagement, in days instead of the months it took to build the
original.

## Why modular

This codebase is actually two things bundled together:

- **Engine** — the reusable logic (scoring math, causal graph, prediction wizards,
  agent/MCP interface, dashboards). Stable across clients; an FDE should rarely need
  to touch its internals.
- **Config** — the client-specific parameterization (which KPIs, what weights, what
  thresholds, what verticals). This is what actually changes per engagement.

Every module below states which of its pieces are Engine (build once, reuse) and
which are Config (an FDE fills in per client). A client engagement selects a subset
of modules — a client that only wants dashboards over their existing KPI warehouse
doesn't need Wizards or the context graph; one that only wants churn prediction
doesn't need the full persona-dashboard suite.

## How a module spec works

Each file in `modules/` follows [`MODULE_TEMPLATE.md`](MODULE_TEMPLATE.md): purpose,
boundary (what it owns vs explicitly does not), dependencies on other modules, an
Engine/Config split, a literal build prompt to hand to a coding agent, acceptance
criteria, and — the actual IP — a **Known Gotchas** section. That section is not
theoretical; every entry is a real bug this team hit, root-caused, and fixed while
building the original system, written up so the next FDE doesn't lose the same days
rediscovering it.

## Module roadmap

**Status:** all 12 numbered modules (00–11) **plus the 08-UI companion** are fully
written and validated (a fresh agent rebuilt each from its spec alone, in
isolation, and every run caught real defects in the spec that got fixed as a
result — see each module's Validation Note). The roadmap is complete. Note 08-UI's
validation is scoped to its pure-logic contracts (React rendering fidelity is out
of scope by design — see its Validation Note).

### Foundation
| # | Module | Status | One-liner |
|---|---|---|---|
| 00 | [Integration & Bootstrap](modules/00-foundation-integration-bootstrap.md) | **✅ Validated** | The chassis: single app/db, schema-authority + drift check, the `process_data` stage sequencer, single-source config resolvers, feature toggles, new-tenant bootstrap. Acceptance = the 4-CSV×11-KPI golden E2E. |
| 01 | [Data Model & Schema](modules/01-foundation-data-model.md) | **✅ Validated** | Tenant/identity bedrock: Customer, Account, User, CustomerConfig, CustomerApiKey, multi-tenancy + access-control contract. |
| 02 | [Vertical & KPI Taxonomy Config](modules/02-foundation-vertical-taxonomy.md) | **✅ Validated** | Per-vertical KPI catalog (pillars, weights, ranges) as a JSON file an FDE drops in — no code change — plus validated tiers for phased onboarding. |

### Intelligence
| # | Module | Status | One-liner |
|---|---|---|---|
| 03 | [Health Scoring Engine](modules/03-intelligence-health-scoring-engine.md) | **✅ Validated pilot** | L1→L3 KPI→Pillar→Account rollup, canonical read service, weight-hierarchy resolution, threshold classification. |
| 04 | [Context Graph & Causal Layer](modules/04-intelligence-context-graph.md) | **✅ Validated** | Typed causal graph (SIGNAL/DECISION/OUTCOME nodes), base+overlay taxonomy, invariant checks, arc classification. |
| 05 | [Prediction Wizards (Orchestration)](modules/05-intelligence-wizards.md) | **✅ Validated** | Run tracking, exactly-one-active versioned artifacts, trigger governance (explicit vs lazy). Framework only — analysis algorithms stay client-specific. |
| 06 | [Signal Processing Layer](modules/06-intelligence-signal-processing.md) | **✅ Validated** | Structured signals from unstructured text: deterministic urgency floor, gated LLM enrichment, cost governance, review routing. |

### Interface
| # | Module | Status | One-liner |
|---|---|---|---|
| 07 | [Agent / MCP Tool Layer](modules/07-interface-mcp-tool-layer.md) | **✅ Validated** | Standalone MCP server exposing the platform to LLM agents; two-tier tool-level auth, tenant isolation, impl/tool separation, registry-as-source-of-truth. |
| 08 | [Persona Dashboards](modules/08-interface-persona-dashboards.md) | **✅ Validated** | CRO/CFO/VPCS/CSM views; the two-layer leading (signals) vs trailing (KPI rollup) indicator model; L4 revenue-weighted portfolio rollup; single-source metrics + cross-persona/surface parity. |
| 08-UI | [Component Kit & UX Patterns](modules/08-ui-component-kit.md) | **✅ Validated** (pure-logic) | Contract-bound React tokens + primitives + domain patterns + shell that render Module 08's payloads: one wired health-band classifier, labeled data-states (no mock-as-real), a fail-closed entitlement guard, an anti-drift meta-check. |

### Ops
| # | Module | Status | One-liner |
|---|---|---|---|
| 09 | [Ingestion & Onboarding Pipeline](modules/09-ops-ingestion-pipeline.md) | **✅ Validated** | Shift-left validation, UTC-safe freshness detection, idempotent upsert, stage orchestration with isolation. |
| 10 | [Governance & Audit Layer](modules/10-ops-governance-audit.md) | **✅ Validated** | The meta-layer that keeps a running/regenerated instance honest: code-parity drift auditor, invariant enforcement + paired-test meta-test, tool-auth coverage sweep, LLM call-site gate, model-governance register — every check with an anti-vacuous floor. |
| 11 | [Load-Driver Synthetic Data & Testing](modules/11-ops-loaddriver-testing.md) | **✅ Validated** | Manifest-driven synthetic tenants, deterministic generation, story-arc round-trip guard, multi-phase/`--extend` intervention testing, the generate→onboard→process→validate acceptance harness (pairs with Module 00's golden E2E). |

## Operational deliverables (the FDE glue around the modules)

The modules regenerate the *engine*; these two deliverables are the operational
glue an FDE needs to actually stand an instance up. They are runbooks/manifests
grounded in the real codebase (every cited path verified to exist), not validated
code modules.

| Deliverable | What it is |
|-------------|------------|
| [Config Pack](config-pack/README.md) | The per-client **Config layer** manifest: every config artifact (KPI catalogs, weights, thresholds, taxonomy, story arcs, tiers, nomenclature), its canonical path, its consuming module, and the exact Config-vs-Engine split — plus the two authoring flows (existing vertical vs brand-new vertical). |
| [Deployment & Ops Runbook](DEPLOYMENT_RUNBOOK.md) | The ordered deploy procedure over the existing tooling: the two deploy paths (git-pull-build / ECR rehydrate), prereqs, secrets + the `.env` cardinal rule, boot sequence, verify (health + magic-link), and rollback/troubleshooting. |

**Still open** (flagged in the framework, not yet built): a single stitched
**Onboarding Runbook**, and — the real proof — one **end-to-end assembly dry-run**
that regenerates → configures → deploys → onboards → verifies against the golden
path (the integration test the isolation-based validation never performed).

## Extending this library

Before writing module N+1, re-read the validated modules' Validation Notes
(`modules/01-...md` through `04-...md`) — all four independently caught real
defects, in three overlapping shapes: a Build Prompt that, followed
literally, textually contradicts a Gotcha/Acceptance Criterion/Data Shapes
entry elsewhere in the same doc (01, 03 — including one confirmed real
access-control bypass); a Build Prompt that leaves pseudocode underspecified
in a way whose one natural implementation reproduces a documented anti-
pattern by construction (02); and a whole deliverable promised in Boundary/
Engine that silently never appears in Build Prompt/AC/Test Harness at all
(04). Module 04 also reproduced, VERBATIM, a defect (prose instead of
pseudocode for a scoring function) that Module 03 had already found and
fixed one module earlier — do not assume a lesson learned in one module
automatically holds for the next one written by the same process. Cross-
check every new Build Prompt against every other section before considering
a module done, fully specify any pseudocode gap rather than leaving an
ellipsis, and confirm every "Owns"/Engine commitment has a matching Build
Prompt piece — don't rely on inspection alone or on "we already learned this
lesson"; run the adversarial fresh-agent rebuild (see `MODULE_TEMPLATE.md`)
for every module, no exceptions.
