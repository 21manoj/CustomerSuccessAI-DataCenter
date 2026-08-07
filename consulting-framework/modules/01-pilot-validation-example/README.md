# Pilot validation artifact — do not treat as a reference implementation

What a fresh agent built from **only**
[`../01-foundation-data-model.md`](../01-foundation-data-model.md) — no access
to `models.py` or any other real code — for an invented "fitguild_v1" vertical
(boutique fitness-studio SaaS: Customer=franchise operator, Account=studio
location). Raw SQL DDL was chosen deliberately over an ORM, specifically
because Gotcha 1 in the spec (ORM-declared FKs aren't automatically
DB-enforced) made that the safer default.

Run `python -m pytest test_data_model.py -q` — 27/27 pass.

See the spec's "Validation Note" for what this run got right, what it caught
as genuine spec defects (including a real access-control bypass in the
original Build Prompt's literal code), and what changed as a result.
