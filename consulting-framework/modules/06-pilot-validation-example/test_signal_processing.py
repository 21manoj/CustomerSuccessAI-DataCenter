"""Validation suite for consulting-framework Module 06 (Signal Processing).

Three kinds of test in here:

* `test_ac_*`   -- one per Acceptance Criteria bullet, as literal as possible.
* `test_harness_*` -- the four Reference Test Harness items.
* `test_literal_*` -- executable PROOFS that the spec's own pseudocode is
  wrong. Each runs the Build Prompt's literal code (copied verbatim, exec'd)
  and demonstrates the failure, then shows the corrected version passing.
* `test_mutation_*` -- checks that the structural tests actually bite.
"""

from __future__ import annotations

import ast
import inspect
import json
import sqlite3
import textwrap

import pytest

import signal_processing as sp
from fake_llm import ExplodingLLMClient, FakeLLMClient

C1 = 101
C2 = 202
A1 = 9001


# =====================================================================
# fixtures
# =====================================================================


@pytest.fixture(autouse=True)
def fresh_db():
    sp.reset_config()
    conn = sp.init_db(":memory:")
    sp.REVIEW_WHEN_CONFIDENCE_MISSING = False
    yield conn
    conn.close()
    sp._RUNTIME["db"] = None


def enable(customer_id=C1, **kw):
    sp.configure_tenant(customer_id, **kw)


def mk(signal_id="sig_001", customer_id=C1, **kw):
    kw.setdefault("account_id", A1)
    kw.setdefault("raw_text", "Thanks for the update, all good here.")
    kw.setdefault("signal_date", "2026-08-01")
    kw.setdefault("signal_type", "email")
    kw.setdefault("source_type", "email")
    return sp.process_signal(customer_id=customer_id, signal_id=signal_id, **kw)


NULLABLE_LLM_COLUMNS = [
    "sentiment",
    "relationship_sentiment",
    "product_sentiment",
    "urgency_score",
    "intent_signals",
    "stakeholder_roles",
    "suggested_action",
    "confidence",
    "llm_model_version",
]


# =====================================================================
# Acceptance Criteria
# =====================================================================


def test_ac1_flag_disabled_still_persists_deterministically():
    """AC1: flag off -> persisted, both urgencies set, all enriched cols null,
    reason == 'feature_flag_disabled' (not a bare False)."""
    enable(C1, llm_enabled=False)
    sp.set_llm_client(FakeLLMClient())

    decision = sp.check_enrichment_allowed(C1)
    assert decision.allowed is False
    assert decision.reason == "feature_flag_disabled"
    assert isinstance(decision, sp.GateDecision)  # structured, not a bool

    sig = mk("sig_flagoff")
    row = sp.get_signal(C1, "sig_flagoff")
    assert row is not None
    assert row["structural_urgency"] == "medium"
    assert row["effective_urgency"] == "medium"
    for col in NULLABLE_LLM_COLUMNS:
        assert row[col] is None, col
    assert row["requires_review"] == 0
    assert sp._RUNTIME["llm_client"].call_count == 0


def test_ac2_no_api_key_reason():
    """AC2a: flag on, no key -> reason == 'no_api_key'."""
    enable(C1, llm_enabled=True, api_key=None)
    sp.set_llm_client(FakeLLMClient())
    d = sp.check_enrichment_allowed(C1)
    assert (d.allowed, d.reason) == (False, "no_api_key")

    mk("sig_nokey")
    row = sp.get_signal(C1, "sig_nokey")
    assert row["effective_urgency"] == "medium"
    assert all(row[c] is None for c in NULLABLE_LLM_COLUMNS)
    assert sp._RUNTIME["llm_client"].call_count == 0


def test_ac2_budget_exhausted_reason_carries_actual_numbers():
    """AC2b: budget exhausted -> 'budget_exhausted:<spent>/<cap>'."""
    enable(C1, llm_enabled=True, api_key="sk-x", budget_cap=0.01)
    sp.set_llm_client(FakeLLMClient(tokens_in=2_000_000, tokens_out=0))

    # First call is allowed and burns 2M input tokens (= $6.00 at fake pricing).
    mk("sig_budget_a")
    assert sp.get_spend_this_period(C1) > 0.01

    d = sp.check_enrichment_allowed(C1)
    assert d.allowed is False
    assert d.reason.startswith("budget_exhausted:")
    spent_s, cap_s = d.reason.split(":", 1)[1].split("/")
    assert float(spent_s) == pytest.approx(sp.get_spend_this_period(C1), abs=0.01)
    assert float(cap_s) == 0.01

    calls_before = sp._RUNTIME["llm_client"].call_count
    mk("sig_budget_b")
    row = sp.get_signal(C1, "sig_budget_b")
    assert row is not None
    assert all(row[c] is None for c in NULLABLE_LLM_COLUMNS)
    assert sp._RUNTIME["llm_client"].call_count == calls_before  # no call made


def test_ac2_budget_cap_none_means_unlimited():
    """`cap is not None` branch -- the NULL case of budget_cap."""
    enable(C1, budget_cap=None)
    sp.set_llm_client(FakeLLMClient(tokens_in=10_000_000, tokens_out=10_000_000))
    mk("sig_uncapped_a")
    assert sp.get_spend_this_period(C1) > 100
    assert sp.check_enrichment_allowed(C1).allowed is True


def test_ac3_every_llm_call_produces_exactly_one_usage_record():
    """AC3 behavioural half: N calls (success AND failure) -> N usage rows."""
    enable(C1)
    ok = FakeLLMClient()
    sp.set_llm_client(ok)
    mk("s1")
    mk("s2")

    boom = ExplodingLLMClient(exc=TimeoutError("rate limited"))
    sp.set_llm_client(boom)
    mk("s3")

    total_calls = ok.call_count + boom.call_count
    rows = sp.usage_rows(C1)
    assert total_calls == 3
    assert len(rows) == 3
    assert [r["success"] for r in rows] == [1, 1, 0]
    assert rows[2]["error_message"] == "rate limited"


def test_ac3_structural_no_llm_client_outside_the_wrapper():
    """AC3 structural half / Harness item 2 -- see test_harness2_* below."""
    touches = llm_client_touches(module_source())
    assert touches, "detector found nothing at all -- it is not working"
    offenders = [t for t in touches if t[0] != "call_llm_tracked"]
    assert offenders == [], f"LLM client touched outside call_llm_tracked: {offenders}"


def test_ac4_malformed_output_persists_with_nulls_and_does_not_raise():
    enable(C1)
    sp.set_llm_client(FakeLLMClient(mode="malformed"))
    sig = mk("sig_garbage", raw_text="Ticket 42: printer is jammed again")
    row = sp.get_signal(C1, "sig_garbage")
    assert row is not None
    for col in NULLABLE_LLM_COLUMNS:
        assert row[col] is None, col
    assert row["structural_urgency"] == row["effective_urgency"] == "medium"
    # identical outcome to a skipped enrichment
    enable(C2, llm_enabled=False)
    mk("sig_skipped", customer_id=C2, raw_text="Ticket 42: printer is jammed again")
    skipped = sp.get_signal(C2, "sig_skipped")
    for col in NULLABLE_LLM_COLUMNS + ["structural_urgency", "effective_urgency",
                                       "requires_review"]:
        assert row[col] == skipped[col], col


def test_ac4_empty_response_body_is_treated_as_skipped():
    enable(C1)
    sp.set_llm_client(FakeLLMClient(mode="empty"))
    mk("sig_empty")
    row = sp.get_signal(C1, "sig_empty")
    assert all(row[c] is None for c in NULLABLE_LLM_COLUMNS)


def test_ac5_llm_exception_persists_records_failure_and_does_not_propagate():
    enable(C1)
    boom = ExplodingLLMClient(exc=RuntimeError("529 overloaded"))
    sp.set_llm_client(boom)

    sig = mk("sig_boom", raw_text="Please escalate, this is a blocker")  # no raise
    row = sp.get_signal(C1, "sig_boom")
    assert row is not None
    assert row["structural_urgency"] == "high"
    assert row["effective_urgency"] == "high"
    assert all(row[c] is None for c in NULLABLE_LLM_COLUMNS)

    usage = sp.usage_rows(C1)
    assert len(usage) == 1
    assert usage[0]["success"] == 0
    assert usage[0]["error_message"] == "529 overloaded"
    assert usage[0]["tokens_in"] == 0 and usage[0]["tokens_out"] == 0


def test_ac6_effective_urgency_never_lower_than_structural():
    """AC6, verbatim: deterministic critical + low LLM score -> critical."""
    enable(C1)
    sp.set_llm_client(
        FakeLLMClient(
            payload={
                "sentiment": "neutral",
                "urgency_score": 0.05,
                "confidence": {"sentiment": 0.95, "urgency_score": 0.9},
            }
        )
    )
    mk("sig_floor", signal_type="escalation", raw_text="They are cancelling the contract.")
    row = sp.get_signal(C1, "sig_floor")
    assert row["structural_urgency"] == "critical"
    assert row["urgency_score"] == 0.05          # LLM value recorded...
    assert row["effective_urgency"] == "critical"  # ...but never applied downward


def test_ac7_confidence_below_threshold_sets_requires_review():
    enable(C1)
    sp.set_llm_client(
        FakeLLMClient(payload={"sentiment": "negative", "urgency_score": 0.4,
                               "confidence": {"sentiment": 0.55, "urgency_score": 0.9}})
    )
    mk("sig_lowconf")
    assert sp.get_signal(C1, "sig_lowconf")["requires_review"] == 1


def test_ac7_all_confidences_at_or_above_threshold_leave_review_false():
    enable(C1)
    sp.set_llm_client(
        FakeLLMClient(payload={"sentiment": "negative", "urgency_score": 0.4,
                               "confidence": {"sentiment": 0.6, "urgency_score": 0.6}})
    )
    mk("sig_atthreshold")  # exactly AT the threshold -> not below -> False
    assert sp.get_signal(C1, "sig_atthreshold")["requires_review"] == 0


def test_ac8_model_version_present_iff_any_enriched_field_present():
    enable(C1)
    sp.set_llm_client(FakeLLMClient())
    mk("sig_enriched")
    enriched = sp.get_signal(C1, "sig_enriched")
    assert enriched["sentiment"] is not None
    assert enriched["llm_model_version"] == sp.DEFAULT_MODEL

    enable(C2, llm_enabled=False)
    mk("sig_plain", customer_id=C2)
    plain = sp.get_signal(C2, "sig_plain")
    assert all(plain[c] is None for c in NULLABLE_LLM_COLUMNS[:-1])
    assert plain["llm_model_version"] is None

    # both directions, asserted over the whole table
    for row in sp.db().execute("SELECT * FROM qualitative_signal"):
        any_enriched = any(row[c] is not None for c in NULLABLE_LLM_COLUMNS[:-1])
        assert any_enriched == (row["llm_model_version"] is not None)


def test_ac9_tenant_scoped_signal_id():
    """AC9 / Harness item 3 -- see test_harness3_* for the full version."""
    enable(C1)
    enable(C2)
    sp.set_llm_client(FakeLLMClient())
    mk("sig_001", customer_id=C1)
    mk("sig_001", customer_id=C2)
    assert sp.get_signal(C1, "sig_001") is not None
    assert sp.get_signal(C2, "sig_001") is not None

    with pytest.raises(sqlite3.IntegrityError):
        mk("sig_001", customer_id=C1)


# =====================================================================
# Reference Test Harness
# =====================================================================


DEGRADATION_SCENARIOS = [
    ("flag_off", dict(llm_enabled=False), "success", None),
    ("no_key", dict(api_key=None), "success", None),
    ("budget", dict(budget_cap=0.0000001), "success", None),
    ("llm_raises", dict(), "raise", None),
    ("llm_garbage", dict(), "malformed", None),
]


@pytest.mark.parametrize("name,cfg,mode,_", DEGRADATION_SCENARIOS)
def test_harness1_degradation_matrix(name, cfg, mode, _):
    enable(C1, **cfg)
    if name == "budget":
        # burn the budget with a directly-recorded prior spend
        sp.record_usage(C1, "other_module", sp.DEFAULT_MODEL, 500_000, 0, True)
    sp.set_llm_client(FakeLLMClient(mode=mode))

    sig = mk(f"sig_{name}", raw_text="Ticket 7: the export button is slow")
    row = sp.get_signal(C1, f"sig_{name}")
    assert row is not None, name
    assert row["structural_urgency"] == "medium", name
    assert row["effective_urgency"] == "medium", name
    assert row["content"] == "Ticket 7: the export button is slow"
    assert row["raw_text"] is not None
    for col in NULLABLE_LLM_COLUMNS:
        assert row[col] is None, (name, col)
    assert row["requires_review"] == 0, name


def module_source() -> str:
    return inspect.getsource(sp)


def llm_client_touches(source: str) -> list[tuple[str, int]]:
    """Every place the module reads the LLM client.

    Two syntactic shapes count as a touch:
      * any `X.messages` attribute access (the SDK call surface)
      * any LOAD of `_RUNTIME["llm_client"]` (writes are fine -- that's the
        setter)
    Returns (enclosing_function_name, lineno) pairs.
    """
    tree = ast.parse(source)
    scope: dict[int, str] = {}

    def walk(node, fname):
        for child in ast.iter_child_nodes(node):
            nxt = child.name if isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef)) else fname
            scope[id(child)] = nxt
            walk(child, nxt)

    scope[id(tree)] = "<module>"
    walk(tree, "<module>")

    hits: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "messages":
            hits.append((scope.get(id(node), "<module>"), node.lineno))
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name)
            and node.value.id == "_RUNTIME"
            and isinstance(node.slice, ast.Constant)
            and node.slice.value == "llm_client"
            and isinstance(node.ctx, ast.Load)
        ):
            hits.append((scope.get(id(node), "<module>"), node.lineno))
    return hits


def test_harness2_source_level_llm_call_containment():
    src = module_source()
    touches = llm_client_touches(src)
    assert touches, "detector matched nothing -- vacuous pass"
    assert {fn for fn, _ in touches} == {"call_llm_tracked"}


def test_harness2_module_never_imports_or_constructs_an_llm_client():
    tree = ast.parse(module_source())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert a.name.split(".")[0] not in {"anthropic", "openai", "fake_llm"}
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in {
                "anthropic", "openai", "fake_llm"}


def test_mutation_containment_detector_catches_an_untracked_call_site():
    """The detector must FAIL on a module that sneaks in a second call site --
    otherwise test_harness2 is a vacuous pass."""
    mutated = module_source() + textwrap.dedent(
        '''

        def summarize_signal_untracked(prompt):
            # the exact Gotcha-1 shape: a real call site nobody wired to
            # record_usage()
            return _RUNTIME["llm_client"].messages.create(
                model="fake-model-v1", max_tokens=64,
                messages=[{"role": "user", "content": prompt}])
        '''
    )
    offenders = [t for t in llm_client_touches(mutated) if t[0] != "call_llm_tracked"]
    assert offenders, "detector failed to notice an untracked call site"
    assert offenders[0][0] == "summarize_signal_untracked"


def test_harness3_tenant_collision_and_same_tenant_duplicate():
    enable(C1)
    enable(C2)
    sp.set_llm_client(FakeLLMClient())

    a = mk("TICKET-1042", customer_id=C1, account_id=1)
    b = mk("TICKET-1042", customer_id=C2, account_id=2)
    assert a.id != b.id
    rows = sp.db().execute(
        "SELECT customer_id FROM qualitative_signal WHERE signal_id='TICKET-1042'"
    ).fetchall()
    assert sorted(r["customer_id"] for r in rows) == [C1, C2]

    with pytest.raises(sqlite3.IntegrityError):
        mk("TICKET-1042", customer_id=C1, account_id=1)


def test_mutation_global_unique_would_break_the_tenant_collision_case():
    """Gotcha 4, proven: a global UNIQUE(signal_id) passes every single-tenant
    test and fails the two-tenant one."""
    global_schema = sp.SCHEMA_SQL.replace(
        "UNIQUE (customer_id, signal_id)          -- composite, NOT global",
        "UNIQUE (signal_id)",
    )
    conn = sqlite3.connect(":memory:")
    conn.executescript(global_schema)
    ins = ("INSERT INTO qualitative_signal (signal_id, customer_id, account_id,"
           " signal_date, structural_urgency, effective_urgency)"
           " VALUES (?,?,?,?, 'low','low')")
    conn.execute(ins, ("TICKET-1042", C1, 1, "2026-08-01"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ins, ("TICKET-1042", C2, 2, "2026-08-01"))
    conn.close()


STRUCTURAL_CASES = {
    "critical": dict(signal_type="escalation", source_type="email",
                     raw_text="Please review the attached summary."),
    "high": dict(signal_type="note", source_type="transcript",
                 raw_text="Quarterly business review recording."),
    "medium": dict(signal_type="ticket", source_type="email",
                   raw_text="Export takes a while."),
    "low": dict(signal_type="note", source_type="manual",
                raw_text="Sent over the new onboarding deck."),
}
LLM_SCORE_FOR_LEVEL = {"critical": 0.95, "high": 0.70, "medium": 0.40, "low": 0.10}


@pytest.mark.parametrize("s_level", list(STRUCTURAL_CASES))
@pytest.mark.parametrize("l_level", list(LLM_SCORE_FOR_LEVEL))
def test_harness4_urgency_floor_property_matrix(s_level, l_level):
    enable(C1)
    sp.set_llm_client(
        FakeLLMClient(payload={
            "sentiment": "neutral",
            "urgency_score": LLM_SCORE_FOR_LEVEL[l_level],
            "confidence": {"sentiment": 0.9},
        })
    )
    sid = f"sig_{s_level}_{l_level}"
    mk(sid, **STRUCTURAL_CASES[s_level])
    row = sp.get_signal(C1, sid)
    assert row["structural_urgency"] == s_level
    expected = max(s_level, l_level, key=lambda x: sp.URGENCY_ORDER[x])
    assert row["effective_urgency"] == expected
    assert sp.URGENCY_ORDER[row["effective_urgency"]] >= sp.URGENCY_ORDER[s_level]


# =====================================================================
# NULL-case coverage (mandated: every nullable column exercised as NULL)
# =====================================================================


def test_null_case_every_nullable_column_null_and_row_still_valid():
    enable(C1, llm_enabled=False)
    mk("sig_allnull", raw_text=None, signal_type=None, source_type=None)
    row = sp.get_signal(C1, "sig_allnull")
    for col in NULLABLE_LLM_COLUMNS + ["signal_type", "source_type", "raw_text",
                                       "content", "cg_node_id"]:
        assert row[col] is None, col
    assert row["structural_urgency"] == "low"
    assert row["effective_urgency"] == "low"
    assert row["requires_review"] == 0


def test_null_case_null_content_with_llm_enabled():
    enable(C1)
    sp.set_llm_client(FakeLLMClient())
    mk("sig_nulltext", raw_text=None, signal_type=None, source_type=None)
    row = sp.get_signal(C1, "sig_nulltext")
    assert row["content"] is None
    assert row["structural_urgency"] == "low"
    assert row["sentiment"] == "negative"


def test_null_case_cg_node_id_present_when_module_04_is():
    enable(C1, llm_enabled=False)
    mk("sig_graph", cg_node_id=777)
    assert sp.get_signal(C1, "sig_graph")["cg_node_id"] == 777


def test_null_case_llm_returns_no_urgency_score():
    """`urgency_score` is nullable -- a well-formed enrichment may omit it."""
    enable(C1)
    sp.set_llm_client(
        FakeLLMClient(payload={"sentiment": "positive", "confidence": {"sentiment": 0.9}})
    )
    mk("sig_noscore", signal_type="ticket")
    row = sp.get_signal(C1, "sig_noscore")
    assert row["urgency_score"] is None
    assert row["sentiment"] == "positive"
    assert row["effective_urgency"] == "medium"  # floor holds
    assert row["llm_model_version"] == sp.DEFAULT_MODEL


def test_null_case_llm_returns_no_confidence_block():
    enable(C1)
    sp.set_llm_client(FakeLLMClient(payload={"sentiment": "negative", "urgency_score": 0.9}))
    mk("sig_noconf", signal_type="ticket")
    row = sp.get_signal(C1, "sig_noconf")
    assert row["confidence"] is None
    # Spec's literal rule: any([]) is False -> silently trusted.
    assert row["requires_review"] == 0
    assert row["effective_urgency"] == "critical"


def test_null_case_missing_confidence_can_be_routed_to_review():
    """Documents the ambiguity: Boundary says enrichment must not be 'silently
    trusted', but the AC's literal any()-rule trusts a missing confidence."""
    enable(C1)
    sp.REVIEW_WHEN_CONFIDENCE_MISSING = True
    sp.set_llm_client(FakeLLMClient(payload={"sentiment": "negative", "urgency_score": 0.9}))
    mk("sig_noconf2", signal_type="ticket")
    assert sp.get_signal(C1, "sig_noconf2")["requires_review"] == 1


def test_gate_checks_flag_then_key_then_budget_in_that_order():
    """Engine bullet 1 pins the order. With all three failing, the reported
    reason must be the first one."""
    enable(C1, llm_enabled=False, api_key=None, budget_cap=0.0)
    assert sp.check_enrichment_allowed(C1).reason == "feature_flag_disabled"
    enable(C1, llm_enabled=True, api_key=None, budget_cap=0.0)
    assert sp.check_enrichment_allowed(C1).reason == "no_api_key"
    enable(C1, llm_enabled=True, api_key="sk", budget_cap=0.0)
    assert sp.check_enrichment_allowed(C1).reason.startswith("budget_exhausted:")


def test_gate_reason_is_populated_even_when_allowed():
    enable(C1)
    d = sp.check_enrichment_allowed(C1)
    assert (d.allowed, d.reason) == (True, "allowed")


def test_usage_record_survives_a_failed_signal_insert():
    """UNSPECIFIED IN THE SPEC: the Build Prompt writes both the usage row and
    the signal through the same `db.session`, so a rollback of the signal
    insert (e.g. the duplicate-signal_id case AC9 requires) would also discard
    the usage row for a call that really was made and really was billed --
    Gotcha 1's symptom, produced by the spec's own transaction boundary. This
    implementation commits usage independently; asserted here so the choice is
    visible rather than accidental."""
    enable(C1)
    sp.set_llm_client(FakeLLMClient())
    mk("dup_1")
    assert len(sp.usage_rows(C1)) == 1
    with pytest.raises(sqlite3.IntegrityError):
        mk("dup_1")
    assert sp._RUNTIME["llm_client"].call_count == 2
    assert len(sp.usage_rows(C1)) == 2   # the second call is still accounted for


def test_requires_review_column_default_is_false():
    sp.db().execute(
        "INSERT INTO qualitative_signal (signal_id, customer_id, account_id,"
        " signal_date, structural_urgency, effective_urgency)"
        " VALUES ('sig_default', 1, 1, '2026-08-01', 'low', 'low')"
    )
    row = sp.db().execute(
        "SELECT requires_review FROM qualitative_signal WHERE signal_id='sig_default'"
    ).fetchone()
    assert row["requires_review"] == 0


# =====================================================================
# PROOFS the spec's literal pseudocode is wrong
# =====================================================================

# --- (1) NULL content crashes the deterministic rules --------------------

SPEC_URGENCY_BLOCK = '''
URGENCY_RULES = [   # ordered; first match wins. FDE-tunable Config.
    ("critical", lambda s: s.signal_type == "escalation"
                          or any(k in s.content.lower() for k in CRITICAL_KEYWORDS)),
    ("high",     lambda s: s.source_type == "transcript"
                          or any(k in s.content.lower() for k in HIGH_KEYWORDS)),
    ("medium",   lambda s: s.signal_type in ("ticket", "email")),
    ("low",      lambda s: True),   # mandatory catch-all -- every signal
                                    # gets a structural urgency, always
]
URGENCY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

def derive_structural_urgency(signal) -> str:
    for level, rule in URGENCY_RULES:
        if rule(signal): return level
    return "low"   # unreachable given the catch-all, but never omit it
'''


def _exec_spec(src, extra=None):
    ns = {
        "CRITICAL_KEYWORDS": sp.CRITICAL_KEYWORDS,
        "HIGH_KEYWORDS": sp.HIGH_KEYWORDS,
    }
    ns.update(extra or {})
    exec(compile(textwrap.dedent(src), "<spec-06-build-prompt>", "exec"), ns)
    return ns


def test_literal_urgency_rules_crash_on_null_content():
    """Data Shapes: `content (TEXT, nullable)`. The Build Prompt's rule 1 calls
    `s.content.lower()` unguarded, so the FIRST rule raises and the 'mandatory
    catch-all' is never reached -- for a column the spec itself says may be
    NULL, and for a field it says is NOT NULL and 'always' populated."""
    ns = _exec_spec(SPEC_URGENCY_BLOCK)
    literal = ns["derive_structural_urgency"]

    null_signal = sp.QualitativeSignal(
        customer_id=C1, account_id=A1, signal_id="x", signal_date="2026-08-01",
        signal_type=None, source_type=None, raw_text=None, content=None,
    )
    with pytest.raises(AttributeError):
        literal(null_signal)

    # the corrected version returns the catch-all instead
    assert sp.derive_structural_urgency(null_signal) == "low"

    # and both agree on the non-null path (the correction is not a behaviour change)
    for case in STRUCTURAL_CASES.values():
        s = sp.QualitativeSignal(
            customer_id=C1, account_id=A1, signal_id="x", signal_date="d",
            signal_type=case["signal_type"], source_type=case["source_type"],
            content=case["raw_text"],
        )
        assert literal(s) == sp.derive_structural_urgency(s)


# --- (2) llm_model_version sourced from the LLM's own output -------------

SPEC_PROCESS_BLOCK = '''
def process_signal(customer_id, account_id, raw_text, signal_date,
                    signal_type, source_type, signal_id):
    signal = QualitativeSignal(
        customer_id=customer_id, account_id=account_id,
        signal_id=signal_id, signal_date=signal_date,
        signal_type=signal_type, source_type=source_type,
        raw_text=raw_text, content=normalize(raw_text),
    )
    signal.structural_urgency = derive_structural_urgency(signal)
    signal.effective_urgency = signal.structural_urgency   # floor, set BEFORE
        # any LLM attempt, so a failed/skipped enrichment can never leave
        # effective_urgency unset

    response, status = call_llm_tracked(customer_id, "signal_enrichment",
                                         build_prompt(signal))
    if response is not None:
        parsed = parse_enrichment(response)   # must tolerate malformed
            # output: on a parse failure, treat exactly like a skipped
            # enrichment (leave enriched fields null), never raise
        if parsed is not None:
            signal.sentiment = parsed.sentiment
            signal.urgency_score = parsed.urgency_score
            signal.confidence = parsed.confidence
            signal.llm_model_version = parsed.model_version  # REQUIRED
                # whenever any enriched field is set -- see Gotcha 3
            llm_level = score_to_level(parsed.urgency_score)
            if URGENCY_ORDER[llm_level] > URGENCY_ORDER[signal.structural_urgency]:
                signal.effective_urgency = llm_level    # RAISE only
                # never lower: a deterministic "critical" stands even if
                # the LLM disagrees -- see Gotcha 2
            signal.requires_review = any(
                v < REVIEW_THRESHOLD for v in (parsed.confidence or {}).values()
            )
    db.session.add(signal); db.session.commit()
    return signal       # ALWAYS persisted, enriched or not
'''


class _SpecParsed:
    """What `parse_enrichment` naturally returns: attributes read straight off
    the LLM's JSON body, including `model_version`."""

    def __init__(self, body: dict):
        self.sentiment = body.get("sentiment")
        self.urgency_score = body.get("urgency_score")
        self.confidence = body.get("confidence")
        self.model_version = body.get("model_version")  # absent -> None


class _FakeSession:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass


class _FakeDB:
    def __init__(self):
        self.session = _FakeSession()


def _spec_namespace(body: dict, score_to_level=None):
    """Wire the literal block up to stubs that behave exactly as the spec
    describes them, so what fails is the spec's own code, not the stubs."""

    def naive_score_to_level(score):
        # The spec never defines this. This is the most natural implementation.
        if score >= 0.85:
            return "critical"
        if score >= 0.60:
            return "high"
        if score >= 0.30:
            return "medium"
        return "low"

    fake_db = _FakeDB()
    ns = _exec_spec(
        SPEC_URGENCY_BLOCK + SPEC_PROCESS_BLOCK,
        {
            "QualitativeSignal": sp.QualitativeSignal,
            "normalize": sp.normalize,
            "build_prompt": sp.build_prompt,
            "call_llm_tracked": lambda *a, **k: (object(), "ok"),
            "parse_enrichment": lambda r: _SpecParsed(body),
            "score_to_level": score_to_level or naive_score_to_level,
            "REVIEW_THRESHOLD": sp.REVIEW_THRESHOLD,
            "db": fake_db,
        },
    )
    ns["_fake_db"] = fake_db
    return ns


def test_literal_model_version_comes_from_llm_output_not_from_the_caller():
    """Build Prompt: `signal.llm_model_version = parsed.model_version`.

    But `call_llm_tracked` returns only `(response, status)` -- the model id
    this module actually used is never handed back. So the ONLY available
    source is the LLM's own JSON body, which is not something the spec's
    prompt is required to ask for and not something a model is required to
    return. An LLM that returns perfectly good sentiment but no
    `model_version` key silently violates Acceptance Criterion 8 and Gotcha 3
    -- with no exception raised anywhere."""
    ns = _spec_namespace(
        {"sentiment": "negative", "urgency_score": 0.4, "confidence": {"sentiment": 0.9}}
    )
    sig = ns["process_signal"](C1, A1, "Ticket 9: slow export", "2026-08-01",
                               "ticket", "email", "sig_x")
    assert sig.sentiment == "negative"          # enriched
    assert sig.llm_model_version is None        # ...and unauditable. AC8 broken.

    # corrected version: the model id comes from the wrapper, and the pairing
    # invariant is executable rather than a comment
    enable(C1)
    sp.set_llm_client(FakeLLMClient(payload={
        "sentiment": "negative", "urgency_score": 0.4, "confidence": {"sentiment": 0.9}}))
    mk("sig_x_fixed", raw_text="Ticket 9: slow export", signal_type="ticket")
    row = sp.get_signal(C1, "sig_x_fixed")
    assert row["sentiment"] == "negative"
    assert row["llm_model_version"] == sp.DEFAULT_MODEL


def test_literal_pairing_invariant_lives_only_in_a_comment():
    """`# REQUIRED whenever any enriched field is set` is a comment. Nothing in
    the literal block enforces it -- proven by the assertion below firing only
    in the corrected implementation."""
    ns = _spec_namespace(
        {"sentiment": "negative", "urgency_score": 0.2, "confidence": {"sentiment": 0.9}}
    )
    sig = ns["process_signal"](C1, A1, "hi", "2026-08-01", "ticket", "email", "s")
    assert sig.has_any_enriched_field() and sig.llm_model_version is None
    with pytest.raises(AssertionError, match="Gotcha 3"):
        sp._assert_enrichment_pairing(sig)


# --- (3) nullable urgency_score raises out of process_signal -------------


def test_literal_process_signal_raises_when_llm_omits_urgency_score():
    """`urgency_score (float 0.0..1.0, nullable)`. The literal block calls
    `score_to_level(parsed.urgency_score)` then `URGENCY_ORDER[llm_level]`
    with no null guard, so a well-formed enrichment that simply doesn't
    include an urgency score blows up -- the signal is NEVER persisted,
    breaking 'ALWAYS persisted, enriched or not' and the graceful-degradation
    Engine bullet."""
    ns = _spec_namespace({"sentiment": "positive", "confidence": {"sentiment": 0.95}})
    with pytest.raises(TypeError):
        ns["process_signal"](C1, A1, "all good", "2026-08-01", "ticket", "email", "s")
    assert ns["_fake_db"].session.added == []   # signal lost

    # Even with a null-tolerant score_to_level, the spec's next line still dies:
    ns2 = _spec_namespace(
        {"sentiment": "positive", "confidence": {"sentiment": 0.95}},
        score_to_level=sp.score_to_level,
    )
    with pytest.raises(KeyError):
        ns2["process_signal"](C1, A1, "all good", "2026-08-01", "ticket", "email", "s")

    # corrected version persists it
    enable(C1)
    sp.set_llm_client(FakeLLMClient(payload={
        "sentiment": "positive", "confidence": {"sentiment": 0.95}}))
    mk("sig_noscore_fixed", signal_type="ticket")
    assert sp.get_signal(C1, "sig_noscore_fixed") is not None


# --- (4) the budget half of the gate can never fire ----------------------

SPEC_GATE_BLOCK = '''
class GateDecision:
    def __init__(self, allowed, reason):
        self.allowed = allowed
        self.reason = reason

def check_enrichment_allowed(customer_id) -> GateDecision:
    if not feature_enabled("LLM_ENRICHMENT", customer_id):
        return GateDecision(False, "feature_flag_disabled")
    if not get_api_key(customer_id):
        return GateDecision(False, "no_api_key")
    spent = get_spend_this_period(customer_id)
    cap = get_budget_cap(customer_id)
    if cap is not None and spent >= cap:
        return GateDecision(False, "budget_exhausted:%.2f/%.2f" % (spent, cap))
    return GateDecision(True, "allowed")
'''

SPEC_WRAPPER_BLOCK = '''
def call_llm_tracked(customer_id, module_name, prompt, model=DEFAULT_MODEL):
    gate = check_enrichment_allowed(customer_id)
    if not gate.allowed:
        return None, gate.reason      # caller degrades gracefully
    try:
        response = llm_client.messages.create(model=model)
        record_usage(customer_id, module_name, model=model,
                     tokens_in=response.usage.input_tokens,
                     tokens_out=response.usage.output_tokens,
                     success=True)
        return response, "ok"
    except Exception as e:
        record_usage(customer_id, module_name, model=model,
                     tokens_in=0, tokens_out=0,
                     success=False, error_message=str(e))
        return None, "llm_error:%s" % type(e).__name__
'''


def test_literal_budget_gate_can_never_fire():
    """Data Shapes declares `LLMUsageRecord.cost_estimate_usd`, and the gate's
    `get_spend_this_period` has nowhere else to read spend from. But NEITHER
    `record_usage(...)` call in the Build Prompt passes a cost, and the spec
    defines no cost formula and no price table. So spend is permanently 0 and
    the budget cap never triggers -- verbatim Gotcha 1's own symptom:
    'a tenant's budget cap is exceeded without the cap ever triggering'."""
    enable(C1, budget_cap=0.01)
    client = FakeLLMClient(tokens_in=1_000_000, tokens_out=1_000_000)

    def spec_record_usage(customer_id, module_name, model, tokens_in, tokens_out,
                          success, error_message=None):
        # exactly the columns the Build Prompt's call sites supply
        sp.db().execute(
            "INSERT INTO llm_usage_record (customer_id, module, model, tokens_in,"
            " tokens_out, cost_estimate_usd, success, error_message, created_at)"
            " VALUES (?,?,?,?,?,NULL,?,?,0)",
            (customer_id, module_name, model, tokens_in, tokens_out,
             1 if success else 0, error_message),
        )
        sp.db().commit()

    ns = _exec_spec(
        SPEC_GATE_BLOCK + SPEC_WRAPPER_BLOCK,
        {
            "feature_enabled": sp.feature_enabled,
            "get_api_key": sp.get_api_key,
            "get_budget_cap": sp.get_budget_cap,
            "get_spend_this_period": sp.get_spend_this_period,
            "record_usage": spec_record_usage,
            "llm_client": client,
            "DEFAULT_MODEL": sp.DEFAULT_MODEL,
        },
    )
    for i in range(25):
        resp, status = ns["call_llm_tracked"](C1, "signal_enrichment", "p")
        assert status == "ok", f"gate fired on call {i} -- it should not have"

    assert client.call_count == 25
    assert len(sp.usage_rows(C1)) == 25          # usage IS logged...
    assert sp.get_spend_this_period(C1) == 0.0   # ...with no cost on it
    assert ns["check_enrichment_allowed"](C1).allowed is True

    # corrected wrapper: cost is computed, the cap fires on the second call
    sp.db().execute("DELETE FROM llm_usage_record")
    sp.set_llm_client(client)
    r1 = sp.call_llm_tracked(C1, "signal_enrichment", "p")
    assert r1.status == "ok"
    assert sp.get_spend_this_period(C1) > 0.01
    r2 = sp.call_llm_tracked(C1, "signal_enrichment", "p")
    assert r2.status.startswith("budget_exhausted:")


# --- (5) deliverables promised but absent from the Build Prompt ----------


def test_literal_build_prompt_never_writes_the_stakeholder_columns():
    """Boundary 'Owns' #1 promises 'stakeholder attribution'. Data Shapes
    declares `stakeholder_roles`, `relationship_sentiment`,
    `product_sentiment`, `intent_signals`, `suggested_action`. The Build
    Prompt's `process_signal` writes NONE of them -- five dead columns."""
    ns = _spec_namespace({
        "sentiment": "negative",
        "urgency_score": 0.4,
        "confidence": {"sentiment": 0.9},
        "stakeholder_roles": {"jane@acme.test": "economic_buyer"},
        "relationship_sentiment": -0.4,
        "product_sentiment": -0.2,
        "intent_signals": ["renewal_risk"],
        "suggested_action": "Escalate to the exec sponsor.",
        "model_version": "fake-model-v1",
    })
    sig = ns["process_signal"](C1, A1, "t", "2026-08-01", "ticket", "email", "s")
    for col in ("stakeholder_roles", "relationship_sentiment", "product_sentiment",
                "intent_signals", "suggested_action"):
        assert getattr(sig, col) is None, f"{col} unexpectedly written"

    # corrected version populates all five
    enable(C1)
    sp.set_llm_client(FakeLLMClient())
    mk("sig_stakeholders", signal_type="ticket")
    row = sp.get_signal(C1, "sig_stakeholders")
    assert json.loads(row["stakeholder_roles"]) == {"jane@acme.test": "economic_buyer"}
    assert row["relationship_sentiment"] == -0.4
    assert row["product_sentiment"] == -0.2
    assert json.loads(row["intent_signals"]) == ["renewal_risk"]
    assert row["suggested_action"].startswith("Schedule an exec sync")


def test_spec_now_defines_every_helper_its_build_prompt_calls():
    """REGRESSION GUARD (inverted proof-of-defect test).

    The original spec's Build Prompt CALLED `get_spend_this_period`,
    `score_to_level`, `normalize` and `record_usage`, and DEFINED none of
    them -- and declared `LLMUsageRecord`/`cost_estimate_usd` in Data Shapes
    with no DDL anywhere. That was validation finding (b)/(c) for this
    module. The spec has since been corrected; this test now asserts the
    fix holds, so a future edit that re-introduces an undefined helper
    fails here."""
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "..", "06-intelligence-signal-processing.md"),
        "/Users/manojgupta/CustomerSuccessAI-DataCenter/consulting-framework/modules/"
        "06-intelligence-signal-processing.md",
    ]
    p = next((c for c in candidates if os.path.exists(c)), None)
    if p is None:
        pytest.skip("spec file not reachable from this worktree")
    text = open(p).read()
    build_prompt = text.split("## Build Prompt")[1].split("## Acceptance Criteria")[0]
    # every helper the Build Prompt calls must also be defined by it
    for defined in ("LLMUsageRecord", "def record_usage", "cost_estimate_usd",
                    "def get_spend_this_period", "def score_to_level",
                    "def normalize", "def estimate_cost",
                    "def assert_enrichment_pairing", "def parse_enrichment"):
        assert defined in build_prompt, f"Build Prompt no longer defines {defined!r}"
