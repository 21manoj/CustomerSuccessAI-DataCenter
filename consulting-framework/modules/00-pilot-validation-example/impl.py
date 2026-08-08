"""
Module 00 — Integration & Bootstrap: literal rebuild from SPEC.md alone.

Self-contained. Fakes for module01..module09 hooks. Real sqlite/SQLAlchemy used
for the schema-drift check so the headline guarantee can be tested for real.

Python 3.9 compatible (Optional[...] not X | Y).
"""
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Any

from sqlalchemy import (
    MetaData, Table, Column, Integer, String, ForeignKey, UniqueConstraint,
    create_engine, inspect, text,
)


# ---------------------------------------------------------------------------
# Piece 2: Schema authority + drift check  (implemented LITERALLY per spec)
# ---------------------------------------------------------------------------
class SchemaDriftError(Exception):
    pass


@dataclass
class DriftReport:
    missing: List[str] = field(default_factory=list)


class _DbShim:
    """Minimal stand-in for Flask-SQLAlchemy `db`: an .engine and .metadata,
    plus create_all(). Enough to drive ensure_schema/check_constraint_drift."""
    def __init__(self, engine, metadata):
        self.engine = engine
        self.metadata = metadata

    def create_all(self):
        # create_all fills MISSING tables only; never ALTERs an existing one.
        self.metadata.create_all(self.engine)


def ensure_schema(app, db, run_migrations):
    # `app` is only used for app_context in the real platform; ignored in shim.
    db.create_all()              # fills MISSING tables only
    run_migrations(db)           # applies ALTERs create_all cannot
    report = check_constraint_drift(db)
    if report.missing:
        raise SchemaDriftError(
            f"ORM declares constraints absent in the live DB: {report.missing}. "
            f"A migration is required — create_all cannot add them.")


def check_constraint_drift(db):
    # LITERAL transcription of the spec pseudocode (piece 2).
    insp = inspect(db.engine)
    missing = []
    for table in db.metadata.sorted_tables:
        declared = {fk.target_fullname for c in table.columns for fk in c.foreign_keys}
        live = {f"{fk['referred_table']}.{col}"
                for fk in insp.get_foreign_keys(table.name)
                for col in fk["referred_columns"]}
        missing += [d for d in declared if d.split(".")[-2] + "." + d.split(".")[-1]
                    not in live and d not in live]
    return DriftReport(missing=missing)


def check_constraint_drift_FIXED(db):
    """Corrected: also compares UNIQUE constraints (the second symptom named in
    Gotcha 1). Foreign-key logic unchanged."""
    insp = inspect(db.engine)
    missing = []
    for table in db.metadata.sorted_tables:
        declared = {fk.target_fullname for c in table.columns for fk in c.foreign_keys}
        live = {f"{fk['referred_table']}.{col}"
                for fk in insp.get_foreign_keys(table.name)
                for col in fk["referred_columns"]}
        missing += [d for d in declared if d not in live]
        # uniques
        declared_uq = {tuple(sorted(uc.columns.keys()))
                       for uc in table.constraints
                       if isinstance(uc, UniqueConstraint)}
        live_uq = {tuple(sorted(u["column_names"]))
                   for u in insp.get_unique_constraints(table.name)}
        missing += [f"{table.name}.UNIQUE{cols}" for cols in declared_uq if cols not in live_uq]
    return DriftReport(missing=missing)


# ---------------------------------------------------------------------------
# Piece 3: Config-resolution services (one resolver each)
# ---------------------------------------------------------------------------
# Fakes for the module01 hooks; tests monkeypatch these.
def module01_customer_config_weights(customer_id):   # tier 1
    return None
def load_bootstrap_weights(customer_id):             # tier 2
    return None
def default_weights(vertical):                       # tier 3
    return {"P1-KPI1": 1.0, "_source": f"kpi_definitions:{vertical}"}


def resolve_weights(customer_id, vertical):
    db_w = module01_customer_config_weights(customer_id)   # tier 1 (Wizard C)
    if db_w:
        return db_w
    boot = load_bootstrap_weights(customer_id)             # tier 2 (JSON)
    if boot:
        return boot
    return default_weights(vertical)                       # tier 3 (kpi_definitions)


THRESHOLDS = {"healthy": {"min": 70}, "at_risk": {"min": 50}}  # loaded from health_thresholds.json


def classify(health) -> str:
    if health is None:
        return "no_data"
    if health >= THRESHOLDS["healthy"]["min"]:
        return "healthy"
    if health >= THRESHOLDS["at_risk"]["min"]:
        return "at_risk"
    return "critical"


def normalize_vertical(raw) -> str:
    if raw is None:
        return "dc2_s"
    r = str(raw).strip().lower()
    aliases = {"dc2s": "dc2_s", "dc2-s": "dc2_s", "saas": "saas_premium",
               "saaspremium": "saas_premium", "saas-premium": "saas_premium"}
    return aliases.get(r, r)


def module01_customer_config_vertical(customer_id):  # the ONE canonical source
    return None
def module01_customer_vertical(customer_id):         # legacy, same value at create
    return None


def resolve_vertical(customer_id) -> str:
    raw = (module01_customer_config_vertical(customer_id)
           or module01_customer_vertical(customer_id))
    return normalize_vertical(raw) if raw else "dc2_s"


def data_path(customer_id):
    return f"verticals/customer{customer_id}-{resolve_vertical(customer_id)}/data"


# ---------------------------------------------------------------------------
# Piece 4: Feature toggles
# ---------------------------------------------------------------------------
class Toggle(Enum):
    SIGNAL_ANALYST = "signal_analyst"
    ROI = "roi"
    INDEX = "index"
    RECORD_RUN = "record_run"
    LLM_TIER1 = "llm_tier1"
    WIZARD_B = "wizard_b"


@dataclass
class ToggleCfg:
    default: bool = True
    dependencies: tuple = ()
    per_customer: bool = False


TOGGLES: Dict[Toggle, ToggleCfg] = {
    Toggle.SIGNAL_ANALYST: ToggleCfg(default=True),
    Toggle.ROI: ToggleCfg(default=True),
    Toggle.INDEX: ToggleCfg(default=True),
    Toggle.RECORD_RUN: ToggleCfg(default=True),
    Toggle.LLM_TIER1: ToggleCfg(default=True, per_customer=True),
    Toggle.WIZARD_B: ToggleCfg(default=True, dependencies=(Toggle.LLM_TIER1,)),
}

_PER_CUSTOMER_ROWS: Dict[tuple, bool] = {}   # (toggle, customer_id) -> bool


def per_customer_row_enabled(toggle, customer_id) -> bool:
    return _PER_CUSTOMER_ROWS.get((toggle, customer_id), True)  # defaults True if no row


def enable_per_customer(toggle, customer_id):
    _PER_CUSTOMER_ROWS[(toggle, customer_id)] = True


def is_enabled(toggle, customer_id=None) -> bool:
    cfg = TOGGLES[toggle]
    env = os.environ.get(f"FEATURE_{toggle.name}")
    enabled = (env.lower() in ("true", "1", "yes")) if env is not None else cfg.default
    if not enabled:
        return False
    for dep in cfg.dependencies:               # off if any dependency is off
        if not is_enabled(dep, customer_id):
            return False
    if customer_id is not None and cfg.per_customer:
        return per_customer_row_enabled(toggle, customer_id)  # defaults True if no row
    return True


# ---------------------------------------------------------------------------
# Piece 5: process_data stage sequencer
# ---------------------------------------------------------------------------
@dataclass
class ProcessResult:
    status: str = ""
    steps_completed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    scores_written: int = 0
    stages: Dict[str, Any] = field(default_factory=dict)


def run_stage(name, fn, result):
    try:
        out = fn()
        result.stages[name] = {"ok": True, "detail": str(out)}
        result.steps_completed.append(name)
        return out
    except Exception as e:               # per-stage isolation: log it, return None
        result.stages[name] = {"ok": False, "detail": f"non-fatal: {e}"}
        result.errors.append(f"{name}: {e}")
        return None


STAGE_ORDER = ["score", "publish_health", "signal_scan", "wizard_a",
               "llm_tier1", "wizard_b", "signal_analyst", "roi", "index",
               "record_run"]   # 'score' precedes 'signal_scan' by contract

MIN_ACCOUNTS_FOR_WIZARD_B = 5


# --- module hooks (fakes; monkeypatched by tests) --------------------------
def module03_score(customer_id, mode):        return 11
def module04_build_graph(customer_id):        return {"nodes": 1, "edges": 1}
def module05_wizard_a(customer_id):           return "wizard_a ok"
def module05_wizard_b(customer_id):           return "wizard_b ok"
def module06_signal_scan(customer_id):        return "signals ok"
def module09_load_csvs(customer_id, path):    return "loaded"
def publish_health_events(customer_id):       return "health published"
def run_llm_tier1(customer_id):               return "llm ok"
def fresh_or_incremental_csvs(customer_id):   return True
def journey_count(customer_id):               return 11


OPTIONAL_STAGES: Dict[str, Callable] = {
    "signal_analyst": lambda cid: "signal_analyst ok",
    "roi": lambda cid: "roi ok",
    "index": lambda cid: "index ok",
    "record_run": lambda cid: "record_run ok",
}


def process_data(customer_id, mode="auto"):
    assert mode in ("auto", "full_recalc")
    result = ProcessResult(status="", steps_completed=[], errors=[],
                           scores_written=0, stages={})
    if fresh_or_incremental_csvs(customer_id):
        module09_load_csvs(customer_id, data_path(customer_id))
    n = run_stage("score", lambda: module03_score(customer_id, mode), result)
    result.scores_written = int(n or 0)          # explicit int, not parsed from a string
    run_stage("publish_health", lambda: publish_health_events(customer_id), result)
    run_stage("signal_scan", lambda: module06_signal_scan(customer_id), result)  # after score
    run_stage("wizard_a", lambda: module05_wizard_a(customer_id), result)
    run_stage("llm_tier1", lambda: run_llm_tier1(customer_id), result)
    if journey_count(customer_id) >= MIN_ACCOUNTS_FOR_WIZARD_B:
        run_stage("wizard_b", lambda: module05_wizard_b(customer_id), result)
    for extra in ("signal_analyst", "roi", "index", "record_run"):
        run_stage(extra, lambda e=extra: OPTIONAL_STAGES[e](customer_id), result)
    result.status = ("success" if result.steps_completed and not result.errors
                     else "failed" if not result.steps_completed else "partial")
    return result


# ---------------------------------------------------------------------------
# Piece 6: new-tenant bootstrap (in-memory fake of the ORM writes)
# ---------------------------------------------------------------------------
@dataclass
class FakeCustomer:
    customer_id: int
    name: str
    domain: str
    vertical: str


@dataclass
class FakeCustomerConfig:
    customer_id: int
    vertical: str
    tier: Optional[str]


class FakeSession:
    def __init__(self):
        self.objects = []
        self._next_id = 100
        self.committed = False

    def add(self, obj):
        self.objects.append(obj)

    def flush(self):
        for o in self.objects:
            if isinstance(o, FakeCustomer) and getattr(o, "customer_id", None) is None:
                o.customer_id = self._next_id
                self._next_id += 1

    def commit(self):
        self.committed = True


class _DbSessionShim:
    def __init__(self):
        self.session = FakeSession()


db = _DbSessionShim()  # module-level "db" facade for bootstrap writes
DEFAULT_CUSTOMER_TOGGLES = [Toggle.LLM_TIER1]


def kpi_tier(tier, vertical):
    return {"tier": tier}


def generate_api_key(customer_id):
    return f"rawkey-{customer_id}"


def provision_data_dir(customer_id, vertical):
    return f"verticals/customer{customer_id}-{vertical}/data"


def create_customer(name, domain, vertical, admin_email, tier=None):
    v = normalize_vertical(vertical)
    cust = FakeCustomer(customer_id=None, name=name, domain=domain, vertical=v)
    db.session.add(cust)
    db.session.flush()
    db.session.add(FakeCustomerConfig(customer_id=cust.customer_id, vertical=v,
                                      **kpi_tier(tier, v)))
    raw_key = generate_api_key(cust.customer_id)
    provision_data_dir(cust.customer_id, v)
    for t in DEFAULT_CUSTOMER_TOGGLES:
        enable_per_customer(t, cust.customer_id)
    db.session.commit()
    return {"customer_id": cust.customer_id, "api_key": raw_key}
