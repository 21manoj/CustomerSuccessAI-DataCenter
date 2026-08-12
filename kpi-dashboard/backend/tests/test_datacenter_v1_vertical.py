#!/usr/bin/env python3
"""DataCenterV1 vertical — proof that the GPU-rental neocloud vertical is
auto-discovered, scores through the generic engine, and merges its taxonomy
overlay, all WITHOUT touching dc2_s.

Run:
    cd kpi-dashboard/backend
    python -m pytest tests/test_datacenter_v1_vertical.py -v
    # or standalone:
    python tests/test_datacenter_v1_vertical.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

VERT = "datacenter_v1"


def test_auto_discovered():
    from utils import vertical_registry as vr
    assert VERT in vr._discover_verticals()
    # bare 'datacenter' must still alias to dc2_s (do not shadow it)
    assert vr.normalize_vertical("datacenter") == "dc2_s"
    assert vr.normalize_vertical(VERT) == VERT


def test_catalog_loads_and_weights_sum_to_one():
    from utils.vertical_registry import get_pillars, get_kpis
    pillars, kpis = get_pillars(VERT), get_kpis(VERT)
    assert len(pillars) == 6
    assert len(kpis) == 38
    assert round(sum(p["weight_l2"] for p in pillars.values()), 4) == 1.0
    # per-pillar L1 weights sum to 1.0
    from collections import defaultdict
    wl1 = defaultdict(float)
    for code, kd in kpis.items():
        wl1[kd["pillar"]] += kd.get("weight_l1", 0)
    for pc, s in wl1.items():
        assert round(s, 4) == 1.0, f"{pc} weight_l1 sum={s}"


def _synth(kpis, profile):
    vals = {}
    for code, kd in kpis.items():
        band = kd["ranges"]["healthy" if profile == "healthy" else "critical"]
        vals[code] = (band["min"] + band["max"]) / 2
    return vals


def test_generic_scorer_discriminates():
    from utils.vertical_registry import get_pillars, get_kpis
    from utils.generic_scorer import score_account_health
    pillars, kpis = get_pillars(VERT), get_kpis(VERT)
    healthy, _ = score_account_health(kpi_values=_synth(kpis, "healthy"),
                                      kpi_catalog=kpis, pillar_catalog=pillars)
    bleeding, _ = score_account_health(kpi_values=_synth(kpis, "bleeding"),
                                       kpi_catalog=kpis, pillar_catalog=pillars)
    assert healthy >= 70, f"healthy={healthy}"
    assert bleeding < 50, f"bleeding={bleeding}"


def test_taxonomy_overlay_merges_and_boot_validates():
    from utils.taxonomy_loader import get_taxonomy, validate_all_at_boot
    validate_all_at_boot()  # raises if any overlay (incl. datacenter_v1) is invalid
    t = get_taxonomy(VERT)
    m = t.revenue_bucket_map
    assert "reserved_cluster_idle" in m["at_risk"]          # overlay
    assert "silicon_refresh_interest" in m["expansion"]     # overlay
    assert "churn_risk" in m["at_risk"]                     # base inherited


def test_playbooks_have_no_dangling_kpi_refs():
    from verticals.datacenter_v1.vertical_config import PLAYBOOK_CONFIG
    from utils.vertical_registry import get_kpis
    valid = set(get_kpis(VERT).keys()) | {"OVERALL_HEALTH"}
    assert len(PLAYBOOK_CONFIG) == 12
    for pid, pb in PLAYBOOK_CONFIG.items():
        for k in pb.get("trigger_kpis", []):
            assert k in valid, f"{pid} references unknown KPI {k}"


def test_dc2s_untouched():
    from utils.vertical_registry import get_pillars, get_kpis
    assert len(get_pillars("dc2_s")) == 5
    assert len(get_kpis("dc2_s")) == 38


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn(); print(f"  PASS  {fn.__name__}"); passed += 1
        except Exception as e:
            print(f"  FAIL  {fn.__name__}: {e!r}")
    print(f"\n{passed}/{len(fns)} passed")
    sys.exit(0 if passed == len(fns) else 1)
