"""
Onboarding custom-weight validation — vertical-coupling guard tests
(Aug 21 2026 vertical-coupling audit, bug A).

`validate_dc2s_pillar_weights` / `validate_dc2s_kpi_weights` in
onboarding_api_v2_config_aware.py used to check submitted /complete
pillar/KPI weights against hardcoded DC2S_PILLAR_NAMES / DC2S_KPIS
constants regardless of the `vertical` field in the same onboarding
request. This was a functional blocker, not a display bug: any
non-dc2_s customer (saas_premium, datacenter_v1, healthcare_provider)
submitting custom pillar/KPI weights valid for THEIR OWN vertical's
real catalog was rejected with "unknown pillar/KPI names" — e.g. a
datacenter_v1 customer (6 pillars, P1-P6) could never set a weight on
P6, because dc2_s only has P1-P5.

Fix: both validators (and the sibling enabled_pillars/enabled_kpis
inline checks in the /complete handler) now take a `vertical` argument
and resolve valid pillar/KPI codes via utils.vertical_registry
(get_pillars/get_kpis) instead of the hardcoded dc2_s constants, with a
fail-closed error (not a silent dc2_s fallback) if the vertical's
catalog can't be loaded.

No Flask app or DB needed — validate_dc2s_pillar_weights/
validate_dc2s_kpi_weights are pure functions; same convention as
test_vertical_catalog_consistency.py.
"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from onboarding_api_v2_config_aware import (  # noqa: E402
    validate_dc2s_pillar_weights,
    validate_dc2s_kpi_weights,
)


# ──────────────────────────────────────────────────────────────────────────
# Pillar weights
# ──────────────────────────────────────────────────────────────────────────

def test_datacenter_v1_custom_pillar_weights_with_p6_accepted():
    """datacenter_v1 has 6 pillars (P1-P6); a customer must be able to set
    a non-default weight on P6, which does not exist in dc2_s's 5-pillar
    catalog. This is the exact submission the audit says was never
    exercised by the earlier 'e2e verified' onboarding runs (those used
    default weights)."""
    custom_weights = {
        "P1": 0.20, "P2": 0.20, "P3": 0.20,
        "P4": 0.15, "P5": 0.15, "P6": 0.10,
    }
    ok, err = validate_dc2s_pillar_weights(custom_weights, "datacenter_v1")
    assert ok, f"valid datacenter_v1 P6 weights were rejected: {err}"
    assert err is None


def test_saas_premium_custom_pillar_weights_accepted():
    """saas_premium is a real, registered non-dc2_s vertical; non-default
    custom weights for its own 5 pillars must be accepted."""
    custom_weights = {"P1": 0.10, "P2": 0.40, "P3": 0.10, "P4": 0.10, "P5": 0.30}
    ok, err = validate_dc2s_pillar_weights(custom_weights, "saas_premium")
    assert ok, f"valid saas_premium weights were rejected: {err}"


def test_datacenter_v1_p6_weight_rejected_against_dc2s_catalog():
    """Sanity check on the OLD behavior: P6 is genuinely not a dc2_s pillar,
    so validating a P6 weight against the dc2_s catalog must still fail.
    This proves the test is discriminating on the catalog actually used,
    not just always returning True."""
    ok, err = validate_dc2s_pillar_weights({"P6": 1.0}, "dc2_s")
    assert not ok
    assert "P6" in err


def test_unknown_vertical_pillar_weights_fail_closed_not_dc2s_default():
    """An unresolvable vertical must error out, not silently validate
    against dc2_s's catalog (fail-closed, matching vertical_registry's
    get_vertical_for_customer / get_kpi_catalog convention elsewhere)."""
    ok, err = validate_dc2s_pillar_weights({"P1": 1.0}, "totally_made_up_vertical")
    assert not ok
    assert "totally_made_up_vertical" in err


# ──────────────────────────────────────────────────────────────────────────
# KPI-level weights
# ──────────────────────────────────────────────────────────────────────────

def test_datacenter_v1_custom_kpi_weights_for_p6_accepted():
    """P6-KPI* codes only exist in datacenter_v1's catalog, not dc2_s's."""
    custom_kpi_weights = {
        "P6": {"P6-KPI1": 0.5, "P6-KPI2": 0.3, "P6-KPI3": 0.2},
    }
    ok, err = validate_dc2s_kpi_weights(custom_kpi_weights, "datacenter_v1")
    assert ok, f"valid datacenter_v1 P6 KPI weights were rejected: {err}"


def test_saas_premium_custom_kpi_weights_accepted():
    custom_kpi_weights = {"P1": {"P1-KPI1": 0.6, "P1-KPI2": 0.4}}
    ok, err = validate_dc2s_kpi_weights(custom_kpi_weights, "saas_premium")
    assert ok, f"valid saas_premium KPI weights were rejected: {err}"


def test_datacenter_v1_p6_kpi_weights_rejected_against_dc2s_catalog():
    ok, err = validate_dc2s_kpi_weights({"P6": {"P6-KPI1": 1.0}}, "dc2_s")
    assert not ok
    assert "P6" in err


def test_default_vertical_argument_still_validates_as_dc2s():
    """Backward compatibility: callers that don't pass `vertical` keep
    validating against dc2_s (the historical default)."""
    ok, err = validate_dc2s_pillar_weights({"P1": 0.5, "P2": 0.5})
    assert ok, err
    ok2, err2 = validate_dc2s_pillar_weights({"P6": 1.0})
    assert not ok2
    assert "P6" in err2
