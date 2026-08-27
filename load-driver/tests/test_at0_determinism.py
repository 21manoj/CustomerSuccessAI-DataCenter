"""AT-0 — the safety property (fix-load-generator-prompt-v2.md).

"This converts 'refactoring the thing that provisions all our demos' from a
risky change into a bounded one." Establish BEFORE the Track D rewrite
touches anything, and run after every commit — not just at the end.

--profile demo (today: the generator's only mode, unflagged) must reproduce
these archived golden CSVs byte-for-byte, for every representative manifest,
except the one intentionally non-deterministic field: account_details.csv's
`uuid` column, generated via uuid.uuid4() by design (a real per-account
identity token, not a data-generation artifact) and excluded from the
comparison on that basis alone — every other column, in every other file,
must match exactly.

Golden files were captured 2026-08-25 AFTER fixing a real non-determinism bug
in _generate_kpi_series (bare random.gauss() on the global stream + a
PYTHONHASHSEED-salted hash(kpi_code) — see commit 951d9f380). Before that fix,
this test would have failed on cascade_predictive_11_saas alone.
"""
import csv
import io
import subprocess
import sys
from pathlib import Path

LOAD_DRIVER = Path(__file__).resolve().parent.parent
GOLDEN_ROOT = LOAD_DRIVER / 'tests' / 'golden'

# 3 representative manifests: spans all 3 verticals with data today, and a
# spread of KPI counts / account counts (11 KPIs x 6 accts, 20 KPIs x 18
# accts, 38 KPIs x 12 accts) so a regression narrow to one shape can't hide.
MANIFESTS = [
    'novagrid_datacenter_v1',
    'cascade_predictive_11_saas',
    'novastar_dc2s',
]

# Column excluded from the byte-identical claim, and why. Extend this dict,
# never silently loosen a whole-file comparison, if a future column needs the
# same treatment — each entry must name a real, deliberate source of
# randomness (not a bug being swept under the rug).
EXCLUDED_COLUMNS = {
    'account_details.csv': {'uuid'},
}


def _generate(manifest_name: str, out_dir: Path) -> None:
    result = subprocess.run(
        [
            sys.executable, str(LOAD_DRIVER / 'cs_pulse_driver.py'),
            '--manifest', str(LOAD_DRIVER / 'manifests' / f'{manifest_name}.json'),
            '--generate-only', str(out_dir),
        ],
        cwd=str(LOAD_DRIVER),
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, (
        f"generator failed for {manifest_name}:\n{result.stdout}\n{result.stderr}"
    )


def _read_csv_rows(path: Path, drop_columns: set) -> list:
    with open(path, newline='') as f:
        rows = list(csv.reader(f))
    if not drop_columns or not rows:
        return rows
    header = rows[0]
    keep_idx = [i for i, col in enumerate(header) if col not in drop_columns]
    return [[row[i] for i in keep_idx] for row in rows]


def _diff_first(golden_rows: list, actual_rows: list) -> str:
    for i, (g, a) in enumerate(zip(golden_rows, actual_rows)):
        if g != a:
            return f"row {i} differs:\n  golden: {g}\n  actual: {a}"
    if len(golden_rows) != len(actual_rows):
        return f"row count differs: golden={len(golden_rows)} actual={len(actual_rows)}"
    return "unknown (should not happen)"


class TestAT0Determinism:
    """--profile demo (today's unflagged default) reproduces the archived
    goldens byte-for-byte, column-for-column, except EXCLUDED_COLUMNS."""

    def _check_manifest(self, manifest_name: str, tmp_path: Path):
        golden_dir = GOLDEN_ROOT / manifest_name
        assert golden_dir.is_dir(), f"no golden fixtures archived for {manifest_name}"

        out_dir = tmp_path / manifest_name
        _generate(manifest_name, out_dir)

        golden_files = sorted(p.name for p in golden_dir.glob('*.csv'))
        assert golden_files, f"golden dir {golden_dir} has no CSVs"

        for fname in golden_files:
            golden_path = golden_dir / fname
            actual_path = out_dir / fname
            assert actual_path.exists(), (
                f"{manifest_name}/{fname}: generator did not emit this file "
                f"(golden fixture exists, output is missing it — output contract changed)"
            )

            drop = EXCLUDED_COLUMNS.get(fname, set())
            golden_rows = _read_csv_rows(golden_path, drop)
            actual_rows = _read_csv_rows(actual_path, drop)

            assert golden_rows == actual_rows, (
                f"{manifest_name}/{fname} is not byte-identical to its golden "
                f"(after excluding {drop or 'no columns'}):\n"
                f"{_diff_first(golden_rows, actual_rows)}"
            )

    def test_novagrid_datacenter_v1(self, tmp_path):
        self._check_manifest('novagrid_datacenter_v1', tmp_path)

    def test_cascade_predictive_11_saas(self, tmp_path):
        self._check_manifest('cascade_predictive_11_saas', tmp_path)

    def test_novastar_dc2s(self, tmp_path):
        self._check_manifest('novastar_dc2s', tmp_path)


class TestAT0ExcludedColumnIsGenuinelyRandom:
    """Guard against EXCLUDED_COLUMNS being used to hide a real bug: the
    excluded uuid column must actually DIFFER across two runs (proving it's
    live randomness, not a frozen/constant value someone excluded out of
    laziness), while every other column in the same file stays identical."""

    def test_uuid_column_varies_but_nothing_else_does(self, tmp_path):
        manifest_name = 'novagrid_datacenter_v1'
        out_a = tmp_path / 'a'
        out_b = tmp_path / 'b'
        _generate(manifest_name, out_a)
        _generate(manifest_name, out_b)

        with open(out_a / 'account_details.csv', newline='') as f:
            rows_a = list(csv.reader(f))
        with open(out_b / 'account_details.csv', newline='') as f:
            rows_b = list(csv.reader(f))

        header = rows_a[0]
        uuid_idx = header.index('uuid')
        assert any(
            a[uuid_idx] != b[uuid_idx]
            for a, b in zip(rows_a[1:], rows_b[1:])
        ), "uuid column never varied across 2 runs — EXCLUDED_COLUMNS entry may be masking a bug, not real randomness"

        # every OTHER column must still match
        rows_a_no_uuid = [[v for i, v in enumerate(r) if i != uuid_idx] for r in rows_a]
        rows_b_no_uuid = [[v for i, v in enumerate(r) if i != uuid_idx] for r in rows_b]
        assert rows_a_no_uuid == rows_b_no_uuid


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
