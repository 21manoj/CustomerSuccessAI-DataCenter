"""Signal Processing Layer -- pilot rebuild from consulting-framework Module 06.

Built from ONLY `modules/06-intelligence-signal-processing.md`. No access to
the reference implementation (`kpi-dashboard/backend/**`).

SQLite-backed so the tenancy/uniqueness guarantees are enforced by a real
database rather than simulated in Python.

STRUCTURAL RULE (Gotcha 1 / Harness item 2): the LLM client is touched in
exactly one place in this file -- inside `call_llm_tracked`. Nothing else may
read `_RUNTIME["llm_client"]` or touch `.messages`. `test_signal_processing.py`
asserts that with an AST walk over this file's own source.

Deviations from the spec's literal Build Prompt pseudocode are each marked
`SPEC-DEVIATION #n` and are proven necessary by a test in the suite.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Optional

# =====================================================================
# Config -- "an FDE fills in per client" (Engine vs. Config section)
# =====================================================================

REVIEW_THRESHOLD = 0.6

CRITICAL_KEYWORDS = ["cancel", "cancelling", "terminate", "churn", "lawsuit", "breach"]
HIGH_KEYWORDS = ["frustrated", "escalate", "unacceptable", "blocker", "outage"]

DEFAULT_MODEL = "fake-model-v1"

# SPEC-DEVIATION #4: `score_to_level` is referenced by the Build Prompt but
# never defined anywhere in the spec. Thresholds invented here. Two FDEs would
# invent different ones -> incompatible effective_urgency for the same score.
URGENCY_SCORE_BANDS = [
    (0.85, "critical"),
    (0.60, "high"),
    (0.30, "medium"),
    (0.00, "low"),
]

# SPEC-DEVIATION #6: cost is required for the budget gate to work but the spec
# never gives a price table or a cost formula. USD per 1M tokens.
MODEL_PRICING_USD_PER_MTOK = {
    "fake-model-v1": (3.00, 15.00),
    "fake-model-cheap": (0.25, 1.25),
}
FALLBACK_PRICING = (3.00, 15.00)

# Ambiguity switch (see report section 2). The spec's literal rule is
# `any(v < REVIEW_THRESHOLD for v in (parsed.confidence or {}).values())`,
# which routes an enrichment that reported NO confidence at all straight to
# "trusted". Boundary says enrichment must not be "silently trusted".
REVIEW_WHEN_CONFIDENCE_MISSING = False

URGENCY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

# Per-tenant Config, keyed by customer_id.
FEATURE_FLAGS: dict[tuple[str, int], bool] = {}
API_KEYS: dict[int, Optional[str]] = {}
BUDGET_CAPS: dict[int, Optional[float]] = {}

# The one mutable runtime slot holding the LLM client. Written by
# `set_llm_client`, read ONLY by `call_llm_tracked`.
_RUNTIME: dict[str, Any] = {"llm_client": None, "db": None}


def set_llm_client(client: Any) -> None:
    _RUNTIME["llm_client"] = client


def configure_tenant(
    customer_id: int,
    llm_enabled: bool = True,
    api_key: Optional[str] = "sk-test",
    budget_cap: Optional[float] = None,
) -> None:
    FEATURE_FLAGS[("LLM_ENRICHMENT", customer_id)] = llm_enabled
    API_KEYS[customer_id] = api_key
    BUDGET_CAPS[customer_id] = budget_cap


def feature_enabled(flag: str, customer_id: int) -> bool:
    return bool(FEATURE_FLAGS.get((flag, customer_id), False))


def get_api_key(customer_id: int) -> Optional[str]:
    return API_KEYS.get(customer_id)


def get_budget_cap(customer_id: int) -> Optional[float]:
    return BUDGET_CAPS.get(customer_id)


# =====================================================================
# 1. Schema
# =====================================================================
# NOTE: Build Prompt piece 1 names only `QualitativeSignal`. `LLMUsageRecord`
# is declared in Data Shapes and required by Boundary "Owns" #3 but has no
# Build Prompt piece -- see report, shape (c).

SCHEMA_SQL = """
CREATE TABLE qualitative_signal (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id              TEXT    NOT NULL,
    customer_id            INTEGER NOT NULL,
    account_id             INTEGER NOT NULL,
    signal_date            TEXT    NOT NULL,
    signal_type            TEXT,
    source_type            TEXT,
    raw_text               TEXT,
    content                TEXT,

    -- deterministic, always populated
    structural_urgency     TEXT    NOT NULL
                             CHECK (structural_urgency IN
                                    ('critical','high','medium','low')),

    -- LLM-enriched, ALL NULLABLE
    sentiment              TEXT
                             CHECK (sentiment IS NULL OR sentiment IN
                                    ('positive','negative','neutral')),
    relationship_sentiment REAL,
    product_sentiment      REAL,
    urgency_score          REAL,
    intent_signals         TEXT,      -- JSON list
    stakeholder_roles      TEXT,      -- JSON object
    suggested_action       TEXT,
    confidence             TEXT,      -- JSON object
    llm_model_version      TEXT,

    -- derived
    effective_urgency      TEXT    NOT NULL
                             CHECK (effective_urgency IN
                                    ('critical','high','medium','low')),
    requires_review        INTEGER NOT NULL DEFAULT 0,
    cg_node_id             INTEGER,

    UNIQUE (customer_id, signal_id)          -- composite, NOT global
);

CREATE TABLE llm_usage_record (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id       INTEGER NOT NULL,
    module            TEXT    NOT NULL,
    model             TEXT    NOT NULL,
    tokens_in         INTEGER NOT NULL,
    tokens_out        INTEGER NOT NULL,
    cost_estimate_usd REAL,            -- nullable: Data Shapes states no
                                       -- NOT NULL, and the Build Prompt's own
                                       -- record_usage() call sites pass no cost
    success           INTEGER NOT NULL,
    error_message     TEXT,
    created_at        REAL    NOT NULL
);
"""


def init_db(path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    _RUNTIME["db"] = conn
    return conn


def db() -> sqlite3.Connection:
    conn = _RUNTIME["db"]
    if conn is None:
        raise RuntimeError("init_db() has not been called")
    return conn


def reset_config() -> None:
    FEATURE_FLAGS.clear()
    API_KEYS.clear()
    BUDGET_CAPS.clear()
    _RUNTIME["llm_client"] = None


# =====================================================================
# The signal record
# =====================================================================

LLM_ENRICHED_FIELDS = (
    "sentiment",
    "relationship_sentiment",
    "product_sentiment",
    "urgency_score",
    "intent_signals",
    "stakeholder_roles",
    "suggested_action",
    "confidence",
)


@dataclass
class QualitativeSignal:
    customer_id: int
    account_id: int
    signal_id: str
    signal_date: str
    signal_type: Optional[str] = None
    source_type: Optional[str] = None
    raw_text: Optional[str] = None
    content: Optional[str] = None

    structural_urgency: Optional[str] = None

    sentiment: Optional[str] = None
    relationship_sentiment: Optional[float] = None
    product_sentiment: Optional[float] = None
    urgency_score: Optional[float] = None
    intent_signals: Optional[list] = None
    stakeholder_roles: Optional[dict] = None
    suggested_action: Optional[str] = None
    confidence: Optional[dict] = None
    llm_model_version: Optional[str] = None

    effective_urgency: Optional[str] = None
    requires_review: bool = False
    cg_node_id: Optional[int] = None

    id: Optional[int] = None

    def has_any_enriched_field(self) -> bool:
        return any(getattr(self, f) is not None for f in LLM_ENRICHED_FIELDS)


# =====================================================================
# 2. Deterministic enrichment (always runs, no LLM)
# =====================================================================

# SPEC-DEVIATION #1: the spec's rules call `s.content.lower()` unguarded, but
# Data Shapes declares `content` nullable. Literal pseudocode raises
# AttributeError on the FIRST rule for a null-content signal -- the mandatory
# catch-all is never reached and the signal is lost. `_text()` makes it
# NULL-safe. Proven by test_literal_urgency_rules_crash_on_null_content.
def _text(s: QualitativeSignal) -> str:
    return (s.content or "").lower()


URGENCY_RULES = [
    (
        "critical",
        lambda s: s.signal_type == "escalation"
        or any(k in _text(s) for k in CRITICAL_KEYWORDS),
    ),
    (
        "high",
        lambda s: s.source_type == "transcript"
        or any(k in _text(s) for k in HIGH_KEYWORDS),
    ),
    ("medium", lambda s: s.signal_type in ("ticket", "email")),
    ("low", lambda s: True),  # mandatory catch-all
]


def derive_structural_urgency(signal: QualitativeSignal) -> str:
    for level, rule in URGENCY_RULES:
        if rule(signal):
            return level
    return "low"  # unreachable given the catch-all, but never omit it


def score_to_level(score: Optional[float]) -> Optional[str]:
    """SPEC-DEVIATION #4: undefined in the spec. Returns None for a null score
    rather than raising -- `urgency_score` is nullable per Data Shapes."""
    if score is None:
        return None
    for floor, level in URGENCY_SCORE_BANDS:
        if score >= floor:
            return level
    return "low"


def normalize(raw_text: Optional[str]) -> Optional[str]:
    """Undefined in the spec. NULL-safe: `raw_text` is nullable."""
    if raw_text is None:
        return None
    return " ".join(raw_text.split())


# =====================================================================
# Cost governance
# =====================================================================


def estimate_cost_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    price_in, price_out = MODEL_PRICING_USD_PER_MTOK.get(model, FALLBACK_PRICING)
    return (tokens_in / 1_000_000) * price_in + (tokens_out / 1_000_000) * price_out


def record_usage(
    customer_id: int,
    module_name: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    success: bool,
    error_message: Optional[str] = None,
) -> None:
    """Never defined in the Build Prompt; required by Boundary 'Owns' #3.

    SPEC-DEVIATION #6: the spec's `record_usage(...)` call sites pass no cost,
    so `cost_estimate_usd` would be permanently unpopulated and
    `get_spend_this_period` -- which the budget gate depends on -- would always
    read 0. Cost is computed here so the gate can actually fire.
    """
    cost = estimate_cost_usd(model, tokens_in, tokens_out)
    db().execute(
        "INSERT INTO llm_usage_record (customer_id, module, model, tokens_in,"
        " tokens_out, cost_estimate_usd, success, error_message, created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (
            customer_id,
            module_name,
            model,
            tokens_in,
            tokens_out,
            cost,
            1 if success else 0,
            error_message,
            time.time(),
        ),
    )
    db().commit()


def get_spend_this_period(customer_id: int) -> float:
    row = db().execute(
        "SELECT COALESCE(SUM(cost_estimate_usd), 0.0) AS spend"
        " FROM llm_usage_record WHERE customer_id = ?",
        (customer_id,),
    ).fetchone()
    return float(row["spend"])


# =====================================================================
# 3. The enrichment gate
# =====================================================================


@dataclass
class GateDecision:
    allowed: bool
    reason: str  # always populated, including when allowed


def check_enrichment_allowed(customer_id: int) -> GateDecision:
    if not feature_enabled("LLM_ENRICHMENT", customer_id):
        return GateDecision(False, "feature_flag_disabled")
    if not get_api_key(customer_id):
        return GateDecision(False, "no_api_key")
    spent = get_spend_this_period(customer_id)
    cap = get_budget_cap(customer_id)
    if cap is not None and spent >= cap:
        return GateDecision(False, f"budget_exhausted:{spent:.2f}/{cap:.2f}")
    return GateDecision(True, "allowed")


# =====================================================================
# 4. The tracked LLM call wrapper -- the ONLY way this module calls an LLM
# =====================================================================


@dataclass
class LLMCallResult:
    """SPEC-DEVIATION #2: the spec returns `(response, status)` only, so the
    caller has no access to the model id actually used and is told to read
    `parsed.model_version` out of the LLM's own output instead. `model` is
    returned here so `llm_model_version` records the model this module really
    called. Proven by test_literal_model_version_comes_from_llm_output."""

    response: Any
    status: str
    model: str


def call_llm_tracked(
    customer_id: int,
    module_name: str,
    prompt: str,
    model: str = DEFAULT_MODEL,
) -> LLMCallResult:
    gate = check_enrichment_allowed(customer_id)
    if not gate.allowed:
        return LLMCallResult(None, gate.reason, model)  # caller degrades gracefully
    try:
        # The one and only LLM invocation in this module.
        response = _RUNTIME["llm_client"].messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        record_usage(
            customer_id,
            module_name,
            model=model,
            tokens_in=response.usage.input_tokens,
            tokens_out=response.usage.output_tokens,
            success=True,
        )
        return LLMCallResult(response, "ok", model)
    except Exception as e:
        # Record the FAILED call too.
        record_usage(
            customer_id,
            module_name,
            model=model,
            tokens_in=0,
            tokens_out=0,
            success=False,
            error_message=str(e),
        )
        return LLMCallResult(None, f"llm_error:{type(e).__name__}", model)


# =====================================================================
# 5. Enrichment + persistence
# =====================================================================


@dataclass
class ParsedEnrichment:
    sentiment: Optional[str] = None
    relationship_sentiment: Optional[float] = None
    product_sentiment: Optional[float] = None
    urgency_score: Optional[float] = None
    intent_signals: Optional[list] = None
    stakeholder_roles: Optional[dict] = None
    suggested_action: Optional[str] = None
    confidence: Optional[dict] = None


def build_prompt(signal: QualitativeSignal) -> str:
    """Config, per Boundary ('which specific prompt text to send an LLM')."""
    return (
        "Classify this customer signal. Return JSON with keys sentiment, "
        "relationship_sentiment, product_sentiment, urgency_score, "
        "intent_signals, stakeholder_roles, suggested_action, confidence.\n\n"
        f"type={signal.signal_type} source={signal.source_type}\n"
        f"{signal.content or ''}"
    )


def _response_text(response: Any) -> Optional[str]:
    blocks = getattr(response, "content", None)
    if not blocks:
        return None
    return "".join(getattr(b, "text", "") for b in blocks)


def parse_enrichment(response: Any) -> Optional[ParsedEnrichment]:
    """Must tolerate malformed output: on a parse failure behave exactly like a
    skipped enrichment (return None), never raise."""
    text = _response_text(response)
    if not text:
        return None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    parsed = ParsedEnrichment(
        sentiment=data.get("sentiment"),
        relationship_sentiment=data.get("relationship_sentiment"),
        product_sentiment=data.get("product_sentiment"),
        urgency_score=data.get("urgency_score"),
        intent_signals=data.get("intent_signals"),
        stakeholder_roles=data.get("stakeholder_roles"),
        suggested_action=data.get("suggested_action"),
        confidence=data.get("confidence"),
    )
    # A well-formed JSON object carrying none of the enriched fields is
    # indistinguishable from a skipped enrichment; treat it as one.
    if all(getattr(parsed, f) is None for f in LLM_ENRICHED_FIELDS):
        return None
    return parsed


def _insert(signal: QualitativeSignal) -> QualitativeSignal:
    cur = db().execute(
        "INSERT INTO qualitative_signal (signal_id, customer_id, account_id,"
        " signal_date, signal_type, source_type, raw_text, content,"
        " structural_urgency, sentiment, relationship_sentiment,"
        " product_sentiment, urgency_score, intent_signals, stakeholder_roles,"
        " suggested_action, confidence, llm_model_version, effective_urgency,"
        " requires_review, cg_node_id)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            signal.signal_id,
            signal.customer_id,
            signal.account_id,
            signal.signal_date,
            signal.signal_type,
            signal.source_type,
            signal.raw_text,
            signal.content,
            signal.structural_urgency,
            signal.sentiment,
            signal.relationship_sentiment,
            signal.product_sentiment,
            signal.urgency_score,
            json.dumps(signal.intent_signals) if signal.intent_signals is not None else None,
            json.dumps(signal.stakeholder_roles) if signal.stakeholder_roles is not None else None,
            signal.suggested_action,
            json.dumps(signal.confidence) if signal.confidence is not None else None,
            signal.llm_model_version,
            signal.effective_urgency,
            1 if signal.requires_review else 0,
            signal.cg_node_id,
        ),
    )
    db().commit()
    signal.id = cur.lastrowid
    return signal


def process_signal(
    customer_id: int,
    account_id: int,
    raw_text: Optional[str],
    signal_date: str,
    signal_type: Optional[str],
    source_type: Optional[str],
    signal_id: str,
    cg_node_id: Optional[int] = None,  # SPEC-DEVIATION #7: declared in Data
    # Shapes + promised in Dependencies, but the spec gives no parameter or
    # code capable of populating it.
) -> QualitativeSignal:
    signal = QualitativeSignal(
        customer_id=customer_id,
        account_id=account_id,
        signal_id=signal_id,
        signal_date=signal_date,
        signal_type=signal_type,
        source_type=source_type,
        raw_text=raw_text,
        content=normalize(raw_text),
        cg_node_id=cg_node_id,
    )
    signal.structural_urgency = derive_structural_urgency(signal)
    signal.effective_urgency = signal.structural_urgency  # floor, set BEFORE
    # any LLM attempt, so a failed/skipped enrichment can never leave
    # effective_urgency unset

    call = call_llm_tracked(customer_id, "signal_enrichment", build_prompt(signal))
    if call.response is not None:
        parsed = parse_enrichment(call.response)
        if parsed is not None:
            signal.sentiment = parsed.sentiment
            signal.relationship_sentiment = parsed.relationship_sentiment
            signal.product_sentiment = parsed.product_sentiment
            signal.urgency_score = parsed.urgency_score
            # SPEC-DEVIATION #3: Boundary "Owns" promises stakeholder
            # attribution; the Build Prompt never writes these four columns.
            signal.intent_signals = parsed.intent_signals
            signal.stakeholder_roles = parsed.stakeholder_roles
            signal.suggested_action = parsed.suggested_action
            signal.confidence = parsed.confidence
            signal.llm_model_version = call.model  # the model WE called

            llm_level = score_to_level(parsed.urgency_score)
            # SPEC-DEVIATION #5: `urgency_score` is nullable, so `llm_level`
            # can be None; the spec indexes URGENCY_ORDER[llm_level] unguarded.
            if (
                llm_level is not None
                and URGENCY_ORDER[llm_level] > URGENCY_ORDER[signal.structural_urgency]
            ):
                signal.effective_urgency = llm_level  # RAISE only, never lower

            conf = parsed.confidence or {}
            if conf:
                signal.requires_review = any(
                    v < REVIEW_THRESHOLD for v in conf.values()
                )
            else:
                signal.requires_review = REVIEW_WHEN_CONFIDENCE_MISSING

    _assert_enrichment_pairing(signal)
    return _insert(signal)  # ALWAYS persisted, enriched or not


def _assert_enrichment_pairing(signal: QualitativeSignal) -> None:
    """SPEC-DEVIATION #2b: the spec states the enriched-implies-model-version
    invariant only in a code COMMENT. Executable here (Module 01's finding:
    'a required check living in a comment instead of executable code')."""
    enriched = signal.has_any_enriched_field()
    if enriched and not signal.llm_model_version:
        raise AssertionError(
            f"signal {signal.signal_id}: enriched fields set but "
            "llm_model_version is null (Gotcha 3)"
        )
    if not enriched and signal.llm_model_version:
        raise AssertionError(
            f"signal {signal.signal_id}: llm_model_version set but no "
            "enriched field is populated (Gotcha 3)"
        )


# =====================================================================
# Read helpers for tests
# =====================================================================


def get_signal(customer_id: int, signal_id: str) -> Optional[sqlite3.Row]:
    return db().execute(
        "SELECT * FROM qualitative_signal WHERE customer_id=? AND signal_id=?",
        (customer_id, signal_id),
    ).fetchone()


def usage_rows(customer_id: Optional[int] = None) -> list:
    if customer_id is None:
        return db().execute("SELECT * FROM llm_usage_record ORDER BY id").fetchall()
    return db().execute(
        "SELECT * FROM llm_usage_record WHERE customer_id=? ORDER BY id",
        (customer_id,),
    ).fetchall()
