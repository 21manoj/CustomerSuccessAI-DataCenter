# Pilot validation artifact — do not treat as a reference implementation

This is what a fresh agent built from **only**
[`../03-intelligence-health-scoring-engine.md`](../03-intelligence-health-scoring-engine.md)
— no access to this repo's real health-scoring code — for an invented
"freightops_v1" vertical (fleet-management SaaS). It exists to prove the spec
format is sufficient on its own, not as a second reference implementation to
keep in sync. The real reference implementation lives in
`kpi-dashboard/backend/utils/account_health.py` and the other files listed
under the spec's Provenance section.

Run `python -m pytest test_health_scoring_engine.py -q` — 16/16 pass.

See the spec's "Validation Note" section for what this run got right, what it
got wrong, and what changed in the spec as a result.
