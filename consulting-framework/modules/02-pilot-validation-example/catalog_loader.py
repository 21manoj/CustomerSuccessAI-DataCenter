"""
Module 02 pilot implementation: Vertical & KPI Taxonomy Config.

Built strictly from consulting-framework/modules/02-foundation-vertical-taxonomy.md
for an invented client vertical ("boutique_hotel_v1", a boutique-hotel-chain
SaaS) as part of the fresh-agent validation pass for that spec. This file
was NOT written by consulting the reference implementation
(kpi-dashboard/backend/utils/vertical_registry.py / generic_scorer.py /
config_validator.py) -- per the validation exercise's ground rules, only the
spec markdown and the two other already-validated module specs were read.

Public surface (matches the Build Prompt's contract):
    load_catalog(vertical, config_dir=..., legacy_module_prefix=...)
        -> (pillars: dict, kpis: dict)
    get_kpis_for_tier(vertical, tier=None, config_dir=..., legacy_module_prefix=...)
        -> dict[kpi_code -> kpi_def]
    discover_verticals(config_dir=...) -> set[str]
    clear_cache(vertical=None) -> None   # test/ops helper, not in the spec

Deliberate deviations from the Build Prompt's literal pseudocode signature,
called out here (and in the validation report) rather than left silent:

  1. load_catalog/get_kpis_for_tier take an explicit `config_dir` (default:
     ./config next to this file) instead of a single implicit global config
     directory. The spec's pseudocode signature is `load_catalog(vertical)`
     with no config_dir parameter. A real single-process deployment would
     only ever need one config_dir and could hardcode it; this parameter
     exists so the test suite can point the loader at isolated temp
     directories per test (in particular the auto-discovery test, which
     must prove a *newly written* file becomes visible without restart --
     that is much cleaner to prove in a scratch directory than by mutating
     the one shared fixture directory shipped with this module). The cache
     key includes config_dir precisely so this parameter can never silently
     paper over a stale-cache bug between tests.
  2. Tier-2 resolution's Python import prefix is a parameter
     (`legacy_module_prefix`, default "verticals" to match the Build
     Prompt's own example `verticals.{vertical}.kpi_definitions`) rather
     than hardcoded, again purely for test isolation (this repo ships its
     own `legacy_verticals/` package of fixtures rather than a real
     `verticals/` package).

Everything else -- the 3-tier resolution order, the four load-time
validation rules, tier-as-pure-filter, and per-vertical caching -- follows
the spec's Build Prompt as literally as possible.
"""

from __future__ import annotations

import glob
import importlib
import json
import os
from dataclasses import dataclass, field
from typing import Optional

WEIGHT_TOLERANCE = 0.001

DEFAULT_CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
DEFAULT_LEGACY_MODULE_PREFIX = "verticals"


class CatalogValidationError(ValueError):
    """Raised when a catalog or tier file fails one of the four load-time
    validation rules. Always raised loudly at load time -- see Build Prompt
    step 2 and Gotcha 1: a catalog that fails validation must never be
    returned as usable, silently or otherwise."""


class UnknownVerticalError(ValueError):
    """Raised when neither Tier 1 (JSON file) nor Tier 2 (legacy Python
    module) resolves a vertical name."""


# Cache is keyed on (vertical, config_dir, legacy_module_prefix) so that
# tests using different temp config_dirs never collide, and so that
# "cached after first load" is provably true per (vertical, location) pair,
# matching what a real deployment would actually observe (one process, one
# config_dir, so effectively keyed on vertical alone in production).
_catalog_cache: dict[tuple, tuple[dict, dict]] = {}
_tier_cache: dict[tuple, dict] = {}


def _cache_key(vertical: str, config_dir: str, legacy_module_prefix: str) -> tuple:
    return (vertical, os.path.abspath(config_dir), legacy_module_prefix)


def clear_cache(vertical: Optional[str] = None) -> None:
    """Test/ops helper -- not part of the spec's own contract, but every
    caching acceptance criterion needs a way to reset between test cases
    without restarting the process. If `vertical` is given, only cache
    entries for that vertical name are dropped (across all config_dirs);
    otherwise the whole cache is cleared."""
    global _catalog_cache, _tier_cache
    if vertical is None:
        _catalog_cache = {}
        _tier_cache = {}
        return
    _catalog_cache = {k: v for k, v in _catalog_cache.items() if k[0] != vertical}
    _tier_cache = {k: v for k, v in _tier_cache.items() if k[0] != vertical}


def _catalog_path(vertical: str, config_dir: str) -> str:
    return os.path.join(config_dir, f"{vertical}_kpi_catalog.json")


def _tiers_path(vertical: str, config_dir: str) -> str:
    return os.path.join(config_dir, f"{vertical}_kpi_tiers.json")


def discover_verticals(config_dir: str = DEFAULT_CONFIG_DIR) -> set:
    """Vertical auto-discovery: scan config_dir for *_kpi_catalog.json files
    and return the set of vertical names found. Dropping a new, correctly
    named file into config_dir is sufficient to register a vertical -- no
    code change, no restart-and-hope (Build Prompt step 1). This function
    does not validate the files it finds; it only reports names. A vertical
    appearing here that fails validation when actually loaded is expected
    and correct -- discovery and validation are separate concerns."""
    if not os.path.isdir(config_dir):
        return set()
    verticals = set()
    suffix = "_kpi_catalog.json"
    for path in glob.glob(os.path.join(config_dir, f"*{suffix}")):
        filename = os.path.basename(path)
        verticals.add(filename[: -len(suffix)])
    return verticals


def _validate_catalog(vertical: str, data: dict) -> tuple[dict, dict]:
    """The four load-time validation rules from Build Prompt step 2 /
    Acceptance Criteria, run against a raw parsed catalog dict, regardless
    of whether it came from a JSON file (Tier 1) or a legacy Python module
    (Tier 2) -- see Gotcha 1: the whole point is that validation must not
    be tied to one particular authoring path."""
    pillars = data.get("pillars")
    kpis = data.get("kpis")

    if not isinstance(pillars, dict) or not pillars:
        raise CatalogValidationError(
            f"[{vertical}] catalog must declare a non-empty 'pillars' dict"
        )
    if not isinstance(kpis, dict):
        raise CatalogValidationError(f"[{vertical}] catalog must declare a 'kpis' dict")

    # Rule: pillar weight_l2 values sum to 1.0 (+/- WEIGHT_TOLERANCE).
    total_l2 = sum(float(p["weight_l2"]) for p in pillars.values())
    if abs(total_l2 - 1.0) > WEIGHT_TOLERANCE:
        raise CatalogValidationError(
            f"[{vertical}] pillar weight_l2 values sum to {total_l2:.6f}, "
            f"expected 1.0 +/- {WEIGHT_TOLERANCE} "
            f"(off by {abs(total_l2 - 1.0):.6f})"
        )

    # Rule: every KPI's `pillar` field references a pillar that exists.
    for kpi_code, kpi in kpis.items():
        pillar_ref = kpi.get("pillar")
        if pillar_ref not in pillars:
            raise CatalogValidationError(
                f"[{vertical}] KPI '{kpi_code}' references pillar "
                f"'{pillar_ref}', which does not exist in this catalog's "
                f"'pillars' dict"
            )

    # Rule: within each pillar, that pillar's KPIs' weight_l1 values sum to
    # 1.0 (+/- WEIGHT_TOLERANCE).
    per_pillar_members: dict[str, list[tuple[str, float]]] = {}
    for kpi_code, kpi in kpis.items():
        per_pillar_members.setdefault(kpi["pillar"], []).append(
            (kpi_code, float(kpi["weight_l1"]))
        )

    for pillar_code in pillars:
        members = per_pillar_members.get(pillar_code, [])
        if not members:
            # A pillar with zero assigned KPIs is not one of the four rules
            # named in the Build Prompt/Acceptance Criteria -- see the
            # validation report's "ambiguous" section. We do not treat it
            # as a hard error here, since the spec never says a pillar must
            # have at least one KPI, only that weights sum correctly among
            # whatever KPIs a pillar *does* have.
            continue
        total_l1 = sum(w for _, w in members)
        if abs(total_l1 - 1.0) > WEIGHT_TOLERANCE:
            raise CatalogValidationError(
                f"[{vertical}] pillar '{pillar_code}' KPI weight_l1 values "
                f"sum to {total_l1:.6f}, expected 1.0 +/- {WEIGHT_TOLERANCE} "
                f"(off by {abs(total_l1 - 1.0):.6f})"
            )

    return pillars, kpis


def _validate_tiers(vertical: str, kpis: dict, tier_data: dict) -> dict:
    """Rule: every tier's kpi_codes must be a subset of the base catalog's
    KPI codes -- reject a tier referencing a KPI code the catalog doesn't
    define (Build Prompt step 2, last bullet)."""
    tiers = tier_data.get("tiers")
    if not isinstance(tiers, dict) or not tiers:
        raise CatalogValidationError(f"[{vertical}] tier file must declare a non-empty 'tiers' dict")

    default_tier = tier_data.get("default_tier")
    if default_tier is not None and default_tier not in tiers:
        raise CatalogValidationError(
            f"[{vertical}] default_tier '{default_tier}' is not one of the "
            f"defined tiers: {sorted(tiers.keys())}"
        )

    for tier_name, tier_def in tiers.items():
        kpi_codes = tier_def.get("kpi_codes", [])
        unknown = [code for code in kpi_codes if code not in kpis]
        if unknown:
            raise CatalogValidationError(
                f"[{vertical}] tier '{tier_name}' references KPI code(s) "
                f"not present in the base catalog: {unknown}"
            )

    return tier_data


def load_catalog(
    vertical: str,
    config_dir: str = DEFAULT_CONFIG_DIR,
    legacy_module_prefix: str = DEFAULT_LEGACY_MODULE_PREFIX,
) -> tuple[dict, dict]:
    """Fixed 3-tier resolution order, cached per vertical after first load
    (Build Prompt step 1):
      Tier 1: JSON file at {config_dir}/{vertical}_kpi_catalog.json
      Tier 2: legacy Python module `{legacy_module_prefix}.{vertical}.kpi_definitions`
              (backward-compat only -- never a valid path for a NEW vertical)
      Tier 3: raise UnknownVerticalError

    Validation (Build Prompt step 2) always runs, on every load, regardless
    of which tier resolved the catalog -- this is deliberately not skippable
    and not tied to any particular authoring path (Gotcha 1).

    If a co-located tier file (`{vertical}_kpi_tiers.json`) exists in the
    same config_dir, it is also validated right now, eagerly, as part of
    this same load -- not deferred until the first get_kpis_for_tier() call.
    The spec's Build Prompt says tier-subset validation must be "wired into
    load_catalog itself" and run "at catalog LOAD time", even though
    load_catalog's own pseudocode signature only returns (pillars, kpis)
    with no tiers involved -- see the validation report for why this is
    flagged as underspecified, and this eager-check as this implementation's
    resolution of that gap. A vertical with no tier file at all is valid;
    tiers are optional.
    """
    key = _cache_key(vertical, config_dir, legacy_module_prefix)
    if key in _catalog_cache:
        return _catalog_cache[key]

    pillars: Optional[dict] = None
    kpis: Optional[dict] = None

    # --- Tier 1: JSON file ---
    json_path = _catalog_path(vertical, config_dir)
    if os.path.isfile(json_path):
        with open(json_path, "r") as f:
            data = json.load(f)
        pillars, kpis = _validate_catalog(vertical, data)

    # --- Tier 2: legacy Python module (only if Tier 1 didn't resolve) ---
    if pillars is None:
        module_name = f"{legacy_module_prefix}.{vertical}.kpi_definitions"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as e:
            # Gotcha 2 ("silent import failures degrade a whole feature to
            # a warning with no loud failure") applies directly to this
            # Tier-2 fallback: the Build Prompt's own pseudocode is just
            # `if module_exists(...): ...`, and the obvious Python
            # implementation of "module_exists" is a bare
            # `try/except ImportError`. That conflates two very different
            # situations:
            #   (a) the target module/package genuinely doesn't exist for
            #       this vertical -- expected, legitimate, falls through to
            #       Tier 3's "Unknown vertical" error.
            #   (b) the target module DOES exist, but something it imports
            #       internally is broken/renamed/missing -- a real bug that
            #       must fail loudly, not get silently misreported as
            #       "Unknown vertical: X" (which sends whoever's debugging
            #       it looking for a missing config file instead of a
            #       broken import).
            # ModuleNotFoundError.name identifies exactly which module
            # import machinery couldn't find. Only treat this as case (a)
            # if the missing name IS the module we asked for (or an
            # ancestor package of it) -- otherwise some other, unrelated
            # import failed while loading it, which is case (b).
            if e.name is not None and (
                module_name == e.name or module_name.startswith(e.name + ".")
            ):
                module = None
            else:
                raise
        if module is not None:
            legacy_pillars = getattr(module, "PILLARS", None)
            legacy_kpis = getattr(module, "KPIS", None)
            if legacy_pillars is None or legacy_kpis is None:
                raise CatalogValidationError(
                    f"[{vertical}] legacy module {module_name} must define "
                    f"both PILLARS and KPIS"
                )
            pillars, kpis = _validate_catalog(
                vertical, {"pillars": legacy_pillars, "kpis": legacy_kpis}
            )

    # --- Tier 3: unknown vertical ---
    if pillars is None:
        raise UnknownVerticalError(f"Unknown vertical: {vertical}")

    _catalog_cache[key] = (pillars, kpis)

    # Eagerly validate a co-located tier file, if any, as part of this same
    # load-time validation pass (see docstring above).
    tiers_path = _tiers_path(vertical, config_dir)
    if os.path.isfile(tiers_path):
        with open(tiers_path, "r") as f:
            tier_data = json.load(f)
        validated_tiers = _validate_tiers(vertical, kpis, tier_data)
        _tier_cache[key] = validated_tiers

    return _catalog_cache[key]


def get_kpis_for_tier(
    vertical: str,
    tier: Optional[str] = None,
    config_dir: str = DEFAULT_CONFIG_DIR,
    legacy_module_prefix: str = DEFAULT_LEGACY_MODULE_PREFIX,
) -> dict:
    """Pure filter over the validated base catalog (Build Prompt step 3):
    given a vertical and a tier name (or the vertical's configured
    default_tier), return only the KPI codes listed for that tier, each
    mapped to its byte-for-byte-identical definition from the full catalog.
    Never a second source of KPI definitions."""
    pillars, kpis = load_catalog(
        vertical, config_dir=config_dir, legacy_module_prefix=legacy_module_prefix
    )
    key = _cache_key(vertical, config_dir, legacy_module_prefix)

    if key not in _tier_cache:
        raise CatalogValidationError(
            f"[{vertical}] no tier file found at "
            f"{_tiers_path(vertical, config_dir)}"
        )
    tier_data = _tier_cache[key]

    tier_name = tier or tier_data.get("default_tier")
    if tier_name is None:
        raise CatalogValidationError(
            f"[{vertical}] no tier specified and no default_tier configured"
        )
    if tier_name not in tier_data["tiers"]:
        raise CatalogValidationError(
            f"[{vertical}] unknown tier '{tier_name}'; known tiers: "
            f"{sorted(tier_data['tiers'].keys())}"
        )

    kpi_codes = tier_data["tiers"][tier_name]["kpi_codes"]
    # kpi_codes were already proven to be a subset of `kpis` at load time
    # (_validate_tiers); this is a pure lookup, not a re-check.
    return {code: kpis[code] for code in kpi_codes}
