"""
Adversarial validation tests for Module 11 spec.

Two kinds of tests:
  * test_ac_*      -> Acceptance-Criteria conformance of the natural reading.
  * test_defect_*  -> PROVE a spec defect by running the spec's own literal logic
                      and demonstrating the failure, with the corrected version
                      passing alongside. Docstring cites spec section + shape.
"""
import hashlib
import os
import subprocess
import sys
import textwrap

import pytest

import impl
from impl import (
    ManifestError, ArcError, ArcRoundtripError,
    load_manifest, resolve_arc, check_arc_vocabulary, assert_arc_roundtrip,
    make_rng, kpi_series, trajectory_value, phase_window, resolve_target,
    generate_all, run_acceptance, run_acceptance_fixed, validate_post_process,
    FakeClient, KpiRange, set_classify_impl,
)

HERE = os.path.dirname(os.path.abspath(__file__))

# FDE-config tables (Config section says the FDE fills these in).
ARC_TEMPLATES = {
    "silent_churn": {}, "crisis_recovery": {}, "steady_performer": {},
    "budget_pressure": {}, "expansion": {},
}
CLASSIFICATION_TO_ARC = {
    "critical": "crisis_recovery",
    "at_risk": "budget_pressure",
    "healthy": "steady_performer",
}


def base_manifest(accounts=None):
    return {
        "customer": {"name": "Acme", "domain": "acme.com", "vertical": "dc2_s",
                     "admin_email": "a@acme.com", "total_arr": 1000000},
        "time_range": {"start": "2025-01", "end": "2025-06", "frequency": "monthly",
                       "data_points_per_kpi": 6},
        "kpis": {"selection": "predictive_11", "count": 11},
        "accounts": accounts if accounts is not None else [
            {"name": "A1", "arr": 500000, "target_health": 80,
             "classification": "healthy", "story_arc": "steady_performer",
             "kpi_trajectory": "stable", "decline_start_month": None,
             "renewal_date": "2026-01", "narrative": "", "lifecycle": None},
        ],
    }


# ---------------------------------------------------------------------------
# Acceptance-Criteria conformance (natural reading works)
# ---------------------------------------------------------------------------
def test_ac_determinism_in_process():
    """AC Determinism: generate_all twice in-process is byte-identical."""
    m = base_manifest()
    a = generate_all(m, make_rng(42))
    b = generate_all(m, make_rng(42))
    assert a == b


def test_ac_kpi_tier_resolution():
    """AC KPI tier resolution: predictive_11 -> 11 codes; explicit codes verbatim."""
    m = base_manifest()
    assert "codes" not in m["kpis"]
    m["kpis"]["codes"] = m["kpis"].get("codes") or impl.module02_tier_codes(m["kpis"]["selection"])
    assert len(m["kpis"]["codes"]) == 11
    explicit = ["P1-KPI1", "P2-KPI2"]
    m2 = base_manifest()
    m2["kpis"]["codes"] = explicit
    got = m2["kpis"].get("codes") or impl.module02_tier_codes(m2["kpis"]["selection"])
    assert got == explicit


def test_ac_phase_window():
    """AC Phase: baseline = first 2/3, intervention = last 1/3."""
    assert list(phase_window(9, "baseline")) == list(range(0, 6))
    assert list(phase_window(9, "intervention")) == list(range(6, 9))
    assert list(phase_window(9, "full")) == list(range(0, 9))


def test_ac_extend_register_exclusive():
    """AC Phase+extend: resolve_target(extend=True, register=True) raises."""
    with pytest.raises(ManifestError):
        resolve_target(True, True)
    assert resolve_target(True, False) == "extend"
    assert resolve_target(False, False) == "register"


def test_ac_trajectory_null_decline_no_crash_and_flat():
    """AC Trajectory nulls: decline_start=None -> no decline, no raise."""
    vals = [trajectory_value("declining", m, 6, 80, 6) for m in range(6)]
    assert all(v == 80 for v in vals)  # ds=months => flat
    series = kpi_series("declining", 6, 80, None, make_rng(1), KpiRange(0, 100))
    assert len(series) == 6  # did not raise


def test_ac_null_lifecycle_no_raise():
    """AC Trajectory nulls: null lifecycle applies no ARR event, no raise."""
    m = base_manifest()
    assert m["accounts"][0]["lifecycle"] is None
    generate_all(m, make_rng(7))  # must not raise


def test_ac_id_discovery_by_name():
    """AC ID discovery (Gotcha 3): match by NAME, read platform account_id."""
    m = base_manifest()
    client = FakeClient([{"name": "A1", "health": 80, "status": "healthy"}])
    res = validate_post_process(m, client, cid=900, tol=5)
    assert res["status"] == "success"
    assert res["discovered_ids"]["A1"] == 7_000_000  # platform id, not manifest formula


def test_ac_vocabulary_fallback_surfaced():
    """AC Vocabulary: fallback-only arc reported with how='fallback'."""
    m = base_manifest([
        {"name": "T", "arr": 1, "target_health": 40, "classification": "critical",
         "story_arc": "land_and_expand", "kpi_trajectory": "declining",
         "decline_start_month": 1, "renewal_date": "", "narrative": "", "lifecycle": None},
    ])
    rep = check_arc_vocabulary(m, ARC_TEMPLATES, CLASSIFICATION_TO_ARC)
    assert rep[0]["how"] == "fallback"
    assert rep[0]["generated_as"] == "crisis_recovery"


def test_ac_vocabulary_unresolvable_raises():
    """AC Vocabulary: no template AND no fallback -> raises."""
    m = base_manifest([
        {"name": "X", "arr": 1, "target_health": 40, "classification": "unknown_class",
         "story_arc": "made_up_arc", "kpi_trajectory": "stable",
         "decline_start_month": None, "renewal_date": "", "narrative": "", "lifecycle": None},
    ])
    with pytest.raises(ArcError):
        check_arc_vocabulary(m, ARC_TEMPLATES, CLASSIFICATION_TO_ARC)


# ===========================================================================
# DEFECT 1 (shape c/d, SEVERITY: HIGHEST) — the headline Gotcha-1 round-trip
# guard is DEFINED but the acceptance harness NEVER invokes it.
# ===========================================================================
def test_defect_1_roundtrip_guard_is_dead_in_harness():
    """
    Defect 1 [shape c/d]. Spec Build Prompt piece 6 `run_acceptance` (SPEC.md
    L238-246) calls only `check_arc_vocabulary` and NEVER `assert_arc_roundtrip`
    (defined piece 2, L166-176). The spec itself calls the round-trip "the guard
    that would have caught silent_churn being reclassified as crisis_recovery"
    (L167-169) and AC 'Arc round-trips' (L274-278) demands the harness catch it,
    yet the harness as written cannot. Proven: a manifest whose story_arc has a
    direct template (so check_arc_vocabulary passes) but whose GENERATED data the
    platform classifier reads as a DIFFERENT canonical arc sails through
    run_acceptance with status 'success'. The corrected harness catches it.
    """
    # silent_churn has a template => vocabulary check is happy.
    m = base_manifest([
        {"name": "S1", "arr": 100, "target_health": 55, "classification": "at_risk",
         "story_arc": "silent_churn", "kpi_trajectory": "declining",
         "decline_start_month": 1, "renewal_date": "", "narrative": "",
         "lifecycle": None},
    ])
    # Platform classifier MISREADS the generated data as crisis_recovery.
    set_classify_impl(lambda nodes: "crisis_recovery")
    client = FakeClient([{"name": "S1", "health": 55, "status": "at_risk"}])

    # LITERAL spec harness: passes despite the misclassification (bug).
    res = run_acceptance(m, client, seed=42, tol=5,
                         ARC_TEMPLATES=ARC_TEMPLATES,
                         CLASSIFICATION_TO_ARC=CLASSIFICATION_TO_ARC)
    assert res["status"] == "success"  # <-- the defect: silent misclassification

    # CORRECTED harness: wires the round-trip guard and catches it.
    intended = {"silent_churn": "silent_churn"}
    with pytest.raises(ArcRoundtripError):
        run_acceptance_fixed(m, client, seed=42, tol=5,
                             ARC_TEMPLATES=ARC_TEMPLATES,
                             CLASSIFICATION_TO_ARC=CLASSIFICATION_TO_ARC,
                             INTENDED_CANONICAL=intended,
                             node_builder=lambda a: {"name": a["name"]})
    set_classify_impl(lambda nodes: nodes.get("intended") if isinstance(nodes, dict) else None)


def test_defect_1b_run_acceptance_source_lacks_roundtrip_call():
    """
    Defect 1 corroboration [shape d, dead code]. Structural proof: the spec's
    run_acceptance body (piece 6) never names assert_arc_roundtrip.
    """
    import inspect
    src = inspect.getsource(run_acceptance)
    assert "check_arc_vocabulary" in src
    assert "assert_arc_roundtrip" not in src  # guard never referenced by harness


# ===========================================================================
# DEFECT 2 (shape c, SEVERITY: HIGH) — INTENDED_CANONICAL is an undefined table
# the round-trip guard needs; the spec references it but never defines or lists
# it (not in Config), so the guard is uninvokable even if wired in.
# ===========================================================================
def test_defect_2_intended_canonical_undefined():
    """
    Defect 2 [shape c]. `assert_arc_roundtrip` (SPEC.md L166-176) indexes
    `INTENDED_CANONICAL[story_arc]`, but INTENDED_CANONICAL is never defined
    anywhere in the spec: not in Data Shapes, not in Engine/Config (Config lists
    ARC_TEMPLATES, tiers, tolerance, seed — NOT this table), and run_acceptance
    has no parameter or global for it. A guard whose lookup table is undefined
    cannot run. Proven by executing the spec-literal guard body in a namespace
    that contains only what the spec defines -> KeyError/NameError.
    """
    literal = textwrap.dedent('''
        def assert_arc_roundtrip(story_arc, generated_nodes, INTENDED_CANONICAL):
            produced = module04_classify_arc(generated_nodes)
            intended = INTENDED_CANONICAL[story_arc]
            return produced == intended
    ''')
    ns = {"module04_classify_arc": lambda n: "silent_churn"}
    exec(literal, ns)
    # The spec never populates INTENDED_CANONICAL, so any real story_arc misses.
    with pytest.raises(KeyError):
        ns["assert_arc_roundtrip"]("silent_churn", {}, {})  # empty == what spec provides

    # Corrected: the table must be a named Config deliverable.
    INTENDED_CANONICAL = {"silent_churn": "silent_churn"}
    assert ns["assert_arc_roundtrip"]("silent_churn", {}, INTENDED_CANONICAL) is True


# ===========================================================================
# DEFECT 3 (shape a/c, SEVERITY: HIGH) — run_acceptance uses ARC_TEMPLATES and
# CLASSIFICATION_TO_ARC as bare globals, but piece 2 only ever defines them as
# function PARAMETERS and Config marks them FDE-supplied. As literally written
# the harness raises NameError.
# ===========================================================================
def test_defect_3_run_acceptance_bare_globals_nameerror():
    """
    Defect 3 [shape a/c]. Build Prompt piece 6 (SPEC.md L239) calls
    `check_arc_vocabulary(manifest, ARC_TEMPLATES, CLASSIFICATION_TO_ARC)` with
    ARC_TEMPLATES / CLASSIFICATION_TO_ARC as bare names, yet piece 2 defines them
    only as parameters (L146,154) and Config (L108-110) says the FDE supplies
    them per-client. No piece assigns them at module scope. Executed literally,
    run_acceptance raises NameError. Proven below; corrected reading threads them
    as parameters (as impl.run_acceptance does).
    """
    literal = textwrap.dedent('''
        def run_acceptance(manifest):
            return check_arc_vocabulary(manifest, ARC_TEMPLATES, CLASSIFICATION_TO_ARC)
    ''')
    ns = {"check_arc_vocabulary": lambda m, t, c: "ok"}
    exec(literal, ns)
    with pytest.raises(NameError):
        ns["run_acceptance"]({"accounts": []})


# ===========================================================================
# DEFECT 4 (shape d, SEVERITY: MEDIUM) — trajectory / harness constants are
# named but never given numeric values or listed as Config: NOISE_SD,
# DECAY_PER_MONTH, RECOVERY_LAG, RECOVERY_PER_MONTH, IMPROVE_PER_MONTH,
# HEALTH_TOL. Left as prose. Executed literally -> NameError.
# ===========================================================================
def test_defect_4_undefined_trajectory_constants_nameerror():
    """
    Defect 4 [shape d]. Piece 4 (SPEC.md L203-214) uses DECAY_PER_MONTH,
    RECOVERY_LAG, RECOVERY_PER_MONTH, IMPROVE_PER_MONTH and piece 4/6 use
    NOISE_SD / HEALTH_TOL, none of which the spec ever assigns a value. Config
    (L108-110) lists only 'the health tolerance' and 'the seed' — the trajectory
    constants are numeric conversions left as prose. Literal execution NameErrors.
    """
    literal = textwrap.dedent('''
        def trajectory_value(traj, m, months, target, ds):
            if traj == "declining":
                return target - DECAY_PER_MONTH * max(0, m - ds)
            return target
    ''')
    ns = {}
    exec(literal, ns)
    with pytest.raises(NameError):
        ns["trajectory_value"]("declining", 3, 6, 80, 1)

    # Corrected: constants are defined (impl.py supplies natural values).
    assert trajectory_value("declining", 3, 6, 80, 1) == 80 - impl.DECAY_PER_MONTH * 2


# ===========================================================================
# DEFECT 5 (shape c, SEVERITY: MEDIUM) — generate_all has no Build-Prompt piece.
# It is called by run_acceptance (L240) and is THE subject of the Determinism
# Acceptance Criterion (L270-273), yet no piece defines it or states its
# determinism contract. A natural per-KPI-stream reading reintroduces the
# Gotcha-2 hash-seed bug: passes in-process, fails cross-process.
# ===========================================================================
def test_defect_5_generate_all_unspecified_determinism_contract():
    """
    Defect 5 [shape c, ties to Gotcha 2 / AC Determinism]. `generate_all` is
    referenced (SPEC.md L240, L270) but never defined by any of the six pieces.
    make_rng looks disciplined, but the determinism headline actually rests on
    generate_all, which the spec never constrains. A natural FDE reading that
    gives each KPI its own independent stream seeds it from hash(kpi_code) —
    reproducible in-process, NON-reproducible across PYTHONHASHSEED. Proven: the
    'bad' generator is stable in-process but differs across two subprocesses with
    PYTHONHASHSEED=0 and =1; the 'good' (single-rng) generator stays identical.
    """
    def run(which, hashseed):
        env = dict(os.environ, PYTHONHASHSEED=str(hashseed))
        out = subprocess.check_output(
            [sys.executable, os.path.join(HERE, "gen_scripts.py"), which],
            env=env)
        return out.decode().strip()

    # in-process stability of the bad generator (why the bug hides):
    import gen_scripts
    assert gen_scripts.bad_generate() == gen_scripts.bad_generate()

    good0, good1 = run("good", 0), run("good", 1)
    bad0, bad1 = run("bad", 0), run("bad", 1)

    assert good0 == good1, "single-rng discipline must be cross-process stable"
    assert bad0 != bad1, "hash-seeded stream must break cross-process (the Gotcha-2 bug)"


# ===========================================================================
# DEFECT 6 (shape d, SEVERITY: MEDIUM) — lifecycle ARR-event behavior is a
# required deliverable in prose with NO code. Data Shapes + Nullable rule
# (L82,97-100) and AC (L300-301) require applying a lifecycle event's delta_pct
# (and doing nothing when null), but no Build-Prompt piece touches lifecycle at
# all. The null case "passes" only vacuously; the positive case is unimplemented.
# ===========================================================================
def test_defect_6_lifecycle_has_no_implementation():
    """
    Defect 6 [shape d]. No piece (1-6) references `lifecycle` / `delta_pct`.
    kpi_series' signature (L194) has no lifecycle parameter, and generate_all is
    undefined. So 'a null lifecycle applies no ARR event without raising' is true
    only because nothing consumes lifecycle; the required non-null behavior
    (apply delta_pct as an ARR expand/contract/churn event) has no code anywhere.
    """
    import inspect
    for fn in (kpi_series, trajectory_value):
        assert "lifecycle" not in inspect.getsource(fn)
        assert "delta_pct" not in inspect.getsource(fn)
    # A non-null lifecycle event carries delta_pct but there is no code path that
    # would move ARR by it -> the behavior is unpopulated (dead requirement).
    m = base_manifest([
        {"name": "E", "arr": 100000, "target_health": 80, "classification": "healthy",
         "story_arc": "steady_performer", "kpi_trajectory": "stable",
         "decline_start_month": None, "renewal_date": "", "narrative": "",
         "lifecycle": {"event": "expand", "event_month": 3, "delta_pct": 25}},
    ])
    csvs = generate_all(m, make_rng(1))
    # ARR in the emitted account row is unchanged by the +25% expand event:
    assert "100000" in csvs["account_details.csv"]
    assert "125000" not in csvs["account_details.csv"]  # event never applied


# ===========================================================================
# GOLDEN acceptance path + post-load-steps assertion (AC + Reference Harness 4)
# ===========================================================================
def test_ac_golden_path_and_post_load_steps_run():
    """AC Golden onboarding + Post-load steps required (Gotchas 4,5)."""
    impl._CALLS["wizard_d"].clear()
    m = base_manifest([
        {"name": "A1", "arr": 500000, "target_health": 80, "classification": "healthy",
         "story_arc": "steady_performer", "kpi_trajectory": "stable",
         "decline_start_month": None, "renewal_date": "", "narrative": "", "lifecycle": None},
        {"name": "A2", "arr": 250000, "target_health": 45, "classification": "critical",
         "story_arc": "crisis_recovery", "kpi_trajectory": "recovering",
         "decline_start_month": 1, "renewal_date": "", "narrative": "", "lifecycle": None},
    ])
    client = FakeClient([
        {"name": "A1", "health": 82, "status": "healthy"},
        {"name": "A2", "health": 43, "status": "critical"},
    ])
    res = run_acceptance(m, client, seed=42, tol=5,
                         ARC_TEMPLATES=ARC_TEMPLATES,
                         CLASSIFICATION_TO_ARC=CLASSIFICATION_TO_ARC)
    assert res["status"] == "success"
    assert all(r["within_tolerance"] for r in res["per_account"])
    # Post-load steps actually ran:
    assert impl._CALLS["wizard_d"], "wizard_d_recalibration must run (Gotcha 5)"
    assert client.backfilled, "backfill_playbook_attribution must run (Gotcha 4)"


def test_ac_recovering_is_a_real_V():
    """Sanity: recovering trajectory declines then recovers (not monotonic)."""
    ds = 1
    vals = [trajectory_value("recovering", m, 12, 80, ds) for m in range(12)]
    trough = min(vals)
    trough_idx = vals.index(trough)
    assert trough < vals[0]          # it declined
    assert vals[-1] > trough         # then recovered
    assert 0 < trough_idx < 11       # V, not an L or a line
