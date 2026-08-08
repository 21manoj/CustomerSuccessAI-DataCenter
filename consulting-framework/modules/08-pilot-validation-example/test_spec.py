"""
Adversarial validation tests for Module 08 (Persona Dashboards), built from
SPEC.md alone. AC tests confirm the spec's happy paths; test_defect_* tests
PROVE defects by executing the spec's literal logic, each with the corrected
behavior alongside.
"""
import inspect
import re
import pytest

import impl
from impl import (
    Account, account_arr, assigned_csm, partition_accounts, rollup_L4,
    exposure_risk, revenue_bundle, build_dashboard, persona_lens,
    assert_persona_parity, assert_surface_parity,
)


# ---------------------------------------------------------------------------
# Harness: wire the dependency hooks against in-memory fixtures.
# ---------------------------------------------------------------------------
def wire(monkeypatch, accounts, *, at_risk=1_000_000.0, protected=500_000.0,
         expansion=250_000.0, arr_basis="sum_active_arr", arr_basis_value=1_000_000.0,
         scores=None, signals=None, wizard_b=1.05, predictor=0.97):
    """scores: dict account_id -> (health_L3, pillars, status)."""
    monkeypatch.setattr(impl, "module01_accounts_for_customer",
                        lambda cid: list(accounts))

    def read_scores(aid):
        if scores is not None and aid in scores:
            return scores[aid]
        # default: derive from a `_health` marker stashed on the account
        acct = next(a for a in accounts if a.account_id == aid)
        return (getattr(acct, "_health", None), {"p1": 1}, acct.account_status)

    monkeypatch.setattr(impl, "module03_read_scores", read_scores)
    monkeypatch.setattr(impl, "module04_aggregate_revenue_with_provenance",
                        lambda cid: {"at_risk": at_risk, "protected": protected,
                                     "expansion": expansion, "arr_basis": arr_basis,
                                     "arr_basis_value": arr_basis_value})
    monkeypatch.setattr(impl, "module04_open_signals",
                        lambda cid: list(signals if signals is not None else []))
    monkeypatch.setattr(impl, "module05_wizard_b_nrr", lambda cid: wizard_b)
    monkeypatch.setattr(impl, "module05_predictor_v3_nrr", lambda cid: predictor)
    # ensure envelope is the extended one for non-envelope tests
    monkeypatch.setattr(impl, "envelope", impl.envelope_with_persona)


def acct(aid, health, arr=None, status="active", meta=None, revenue=None):
    a = Account(aid, account_status=status, revenue=revenue,
                profile_metadata=(meta if meta is not None else
                                  ({"arr": arr} if arr is not None else None)))
    a._health = health
    return a


# ===========================================================================
# ACCEPTANCE CRITERIA
# ===========================================================================
def test_ac_L4_revenue_weighted_churned_excluded(monkeypatch):
    accts = [acct("a", 80, 900_000), acct("b", 40, 100_000),
             acct("c", 10, 5_000_000, status="churned")]
    wire(monkeypatch, accts)
    p = build_dashboard(1, "vpcs")
    ph = p["portfolio_health"]
    assert ph["health"] == 76.0
    assert ph["method"] == "revenue_weighted"
    assert p["churn"] == {"churned_count": 1, "churned_arr": 5_000_000.0}
    # churned moves neither health nor exposure
    active, churned = partition_accounts(1)
    assert exposure_risk(active) == {"critical": 100_000.0, "at_risk": 0.0}


def test_ac_zero_arr_counted_not_hidden(monkeypatch):
    accts = [acct("a", 80, 900_000), acct("b", 40, 100_000), acct("z", 20, 0)]
    wire(monkeypatch, accts)
    active, _ = partition_accounts(1)
    r = rollup_L4(active)
    assert r["health"] == 76.0          # zero weight -> unchanged
    assert r["n_zero_arr"] == 1
    assert r["n_scored"] == 3


def test_ac_all_zero_arr_simple_mean(monkeypatch):
    accts = [acct("a", 80, 0), acct("b", 40, 0)]
    wire(monkeypatch, accts)
    active, _ = partition_accounts(1)
    r = rollup_L4(active)
    assert r["method"] == "simple_unweighted"
    assert r["health"] == 60.0


def test_ac_none_vs_real_50(monkeypatch):
    # None-missing rollup differs from a real 50.0
    a_none = [acct("a", 80, 100_000), acct("b", None, 100_000)]
    a_real = [acct("a", 80, 100_000), acct("b", 50.0, 100_000)]
    wire(monkeypatch, a_none)
    r_none = rollup_L4(partition_accounts(1)[0])
    wire(monkeypatch, a_real)
    r_real = rollup_L4(partition_accounts(1)[0])
    assert r_none["health"] == 80.0 and r_none["n_no_data"] == 1 and r_none["n_scored"] == 1
    assert r_real["health"] == 65.0 and r_real["n_no_data"] == 0 and r_real["n_scored"] == 2
    assert r_none["health"] != r_real["health"]


def test_ac_cold_start_all_none(monkeypatch):
    accts = [acct("a", None, 100_000), acct("b", None, 200_000)]
    wire(monkeypatch, accts)
    r = rollup_L4(partition_accounts(1)[0])
    assert r["health"] is None and r["method"] == "no_scored_accounts"
    p = build_dashboard(1, "cro")           # must not raise
    assert p["persona"] == "cro"


def test_ac_leading_not_filtered_by_trailing(monkeypatch):
    sigs = [{"account_id": "a", "signal": "churn_risk"}]
    accts = [acct("a", 85, 100_000)]
    wire(monkeypatch, accts, signals=sigs)
    _, leading1 = impl.build_layers(1, partition_accounts(1)[0])
    # raise all health above threshold; signals must be unchanged
    for a in accts:
        a._health = 99
    _, leading2 = impl.build_layers(1, partition_accounts(1)[0])
    assert leading1["signals"] == leading2["signals"] == sigs


def test_ac_revenue_from_bundle(monkeypatch):
    accts = [acct("a", 30, 10_000_000)]   # summed ARR (10M) != assessed at_risk (1M)
    wire(monkeypatch, accts, at_risk=1_000_000.0)
    for persona in ("cro", "cfo", "ceo"):
        p = build_dashboard(1, persona)
        assert p["revenue_at_risk"] == 1_000_000.0    # assessed number wins


def test_ac_persona_parity_passes(monkeypatch):
    wire(monkeypatch, [acct("a", 70, 100_000)])
    assert_persona_parity(1)   # no raise


def test_ac_surface_parity_passes(monkeypatch):
    wire(monkeypatch, [acct("a", 70, 100_000)])
    assert_surface_parity(1, "cro", build_dashboard, build_dashboard)


def test_ac_assigned_csm_from_json(monkeypatch):
    a = Account("a", profile_metadata={"assigned_csm": "Dana"})
    assert assigned_csm(a) == "Dana"
    b = Account("b", profile_metadata=None)
    assert assigned_csm(b) is None            # no raise


def test_ac_envelope_scope(monkeypatch):
    wire(monkeypatch, [acct("a", 70, 100_000)])
    p = build_dashboard(1, "cro")
    assert p["scope"] == "portfolio"
    q = build_dashboard(1, "ceo", mode="portfolio_of_customers")
    assert q["scope"] == "platform" and q["mode"] == "portfolio_of_customers"
    assert q["persona"] == "ceo"


def test_ac_arr_precedence_revenue_and_none():
    assert account_arr(Account("x", revenue=500_000)) == 500_000.0   # revenue column
    assert account_arr(Account("y", profile_metadata=None)) == 0.0    # nothing -> 0
    assert account_arr(Account("z", profile_metadata={"arr": 777})) == 777.0  # arr wins


# ===========================================================================
# DEFECT PROOFS
# ===========================================================================
def test_defect_1_envelope_persona_signature_mismatch(monkeypatch):
    """
    DEFECT (shape a): contradiction between the envelope CONTRACT the spec
    documents and the envelope CALL piece 5 makes.

    Spec Dependencies (~L80), Data Shapes (~L105) and piece-5 note (L313)
    document Module 07's helper as `envelope(scope, payload, arr_basis=,
    arr_basis_value=)` -- NO `persona` parameter. Yet build_dashboard (piece 5,
    L296) calls `envelope(..., persona=persona, ...)`. Under the documented
    contract that call is a TypeError: the whole persona dashboard 500s, and no
    payload is ever produced. The spec cannot rely on a Module-07 change it does
    not own and does not verify.
    """
    wire(monkeypatch, [acct("a", 70, 100_000)])
    # Bind envelope to the contract the spec literally documents (no persona):
    monkeypatch.setattr(impl, "envelope", impl.envelope_documented)
    with pytest.raises(TypeError):
        build_dashboard(1, "cro")

    # CORRECTED: extend the envelope signature to accept `persona` (piece-5's
    # own remedy). Then the call succeeds and `persona` is stamped.
    monkeypatch.setattr(impl, "envelope", impl.envelope_with_persona)
    p = build_dashboard(1, "cro")
    assert p["persona"] == "cro"


def test_defect_2_account_arr_falsy_zero_precedence(monkeypatch):
    """
    DEFECT (shape d): `account_arr` uses `if arr:` (falsy test), but the AC
    ("ARR resolution precedence") and the inline comment ("profile_metadata.arr
    wins when present") say metadata arr WINS when present. A genuine, explicit
    profile_metadata.arr == 0 is 'present' yet falsy, so the code silently falls
    through to the revenue column and reports a NON-zero ARR for an account the
    metadata declares as zero-ARR. That mis-weights the L4 rollup and hides a
    real zero-ARR account from `n_zero_arr`.
    """
    a = Account("a", revenue=500_000, profile_metadata={"arr": 0})
    # Spec text: arr is present (== 0) so it should win -> 0.0.
    # Literal code returns the revenue column instead:
    assert account_arr(a) == 500_000.0        # proves the wrong number

    # CORRECTED reading ("present" = key exists / not None):
    def account_arr_fixed(acct):
        meta = acct.profile_metadata if isinstance(acct.profile_metadata, dict) else {}
        arr = meta.get("arr")
        if arr is not None:
            return float(arr)
        return float(acct.revenue or 0)
    assert account_arr_fixed(a) == 0.0

    # Downstream impact on the rollup: a zero-ARR account declared in metadata is
    # invisible to n_zero_arr under the buggy accessor.
    accts = [acct("keep", 80, 900_000),
             Account("z", account_status="active", revenue=100_000,
                     profile_metadata={"arr": 0})]
    accts[1]._health = 20
    wire(monkeypatch, accts)
    r = rollup_L4(partition_accounts(1)[0])
    assert r["n_zero_arr"] == 0    # BUG: the declared zero-ARR account is not counted


def test_defect_3_parity_check_bites_persona(monkeypatch):
    """
    Proof the parity check is not vacuous (Gotcha 5). Mutate one persona to
    recompute revenue_at_risk a second way (from exposure) and assert
    assert_persona_parity RAISES naming the drifted metric. (Confirms the AC's
    'prove it bites'.)
    """
    wire(monkeypatch, [acct("a", 30, 400_000)])
    assert_persona_parity(1)   # baseline passes

    orig = impl.persona_lens

    def drifting_lens(persona, trailing, leading, bundle, churn, active, churned):
        out = orig(persona, trailing, leading, bundle, churn, active, churned)
        if persona == "cfo":
            # recompute at-risk a second way: sum critical-band ARR
            out = dict(out)
            out["revenue_at_risk"] = trailing["exposure_risk"]["critical"]
        return out

    monkeypatch.setattr(impl, "persona_lens", drifting_lens)
    with pytest.raises(AssertionError, match="revenue_at_risk"):
        assert_persona_parity(1)


def test_defect_3b_surface_parity_bites(monkeypatch):
    """Surface parity must raise when a second surface impl drifts (Gotcha 3)."""
    wire(monkeypatch, [acct("a", 30, 400_000)])

    def flask_call(cid, persona):
        return build_dashboard(cid, persona)

    def mcp_call_drift(cid, persona):
        p = dict(build_dashboard(cid, persona))
        p["revenue_at_risk"] = p["revenue_at_risk"] + 1  # reimplemented, drifted
        return p

    with pytest.raises(AssertionError, match="revenue_at_risk"):
        assert_surface_parity(1, "cro", mcp_call_drift, flask_call)


def test_defect_4_no_arr_summing_into_revenue_at_risk():
    """
    Source-inspection guard (Gotcha 2 / AC 'Revenue comes from the bundle'):
    assert impl contains no code path that sums account ARR into a revenue
    number. `churned_arr` legitimately sums churned rows; `revenue_at_risk` etc.
    must only come from the bundle. This test documents/enforces that boundary.
    """
    src = inspect.getsource(impl)
    # the only sum(...arr...) allowed is the churned_arr line
    arr_sums = re.findall(r"sum\([^)]*\[\"arr\"\][^)]*\)", src)
    for s in arr_sums:
        assert "churned" in s or "for a in scored" in s, (
            f"unexpected ARR summation that could feed a revenue number: {s}")
    # revenue_at_risk is only ever read from prov/bundle
    assert "prov[\"at_risk\"]" in src
