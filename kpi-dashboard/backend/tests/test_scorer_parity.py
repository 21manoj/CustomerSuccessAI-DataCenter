#!/usr/bin/env python3
"""
Scorer Parity Test — DC2_S Python Scorer vs Generic JSON Scorer
================================================================

Validates that the generic JSON-based scorer produces identical results to the
DC2_S-specific Python scorer for all edge cases. This test MUST pass before
routing DC2_S through the generic scorer.

Run:
    cd kpi-dashboard/backend
    python -m pytest tests/test_scorer_parity.py -v
    # or standalone:
    python tests/test_scorer_parity.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.generic_scorer import score_kpi, score_account_health, load_catalog_from_json
from verticals.dc2_s.api_routes import _score_kpi_value

# Load the DC2_S JSON catalog (single source of truth)
CATALOG_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'config', 'dc2s_kpi_catalog.json'
)
KPI_CATALOG, PILLAR_CATALOG = load_catalog_from_json(CATALOG_PATH)

# All 38 KPI codes
ALL_KPI_CODES = list(KPI_CATALOG.keys())
assert len(ALL_KPI_CODES) == 38, f"Expected 38 KPIs, got {len(ALL_KPI_CODES)}"

TOLERANCE = 0.01  # Score parity tolerance


# ============================================================
# L1 PARITY: Individual KPI scoring
# ============================================================

def test_l1_score_parity_per_kpi():
    """Each KPI scored identically by both scorers at 5 test points."""
    failures = []

    for kpi_code in ALL_KPI_CODES:
        kpi_def = KPI_CATALOG[kpi_code]
        ranges = kpi_def.get('ranges', {})
        higher_is_better = kpi_def.get('higher_is_better', True)

        # Generate 5 test values spanning the full range
        test_values = _generate_test_values(kpi_def, higher_is_better, ranges)

        for val in test_values:
            python_score = _score_kpi_value(val, kpi_def)
            generic_score = score_kpi(val, kpi_def)

            if abs(python_score - generic_score) > TOLERANCE:
                failures.append(
                    f"  {kpi_code} @ {val}: python={python_score:.2f} generic={generic_score:.2f} "
                    f"delta={abs(python_score - generic_score):.4f}"
                )

    if failures:
        print(f"\n❌ L1 PARITY FAILURES ({len(failures)}):")
        for f in failures:
            print(f)
        assert False, f"{len(failures)} L1 parity failures"
    else:
        print(f"✅ L1 parity: {len(ALL_KPI_CODES)} KPIs × 5 test points = {len(ALL_KPI_CODES) * 5} checks passed")


def _generate_test_values(kpi_def, higher_is_better, ranges):
    """Generate 5 test values: deep critical, boundary, mid-risk, at-target, above-healthy."""
    target_raw = kpi_def.get('target', 100)
    target = target_raw.get('value', 100) if isinstance(target_raw, dict) else target_raw

    healthy = ranges.get('healthy', {})
    critical = ranges.get('critical', {})

    if higher_is_better:
        floor = critical.get('min', 0)
        ceiling = healthy.get('max', target * 1.2 if target else 100)
        return [
            floor,                                # score → 0
            floor + (target - floor) * 0.3,       # deep critical
            target * 0.85,                         # risk zone
            target,                                # at target → 70
            ceiling,                               # max healthy → 100
        ]
    else:
        floor = healthy.get('min', 0)
        ceiling = critical.get('max', target * 4 if target else 100)
        return [
            ceiling,                               # score → 0
            target * 2.5,                          # deep critical
            target * 1.2,                          # risk zone
            target,                                # at target → 70
            floor if floor > 0 else target * 0.5,  # healthy zone
        ]


# ============================================================
# L2+L3 PARITY: Full account health scoring
# ============================================================

def _build_kpi_values(health_level: str) -> dict:
    """Build synthetic KPI values for a given health level."""
    values = {}
    for kpi_code, kpi_def in KPI_CATALOG.items():
        target_raw = kpi_def.get('target', 100)
        target = target_raw.get('value', 100) if isinstance(target_raw, dict) else target_raw
        ranges = kpi_def.get('ranges', {})
        higher_is_better = kpi_def.get('higher_is_better', True)

        if health_level == 'all_healthy':
            # Values well above target (higher_is_better) or well below (lower_is_better)
            if higher_is_better:
                healthy_max = ranges.get('healthy', {}).get('max', target * 1.2)
                values[kpi_code] = target + (healthy_max - target) * 0.8
            else:
                healthy_min = ranges.get('healthy', {}).get('min', 0)
                values[kpi_code] = target - (target - healthy_min) * 0.8

        elif health_level == 'all_critical':
            # Values in deep critical zone
            if higher_is_better:
                floor = ranges.get('critical', {}).get('min', 0)
                values[kpi_code] = floor + (target - floor) * 0.1
            else:
                ceiling = ranges.get('critical', {}).get('max', target * 4)
                values[kpi_code] = ceiling - (ceiling - target) * 0.1

        elif health_level == 'at_target':
            values[kpi_code] = target

        elif health_level == 'mixed':
            # Alternate healthy/critical by pillar
            pillar = kpi_def.get('pillar', '')
            pillar_num = int(pillar[1]) if len(pillar) >= 2 and pillar[1].isdigit() else 1
            if pillar_num % 2 == 1:  # P1, P3, P5 healthy
                if higher_is_better:
                    healthy_max = ranges.get('healthy', {}).get('max', target * 1.2)
                    values[kpi_code] = target + (healthy_max - target) * 0.7
                else:
                    healthy_min = ranges.get('healthy', {}).get('min', 0)
                    values[kpi_code] = target - (target - healthy_min) * 0.7
            else:  # P2, P4 critical
                if higher_is_better:
                    floor = ranges.get('critical', {}).get('min', 0)
                    values[kpi_code] = floor + (target - floor) * 0.15
                else:
                    ceiling = ranges.get('critical', {}).get('max', target * 4)
                    values[kpi_code] = ceiling - (ceiling - target) * 0.15

    return values


def _run_both_scorers(kpi_values, pillar_weight_overrides=None):
    """Run both scorers on the same data and return results."""
    # Generic scorer (what we're migrating to)
    generic_health, generic_pillars = score_account_health(
        kpi_values=kpi_values,
        kpi_catalog=KPI_CATALOG,
        pillar_catalog=PILLAR_CATALOG,
        pillar_weight_overrides=pillar_weight_overrides,
    )

    # DC2_S Python scorer (what we're retiring)
    # NOTE: We call it without customer_id so it uses catalog defaults
    # (same as generic scorer with no overrides)
    from verticals.dc2_s.api_routes import calculate_kpi_health
    python_health, python_pillars = calculate_kpi_health(
        kpi_values=kpi_values,
        customer_id=None,
        vertical='dc2_s',
        pillar_weight_overrides=pillar_weight_overrides,
    )

    return (python_health, python_pillars), (generic_health, generic_pillars)


def test_l2_l3_all_healthy():
    """All KPIs in healthy range → both scorers agree."""
    kpi_values = _build_kpi_values('all_healthy')
    (py_h, py_p), (gen_h, gen_p) = _run_both_scorers(kpi_values)
    _assert_parity("all_healthy", py_h, py_p, gen_h, gen_p)


def test_l2_l3_all_critical():
    """All KPIs in critical range → both scorers agree."""
    kpi_values = _build_kpi_values('all_critical')
    (py_h, py_p), (gen_h, gen_p) = _run_both_scorers(kpi_values)
    _assert_parity("all_critical", py_h, py_p, gen_h, gen_p)


def test_l2_l3_at_target():
    """All KPIs exactly at target → both scorers agree (score ≈ 70)."""
    kpi_values = _build_kpi_values('at_target')
    (py_h, py_p), (gen_h, gen_p) = _run_both_scorers(kpi_values)
    _assert_parity("at_target", py_h, py_p, gen_h, gen_p)
    # Also verify target maps to ~70
    assert 68 <= gen_h <= 72, f"At-target health should be ~70, got {gen_h:.1f}"


def test_l2_l3_mixed():
    """Mixed health (P1/P3/P5 healthy, P2/P4 critical) → both scorers agree."""
    kpi_values = _build_kpi_values('mixed')
    (py_h, py_p), (gen_h, gen_p) = _run_both_scorers(kpi_values)
    _assert_parity("mixed", py_h, py_p, gen_h, gen_p)


def test_l2_l3_missing_kpis():
    """Only 10 of 38 KPIs provided → both scorers agree."""
    full = _build_kpi_values('at_target')
    partial = dict(list(full.items())[:10])
    (py_h, py_p), (gen_h, gen_p) = _run_both_scorers(partial)
    _assert_parity("missing_kpis (10/38)", py_h, py_p, gen_h, gen_p)


def test_l2_l3_with_weight_overrides():
    """Custom pillar weight overrides → both scorers agree."""
    kpi_values = _build_kpi_values('mixed')
    overrides = {"P1": 0.40, "P2": 0.10, "P3": 0.20, "P4": 0.10, "P5": 0.20}
    (py_h, py_p), (gen_h, gen_p) = _run_both_scorers(kpi_values, pillar_weight_overrides=overrides)
    _assert_parity("weight_overrides", py_h, py_p, gen_h, gen_p)


def test_l2_l3_boundary_values():
    """KPI values exactly at range boundaries → both scorers agree."""
    kpi_values = {}
    for kpi_code, kpi_def in KPI_CATALOG.items():
        ranges = kpi_def.get('ranges', {})
        risk = ranges.get('risk', {})
        higher_is_better = kpi_def.get('higher_is_better', True)
        # Use the risk boundary value (should score ~50)
        if higher_is_better:
            kpi_values[kpi_code] = risk.get('min', 50)
        else:
            kpi_values[kpi_code] = risk.get('max', 50)

    (py_h, py_p), (gen_h, gen_p) = _run_both_scorers(kpi_values)
    _assert_parity("boundary_values", py_h, py_p, gen_h, gen_p)


def test_l2_l3_single_pillar():
    """Only P3 KPIs provided → both scorers agree on P3 score."""
    full = _build_kpi_values('at_target')
    p3_only = {k: v for k, v in full.items() if k.startswith('P3-')}
    (py_h, py_p), (gen_h, gen_p) = _run_both_scorers(p3_only)
    _assert_parity("single_pillar_P3", py_h, py_p, gen_h, gen_p)


def _assert_parity(label, py_health, py_pillars, gen_health, gen_pillars):
    """Assert both scorers produce matching results."""
    delta = abs(py_health - gen_health)
    if delta > TOLERANCE:
        print(f"\n❌ {label}: overall health mismatch: python={py_health:.2f} generic={gen_health:.2f} delta={delta:.4f}")
        print(f"  Python pillars: {py_pillars}")
        print(f"  Generic pillars: {gen_pillars}")
        assert False, f"{label}: overall health delta {delta:.4f} > {TOLERANCE}"

    # Check pillar parity
    all_pillars = set(list(py_pillars.keys()) + list(gen_pillars.keys()))
    pillar_failures = []
    for p in sorted(all_pillars):
        py_val = py_pillars.get(p, 0)
        gen_val = gen_pillars.get(p, 0)
        pdelta = abs(py_val - gen_val)
        if pdelta > TOLERANCE:
            pillar_failures.append(f"  {p}: python={py_val:.2f} generic={gen_val:.2f} delta={pdelta:.4f}")

    if pillar_failures:
        print(f"\n❌ {label}: pillar mismatches:")
        for f in pillar_failures:
            print(f)
        assert False, f"{label}: {len(pillar_failures)} pillar mismatches"

    print(f"✅ {label}: health={gen_health:.1f}, pillars={len(gen_pillars)}, delta={delta:.4f}")


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("SCORER PARITY TEST — DC2_S Python vs Generic JSON")
    print("=" * 60)
    print(f"Catalog: {len(ALL_KPI_CODES)} KPIs, {len(PILLAR_CATALOG)} pillars\n")

    # L1 tests
    print("--- L1: Individual KPI scoring ---")
    test_l1_score_parity_per_kpi()

    # L2+L3 tests
    print("\n--- L2+L3: Full account health scoring ---")
    test_l2_l3_all_healthy()
    test_l2_l3_all_critical()
    test_l2_l3_at_target()
    test_l2_l3_mixed()
    test_l2_l3_missing_kpis()
    test_l2_l3_with_weight_overrides()
    test_l2_l3_boundary_values()
    test_l2_l3_single_pillar()

    print(f"\n{'=' * 60}")
    print("ALL PARITY TESTS PASSED ✅")
    print(f"{'=' * 60}")
