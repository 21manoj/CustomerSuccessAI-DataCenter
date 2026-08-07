"""Test suite for the Module 05 wizard-orchestration framework.

Organised to mirror the spec: one test class per Acceptance Criterion, then one
per Reference Test Harness item, then a final class of DEFECT PROOFS -- tests
that transcribe the Build Prompt LITERALLY and demonstrate that the literal
version is broken.  Those last tests are the deliverable of an adversarial
validation run; they are what turns "I think this is a spec bug" into "here is
the failing case."

Run:  python3 -m unittest -v test_wizard_orchestration
"""

from __future__ import annotations

import inspect
import os
import sqlite3
import tempfile
import threading
import unittest

import stub_wizards
import wizard_orchestration as wo
from wizard_orchestration import WizardOrchestrator


class Base(unittest.TestCase):
    def setUp(self):
        stub_wizards.reset_log()
        self.orc = WizardOrchestrator(":memory:")
        self.addCleanup(self.orc.close)


# ==========================================================================
# AC1 -- reachability is dict membership, never a separate allowlist
# ==========================================================================
class TestAC1Reachability(Base):
    def test_wizard_in_entry_points_succeeds(self):
        run = self.orc.trigger_wizard(1, "a", "explicit_trigger:user_42")
        self.assertEqual(run["status"], "completed")
        self.assertEqual(len(stub_wizards.invocations_of("a")), 1)

    def test_unknown_wizard_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            self.orc.trigger_wizard(1, "zzz", "explicit_trigger:user_42")
        self.assertIn("Unknown wizard", str(ctx.exception))

    def test_no_second_allowlist_exists_in_the_dispatcher(self):
        """Gotcha 1's Fix, asserted structurally rather than by hand-reading.

        The dispatcher's source must not contain any literal wizard id.  A
        hard-coded id in the dispatcher is exactly how the reference system's
        `if wizard not in ('a','b','c')` guard drifted out of sync.
        """
        src = inspect.getsource(WizardOrchestrator.trigger_wizard)
        doc = WizardOrchestrator.trigger_wizard.__doc__
        if doc:
            src = src.replace(doc, "")
        for wizard_id in wo.WIZARD_ENTRY_POINTS:
            for literal in ("'%s'" % wizard_id, '"%s"' % wizard_id):
                self.assertNotIn(
                    literal,
                    src,
                    f"dispatcher hard-codes wizard id {wizard_id!r} -- that is a "
                    "second allowlist waiting to drift",
                )

    def test_wizard_missing_from_trigger_policy_is_still_reachable(self):
        """'orphan' is in WIZARD_ENTRY_POINTS but NOT in TRIGGER_POLICY.

        Reachability must come from the entry-point dict alone.  This is also
        the Gotcha 4 default: a wizard nobody configured is runnable, but only
        explicitly.
        """
        self.assertIn("orphan", wo.WIZARD_ENTRY_POINTS)
        self.assertNotIn("orphan", wo.TRIGGER_POLICY)
        run = self.orc.trigger_wizard(1, "orphan", "explicit_trigger:user_42")
        self.assertEqual(run["status"], "completed")
        self.assertEqual(WizardOrchestrator.policy_for("orphan"), "explicit_only")

    def test_unconfigured_wizard_defaults_to_explicit_only(self):
        """Gotcha 4: silence in the config must be SAFE, not auto-triggerable."""
        with self.assertRaises(PermissionError):
            self.orc.trigger_wizard(1, "orphan", "lazy_trigger:cro_dashboard")


# ==========================================================================
# AC2 -- policy rejection happens BEFORE any WizardRun row is created
# ==========================================================================
class TestAC2RejectionLeavesNoAuditTrail(Base):
    def test_lazy_trigger_on_explicit_only_raises_permission_error(self):
        with self.assertRaises(PermissionError) as ctx:
            self.orc.trigger_wizard(7, "d", "lazy_trigger:some_view")
        self.assertIn("explicit-only", str(ctx.exception))

    def test_rejected_trigger_creates_zero_wizard_run_rows(self):
        self.assertEqual(len(self.orc.list_runs()), 0)
        with self.assertRaises(PermissionError):
            self.orc.trigger_wizard(7, "d", "lazy_trigger:some_view")
        runs = self.orc.list_runs()
        self.assertEqual(
            runs, [], "a rejected trigger must leave NO run row at all"
        )

    def test_rejected_trigger_does_not_create_a_failed_row(self):
        """Rejection is not the same event as failure -- explicitly in AC2."""
        with self.assertRaises(PermissionError):
            self.orc.trigger_wizard(7, "d", "lazy_trigger:some_view")
        self.assertEqual(
            [r for r in self.orc.list_runs() if r["status"] == "failed"], []
        )

    def test_rejected_trigger_never_invokes_the_wizard(self):
        with self.assertRaises(PermissionError):
            self.orc.trigger_wizard(7, "d", "lazy_trigger:some_view")
        self.assertEqual(stub_wizards.invocations_of("d"), [])


# ==========================================================================
# AC3 -- both success conventions, one code path, no wizard-specific branching
# ==========================================================================
class TestAC3ResultShapeNormalisation(Base):
    def test_return_code_zero_is_success(self):
        run = self.orc.trigger_wizard(1, "a", "explicit_trigger:user_1")
        self.assertEqual(run["status"], "completed")

    def test_status_completed_is_success(self):
        run = self.orc.trigger_wizard(1, "b", "explicit_trigger:user_1")
        self.assertEqual(run["status"], "completed")

    def test_return_code_one_is_failure(self):
        run = self.orc.trigger_wizard(1, "c", "explicit_trigger:user_1")
        self.assertEqual(run["status"], "failed")

    def test_status_failed_is_failure(self):
        run = self.orc.trigger_wizard(1, "d", "explicit_trigger:user_1")
        self.assertEqual(run["status"], "failed")

    def test_both_failure_conventions_share_one_normaliser(self):
        """AC3 literally: 'by the SAME orchestration code, with no
        wizard-specific branching in the dispatcher to tell them apart.'"""
        src = inspect.getsource(WizardOrchestrator.interpret_result)
        self.assertNotIn("wizard_id", src)
        self.assertFalse(WizardOrchestrator.interpret_result({"return_code": 1}))
        self.assertFalse(WizardOrchestrator.interpret_result({"status": "failed"}))
        self.assertTrue(WizardOrchestrator.interpret_result({"return_code": 0}))
        self.assertTrue(WizardOrchestrator.interpret_result({"status": "completed"}))

    def test_return_code_wins_when_both_keys_present(self):
        """The Build Prompt's expression checks return_code FIRST; Gotcha 2's
        Fix says the same.  Pinned so a refactor can't silently flip it."""
        self.assertTrue(
            WizardOrchestrator.interpret_result(
                {"return_code": 0, "status": "failed"}
            )
        )

    def test_neither_convention_fails_closed(self):
        """UNDERSPECIFIED in the spec.  The Build Prompt's expression yields
        False; pinned here as the fail-closed reading."""
        run = self.orc.trigger_wizard(1, "silent", "explicit_trigger:user_1")
        self.assertEqual(run["status"], "failed")

    def test_non_dict_return_does_not_crash_the_dispatcher(self):
        self.assertFalse(WizardOrchestrator.interpret_result(None))


# ==========================================================================
# AC4 -- an unhandled exception still closes the run out
# ==========================================================================
class TestAC4ExceptionHandling(Base):
    def test_exception_marks_run_failed_and_reraises(self):
        with self.assertRaises(RuntimeError):
            self.orc.trigger_wizard(1, "boom", "explicit_trigger:user_9")
        runs = self.orc.list_runs("boom")
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["status"], "failed")

    def test_completed_at_is_set_on_crash(self):
        with self.assertRaises(RuntimeError):
            self.orc.trigger_wizard(1, "boom", "explicit_trigger:user_9")
        self.assertIsNotNone(self.orc.list_runs("boom")[0]["completed_at"])

    def test_exception_message_is_captured(self):
        with self.assertRaises(RuntimeError):
            self.orc.trigger_wizard(1, "boom", "explicit_trigger:user_9")
        run = self.orc.list_runs("boom")[0]
        self.assertIn("wizard blew up mid-analysis", run["error_message"])
        self.assertIn("wizard blew up mid-analysis", run["results"]["error"])

    def test_no_run_is_ever_left_in_queued_or_running(self):
        for wizard_id in wo.WIZARD_ENTRY_POINTS:
            try:
                self.orc.trigger_wizard(1, wizard_id, "explicit_trigger:user_9")
            except RuntimeError:
                pass
        stuck = [
            r for r in self.orc.list_runs() if r["status"] in ("queued", "running")
        ]
        self.assertEqual(stuck, [], f"runs stuck mid-flight: {stuck}")


# ==========================================================================
# AC5 -- exactly one active row per (customer, scope), history preserved
# ==========================================================================
class TestAC5SingleActiveVersion(Base):
    def test_two_sequential_writes_leave_exactly_one_active(self):
        self.orc.write_versioned_artifact(10, "wizard_b_patterns", {"n": 1}, None)
        self.orc.write_versioned_artifact(10, "wizard_b_patterns", {"n": 2}, None)
        active = self.orc.active_artifacts(10, "wizard_b_patterns")
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["payload"], {"n": 2})
        self.assertEqual(active[0]["version"], 2)

    def test_history_is_never_destroyed(self):
        for i in range(1, 4):
            self.orc.write_versioned_artifact(10, "s", {"n": i}, None)
        rows = self.orc.all_artifacts(10, "s")
        self.assertEqual([r["version"] for r in rows], [1, 2, 3])
        self.assertEqual([r["is_active"] for r in rows], [False, False, True])

    def test_exactly_one_active_holds_after_every_single_write(self):
        """'at all times ... including immediately after the second write's
        transaction commits, with no window where zero or two rows are active.'"""
        for i in range(1, 6):
            self.orc.write_versioned_artifact(10, "s", {"n": i}, None)
            self.assertEqual(len(self.orc.active_artifacts(10, "s")), 1)

    def test_platform_level_null_customer_also_holds(self):
        """customer_id is declared nullable in Data Shapes for BOTH entities."""
        self.orc.write_versioned_artifact(None, "platform_scope", {"n": 1}, None)
        self.orc.write_versioned_artifact(None, "platform_scope", {"n": 2}, None)
        active = self.orc.active_artifacts(None, "platform_scope")
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["version"], 2)


# ==========================================================================
# AC6 -- scope isolation
# ==========================================================================
class TestAC6ScopeIsolation(Base):
    def test_different_scopes_same_customer_do_not_deactivate_each_other(self):
        self.orc.write_versioned_artifact(10, "wizard_b_patterns", {"p": 1}, None)
        self.orc.write_versioned_artifact(10, "wizard_d_hazard_submodel", {"c": 1}, None)
        self.assertEqual(len(self.orc.active_artifacts(10, "wizard_b_patterns")), 1)
        self.assertEqual(
            len(self.orc.active_artifacts(10, "wizard_d_hazard_submodel")), 1
        )

    def test_second_write_to_one_scope_leaves_the_other_scope_alone(self):
        self.orc.write_versioned_artifact(10, "b_scope", {"p": 1}, None)
        self.orc.write_versioned_artifact(10, "d_scope", {"c": 1}, None)
        self.orc.write_versioned_artifact(10, "d_scope", {"c": 2}, None)
        b_active = self.orc.get_active_artifact(10, "b_scope")
        d_active = self.orc.get_active_artifact(10, "d_scope")
        self.assertEqual(b_active["version"], 1)
        self.assertEqual(b_active["payload"], {"p": 1})
        self.assertEqual(d_active["version"], 2)

    def test_versions_are_numbered_per_scope_not_per_customer(self):
        self.orc.write_versioned_artifact(10, "b_scope", {}, None)
        first_d = self.orc.write_versioned_artifact(10, "d_scope", {}, None)
        self.assertEqual(first_d["version"], 1)

    def test_same_scope_different_customers_are_isolated(self):
        self.orc.write_versioned_artifact(10, "s", {"c": 10}, None)
        self.orc.write_versioned_artifact(11, "s", {"c": 11}, None)
        self.assertEqual(len(self.orc.active_artifacts(10, "s")), 1)
        self.assertEqual(len(self.orc.active_artifacts(11, "s")), 1)

    def test_scope_is_required(self):
        with self.assertRaises(ValueError):
            self.orc.write_versioned_artifact(10, "", {}, None)


# ==========================================================================
# AC7 -- trigger_source is required, validated, and specific
# ==========================================================================
class TestAC7TriggerSource(Base):
    def test_omitting_trigger_source_is_a_rejected_call(self):
        with self.assertRaises(TypeError):
            self.orc.trigger_wizard(1, "a")  # type: ignore[call-arg]

    def test_empty_string_rejected(self):
        with self.assertRaises(ValueError):
            self.orc.trigger_wizard(1, "a", "")

    def test_whitespace_only_rejected(self):
        with self.assertRaises(ValueError):
            self.orc.trigger_wizard(1, "a", "   ")

    def test_none_rejected(self):
        with self.assertRaises(ValueError):
            self.orc.trigger_wizard(1, "a", None)  # type: ignore[arg-type]

    def test_generic_value_rejected(self):
        """Gotcha 3 names these two exact values as the real-world failure."""
        for generic in ("system", "mcp_onboarding"):
            with self.assertRaises(ValueError):
                self.orc.trigger_wizard(1, "a", generic)
            with self.assertRaises(ValueError):
                self.orc.trigger_wizard(1, "a", "explicit_trigger:" + generic)

    def test_unprefixed_source_rejected(self):
        """NOT stated in the spec, added by this build: the policy check keys off
        `startswith('lazy_trigger:')`, so an unprefixed source silently reads as
        explicit and bypasses governance entirely.  See defect proofs below."""
        with self.assertRaises(ValueError):
            self.orc.trigger_wizard(1, "a", "cro_dashboard")

    def test_prefix_with_no_actor_rejected(self):
        with self.assertRaises(ValueError):
            self.orc.trigger_wizard(1, "a", "explicit_trigger:")

    def test_rejection_creates_no_run(self):
        for bad in ("", "   ", "system", "cro_dashboard"):
            with self.assertRaises(ValueError):
                self.orc.trigger_wizard(1, "a", bad)
        self.assertEqual(self.orc.list_runs(), [])

    def test_valid_source_is_persisted_verbatim(self):
        run = self.orc.trigger_wizard(1, "a", "explicit_trigger:user_42")
        self.assertEqual(run["created_by"], "explicit_trigger:user_42")

    def test_lazy_source_is_persisted_with_the_view_name(self):
        run = self.orc.trigger_wizard(1, "lazy", "lazy_trigger:cro_dashboard")
        self.assertEqual(run["created_by"], "lazy_trigger:cro_dashboard")


# ==========================================================================
# Reference Test Harness item 1 -- DEAD-BRANCH REGRESSION TEST
# ==========================================================================
class TestHarness1DeadBranchRegression(Base):
    """'for every wizard ID present in WIZARD_ENTRY_POINTS, assert
    trigger_wizard can actually reach and successfully invoke it.'

    Note on wording: the spec simultaneously requires stub wizards that FAIL, so
    'successfully invoke' is read here as 'the entry point is actually reached
    and called' -- which is the property Gotcha 1's dead branch violates.  A
    wizard that reports failure was still reached; a dead-branch wizard is never
    called at all.
    """

    def test_every_registered_wizard_is_actually_reached(self):
        unreached = []
        for wizard_id in wo.WIZARD_ENTRY_POINTS:
            before = len(stub_wizards.INVOCATION_LOG)
            try:
                self.orc.trigger_wizard(1, wizard_id, "explicit_trigger:harness")
            except ValueError as exc:
                self.fail(
                    f"wizard {wizard_id!r} is registered but unreachable: {exc}"
                )
            except PermissionError as exc:
                self.fail(
                    f"wizard {wizard_id!r} rejected its own explicit trigger: {exc}"
                )
            except RuntimeError:
                pass  # run_wizard_boom: reached, then raised. That counts.
            if len(stub_wizards.INVOCATION_LOG) == before:
                unreached.append(wizard_id)
        self.assertEqual(
            unreached, [], f"registered but never invoked (dead branch): {unreached}"
        )

    def test_every_registered_wizard_has_a_run_row(self):
        for wizard_id in wo.WIZARD_ENTRY_POINTS:
            try:
                self.orc.trigger_wizard(1, wizard_id, "explicit_trigger:harness")
            except RuntimeError:
                pass
        seen = {r["wizard_id"] for r in self.orc.list_runs()}
        self.assertEqual(seen, set(wo.WIZARD_ENTRY_POINTS))

    def test_wizard_d_specifically_is_reachable(self):
        """The reference system's live bug is specifically wizard 'd'."""
        run = self.orc.trigger_wizard(1, "d", "explicit_trigger:harness")
        self.assertEqual(len(stub_wizards.invocations_of("d")), 1)
        self.assertEqual(run["wizard_id"], "d")


# ==========================================================================
# Reference Test Harness item 2 -- policy enforcement, one test per wizard
# ==========================================================================
class TestHarness2PolicyEnforcement(Base):
    def test_every_wizards_configured_policy_is_enforced(self):
        for wizard_id in wo.WIZARD_ENTRY_POINTS:
            policy = WizardOrchestrator.policy_for(wizard_id)
            with self.subTest(wizard=wizard_id, policy=policy):
                if policy == "explicit_only":
                    with self.assertRaises(PermissionError):
                        self.orc.trigger_wizard(
                            1, wizard_id, "lazy_trigger:cro_dashboard"
                        )
                else:
                    run = self.orc.trigger_wizard(
                        1, wizard_id, "lazy_trigger:cro_dashboard"
                    )
                    self.assertIn(run["status"], ("completed", "failed"))

    def test_at_least_one_lazy_ok_wizard_exists_to_exercise_that_branch(self):
        """The spec's own TRIGGER_POLICY sets all four wizards explicit_only,
        which makes harness item 2's lazy_ok clause vacuous.  This build adds
        one so the branch is genuinely covered."""
        lazy_ok = [
            w for w in wo.WIZARD_ENTRY_POINTS
            if WizardOrchestrator.policy_for(w) == "lazy_ok"
        ]
        self.assertTrue(lazy_ok)

    def test_explicit_trigger_always_allowed_regardless_of_policy(self):
        for wizard_id in ("a", "lazy"):
            run = self.orc.trigger_wizard(1, wizard_id, "explicit_trigger:user_1")
            self.assertIsNotNone(run)

    def test_policy_check_precedes_run_creation_for_every_wizard(self):
        for wizard_id in wo.WIZARD_ENTRY_POINTS:
            if WizardOrchestrator.policy_for(wizard_id) != "explicit_only":
                continue
            with self.assertRaises(PermissionError):
                self.orc.trigger_wizard(1, wizard_id, "lazy_trigger:v")
        self.assertEqual(self.orc.list_runs(), [])


# ==========================================================================
# Reference Test Harness item 3 -- atomicity / concurrency
# ==========================================================================
class TestHarness3Atomicity(Base):
    def test_crash_mid_write_leaves_the_first_row_still_active(self):
        """'mock the second half of the transaction to raise, and assert the
        FIRST write's row is still active afterwards -- a failed second write
        must not leave zero active rows for that scope.'"""
        first = self.orc.write_versioned_artifact(10, "s", {"n": 1}, None)
        self.assertTrue(first["is_active"])

        def boom():
            raise RuntimeError("crash between deactivate and insert")

        with self.assertRaises(RuntimeError):
            self.orc.write_versioned_artifact(
                10, "s", {"n": 2}, None, _fault_hook=boom
            )

        active = self.orc.active_artifacts(10, "s")
        self.assertEqual(len(active), 1, "a crashed write left != 1 active row")
        self.assertEqual(active[0]["id"], first["id"])
        self.assertEqual(active[0]["payload"], {"n": 1})

    def test_crashed_write_leaves_no_partial_row_behind(self):
        self.orc.write_versioned_artifact(10, "s", {"n": 1}, None)

        def boom():
            raise RuntimeError("crash")

        with self.assertRaises(RuntimeError):
            self.orc.write_versioned_artifact(
                10, "s", {"n": 2}, None, _fault_hook=boom
            )
        self.assertEqual(len(self.orc.all_artifacts(10, "s")), 1)

    def test_the_writer_uses_one_transaction_not_two_commits(self):
        src = inspect.getsource(WizardOrchestrator.write_versioned_artifact)
        self.assertEqual(
            src.count("self.transaction()"), 1, "more than one transaction opened"
        )
        # Engine bullet 2: 'never activate the new row and deactivate the old
        # one as two separate commits.'  No commit is issued inside the body at
        # all -- the single context manager owns COMMIT/ROLLBACK.
        self.assertNotIn("COMMIT", src)
        self.assertNotIn("commit()", src)

    def test_concurrent_writers_still_leave_exactly_one_active(self):
        """Real threads, real separate SQLite connections, one file DB."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))

        setup = WizardOrchestrator(path)
        setup.close()

        errors = []

        def writer(n):
            try:
                orc = WizardOrchestrator(path)
                try:
                    orc.write_versioned_artifact(10, "s", {"n": n}, None)
                finally:
                    orc.close()
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"concurrent writers errored: {errors}")
        checker = WizardOrchestrator(path)
        self.addCleanup(checker.close)
        self.assertEqual(len(checker.active_artifacts(10, "s")), 1)
        versions = [r["version"] for r in checker.all_artifacts(10, "s")]
        self.assertEqual(sorted(versions), [1, 2, 3, 4, 5, 6])

    def test_wizard_produced_artifact_is_linked_to_its_own_run(self):
        run = self.orc.trigger_wizard(
            10, "artifact", "explicit_trigger:user_1", config={"scope": "d_scope"}
        )
        self.assertEqual(run["status"], "completed")
        artifact = self.orc.get_active_artifact(10, "d_scope")
        self.assertEqual(artifact["source_run_id"], run["run_id"])


# ==========================================================================
# DEFECT PROOFS -- literal transcriptions of the spec, shown to be broken
# ==========================================================================
class TestSpecDefectProofs(Base):
    # -- (a)/(d) Build Prompt omits validation that AC7 + Gotcha 3 require ---
    @staticmethod
    def _literal_build_prompt_dispatcher(wizard_id, trigger_source):
        """The Build Prompt's guard clauses, transcribed verbatim.

            if wizard_id not in WIZARD_ENTRY_POINTS: raise ValueError(...)
            if TRIGGER_POLICY[wizard_id] == "explicit_only" and \
                    trigger_source.startswith("lazy_trigger:"):
                raise PermissionError(...)
            run = create_wizard_run(...)

        Returns True if the literal guards would have let the call through.
        """
        if wizard_id not in wo.WIZARD_ENTRY_POINTS:
            raise ValueError(f"Unknown wizard: {wizard_id}")
        if wo.TRIGGER_POLICY[wizard_id] == "explicit_only" and trigger_source.startswith(
            "lazy_trigger:"
        ):
            raise PermissionError("explicit-only")
        return True

    def test_literal_dispatcher_accepts_a_blank_trigger_source(self):
        """AC7 and Gotcha 3 both require rejection; the Build Prompt's code
        contains only a COMMENT saying so, and the comment does not execute."""
        self.assertTrue(self._literal_build_prompt_dispatcher("a", ""))
        # ...whereas the built dispatcher rejects it:
        with self.assertRaises(ValueError):
            self.orc.trigger_wizard(1, "a", "")

    def test_literal_dispatcher_accepts_a_generic_trigger_source(self):
        self.assertTrue(self._literal_build_prompt_dispatcher("a", "mcp_onboarding"))

    def test_literal_dispatcher_lets_an_unprefixed_lazy_trigger_bypass_policy(self):
        """A dashboard that passes 'cro_dashboard' instead of
        'lazy_trigger:cro_dashboard' silently runs an explicit_only wizard.
        The policy mechanism is a string-prefix convention that nothing
        validates."""
        self.assertTrue(self._literal_build_prompt_dispatcher("d", "cro_dashboard"))
        with self.assertRaises(ValueError):
            self.orc.trigger_wizard(1, "d", "cro_dashboard")

    def test_literal_policy_lookup_crashes_on_an_unconfigured_wizard(self):
        """Gotcha 4's Fix claims explicit_only is the code-level default 'as the
        Build Prompt's TRIGGER_POLICY dict does'.  It does not: the Build Prompt
        subscripts the dict, so an unconfigured wizard raises KeyError instead of
        defaulting safely."""
        with self.assertRaises(KeyError):
            _ = wo.TRIGGER_POLICY["orphan"]
        self.assertEqual(WizardOrchestrator.policy_for("orphan"), "explicit_only")

    # -- (a) Build Prompt write ordering vs Data Shapes' partial index ------
    def test_literal_writer_ordering_violates_the_single_active_index(self):
        """The Build Prompt inserts the new row as is_active=True and only THEN
        deactivates the old one.  Inside one transaction that is atomic, but it
        transiently violates the partial unique index Data Shapes floats -- so
        the two sections cannot both be implemented as written."""
        self.orc.write_versioned_artifact(10, "s", {"n": 1}, None)
        with self.assertRaises(sqlite3.IntegrityError):
            self.orc.write_versioned_artifact_spec_literal(10, "s", {"n": 2}, None)

    # -- (a) NULL customer_id + SQL equality --------------------------------
    def test_literal_writer_leaves_two_active_rows_for_platform_scope(self):
        """Data Shapes declares customer_id nullable.  The Build Prompt filters
        `VersionedArtifact.customer_id == customer_id`, which never matches NULL,
        so a platform-level artifact never deactivates its predecessor."""
        orc = WizardOrchestrator(":memory:", single_active_index=False)
        self.addCleanup(orc.close)
        orc.write_versioned_artifact_spec_literal(None, "platform", {"n": 1}, None)
        orc.write_versioned_artifact_spec_literal(None, "platform", {"n": 2}, None)
        self.assertEqual(
            len(orc.active_artifacts(None, "platform")),
            2,
            "expected the literal spec to produce the TWO-active-row bug",
        )
        # The built writer does not have this bug:
        orc.write_versioned_artifact(None, "platform2", {"n": 1}, None)
        orc.write_versioned_artifact(None, "platform2", {"n": 2}, None)
        self.assertEqual(len(orc.active_artifacts(None, "platform2")), 1)

    # -- (a)/(d) Data Shapes' UNIQUE constraint makes AC6 impossible --------
    def test_data_shapes_unique_constraint_makes_scope_isolation_impossible(self):
        """Data Shapes: 'UNIQUE constraint on (customer_id, version)'.
        Versions are numbered per (customer, scope), so the first write to a
        SECOND scope for the same customer is also version 1 and collides.
        AC6 requires exactly that sequence to work."""
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.execute(
            """CREATE TABLE va (
                   id INTEGER PRIMARY KEY, customer_id INTEGER, scope TEXT,
                   version INTEGER, is_active INTEGER,
                   UNIQUE (customer_id, version))"""
        )
        conn.execute(
            "INSERT INTO va (customer_id, scope, version, is_active) "
            "VALUES (10, 'wizard_b_patterns', 1, 1)"
        )
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO va (customer_id, scope, version, is_active) "
                "VALUES (10, 'wizard_d_hazard_submodel', 1, 1)"
            )

    # -- (c) scope missing from Data Shapes entirely ------------------------
    def test_scope_is_required_by_the_writer_but_absent_from_data_shapes(self):
        """Recorded as an executable assertion so the omission is not just a
        prose complaint: every AC5/AC6 guarantee is keyed on a column the Data
        Shapes block never declares."""
        sig = inspect.signature(WizardOrchestrator.write_versioned_artifact)
        self.assertIn("scope", sig.parameters)
        row = self.orc.write_versioned_artifact(10, "s", {}, None)
        self.assertIn("scope", row)

    # -- (c) wizard cannot supply source_run_id under the literal contract --
    def test_literal_entry_point_call_cannot_link_an_artifact_to_its_run(self):
        """The Build Prompt calls `entry_point(customer_id)` -- one positional
        argument, no run id, no orchestrator handle.  A wizard called that way
        cannot satisfy write_versioned_artifact's required source_run_id."""
        result = stub_wizards.run_wizard_artifact(10)
        self.assertEqual(result["return_code"], 1)
        self.assertIn("run_id", result["reason"])

    # -- (c) lazy trigger has no "fire once" mechanism ----------------------
    def test_lazy_trigger_fires_every_time_not_once(self):
        """Boundary promises lazy wizards 'may fire once, automatically, when a
        dashboard needs a result that doesn't exist yet.'  Nothing in the Build
        Prompt implements either the once-ness or the does-not-exist-yet check,
        so a dashboard that renders twice runs the expensive job twice."""
        self.orc.trigger_wizard(1, "lazy", "lazy_trigger:cro_dashboard")
        self.orc.trigger_wizard(1, "lazy", "lazy_trigger:cro_dashboard")
        self.assertEqual(len(self.orc.list_runs("lazy")), 2)

    # -- (c) WizardRun.config has no producer -------------------------------
    def test_wizard_run_config_has_no_producer_in_the_build_prompt(self):
        """Data Shapes declares `config (JSON -- what was requested)`, but
        `trigger_wizard(customer_id, wizard_id, trigger_source)` has no
        parameter that could ever populate it.  This build added one."""
        sig = inspect.signature(WizardOrchestrator.trigger_wizard)
        self.assertIn("config", sig.parameters)
        run = self.orc.trigger_wizard(
            1, "a", "explicit_trigger:user_1", config={"lookback_months": 6}
        )
        self.assertEqual(run["config"], {"lookback_months": 6})


if __name__ == "__main__":
    unittest.main(verbosity=2)
