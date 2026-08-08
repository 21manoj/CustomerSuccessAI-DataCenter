"""
Adversarial rebuild of Module 11 (Load-Driver Synthetic Data & Testing)
FROM SPEC ALONE. Self-contained: fakes for module00_*, module02_tier_codes,
module04_classify_arc, module05_wizard_d, client_*.

Two layers live here:
  * LITERAL_*  -> faithful transcription of the Build Prompt pseudocode, kept as
    source strings / exec'd bodies so the tests can run the spec's OWN logic in a
    namespace that contains only what the spec actually defines. This is how we
    prove NameError-class gaps (undefined tables/constants) and the dead guard.
  * The plain (corrected) functions -> the most natural working reading, used as
    the "corrected version passing alongside" each defect.

Where the spec left an ellipsis / undefined name, the choice is noted with
[FILL] and the section it came from.
"""
import json
import random
from collections import namedtuple


# ----------------------------------------------------------------------------
# Errors (named in Build Prompt pieces 1/2/5 but never defined -> natural fill)
# ----------------------------------------------------------------------------
class ManifestError(Exception):
    pass


class ArcError(Exception):
    pass


class ArcRoundtripError(Exception):
    pass


# ----------------------------------------------------------------------------
# [FILL] Constants used by pieces 4/6 but NEVER given values anywhere in the
# spec (not in Config, which lists only "the health tolerance" and "the seed").
# These are the shape-(d) "numeric conversion left as prose" fills.
# ----------------------------------------------------------------------------
NOISE_SD = 1.0
DECAY_PER_MONTH = 5.0
RECOVERY_LAG = 2
RECOVERY_PER_MONTH = 4.0
IMPROVE_PER_MONTH = 2.0
HEALTH_TOL = 5.0

KpiRange = namedtuple("KpiRange", ["lo", "hi"])


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ----------------------------------------------------------------------------
# Fakes for named dependency hooks (Dependencies section). Test-configurable.
# ----------------------------------------------------------------------------
def module02_tier_codes(selection):
    tiers = {
        "starter_9": [f"P1-KPI{i}" for i in range(1, 10)],
        "predictive_11": [f"P{((i-1)//3)+1}-KPI{((i-1)%3)+1}" for i in range(1, 12)],
        "full_38": [f"P{((i-1)//8)+1}-KPI{((i-1)%8)+1}" for i in range(1, 39)],
    }
    if selection not in tiers:
        raise ManifestError(f"unknown tier '{selection}'")
    return list(tiers[selection])


# classify_arc is monkeypatched per-test; default identity-ish stub.
_CLASSIFY_IMPL = {"fn": lambda nodes: nodes.get("intended") if isinstance(nodes, dict) else None}


def module04_classify_arc(nodes):
    return _CLASSIFY_IMPL["fn"](nodes)


def set_classify_impl(fn):
    _CLASSIFY_IMPL["fn"] = fn


_CALLS = {"wizard_d": [], "process_data": [], "create_customer": [], "upload": []}


def module00_create_customer(customer):
    _CALLS["create_customer"].append(customer)
    return {"customer_id": 900}


def module00_process_data(cid):
    _CALLS["process_data"].append(cid)
    return {"ok": True}


def module05_wizard_d(cid):
    _CALLS["wizard_d"].append(cid)
    return {"prediction_method": "fitted_v3"}


def client_upload(cid, csvs):
    _CALLS["upload"].append((cid, csvs))
    return {"ok": True}


class FakeClient:
    """Stands in for the Module 00 client. Platform assigns its OWN ids."""
    def __init__(self, accounts):
        # accounts: list of {name, health, status}; we assign platform ids that
        # deliberately DO NOT match any manifest customer_id*1000+slot formula.
        self._accounts = []
        for i, a in enumerate(accounts):
            row = dict(a)
            row["account_id"] = 7_000_000 + i  # global sequence, unrelated to manifest
            self._accounts.append(row)
        self.backfilled = []

    def list_accounts(self, cid):
        return list(self._accounts)

    def backfill_playbook_attribution(self, cid):
        self.backfilled.append(cid)
        return {"revenue_protected": 125000, "roi": 3.2}


# ============================================================================
# PIECE 1 — Manifest loader + schema check
# ============================================================================
def load_manifest(path):
    with open(path) as f:
        m = json.loads(f.read())
    for key in ("customer", "time_range", "kpis", "accounts"):
        if key not in m:
            raise ManifestError(f"missing '{key}'")
    m["kpis"]["codes"] = (m["kpis"].get("codes")
                          or module02_tier_codes(m["kpis"]["selection"]))
    return m


# ============================================================================
# PIECE 2 — Arc resolution + round-trip guard
# ============================================================================
def resolve_arc(story_arc, classification, ARC_TEMPLATES, CLASSIFICATION_TO_ARC):
    if story_arc in ARC_TEMPLATES:
        return story_arc, "direct"
    fallback = CLASSIFICATION_TO_ARC.get(classification)
    if fallback in ARC_TEMPLATES:
        return fallback, "fallback"
    raise ArcError(f"story_arc '{story_arc}' has no template and no usable fallback")


def check_arc_vocabulary(manifest, ARC_TEMPLATES, CLASSIFICATION_TO_ARC):
    report = []
    for a in manifest["accounts"]:
        arc, how = resolve_arc(a["story_arc"], a["classification"],
                               ARC_TEMPLATES, CLASSIFICATION_TO_ARC)
        report.append({"name": a["name"], "declared": a["story_arc"],
                       "generated_as": arc, "how": how})
    return report


def assert_arc_roundtrip(story_arc, generated_nodes, INTENDED_CANONICAL):
    produced = module04_classify_arc(generated_nodes)
    intended = INTENDED_CANONICAL[story_arc]
    if produced != intended:
        raise ArcRoundtripError(
            f"'{story_arc}' generated but classified as '{produced}', "
            f"expected '{intended}'")


# ============================================================================
# PIECE 3 — Deterministic RNG discipline
# ============================================================================
def make_rng(seed):
    return random.Random(seed)


# ============================================================================
# PIECE 4 — Trajectory synthesis
# ============================================================================
def kpi_series(traj, months, target, decline_start, rng, kpi_range):
    out = []
    ds = decline_start if decline_start is not None else months
    for m in range(months):
        base = trajectory_value(traj, m, months, target, ds)
        base += rng.gauss(0, NOISE_SD)
        out.append(clamp(base, kpi_range.lo, kpi_range.hi))
    return out


def trajectory_value(traj, m, months, target, ds):
    if traj == "declining":
        return target - DECAY_PER_MONTH * max(0, m - ds)
    if traj == "recovering":
        infl = min(ds + RECOVERY_LAG, months - 1)
        if m <= infl:
            return target - DECAY_PER_MONTH * max(0, m - ds)
        floor = target - DECAY_PER_MONTH * max(0, infl - ds)
        return floor + RECOVERY_PER_MONTH * (m - infl)
    if traj == "improving":
        return target + IMPROVE_PER_MONTH * m
    if traj == "stable":
        return target
    return target


# ============================================================================
# PIECE 5 — Phase windowing + extend
# ============================================================================
def phase_window(points, phase):
    cut = points * 2 // 3
    if phase == "baseline":
        return range(0, cut)
    if phase == "intervention":
        return range(cut, points)
    return range(0, points)


def resolve_target(extend, register):
    if extend and register:
        raise ManifestError("--extend continues an existing customer; not with --register")
    return "extend" if extend else "register"


# ============================================================================
# [FILL] generate_all — referenced by piece 6 and by the Determinism Acceptance
# Criterion, but NO Build-Prompt piece defines it (shape-(c) gap). Most natural
# reading: iterate the manifest's ordered lists, thread the single rng, emit the
# 4 canonical CSVs as strings. This is the deterministic reading.
# ============================================================================
def _account_kpi_range():
    return KpiRange(0.0, 100.0)


def generate_all(manifest, rng):
    codes = (manifest["kpis"].get("codes")
             or module02_tier_codes(manifest["kpis"]["selection"]))
    months = manifest["time_range"].get("data_points_per_kpi", 12)
    account_rows = []
    kpi_rows = []
    for a in manifest["accounts"]:
        account_rows.append(f'{a["name"]},{a["arr"]},{a["classification"]}')
        for code in codes:
            series = kpi_series(a.get("kpi_trajectory", "stable"), months,
                                float(a["target_health"]),
                                a.get("decline_start_month"), rng,
                                _account_kpi_range())
            for m, v in enumerate(series):
                kpi_rows.append(f'{a["name"]},{code},{m},{v:.6f}')
    return {
        "account_details.csv": "name,arr,classification\n" + "\n".join(account_rows) + "\n",
        "kpi_measurements.csv": "account,kpi,month,value\n" + "\n".join(kpi_rows) + "\n",
        "qualitative_signals.csv": "account,signal\n",
        "outcomes.csv": "account,outcome\n",
    }


# ============================================================================
# PIECE 6 — Acceptance harness (LITERAL transcription)
# ============================================================================
# NOTE: the spec's run_acceptance references bare names ARC_TEMPLATES /
# CLASSIFICATION_TO_ARC as if module globals, though piece 2 only ever defines
# them as function parameters and Config marks them FDE-supplied. To make the
# corrected engine importable we accept them as parameters with defaults. The
# LITERAL bare-global behavior is proven in test_defect_* via exec in a bare
# namespace.
def run_acceptance(manifest, client, seed=42, tol=HEALTH_TOL,
                   ARC_TEMPLATES=None, CLASSIFICATION_TO_ARC=None):
    check_arc_vocabulary(manifest, ARC_TEMPLATES, CLASSIFICATION_TO_ARC)  # piece 2
    csvs = generate_all(manifest, make_rng(seed))
    cid = module00_create_customer(manifest["customer"])["customer_id"]
    client_upload(cid, csvs)
    module00_process_data(cid)
    module05_wizard_d(cid)
    client.backfill_playbook_attribution(cid)
    return validate_post_process(manifest, client, cid, tol)


def validate_post_process(manifest, client, cid, tol):
    platform = client.list_accounts(cid)
    if len(platform) != len(manifest["accounts"]):
        return {"status": "failed", "reason": "account count mismatch",
                "per_account": []}
    by_name = {a["name"]: a for a in platform}
    rows, ok = [], True
    for spec in manifest["accounts"]:
        got = by_name.get(spec["name"])
        within = got is not None and abs(got["health"] - spec["target_health"]) <= tol
        ok = ok and within
        rows.append({"name": spec["name"], "expected_health": spec["target_health"],
                     "actual_health": got["health"] if got else None,
                     "within_tolerance": within,
                     "expected_class": spec["classification"],
                     "actual_class": got["status"] if got else None})
    return {"status": "success" if ok else "failed", "per_account": rows,
            "discovered_ids": {n: a["account_id"] for n, a in by_name.items()}}


# ============================================================================
# CORRECTED harness — round-trip guard actually wired in (defect 1/2 fix).
# ============================================================================
def run_acceptance_fixed(manifest, client, seed=42, tol=HEALTH_TOL,
                         ARC_TEMPLATES=None, CLASSIFICATION_TO_ARC=None,
                         INTENDED_CANONICAL=None, node_builder=None):
    check_arc_vocabulary(manifest, ARC_TEMPLATES, CLASSIFICATION_TO_ARC)
    csvs = generate_all(manifest, make_rng(seed))
    # CORRECTED: invoke the headline Gotcha-1 guard on the generated data.
    if INTENDED_CANONICAL is not None and node_builder is not None:
        for a in manifest["accounts"]:
            nodes = node_builder(a)
            assert_arc_roundtrip(a["story_arc"], nodes, INTENDED_CANONICAL)
    cid = module00_create_customer(manifest["customer"])["customer_id"]
    client_upload(cid, csvs)
    module00_process_data(cid)
    module05_wizard_d(cid)
    client.backfill_playbook_attribution(cid)
    return validate_post_process(manifest, client, cid, tol)
