# Pilot validation artifact — do not treat as a reference implementation

What a fresh agent built from **only**
[`../09-ops-ingestion-pipeline.md`](../09-ops-ingestion-pipeline.md).
72 tests + 16 mutation checks (`mutation_check.py`), all passing.

`ingestion.py` deliberately contains BOTH implementations: `SpecLiteral` (the
original Build Prompt's pseudocode made runnable) and the corrected version,
so the tests can prove each defect rather than assert it. Highest-value ones:
- `test_spec_literal_first_pipeline_run_after_upload_processes_nothing` —
  the severe defect: upload 3 rows, run pipeline, get `status="success"`
  with zero stages executed.
- `test_on_conflict_is_not_expressible_without_the_index_the_spec_omits`
- `test_naive_local_impl_is_wrong_on_utc_minus_7` alongside
  `test_naive_local_impl_looks_fine_on_a_utc_host` — showing exactly why the
  real production bug survived review.
- `test_naive_get_fix_still_duplicates_because_sql_nulls_are_distinct`

See the spec's Validation Note for the full finding list.
