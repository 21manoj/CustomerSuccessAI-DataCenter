# Pilot validation artifact — do not treat as a reference implementation

What a fresh agent built from **only**
[`../02-foundation-vertical-taxonomy.md`](../02-foundation-vertical-taxonomy.md)
— no access to `vertical_registry.py`/`generic_scorer.py`/`config_validator.py`
or any real config files — for an invented "boutique_hotel_v1" vertical
(boutique-hotel-chain SaaS). Includes deliberately-broken catalog/tier
fixtures and a deliberately-broken legacy Tier-2 module used to prove the
loader distinguishes "vertical doesn't exist" from "vertical's legacy module
exists but is internally broken" (see Gotcha 3 in the spec).

Run `python -m pytest test_catalog_loader.py -q` — 20/20 pass.

See the spec's "Validation Note" for the subtler failure shape this run
caught: not a Build Prompt contradicting a Gotcha in words, but a Build
Prompt leaving an ellipsis (`if module_exists(x): ...`) whose one natural
implementation reproduced the Gotcha by construction.
