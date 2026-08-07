"""
Adversarial validation suite for Module 09 — Ingestion & Onboarding Pipeline.

Two kinds of test in here:

  * AC / harness tests  — exercise every Acceptance Criterion and every
    Reference Test Harness item against the CORRECTED implementation.
  * DEFECT proofs       — execute the spec's OWN literal pseudocode
    (ingestion.SpecLiteral) and demonstrate the failure, then show the
    corrected implementation passing the same assertion.

Run:  python3 -m unittest -v test_ingestion
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import shutil
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from ingestion import (
    Rule, FILE_SCHEMAS, NATURAL_KEYS, FILE_COLUMNS, REFERENTIAL_KEYS,
    DDL, NATURAL_KEY_INDEXES, open_db, count_rows,
    UploadResult, StageResult, PipelineResult, Stage, StageSpec, Skip,
    Ingestion, IngestionConfig, SpecLiteral,
    validate_row, as_utc, _parse_ts,
    naive_local_has_new_data, utc_has_new_data,
    parse_iso_date,
)

UTC = timezone.utc
OFF_0 = timedelta(0)
OFF_M7 = timedelta(hours=-7)      # US/Pacific in summer — the Gotcha-1 host
OFF_P530 = timedelta(hours=5, minutes=30)   # Asia/Kolkata


# ---------------------------------------------------------------- helpers
def good_kpi_rows(n=3, account="ACC-1"):
    return [{"account_ref": account, "kpi_code": "P1-KPI1",
             "measured_at": "2026-0%d-01" % (i + 1), "value": "10.5",
             "note": None}
            for i in range(n)]


def touch_file(path, when_aware):
    """Write a file and force its mtime to an explicit aware datetime."""
    path = Path(path)
    path.write_text("x")
    ts = when_aware.timestamp()
    os.utime(str(path), (ts, ts))
    return path


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="m09-")
        self.con = open_db()
        self.storage = os.path.join(self.tmp, "storage")
        self.ing = Ingestion(self.con, IngestionConfig(),
                             storage_dir=self.storage)
        self.cid = 344

    def tearDown(self):
        self.con.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def spec_db(self, with_indexes=False):
        """A fresh DB for spec-literal runs.  The spec supplies NO DDL and
        never mentions a unique index, so the default is without one."""
        return open_db(with_natural_key_indexes=with_indexes)

    def state(self, cid=None):
        return self.ing.get_ingestion_state(cid or self.cid)


# =========================================================================
# HARNESS ITEM 1 / AC3 — TIMEZONE MATRIX  (highest-value test)
# =========================================================================
class TestHarness1TimezoneMatrix(Base):
    """Every timestamp here is constructed at an EXPLICIT UTC offset.
    Nothing depends on the test host's own zone, so this suite gives the same
    verdict on a UTC CI runner and on a PDT laptop — which is precisely what
    the reference system's version failed to do."""

    # the mark `datetime.utcnow()` would have written: naive, meaning UTC
    ANCHOR = datetime(2026, 8, 7, 19, 0, 0, tzinfo=UTC)

    def _cases(self):
        naive_stored = self.ANCHOR.replace(tzinfo=None)
        fresh = (self.ANCHOR + timedelta(seconds=30)).timestamp()
        stale = (self.ANCHOR - timedelta(seconds=30)).timestamp()
        return naive_stored, fresh, stale

    def test_corrected_utc_comparison_is_host_independent(self):
        """AC3 / harness 1: the fixed comparison gives the right answer for
        every host offset, because the host offset never enters it."""
        naive_stored, fresh, stale = self._cases()
        for label, off in [("+00:00", OFF_0), ("-07:00", OFF_M7),
                           ("+05:30", OFF_P530)]:
            with self.subTest(host=label):
                self.assertTrue(utc_has_new_data(naive_stored, fresh),
                                "%s: fresh file must be seen as new" % label)
                self.assertFalse(utc_has_new_data(naive_stored, stale),
                                 "%s: stale file must not be seen as new" % label)

    def test_naive_local_impl_is_wrong_on_utc_minus_7(self):
        """PROOF of Gotcha 1's exact live bug: on a host behind UTC, a file
        written 30s AFTER the last-ingested mark converts to a local
        wall-clock 7h BEFORE it, so the load step is silently skipped."""
        naive_stored, fresh, _ = self._cases()
        self.assertFalse(
            naive_local_has_new_data(naive_stored, fresh, OFF_M7),
            "expected the naive/local implementation to WRONGLY report "
            "no-new-data on a UTC-7 host")
        # ...and the corrected one gets it right on the identical inputs.
        self.assertTrue(utc_has_new_data(naive_stored, fresh))

    def test_naive_local_impl_is_wrong_in_the_other_direction_on_utc_plus_530(self):
        """The mirror-image failure the spec never mentions: on a host AHEAD
        of UTC, a genuinely STALE file is reported as new, so every run does a
        redundant full recompute — an availability/cost bug rather than a
        correctness one, but the same root cause."""
        naive_stored, _, stale = self._cases()
        self.assertTrue(
            naive_local_has_new_data(naive_stored, stale, OFF_P530),
            "expected the naive implementation to WRONGLY report new data "
            "for a stale file on a UTC+5:30 host")
        self.assertFalse(utc_has_new_data(naive_stored, stale))

    def test_naive_local_impl_looks_fine_on_a_utc_host(self):
        """Why it survived review: on a UTC container the buggy and the fixed
        implementations agree on every case."""
        naive_stored, fresh, stale = self._cases()
        self.assertTrue(naive_local_has_new_data(naive_stored, fresh, OFF_0))
        self.assertFalse(naive_local_has_new_data(naive_stored, stale, OFF_0))

    def test_full_matrix_table(self):
        """The whole matrix in one place: (host offset, file) -> naive vs fixed."""
        naive_stored, fresh, stale = self._cases()
        expected = {
            ("+00:00", "fresh"): (True, True),
            ("+00:00", "stale"): (False, False),
            ("-07:00", "fresh"): (False, True),    # naive WRONG
            ("-07:00", "stale"): (False, False),
            ("+05:30", "fresh"): (True, True),
            ("+05:30", "stale"): (True, False),     # naive WRONG
        }
        offsets = {"+00:00": OFF_0, "-07:00": OFF_M7, "+05:30": OFF_P530}
        files = {"fresh": fresh, "stale": stale}
        for (label, which), (exp_naive, exp_fixed) in expected.items():
            with self.subTest(host=label, file=which):
                self.assertEqual(
                    naive_local_has_new_data(naive_stored, files[which],
                                             offsets[label]), exp_naive)
                self.assertEqual(
                    utc_has_new_data(naive_stored, files[which]), exp_fixed)
        wrong = [k for k, (n, f) in expected.items() if n != f]
        self.assertEqual(len(wrong), 2,
                         "the naive impl must disagree with the fixed one in "
                         "exactly the two non-UTC cases")

    def test_end_to_end_freshness_on_real_files_at_explicit_offsets(self):
        """AC3 through the real has_new_data(), with mtimes set from datetimes
        carrying explicit tzinfo — never datetime.now() on the test box."""
        processed_at = datetime(2026, 8, 7, 12, 0, 0,
                                tzinfo=timezone(OFF_M7))   # 19:00Z
        self.ing.touch_last_ingested_at(self.cid, when=processed_at)
        self.ing.touch_last_processed_at(self.cid, when=processed_at)

        newer = touch_file(os.path.join(self.tmp, "kpis.csv"),
                           datetime(2026, 8, 7, 12, 1, 0, tzinfo=timezone(OFF_M7)))
        fresh, reason = self.ing.has_new_data(self.cid, [newer])
        self.assertTrue(fresh)
        self.assertEqual(reason, "new_data:kpis.csv")

        # the same instant expressed at +05:30 must behave identically
        older = touch_file(os.path.join(self.tmp, "old.csv"),
                           datetime(2026, 8, 8, 0, 29, 0,
                                    tzinfo=timezone(OFF_P530)))   # 18:59Z
        fresh2, reason2 = self.ing.has_new_data(self.cid, [older])
        self.assertFalse(fresh2)
        self.assertEqual(reason2, "no_new_data")

    def test_as_utc_null_and_aware_cases(self):
        naive = datetime(2026, 8, 7, 19, 0, 0)
        self.assertEqual(as_utc(naive).tzinfo, UTC)
        aware = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone(OFF_M7))
        self.assertIs(as_utc(aware).tzinfo, aware.tzinfo)   # untouched
        # the failure as_utc exists to prevent
        with self.assertRaises(TypeError):
            _ = naive > aware


# =========================================================================
# AC1 + HARNESS ITEM 2 — dry-run / real parity
# =========================================================================
class TestAC1DryRunParity(Base):
    def test_dry_run_matches_real_and_persists_nothing(self):
        rows = good_kpi_rows(3) + [{"account_ref": "ACC-1",
                                    "kpi_code": "NOPE", "measured_at": "x",
                                    "value": "abc"}]
        dry = self.ing.upload(self.cid, "kpi_measurements", rows,
                              validate_only=True)
        self.assertTrue(dry.validated_only)
        self.assertIsNone(dry.stored_path)                # NULL case
        self.assertEqual(count_rows(self.con, "kpi_measurements"), 0)
        self.assertEqual(count_rows(self.con, "accounts"), 0,
                         "a dry-run must not create accounts either")
        self.assertIsNone(self.state(), "dry-run must not create state")

        real = self.ing.upload(self.cid, "kpi_measurements", rows)
        self.assertEqual((dry.file_type, dry.rows_accepted, dry.rows_rejected,
                          dry.errors),
                         (real.file_type, real.rows_accepted,
                          real.rows_rejected, real.errors))
        self.assertFalse(real.validated_only)
        self.assertIsNotNone(real.stored_path)            # non-NULL case
        self.assertEqual(count_rows(self.con, "kpi_measurements"), 3)

    def test_dry_run_does_not_move_last_ingested_at(self):
        self.ing.touch_last_ingested_at(
            self.cid, when=datetime(2026, 1, 1, tzinfo=UTC))
        before = self.state()["last_ingested_at"]
        self.ing.upload(self.cid, "kpi_measurements", good_kpi_rows(2),
                        validate_only=True)
        self.assertEqual(self.state()["last_ingested_at"], before)

    def test_upload_result_shape_is_identical(self):
        rows = good_kpi_rows(1)
        d = self.ing.upload(self.cid, "kpi_measurements", rows, validate_only=True)
        r = self.ing.upload(self.cid, "kpi_measurements", rows)
        self.assertEqual(type(d), type(r))
        self.assertEqual([f for f in d.__dataclass_fields__],
                         [f for f in r.__dataclass_fields__])


# =========================================================================
# AC2 — partial acceptance and row-level error reporting
# =========================================================================
class TestAC2PartialAcceptance(Base):
    def test_bad_row_reported_with_number_column_message_others_accepted(self):
        rows = [
            {"account_ref": "A", "kpi_code": "P1-KPI1",
             "measured_at": "2026-01-01", "value": "1"},          # ok
            {"account_ref": "A", "kpi_code": "BOGUS",
             "measured_at": "2026-02-01", "value": "1"},          # enum
            {"account_ref": "A", "kpi_code": "P1-KPI1",
             "measured_at": "2026-03-01", "value": "1"},          # ok
        ]
        res = self.ing.upload(self.cid, "kpi_measurements", rows)
        self.assertEqual(res.rows_accepted, 2)
        self.assertEqual(res.rows_rejected, 1)
        self.assertEqual(len(res.errors), 1)
        e = res.errors[0]
        self.assertEqual(e["row_number"], 2)
        self.assertEqual(e["column"], "kpi_code")
        self.assertIn("not in", e["message"])
        self.assertEqual(count_rows(self.con, "kpi_measurements"), 2)

    def test_missing_required_column_reported_as_required(self):
        res = self.ing.upload(self.cid, "kpi_measurements",
                              [{"kpi_code": "P1-KPI1",
                                "measured_at": "2026-01-01", "value": "1"}])
        self.assertEqual([(e["column"], e["message"]) for e in res.errors],
                         [("account_ref", "required")])

    def test_empty_string_counts_as_missing_for_required(self):
        res = self.ing.upload(self.cid, "kpi_measurements",
                              [{"account_ref": "", "kpi_code": "P1-KPI1",
                                "measured_at": "2026-01-01", "value": "1"}])
        self.assertEqual(res.rows_rejected, 1)
        self.assertEqual(res.errors[0]["message"], "required")

    def test_optional_nullable_column_absent_is_accepted(self):
        """NULL case for the nullable `note` / `content` columns."""
        res = self.ing.upload(self.cid, "kpi_measurements",
                              [{"account_ref": "A", "kpi_code": "P1-KPI1",
                                "measured_at": "2026-01-01", "value": "1"}])
        self.assertEqual(res.rows_accepted, 1)
        row = self.con.execute("SELECT note FROM kpi_measurements").fetchone()
        self.assertIsNone(row["note"])

        res2 = self.ing.upload(self.cid, "signals",
                               [{"customer_id": self.cid, "signal_id": "s1",
                                 "channel": "email", "content": None}])
        self.assertEqual(res2.rows_accepted, 1)
        self.assertIsNone(
            self.con.execute("SELECT content FROM signals").fetchone()["content"])

    def test_cast_failure_reported(self):
        res = self.ing.upload(self.cid, "kpi_measurements",
                              [{"account_ref": "A", "kpi_code": "P1-KPI1",
                                "measured_at": "2026-01-01", "value": "abc"}])
        self.assertEqual(res.errors[0]["column"], "value")
        self.assertIn("cannot cast to float", res.errors[0]["message"])

    def test_empty_file_is_accepted_not_an_error(self):
        res = self.ing.upload(self.cid, "kpi_measurements", [])
        self.assertEqual((res.rows_accepted, res.rows_rejected), (0, 0))


# =========================================================================
# DEFECT D1 (shape a) — rows_rejected counts ERRORS, not ROWS
# =========================================================================
class TestDefectD1RowsRejectedCountsErrors(Base):
    ONE_BAD_ROW = [{"account_ref": "A", "kpi_code": "BOGUS",
                    "measured_at": "not-a-date", "value": "abc"}]

    def test_spec_literal_reports_three_rejected_rows_for_one_row(self):
        """PROOF: Data Shapes says rows_rejected is an int count of ROWS, and
        AC1 asserts dry-run/real parity on it.  The Build Prompt returns
        len(errors) — a count of error ENTRIES.  One row with three bad
        columns is reported as three rejected rows."""
        spec = SpecLiteral(self.spec_db())
        res = spec.upload(self.cid, "kpi_measurements", self.ONE_BAD_ROW,
                          validate_only=True)
        self.assertEqual(len(self.ONE_BAD_ROW), 1)
        self.assertEqual(res.rows_rejected, 3)          # <-- the defect
        self.assertNotEqual(res.rows_accepted + res.rows_rejected,
                            len(self.ONE_BAD_ROW))

    def test_corrected_counts_rows(self):
        res = self.ing.upload(self.cid, "kpi_measurements", self.ONE_BAD_ROW,
                              validate_only=True)
        self.assertEqual(res.rows_rejected, 1)
        self.assertEqual(len(res.errors), 3)
        self.assertEqual(res.rows_accepted + res.rows_rejected,
                         len(self.ONE_BAD_ROW))

    def test_invariant_holds_across_a_mixed_file(self):
        rows = good_kpi_rows(4) + self.ONE_BAD_ROW * 2
        res = self.ing.upload(self.cid, "kpi_measurements", rows,
                              validate_only=True)
        self.assertEqual(res.rows_accepted + res.rows_rejected, len(rows))


# =========================================================================
# DEFECT D2 (shape a) — touch-on-persist makes the first pipeline run a no-op
# =========================================================================
class TestDefectD2FreshnessMarkConflated(Base):
    """The Build Prompt's piece 1 moves `last_ingested_at` to now() on every
    successful persist, and piece 2's has_new_data asks 'is any source file
    newer than last_ingested_at?'.  Upload necessarily runs AFTER the files it
    reads were written, so the mark is always ahead of every mtime."""

    def _files_and_rows(self):
        f = touch_file(os.path.join(self.tmp, "kpis.csv"),
                       datetime(2026, 8, 7, 19, 0, 0, tzinfo=UTC))
        return [f], good_kpi_rows(3)

    def test_spec_literal_first_pipeline_run_after_upload_processes_nothing(self):
        ran = []
        stages = [Stage("health_scores", lambda c: ran.append("health") or "ok",
                        critical=True),
                  Stage("context_graph", lambda c: ran.append("graph") or "ok")]
        spec = SpecLiteral(self.spec_db(), stages=stages)
        files, rows = self._files_and_rows()

        spec.upload(self.cid, "kpi_measurements", rows)     # moves the mark
        result = spec.process_data(self.cid, files)

        # PROOF: reports success, ran nothing — the module Purpose's own
        # stated worst outcome, and Gotcha 1's symptom, from the Build Prompt.
        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.stages), 1)
        self.assertEqual(result.stages[0].detail, "no_new_data")
        self.assertEqual(ran, [], "no stage should have run — that is the bug")

    def test_corrected_first_pipeline_run_after_upload_processes_everything(self):
        ran = []
        stages = [StageSpec("health_scores",
                            lambda c: ran.append("health") or "ok", critical=True),
                  StageSpec("context_graph", lambda c: ran.append("graph") or "ok")]
        files, rows = self._files_and_rows()
        self.ing.upload(self.cid, "kpi_measurements", rows)
        result = self.ing.process_data(self.cid, files, stages=stages)
        self.assertEqual(result.status, "success")
        self.assertEqual(ran, ["health", "graph"])
        self.assertEqual(
            [s.detail for s in result.stages if s.name == "freshness_check"],
            ["never_processed"])

    def test_corrected_second_run_with_no_changes_is_a_no_op(self):
        stages = [StageSpec("health_scores", lambda c: "ok", critical=True)]
        files, rows = self._files_and_rows()
        self.ing.upload(self.cid, "kpi_measurements", rows)
        self.ing.process_data(self.cid, files, stages=stages)
        again = self.ing.process_data(self.cid, files, stages=stages)
        self.assertEqual(again.status, "success")
        self.assertEqual([s.name for s in again.stages], ["freshness_check"])
        self.assertEqual(again.stages[0].detail, "no_new_data")


# =========================================================================
# AC4 / AC5 — no-new-data skip and full_recalc
# =========================================================================
class TestAC4AC5FreshnessModes(Base):
    def setUp(self):
        super().setUp()
        self.files = [touch_file(os.path.join(self.tmp, "k.csv"),
                                 datetime(2026, 8, 7, 19, 0, tzinfo=UTC))]
        self.ran = []
        self.stages = [StageSpec("health_scores",
                                 lambda c: self.ran.append("h") or "scored",
                                 critical=True)]
        self.ing.upload(self.cid, "kpi_measurements", good_kpi_rows(2))
        self.ing.process_data(self.cid, self.files, stages=self.stages)
        self.ran.clear()

    def test_rerun_returns_success_with_single_skipped_stage_and_reason(self):
        r = self.ing.process_data(self.cid, self.files, stages=self.stages)
        self.assertEqual(r.status, "success")
        self.assertEqual(len(r.stages), 1)
        s = r.stages[0]
        self.assertEqual((s.status, s.detail, s.error),
                         ("skipped", "no_new_data", None))
        self.assertNotEqual(s.detail.strip(), "")
        self.assertEqual(self.ran, [], "must not re-run the stages")
        self.assertEqual(r.timings, {})
        self.assertEqual(r.total, 0.0)

    def test_full_recalc_reruns_and_reports_its_reason(self):
        r = self.ing.process_data(self.cid, self.files, mode="full_recalc",
                                  stages=self.stages)
        self.assertEqual(r.mode, "full_recalc")
        self.assertEqual(self.ran, ["h"])
        reasons = [s.detail for s in r.stages if s.name == "freshness_check"]
        self.assertEqual(reasons, ["full_recalc_requested"])

    def test_spec_literal_cannot_report_the_full_recalc_reason(self):
        """PROOF of D10: AC5 requires the re-run to happen 'with reason
        full_recalc_requested', but the Build Prompt drops `reason` on the
        fresh path and PipelineResult has no field for it.  The reason is
        observable only via a direct has_new_data() call — a workaround."""
        spec = SpecLiteral(self.spec_db(), stages=[Stage("s", lambda c: "ok")])
        spec.touch_last_ingested_at(self.cid)
        r = spec.process_data(self.cid, self.files, mode="full_recalc")
        self.assertNotIn("reason", r.__dataclass_fields__)
        self.assertNotIn("full_recalc_requested",
                         [s.detail for s in r.stages])
        self.assertNotIn("full_recalc_requested",
                         [s.name for s in r.stages])

    def test_touched_file_makes_it_fresh_again(self):
        touch_file(self.files[0], datetime(2026, 8, 8, 6, 0, tzinfo=UTC))
        r = self.ing.process_data(self.cid, self.files, stages=self.stages)
        self.assertEqual(self.ran, ["h"])
        self.assertEqual([s.detail for s in r.stages
                          if s.name == "freshness_check"], ["new_data:k.csv"])

    def test_never_ingested_null_case(self):
        """NULL case for the nullable last_ingested_at column."""
        fresh, reason = self.ing.has_new_data(999, self.files)
        self.assertEqual((fresh, reason), (True, "never_ingested"))
        self.ing.get_or_create_ingestion_state(998)
        self.assertIsNone(self.state(998)["last_ingested_at"])
        self.assertEqual(self.ing.has_new_data(998, self.files),
                         (True, "never_ingested"))


# =========================================================================
# DEFECT D9 (shape a/c) — API-payload tenants are permanently "no_new_data"
# =========================================================================
class TestDefectD9ApiPayloadFreshness(Base):
    def test_spec_literal_never_sees_new_data_without_source_files(self):
        """Boundary: the upload entry point is source-agnostic ('CSV or API
        payload') and connectors 'call this module's upload entry point'.
        has_new_data only ever iterates source_files, so a tenant that has
        never had a file on disk is frozen after its very first upload."""
        spec = SpecLiteral(self.spec_db(), stages=[Stage("s", lambda c: "ok")])
        spec.upload(self.cid, "signals",
                    [{"customer_id": self.cid, "signal_id": "s1",
                      "channel": "email", "content": "hi"}])
        self.assertEqual(spec.has_new_data(self.cid, [], "auto"),
                         (False, "no_new_data"))
        spec.upload(self.cid, "signals",
                    [{"customer_id": self.cid, "signal_id": "s2",
                      "channel": "email", "content": "more"}])
        self.assertEqual(spec.has_new_data(self.cid, [], "auto"),
                         (False, "no_new_data"))   # still frozen

    def test_corrected_tracks_uploads_without_files(self):
        stages = [StageSpec("health_scores", lambda c: "ok", critical=True)]
        self.ing.upload(self.cid, "signals",
                        [{"customer_id": self.cid, "signal_id": "s1",
                          "channel": "email", "content": "hi"}])
        r1 = self.ing.process_data(self.cid, [], stages=stages)
        self.assertEqual(r1.status, "success")
        self.assertEqual(self.ing.has_new_data(self.cid, []),
                         (False, "no_new_data"))
        self.ing.upload(self.cid, "signals",
                        [{"customer_id": self.cid, "signal_id": "s2",
                          "channel": "email", "content": "more"}])
        self.assertEqual(self.ing.has_new_data(self.cid, []),
                         (True, "new_upload"))


# =========================================================================
# AC6 + HARNESS ITEM 4 — idempotency;  DEFECT D4 (shape b) — undefined upsert
# =========================================================================
class TestAC6Idempotency(Base):
    def test_double_upload_same_row_count(self):
        rows = good_kpi_rows(3)
        self.ing.upload(self.cid, "kpi_measurements", rows)
        first = count_rows(self.con, "kpi_measurements")
        self.ing.upload(self.cid, "kpi_measurements", rows)
        self.assertEqual(count_rows(self.con, "kpi_measurements"), first)
        self.assertEqual(first, 3)

    def test_upsert_updates_non_key_columns(self):
        rows = good_kpi_rows(1)
        self.ing.upload(self.cid, "kpi_measurements", rows)
        rows[0]["value"] = "99.9"
        self.ing.upload(self.cid, "kpi_measurements", rows)
        self.assertEqual(count_rows(self.con, "kpi_measurements"), 1)
        self.assertEqual(
            self.con.execute("SELECT value FROM kpi_measurements").fetchone()[0],
            "99.9")

    def test_duplicate_rows_within_one_file(self):
        rows = good_kpi_rows(1) * 4
        self.ing.upload(self.cid, "kpi_measurements", rows)
        self.assertEqual(count_rows(self.con, "kpi_measurements"), 1)

    def test_two_customers_same_natural_key_do_not_collide(self):
        rows = good_kpi_rows(1)
        self.ing.upload(1, "kpi_measurements", rows)
        self.ing.upload(2, "kpi_measurements", rows)
        self.assertEqual(count_rows(self.con, "kpi_measurements"), 2)


class TestDefectD4UndefinedUpsert(Base):
    """`upsert(...)` is called by the Build Prompt and defined only inside a
    comment.  The spec contains NO DDL and never mentions a unique index, so
    `INSERT ... ON CONFLICT (natural key)` is not expressible; the two natural
    fallbacks are exactly the two anti-patterns that comment names."""

    def test_natural_fill_bare_insert_duplicates_and_breaks_ac6(self):
        spec = SpecLiteral(self.spec_db(), upsert_impl="bare_insert")
        rows = good_kpi_rows(3)
        spec.upload(self.cid, "kpi_measurements", rows)
        spec.upload(self.cid, "kpi_measurements", rows)
        self.assertEqual(count_rows(spec.con, "kpi_measurements"), 6)  # defect

    def test_natural_fill_select_then_insert_silently_drops_updates(self):
        """The other natural fill is the comment's second named anti-pattern —
        and besides being racy it is a SELECT-then-skip, so a corrected value
        in a re-upload is silently discarded (no DO UPDATE)."""
        spec = SpecLiteral(self.spec_db(), upsert_impl="select_then_insert")
        rows = good_kpi_rows(1)
        spec.upload(self.cid, "kpi_measurements", rows)
        rows[0]["value"] = "99.9"
        spec.upload(self.cid, "kpi_measurements", rows)
        self.assertEqual(count_rows(spec.con, "kpi_measurements"), 1)
        self.assertEqual(
            spec.con.execute("SELECT value FROM kpi_measurements").fetchone()[0],
            "10.5", "stale value silently retained")

    def test_on_conflict_is_not_expressible_without_the_index_the_spec_omits(self):
        """PROOF that the missing DDL is what forces the anti-pattern: the very
        statement the comment demands raises without a matching unique index."""
        con = self.spec_db(with_indexes=False)
        with self.assertRaises(sqlite3.OperationalError) as cm:
            con.execute(
                "INSERT INTO kpi_measurements "
                "(customer_id,account_ref,kpi_code,measured_at,value) "
                "VALUES (1,'A','P1-KPI1','2026-01-01','1') "
                "ON CONFLICT(customer_id,account_ref,kpi_code,measured_at) "
                "DO UPDATE SET value=excluded.value")
        self.assertIn("ON CONFLICT clause does not match", str(cm.exception))
        # with the index the corrected build creates, it works
        con2 = self.spec_db(with_indexes=True)
        con2.execute(
            "INSERT INTO kpi_measurements "
            "(customer_id,account_ref,kpi_code,measured_at,value) "
            "VALUES (1,'A','P1-KPI1','2026-01-01','1') "
            "ON CONFLICT(customer_id,account_ref,kpi_code,measured_at) "
            "DO UPDATE SET value=excluded.value")


# =========================================================================
# DEFECT D5 (shape d, NULL case) — row[c] on a nullable natural-key column
# =========================================================================
class TestDefectD5NullNaturalKey(Base):
    TP = [{"account_ref": "A", "touchpoint_id": "t1",
           "occurred_at": "2026-01-01", "summary": "call"},
          {"account_ref": "A", "touchpoint_id": "t2", "summary": "email"}]
          # ^ occurred_at is OPTIONAL in the schema and absent here

    def test_spec_literal_persist_raises_keyerror_midway(self):
        """PROOF: piece 3 uses `row[c]`, so an optional natural-key column that
        validated fine explodes inside persist — after earlier rows were
        already written and BEFORE touch_last_ingested_at runs."""
        spec = SpecLiteral(self.spec_db())
        v = spec.upload(self.cid, "touchpoints", self.TP, validate_only=True)
        self.assertEqual(v.rows_accepted, 2)      # validation says it's fine
        with self.assertRaises(KeyError) as cm:
            spec.upload(self.cid, "touchpoints", self.TP)
        self.assertEqual(cm.exception.args[0], "occurred_at")
        # partially persisted, and the freshness mark never moved
        self.assertEqual(count_rows(spec.con, "touchpoints"), 1)
        self.assertIsNone(spec.get_ingestion_state(self.cid))

    def test_naive_get_fix_still_duplicates_because_sql_nulls_are_distinct(self):
        """PROOF that swapping row[c] -> row.get(c) is NOT enough: a real SQL
        NULL never conflicts with another NULL, so the unique index that is
        supposed to deliver AC6 does not fire."""
        con = self.spec_db(with_indexes=True)
        for _ in range(2):
            con.execute("INSERT INTO touchpoints "
                        "(customer_id,account_ref,touchpoint_id,occurred_at) "
                        "VALUES (1,'A','t2',NULL)")
        con.commit()
        self.assertEqual(count_rows(con, "touchpoints"), 2)   # defect

    def test_corrected_handles_null_natural_key_and_stays_idempotent(self):
        r1 = self.ing.upload(self.cid, "touchpoints", self.TP)
        self.assertEqual(r1.rows_accepted, 2)
        self.assertEqual(count_rows(self.con, "touchpoints"), 2)
        self.ing.upload(self.cid, "touchpoints", self.TP)
        self.assertEqual(count_rows(self.con, "touchpoints"), 2)
        self.assertIsNotNone(self.state()["last_ingested_at"])

    def test_corrected_null_key_row_updates_rather_than_duplicates(self):
        self.ing.upload(self.cid, "touchpoints", self.TP)
        changed = [dict(self.TP[1], summary="email v2")]
        self.ing.upload(self.cid, "touchpoints", changed)
        self.assertEqual(count_rows(self.con, "touchpoints"), 2)
        got = self.con.execute(
            "SELECT summary FROM touchpoints WHERE touchpoint_id='t2'"
        ).fetchone()[0]
        self.assertEqual(got, "email v2")


# =========================================================================
# DEFECT D3 (shape c/d) — persist() has no return; stored_path is dead
# =========================================================================
class TestDefectD3StoredPathDead(Base):
    def test_spec_literal_stored_path_is_always_none(self):
        """PROOF: `path = persist(...)` binds None because the Build Prompt's
        persist() body has no return statement.  `stored_path` is a declared
        Data Shapes field with no producer — and `validated_only` is then the
        ONLY thing distinguishing a dry-run result from a real one."""
        spec = SpecLiteral(self.spec_db())
        real = spec.upload(self.cid, "kpi_measurements", good_kpi_rows(2))
        dry = spec.upload(self.cid, "kpi_measurements", good_kpi_rows(2),
                          validate_only=True)
        self.assertIsNone(real.stored_path)
        self.assertIsNone(dry.stored_path)
        self.assertEqual(real.stored_path, dry.stored_path)

    def test_corrected_returns_a_real_path_and_null_when_unconfigured(self):
        real = self.ing.upload(self.cid, "kpi_measurements", good_kpi_rows(2))
        self.assertIsNotNone(real.stored_path)
        self.assertTrue(os.path.exists(real.stored_path))
        # NULL case: no storage_dir configured -> stored_path is None
        bare = Ingestion(open_db(), IngestionConfig(), storage_dir=None)
        self.assertIsNone(
            bare.upload(self.cid, "kpi_measurements",
                        good_kpi_rows(1)).stored_path)


# =========================================================================
# AC7 / AC8 + HARNESS ITEM 3 — stage isolation matrix
# =========================================================================
def boom(_c):
    raise RuntimeError("stage exploded")


class TestAC7AC8StageIsolation(Base):
    def _stages(self, ran, failing=None, critical_names=("health_scores",)):
        def mk(name):
            def fn(c):
                if name == failing:
                    boom(c)
                ran.append(name)
                return "%s ok" % name
            return fn
        return [StageSpec(n, mk(n), critical=(n in critical_names))
                for n in ("health_scores", "context_graph",
                          "signal_enrichment", "wizards")]

    def test_non_critical_failure_gives_partial_and_continues(self):
        ran = []
        st = self._stages(ran, failing="context_graph")
        r = self.ing.process_data(self.cid, [], stages=st)
        self.assertEqual(r.status, "partial")
        bad = [s for s in r.stages if s.name == "context_graph"][0]
        self.assertEqual(bad.status, "failed")
        self.assertIn("stage exploded", bad.error)      # non-NULL error
        self.assertEqual(ran, ["health_scores", "signal_enrichment", "wizards"])
        for s in r.stages:
            if s.status == "completed":
                self.assertIsNone(s.error)              # NULL error case

    def test_critical_failure_aborts_with_failed_and_no_subsequent_stages(self):
        ran = []
        st = self._stages(ran, failing="health_scores")
        r = self.ing.process_data(self.cid, [], stages=st)
        self.assertEqual(r.status, "failed")
        self.assertEqual(ran, [])
        names = [s.name for s in r.stages if s.name != "freshness_check"]
        self.assertEqual(names, ["health_scores"])
        self.assertEqual(r.stages[-1].status, "failed")

    def test_critical_failure_mid_list_keeps_earlier_results_and_timings(self):
        ran = []
        st = self._stages(ran, failing="signal_enrichment",
                          critical_names=("signal_enrichment",))
        r = self.ing.process_data(self.cid, [], stages=st)
        self.assertEqual(r.status, "failed")
        self.assertEqual(ran, ["health_scores", "context_graph"])
        self.assertIn("signal_enrichment", r.timings)
        self.assertNotIn("wizards", r.timings)
        self.assertAlmostEqual(r.total, sum(r.timings.values()))

    def test_all_stages_succeed_is_plain_success(self):
        ran = []
        r = self.ing.process_data(self.cid, [], stages=self._stages(ran))
        self.assertEqual(r.status, "success")
        self.assertEqual(len(ran), 4)
        self.assertTrue(all(s.error is None for s in r.stages))

    def test_two_non_critical_failures_still_partial(self):
        ran = []
        st = self._stages(ran)
        st[1].fn = boom
        st[3].fn = boom
        r = self.ing.process_data(self.cid, [], stages=st)
        self.assertEqual(r.status, "partial")
        self.assertEqual(len([s for s in r.stages if s.status == "failed"]), 2)

    def test_timings_recorded_per_stage(self):
        ran = []
        r = self.ing.process_data(self.cid, [], stages=self._stages(ran))
        for name in ("health_scores", "context_graph", "signal_enrichment",
                     "wizards"):
            self.assertIn(name, r.timings)
            self.assertGreaterEqual(r.timings[name], 0.0)
        self.assertAlmostEqual(r.total, sum(r.timings.values()))

    def test_spec_literal_matches_on_the_isolation_matrix(self):
        """The one part of piece 4 that is genuinely correct — assert it, so
        the report can say the isolation mechanism itself is sound."""
        ran = []

        def mk(name, fail=False):
            def fn(c):
                if fail:
                    boom(c)
                ran.append(name)
                return "ok"
            return fn
        spec = SpecLiteral(self.spec_db(), stages=[
            Stage("a", mk("a"), critical=True),
            Stage("b", mk("b", fail=True)),
            Stage("c", mk("c"))])
        spec.touch_last_ingested_at(self.cid)
        r = spec.process_data(self.cid, [], mode="full_recalc")
        self.assertEqual(r.status, "partial")
        self.assertEqual(ran, ["a", "c"])


# =========================================================================
# AC9 — a partial stage list runs cleanly;  DEFECT D8 — STAGES is a global
# =========================================================================
class TestAC9OptionalStages(Base):
    def test_only_health_stage(self):
        ran = []
        r = self.ing.process_data(
            self.cid, [], stages=[StageSpec("health_scores",
                                            lambda c: ran.append("h") or "ok",
                                            critical=True)])
        self.assertEqual(r.status, "success")
        self.assertEqual(ran, ["h"])
        self.assertNotIn("context_graph", r.timings)

    def test_no_graph_stage_for_a_client_without_one(self):
        names = ("health_scores", "signal_enrichment")
        r = self.ing.process_data(
            self.cid, [], stages=[StageSpec(n, lambda c: "ok",
                                            critical=(n == "health_scores"))
                                  for n in names])
        self.assertEqual(r.status, "success")
        self.assertEqual([s.name for s in r.stages if s.name != "freshness_check"],
                         list(names))

    def test_empty_stage_list_runs_cleanly(self):
        r = self.ing.process_data(self.cid, [], stages=[])
        self.assertEqual(r.status, "success")
        self.assertEqual([s.name for s in r.stages], ["freshness_check"])

    def test_defect_d8_spec_literal_stage_list_is_not_a_parameter(self):
        """PROOF: process_data's signature is (customer_id, source_files,
        mode) and it iterates a module-level global STAGES.  AC9 can only be
        satisfied by mutating that global — the stage list is declared Config
        but is not injectable."""
        import inspect
        sig = inspect.signature(SpecLiteral.process_data)
        self.assertNotIn("stages", sig.parameters)
        self.assertIn("stages", inspect.signature(Ingestion.process_data).parameters)


# =========================================================================
# AC10 + DEFECT D6 (shape c) — structured skip reasons for STAGES
# =========================================================================
class TestAC10SkipReasons(Base):
    def test_several_stages_skip_each_with_a_nonempty_reason(self):
        stages = [
            StageSpec("health_scores", lambda c: "scored", critical=True),
            StageSpec("context_graph", lambda c: "built",
                      enabled=lambda c: Skip("feature_disabled")),
            StageSpec("signal_enrichment", lambda c: Skip("no_signals_for_tenant")),
            StageSpec("wizards", lambda c: "ran"),
        ]
        r = self.ing.process_data(self.cid, [], stages=stages)
        skipped = [s for s in r.stages if s.status == "skipped"]
        self.assertEqual(len(skipped), 2)
        for s in skipped:
            self.assertTrue(s.detail and s.detail.strip())
            self.assertNotEqual(s.detail.lower(), "skipped")
            self.assertIsNone(s.error)
        self.assertEqual(sorted(s.detail for s in skipped),
                         ["feature_disabled", "no_signals_for_tenant"])
        self.assertEqual(r.status, "success")

    def test_every_skipped_result_in_any_run_has_a_reason(self):
        stages = [StageSpec("a", lambda c: Skip("no_new_data")),
                  StageSpec("b", lambda c: Skip("feature_disabled")),
                  StageSpec("c", lambda c: "ok")]
        for mode in ("auto", "full_recalc"):
            r = self.ing.process_data(self.cid, [], mode=mode, stages=stages)
            for s in r.stages:
                if s.status == "skipped":
                    self.assertTrue(s.detail.strip())

    def test_blank_skip_reason_is_rejected_structurally(self):
        with self.assertRaises(ValueError):
            self.ing.process_data(
                self.cid, [], stages=[StageSpec("a", lambda c: Skip(""))])
        with self.assertRaises(ValueError):
            self.ing.process_data(
                self.cid, [], stages=[StageSpec("a", lambda c: Skip("   "))])

    def test_defect_d6_spec_literal_can_never_produce_a_skipped_stage(self):
        """PROOF that AC10 ('assert this across all stages in a run where
        several skip') is unsatisfiable against the Build Prompt: piece 4's
        loop has exactly two outcomes, 'completed' and 'failed'.  A stage that
        wants to skip can only return a value, which is recorded as COMPLETED
        — so a genuine skip is indistinguishable from real work, the inverse
        of Gotcha 4.  Data Shapes' 'feature_disabled' example is unreachable
        and StageResult.status='skipped' is dead surface outside the freshness
        branch."""
        spec = SpecLiteral(self.spec_db(), stages=[
            Stage("context_graph", lambda c: "skipped: feature_disabled"),
            Stage("wizards", lambda c: "ran")])
        spec.touch_last_ingested_at(self.cid)
        r = spec.process_data(self.cid, [], mode="full_recalc")
        self.assertEqual([s.status for s in r.stages],
                         ["completed", "completed"])
        self.assertEqual([s.status for s in r.stages].count("skipped"), 0)
        import inspect
        src = inspect.getsource(SpecLiteral.process_data)
        self.assertEqual(src.count('"skipped"'), 1,
                         "the only 'skipped' in piece 4 is the freshness one")


# =========================================================================
# DEFECT D7 (shape c) — referential sanity / account resolution absent
# =========================================================================
class TestDefectD7ReferentialSanity(Base):
    BAD = [{"account_ref": "GHOST", "kpi_code": "P1-KPI1",
            "measured_at": "2026-01-01", "value": "1"}]

    def test_spec_literal_accepts_a_row_referencing_a_nonexistent_account(self):
        """PROOF: Boundary 'Owns' bullet 1 lists 'referential sanity' among
        what is validated at the boundary, and Dependencies says accounts are
        'resolved or created during ingestion'.  validate_row only ever looks
        inside one row — neither behaviour exists anywhere in the Build
        Prompt, so the shift-left promise downstream modules rely on is not
        kept."""
        spec = SpecLiteral(self.spec_db())
        res = spec.upload(self.cid, "kpi_measurements", self.BAD)
        self.assertEqual(res.rows_accepted, 1)
        self.assertEqual(res.errors, [])
        self.assertEqual(count_rows(spec.con, "kpi_measurements"), 1)
        self.assertEqual(count_rows(spec.con, "accounts"), 0,
                         "no account was resolved or created")
        import inspect
        whole = inspect.getsource(SpecLiteral)
        for token in ("account", "referential", "resolve"):
            self.assertNotIn(token, whole.replace("account_ref", ""))

    def test_corrected_creates_the_account_when_policy_allows(self):
        res = self.ing.upload(self.cid, "kpi_measurements", self.BAD)
        self.assertEqual(res.rows_accepted, 1)
        self.assertTrue(self.ing.account_exists(self.cid, "GHOST"))

    def test_corrected_rejects_unknown_account_when_policy_forbids(self):
        strict = Ingestion(open_db(), IngestionConfig(create_missing_accounts=False))
        res = strict.upload(self.cid, "kpi_measurements", self.BAD)
        self.assertEqual(res.rows_accepted, 0)
        self.assertEqual(res.rows_rejected, 1)
        self.assertEqual(res.errors[0]["column"], "account_ref")
        self.assertEqual(res.errors[0]["message"], "unknown_account")

    def test_referential_check_runs_in_dry_run_without_creating(self):
        strict = Ingestion(open_db(), IngestionConfig(create_missing_accounts=False))
        dry = strict.upload(self.cid, "kpi_measurements", self.BAD,
                            validate_only=True)
        real = strict.upload(self.cid, "kpi_measurements", self.BAD)
        self.assertEqual((dry.rows_accepted, dry.rows_rejected),
                         (real.rows_accepted, real.rows_rejected))
        self.assertEqual(count_rows(strict.con, "accounts"), 0)

    def test_null_referential_value_is_left_to_the_required_rule(self):
        """NULL case: a NULL account_ref must not be reported as
        unknown_account on top of 'required'."""
        strict = Ingestion(open_db(), IngestionConfig(create_missing_accounts=False))
        res = strict.upload(self.cid, "kpi_measurements",
                            [{"account_ref": None, "kpi_code": "P1-KPI1",
                              "measured_at": "2026-01-01", "value": "1"}])
        self.assertEqual([e["message"] for e in res.errors], ["required"])


# =========================================================================
# Cross-cutting: data-shape conformance and null-field coverage
# =========================================================================
class TestDataShapeConformance(Base):
    def test_upload_result_fields_match_data_shapes(self):
        self.assertEqual(list(UploadResult.__dataclass_fields__),
                         ["file_type", "rows_accepted", "rows_rejected",
                          "errors", "stored_path", "validated_only"])

    def test_pipeline_and_stage_result_fields_match_data_shapes(self):
        self.assertEqual(list(PipelineResult.__dataclass_fields__),
                         ["customer_id", "mode", "status", "stages",
                          "timings", "total"])
        self.assertEqual(list(StageResult.__dataclass_fields__),
                         ["name", "status", "detail", "error"])

    def test_error_entries_match_declared_shape(self):
        res = self.ing.upload(self.cid, "kpi_measurements",
                              [{"kpi_code": "X", "value": "y"}],
                              validate_only=True)
        for e in res.errors:
            self.assertEqual(sorted(e), ["column", "message", "row_number"])

    def test_all_three_pipeline_statuses_are_reachable(self):
        seen = set()
        seen.add(self.ing.process_data(
            self.cid, [], stages=[StageSpec("a", lambda c: "ok")]).status)
        seen.add(self.ing.process_data(
            self.cid, [], mode="full_recalc",
            stages=[StageSpec("a", lambda c: "ok"),
                    StageSpec("b", boom)]).status)
        seen.add(self.ing.process_data(
            self.cid, [], mode="full_recalc",
            stages=[StageSpec("a", boom, critical=True)]).status)
        self.assertEqual(seen, {"success", "partial", "failed"})

    def test_all_three_stage_statuses_are_reachable(self):
        r = self.ing.process_data(
            self.cid, [], stages=[StageSpec("a", lambda c: "ok"),
                                  StageSpec("b", lambda c: Skip("feature_disabled")),
                                  StageSpec("c", boom)])
        self.assertEqual({s.status for s in r.stages},
                         {"completed", "skipped", "failed"})

    def test_every_nullable_field_exercised_null_and_non_null(self):
        """Explicit NULL-case sweep over every nullable field in Data Shapes:
        stored_path, StageResult.error, last_ingested_at, and the nullable
        content/note columns."""
        # stored_path
        self.assertIsNone(self.ing.upload(self.cid, "kpi_measurements",
                                          good_kpi_rows(1),
                                          validate_only=True).stored_path)
        self.assertIsNotNone(self.ing.upload(self.cid, "kpi_measurements",
                                             good_kpi_rows(1)).stored_path)
        # StageResult.error
        r = self.ing.process_data(self.cid, [], mode="full_recalc",
                                  stages=[StageSpec("a", lambda c: "ok"),
                                          StageSpec("b", boom)])
        errs = {s.name: s.error for s in r.stages}
        self.assertIsNone(errs["a"])
        self.assertIsNotNone(errs["b"])
        # last_ingested_at
        self.ing.get_or_create_ingestion_state(777)
        self.assertIsNone(self.state(777)["last_ingested_at"])
        self.ing.touch_last_ingested_at(777)
        self.assertIsNotNone(self.state(777)["last_ingested_at"])
        # last_processed_at
        self.assertIsNone(self.state(777)["last_processed_at"])
        self.ing.touch_last_processed_at(777)
        self.assertIsNotNone(self.state(777)["last_processed_at"])


class TestValidateRowUnit(Base):
    """The one Build-Prompt helper that is fully specified — pin its behaviour
    so the report can distinguish 'spec is right' from 'spec is silent'."""

    def test_one_row_can_emit_multiple_errors_for_one_column(self):
        schema = {"c": Rule(required=True, enum={"a", "b"}, cast=int)}
        errs = validate_row({"c": "zzz"}, schema, 1)
        self.assertEqual(len(errs), 2)      # enum AND cast, no `continue`
        self.assertEqual({e["column"] for e in errs}, {"c"})

    def test_required_short_circuits_the_rest(self):
        schema = {"c": Rule(required=True, enum={"a"}, cast=int)}
        self.assertEqual([e["message"] for e in validate_row({}, schema, 1)],
                         ["required"])

    def test_zero_and_false_are_not_treated_as_missing(self):
        schema = {"c": Rule(required=True, cast=float)}
        self.assertEqual(validate_row({"c": 0}, schema, 1), [])
        self.assertEqual(validate_row({"c": False}, schema, 1), [])

    def test_row_numbers_are_one_based(self):
        rows = [{"account_ref": "A", "kpi_code": "P1-KPI1",
                 "measured_at": "2026-01-01", "value": "1"},
                {"account_ref": "A", "kpi_code": "BAD",
                 "measured_at": "2026-01-01", "value": "1"}]
        res = self.ing.upload(self.cid, "kpi_measurements", rows,
                              validate_only=True)
        self.assertEqual(res.errors[0]["row_number"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
