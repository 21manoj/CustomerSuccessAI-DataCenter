"""Trivial stub wizard entry points.

Module 05's Boundary is explicit that the ANALYSIS ALGORITHMS are not owned by
this module ("Explicitly does not own: the actual pattern-detection /
calibration / prediction algorithms themselves").  So every entry point here is
a stub: it does no analysis at all.  What it DOES exercise is the contract the
orchestration layer depends on:

    run_wizard_X(customer_id: int, **kwargs) -> dict

...where the return dict signals success either via ``return_code`` (0 = success)
or via ``status`` ('completed' / 'failed').  Per Data Shapes and Gotcha 2 the
ORCHESTRATION layer must handle BOTH conventions with no wizard-specific
branching, so this file deliberately ships wizards using each convention, in
both the success and the failure direction, plus one that raises.

NOTE (spec gap, reported): the Build Prompt's dispatcher calls
``entry_point(customer_id)`` with exactly one positional argument, while Data
Shapes declares the contract as ``run_wizard_X(customer_id, **kwargs)``.  Nothing
in the spec ever passes ``**kwargs``, a run id, or ``WizardRun.config`` through.
These stubs therefore accept ``**kwargs`` and tolerate being called with only
``customer_id``.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Every invocation appends here.  The dead-branch regression test (Reference
# Test Harness item 1) uses this to prove a wizard was actually REACHED, which
# is a strictly stronger assertion than "trigger_wizard didn't raise".
INVOCATION_LOG: List[Dict[str, Any]] = []


def _record(wizard_id: str, customer_id, kwargs) -> None:
    INVOCATION_LOG.append(
        {"wizard_id": wizard_id, "customer_id": customer_id, "kwargs": dict(kwargs)}
    )


def reset_log() -> None:
    INVOCATION_LOG.clear()


def invocations_of(wizard_id: str) -> List[Dict[str, Any]]:
    return [inv for inv in INVOCATION_LOG if inv["wizard_id"] == wizard_id]


# --------------------------------------------------------------------------
# Success, `return_code` convention
# --------------------------------------------------------------------------
def run_wizard_a(customer_id, **kwargs) -> Dict[str, Any]:
    """Stands in for a pattern-detection wizard.  Succeeds via return_code."""
    _record("a", customer_id, kwargs)
    return {"return_code": 0, "patterns_found": 0}


# --------------------------------------------------------------------------
# Success, `status` convention
# --------------------------------------------------------------------------
def run_wizard_b(customer_id, **kwargs) -> Dict[str, Any]:
    """Stands in for an arc/learning wizard.  Succeeds via status."""
    _record("b", customer_id, kwargs)
    return {"status": "completed", "learnings": []}


# --------------------------------------------------------------------------
# Failure, `return_code` convention
# --------------------------------------------------------------------------
def run_wizard_c(customer_id, **kwargs) -> Dict[str, Any]:
    """Stands in for weight self-calibration.  Fails via return_code == 1."""
    _record("c", customer_id, kwargs)
    return {"return_code": 1, "reason": "not enough labelled outcomes"}


# --------------------------------------------------------------------------
# Failure, `status` convention
# --------------------------------------------------------------------------
def run_wizard_d(customer_id, **kwargs) -> Dict[str, Any]:
    """Stands in for the predictor calibrator.  Fails via status == 'failed'.

    'd' is deliberately the id used here: Gotcha 1 documents that in the
    reference system wizard 'd' is the one made unreachable by a stale
    allowlist guard, so the dead-branch regression test is most meaningful when
    'd' is present in WIZARD_ENTRY_POINTS.
    """
    _record("d", customer_id, kwargs)
    return {"status": "failed", "reason": "hazard sub-model did not converge"}


# --------------------------------------------------------------------------
# Unhandled exception
# --------------------------------------------------------------------------
def run_wizard_boom(customer_id, **kwargs) -> Dict[str, Any]:
    """Raises.  The run must still land in `failed` with completed_at set."""
    _record("boom", customer_id, kwargs)
    raise RuntimeError("wizard blew up mid-analysis")


# --------------------------------------------------------------------------
# Lazy-triggerable wizard
# --------------------------------------------------------------------------
def run_wizard_lazy(customer_id, **kwargs) -> Dict[str, Any]:
    """The only wizard configured `lazy_ok`.

    The spec's own TRIGGER_POLICY sets ALL FOUR wizards to explicit_only, which
    makes Reference Test Harness item 2's "if any wizard is configured lazy_ok,
    confirm it accepts one" vacuous.  This stub exists so the lazy_ok branch is
    actually exercised.
    """
    _record("lazy", customer_id, kwargs)
    return {"return_code": 0}


# --------------------------------------------------------------------------
# Neither convention (undefined by the spec; orchestration must not crash)
# --------------------------------------------------------------------------
def run_wizard_silent(customer_id, **kwargs) -> Dict[str, Any]:
    """Returns a dict with neither `return_code` nor `status`.

    The spec never says what this means.  The Build Prompt's expression
    evaluates it to False (failure), which is the fail-closed reading; this stub
    pins that behaviour under test.
    """
    _record("silent", customer_id, kwargs)
    return {"note": "did some work, forgot to say whether it worked"}


# --------------------------------------------------------------------------
# A wizard that produces a versioned artifact
# --------------------------------------------------------------------------
def run_wizard_artifact(customer_id, **kwargs) -> Dict[str, Any]:
    """Writes a versioned artifact through the orchestrator's single writer.

    This is the only stub that needs anything from the orchestration layer, and
    it is the stub that exposes a structural gap in the spec: the Build Prompt
    calls ``entry_point(customer_id)`` with no run id, yet
    ``write_versioned_artifact`` REQUIRES ``source_run_id``.  A wizard following
    the spec literally therefore cannot link its artifact to its own run.  Here
    the orchestrator passes ``run_id`` and ``orchestrator`` through **kwargs.
    """
    _record("artifact", customer_id, kwargs)
    orchestrator = kwargs.get("orchestrator")
    run_id = kwargs.get("run_id")
    if orchestrator is None or run_id is None:
        return {"return_code": 1, "reason": "orchestrator/run_id not supplied"}
    artifact = orchestrator.write_versioned_artifact(
        customer_id=customer_id,
        scope=kwargs.get("scope", "stub_scope"),
        payload={"coefficients": [0.1, 0.2]},
        source_run_id=run_id,
    )
    return {"return_code": 0, "artifact_version": artifact["version"]}
