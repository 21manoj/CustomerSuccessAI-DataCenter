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

**Status:** 2 of 11 modules are fully written and validated (a fresh agent rebuilt
each from its spec alone, in isolation, and both runs caught real defects in the
spec that got fixed as a result — see each module's Validation Note). The rest are
placeholders — do not treat their one-liners below as validated specs.

### Foundation
| # | Module | Status | One-liner |
|---|---|---|---|
| 01 | [Data Model & Schema](modules/01-foundation-data-model.md) | **✅ Validated** | Tenant/identity bedrock: Customer, Account, User, CustomerConfig, CustomerApiKey, multi-tenancy + access-control contract. |
| 02 | Vertical & KPI Taxonomy Config | Planned | Per-vertical KPI catalog (codes, pillars, weights, ranges) as versioned JSON + overlay pattern — the main lever an FDE pulls per client. |

### Intelligence
| # | Module | Status | One-liner |
|---|---|---|---|
| 03 | [Health Scoring Engine](modules/03-intelligence-health-scoring-engine.md) | **✅ Validated pilot** | L1→L3 KPI→Pillar→Account rollup, canonical read service, weight-hierarchy resolution, threshold classification. |
| 04 | Context Graph & Causal Layer | Planned | ContextNode/Edge, story-arc classification, causal-graph invariants. |
| 05 | Prediction Wizards (A–D) | Planned | Arc/trajectory detection, early-warning patterns, weight calibration from outcomes, NRR/renewal prediction. |
| 06 | Signal Processing Layer | Planned | Qualitative signal ingestion, LLM classification, sentiment. |

### Interface
| # | Module | Status | One-liner |
|---|---|---|---|
| 07 | Agent / MCP Tool Layer | Planned | Standalone MCP server exposing the platform to LLM agents; tool-level auth. |
| 08 | Persona Dashboards | Planned | CRO/CFO/VPCS/CSM views; the two-layer leading (signals) vs trailing (KPI rollup) indicator model; L4 revenue-weighted portfolio rollup. |

### Ops
| # | Module | Status | One-liner |
|---|---|---|---|
| 09 | Ingestion & Onboarding Pipeline | Planned | CSV/API upload, process-data orchestration, shift-left validation. |
| 10 | Governance & Audit Layer | Planned | Drift auditor, invariant checks, tool-auth gates. |
| 11 | Load-Driver Synthetic Data & Testing | Planned | Manifest-driven scenario generation, multi-phase intervention testing, acceptance/parity suites. |

## Extending this library

Before writing module N+1, re-read the validated modules' Validation Notes
(`modules/01-...md`, `modules/03-...md`) — both independently caught the same
failure class (a Build Prompt that, followed literally, contradicts or omits
something a Gotcha/Acceptance Criterion/Data Shapes entry requires, including
one confirmed real access-control bypass). Cross-check every new Build Prompt
against every other section before considering a module done — don't rely on
inspection alone; run the adversarial fresh-agent rebuild (see
`MODULE_TEMPLATE.md`) for every module, not just the first two.
