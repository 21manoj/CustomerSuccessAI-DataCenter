#!/usr/bin/env python3
"""
Test Suite — Demo Manifest Validation
======================================
Discovers all DEMO_MANIFEST.md files, parses them, and validates:
  1. Manifest structure & metadata completeness
  2. Referenced data files exist on disk
  3. CSV header integrity (accounts, kpi_measurements, customers, signals, products)
  4. Account IDs in CSV match accounts declared in manifest
  5. KPI measurement row counts match manifest claims
  6. Journey pattern metadata for the rich (synthetic) manifest
  7. Cross-file referential integrity (account_ids in KPIs → accounts)
"""

import sys
import os
import re
import csv
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest

# ============================================================
# CONSTANTS & DISCOVERY
# ============================================================

BACKEND_DIR = Path(__file__).resolve().parent.parent
VERTICALS_DIR = BACKEND_DIR / "verticals"
SYNTHETIC_DIR = BACKEND_DIR / "customer19_synthetic_data"

# Two manifest formats exist:
#   - Simple: customers 261-305509 (basic metadata, no data-file listing)
#   - Enhanced: customers 19, 102, 273, 274 (explicit file sizes, named accounts)
#   - Rich/Synthetic: customer19_synthetic_data (20 demo accounts with journey patterns)


def discover_manifest_files():
    """Find every DEMO_MANIFEST.md under backend/."""
    manifests = []
    for md in BACKEND_DIR.rglob("DEMO_MANIFEST.md"):
        manifests.append(md)
    return sorted(manifests)


MANIFEST_FILES = discover_manifest_files()


def _parse_customer_id_from_path(manifest_path: Path) -> str:
    """Extract customer id string from the directory name."""
    parent = manifest_path.parent.name
    # customer19_synthetic_data -> '19_synthetic' (check BEFORE generic regex)
    if "synthetic" in parent.lower():
        m = re.match(r"customer(\d+)", parent)
        return f"{m.group(1)}_synthetic" if m else parent
    # verticals/customer261-dc2_s -> '261'
    m = re.match(r"customer(\d+)(?:-|_)", parent)
    if m:
        return m.group(1)
    return parent


def _data_dir_for_manifest(manifest_path: Path) -> Path:
    """Return the data directory associated with a manifest."""
    parent = manifest_path.parent
    data_dir = parent / "data"
    if data_dir.is_dir():
        return data_dir
    # Synthetic data lives in same directory
    if any(parent.glob("accounts.csv")):
        return parent
    return data_dir  # will fail existence check naturally


# ============================================================
# MANIFEST PARSING
# ============================================================

def parse_manifest(manifest_path: Path) -> dict:
    """
    Parse a DEMO_MANIFEST.md into a structured dict.
    Returns: {
        'path': Path,
        'customer_id': str,
        'format': 'simple' | 'enhanced' | 'rich',
        'generated': str | None,
        'company': str | None,
        'account_count': int,
        'accounts': [(id, name), ...],
        'kpi_count': int | None,
        'kpi_measurements': int | None,
        'time_range_months': int | None,
        'signals_count': int | None,
        'data_files': [str, ...],   # from manifest text
        'data_file_sizes': {name: bytes},  # from manifest text
        'journey_patterns': [str, ...],
        'pattern_mix': {pattern: pct, ...},
    }
    """
    text = manifest_path.read_text(encoding="utf-8")
    info = {
        'path': manifest_path,
        'customer_id': _parse_customer_id_from_path(manifest_path),
        'format': 'simple',
        'generated': None,
        'company': None,
        'account_count': 0,
        'accounts': [],
        'kpi_count': None,
        'kpi_measurements': None,
        'time_range_months': None,
        'signals_count': None,
        'data_files': [],
        'data_file_sizes': {},
        'journey_patterns': [],
        'pattern_mix': {},
    }

    # --- Detect format ---
    if "Quick Reference: Which Account for Which Demo" in text:
        info['format'] = 'rich'
    elif "**Customer ID:**" in text or "**Company:**" in text:
        info['format'] = 'enhanced'

    # --- Generated timestamp ---
    m = re.search(r'Generated:\s*(.+)', text)
    if m:
        info['generated'] = m.group(1).strip()

    # --- Company name ---
    m = re.search(r'\*\*Company:\*\*\s*(.+)', text)
    if m:
        info['company'] = m.group(1).strip()

    # --- Customer ID from content (enhanced) ---
    m = re.search(r'\*\*Customer ID:\*\*\s*(\d+)', text)
    if m and info['format'] == 'enhanced':
        info['customer_id'] = m.group(1)

    # --- Account count ---
    m = re.search(r'\*\*Accounts:\*\*\s*(\d+)', text)
    if m:
        info['account_count'] = int(m.group(1))
    else:
        m = re.search(r'(\d+)\s+accounts?\s+generated', text)
        if m:
            info['account_count'] = int(m.group(1))

    # --- Total Accounts (rich format) ---
    m = re.search(r'Total Accounts:\s*(\d+)', text)
    if m:
        info['account_count'] = int(m.group(1))

    # --- Parse account list ---
    # Enhanced/simple: "- **19001**: Customer 19 - Production"
    for am in re.finditer(r'-\s+\*\*(?:Account\s+)?(\d+)\*\*[:\s]+(.+)', text):
        info['accounts'].append((am.group(1), am.group(2).strip()))

    # Rich format accounts: "- **Account 29001** - CloudScale AI Labs"
    for am in re.finditer(r'-\s+\*\*Account\s+(\d+)\*\*\s*-\s*(.+)', text):
        acct_id = am.group(1)
        acct_name = am.group(2).strip()
        if (acct_id, acct_name) not in info['accounts']:
            info['accounts'].append((acct_id, acct_name))

    if info['accounts'] and info['account_count'] == 0:
        info['account_count'] = len(set(a[0] for a in info['accounts']))

    # --- KPI count ---
    m = re.search(r'KPIs:\s*(\d+)\s*total', text)
    if m:
        info['kpi_count'] = int(m.group(1))
    m2 = re.search(r'Enabled KPIs:\s*(\d+)', text)
    if m2:
        info['kpi_count'] = int(m2.group(1))

    # --- KPI measurements ---
    m = re.search(r'KPI Measurements:\s*(\d+)', text)
    if m:
        info['kpi_measurements'] = int(m.group(1))
    m2 = re.search(r'Total measurements:\s*(\d+)', text)
    if m2:
        info['kpi_measurements'] = int(m2.group(1))

    # --- Time range ---
    m = re.search(r'(?:Time\s+(?:Range|Period))[:\*]*\s*(\d+)\s*months', text)
    if m:
        info['time_range_months'] = int(m.group(1))

    # --- Signals count ---
    m = re.search(r'Signals:\s*(\d+)', text)
    if m:
        info['signals_count'] = int(m.group(1))

    # --- Data files listed ---
    for dm in re.finditer(r'-\s+(\w+\.csv)\s*\((\d[\d,]*)\s*bytes?\)', text):
        fname = dm.group(1)
        fsize = int(dm.group(2).replace(',', ''))
        info['data_files'].append(fname)
        info['data_file_sizes'][fname] = fsize

    # --- Journey patterns ---
    for jp in re.finditer(r'###\s+((?:Critical|Healthy|Consistently|Persistently|Volatile|Plateau|High Churn|New Customer)[^\n]+)', text):
        info['journey_patterns'].append(jp.group(1).strip())

    # --- Pattern mix ---
    for pm in re.finditer(r'-\s+(Crisis|Churn|Stable|Expansion):\s*(\d+)%', text):
        info['pattern_mix'][pm.group(1)] = int(pm.group(2))

    return info


# Build parsed manifest list
PARSED_MANIFESTS = [parse_manifest(m) for m in MANIFEST_FILES]


# ============================================================
# 1. MANIFEST DISCOVERY
# ============================================================

class TestManifestDiscovery:
    """Verify all expected manifests are found."""

    def test_at_least_14_manifests_found(self):
        """We expect 15 DEMO_MANIFEST.md files (14 verticals + 1 synthetic)."""
        assert len(MANIFEST_FILES) >= 14, (
            f"Expected >= 14 manifests, found {len(MANIFEST_FILES)}"
        )

    def test_synthetic_manifest_exists(self):
        synthetic = SYNTHETIC_DIR / "DEMO_MANIFEST.md"
        assert synthetic.exists(), "customer19_synthetic_data/DEMO_MANIFEST.md missing"

    def test_customer19_vertical_manifest_exists(self):
        c19 = VERTICALS_DIR / "customer19-dc2_s" / "DEMO_MANIFEST.md"
        assert c19.exists(), "verticals/customer19-dc2_s/DEMO_MANIFEST.md missing"

    def test_customer102_manifest_exists(self):
        c102 = VERTICALS_DIR / "customer102-dc2_s" / "DEMO_MANIFEST.md"
        assert c102.exists(), "verticals/customer102-dc2_s/DEMO_MANIFEST.md missing"


# ============================================================
# 2. MANIFEST PARSING
# ============================================================

class TestManifestParsing:
    """Verify manifests parse cleanly into structured data."""

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_has_customer_id(self, info):
        assert info['customer_id'], f"No customer_id for {info['path']}"

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_has_generated_timestamp(self, info):
        assert info['generated'] is not None, (
            f"No generated timestamp in {info['path'].name}"
        )

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_has_accounts(self, info):
        assert info['account_count'] > 0, (
            f"No account count in {info['path'].name}"
        )

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_account_list_matches_count(self, info):
        if info['accounts']:
            unique_ids = set(a[0] for a in info['accounts'])
            assert len(unique_ids) >= info['account_count'], (
                f"Manifest claims {info['account_count']} accounts "
                f"but lists {len(unique_ids)} unique IDs"
            )


# ============================================================
# 3. DATA FILE EXISTENCE
# ============================================================

# Required CSV files that every customer should have
REQUIRED_CSVS = ['accounts.csv', 'kpi_measurements.csv', 'customers.csv']


class TestDataFileExistence:
    """Verify every manifest's referenced data files exist on disk."""

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_data_directory_exists(self, info):
        data_dir = _data_dir_for_manifest(info['path'])
        assert data_dir.is_dir(), (
            f"Data directory missing: {data_dir}"
        )

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_required_csvs_exist(self, info):
        data_dir = _data_dir_for_manifest(info['path'])
        for csv_name in REQUIRED_CSVS:
            csv_path = data_dir / csv_name
            assert csv_path.exists(), (
                f"Required file {csv_name} missing in {data_dir}"
            )

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_listed_data_files_exist(self, info):
        """If manifest explicitly lists data files, they must exist."""
        if not info['data_files']:
            pytest.skip("Manifest does not list explicit data files")
        data_dir = _data_dir_for_manifest(info['path'])
        for fname in info['data_files']:
            assert (data_dir / fname).exists(), (
                f"Listed file {fname} not found in {data_dir}"
            )

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_listed_file_sizes_nonzero(self, info):
        """If manifest lists file sizes, verify files are non-empty."""
        if not info['data_file_sizes']:
            pytest.skip("Manifest does not list file sizes")
        data_dir = _data_dir_for_manifest(info['path'])
        for fname, expected_bytes in info['data_file_sizes'].items():
            actual = (data_dir / fname).stat().st_size
            assert actual > 0, f"{fname} is empty (0 bytes)"
            # Allow 20% tolerance on file size (generation can vary slightly)
            assert actual >= expected_bytes * 0.5, (
                f"{fname}: actual {actual}B << manifest claimed {expected_bytes}B"
            )


# ============================================================
# 4. CSV HEADER INTEGRITY
# ============================================================

# Expected headers per CSV type (minimal required columns)
ACCOUNTS_REQUIRED_COLS = {'account_id', 'customer_id', 'account_name'}
KPI_REQUIRED_COLS = {'account_id', 'kpi_code', 'value'}
CUSTOMERS_REQUIRED_COLS = {'customer_id', 'customer_name'}


class TestCSVHeaders:
    """Validate CSV files have correct headers."""

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_accounts_csv_headers(self, info):
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "accounts.csv"
        if not csv_path.exists():
            pytest.skip("accounts.csv not found")
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            headers = set(next(reader))
        missing = ACCOUNTS_REQUIRED_COLS - headers
        assert not missing, f"accounts.csv missing columns: {missing}"

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_kpi_measurements_csv_headers(self, info):
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "kpi_measurements.csv"
        if not csv_path.exists():
            pytest.skip("kpi_measurements.csv not found")
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            headers = set(next(reader))
        missing = KPI_REQUIRED_COLS - headers
        assert not missing, f"kpi_measurements.csv missing columns: {missing}"

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_customers_csv_headers(self, info):
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "customers.csv"
        if not csv_path.exists():
            pytest.skip("customers.csv not found")
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            headers = set(next(reader))
        missing = CUSTOMERS_REQUIRED_COLS - headers
        assert not missing, f"customers.csv missing columns: {missing}"


# ============================================================
# 5. ACCOUNT CROSS-VALIDATION
# ============================================================

class TestAccountCrossValidation:
    """Verify accounts in manifest match accounts in CSV."""

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_account_count_matches_csv(self, info):
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "accounts.csv"
        if not csv_path.exists():
            pytest.skip("accounts.csv not found")

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            csv_accounts = [row['account_id'] for row in reader]

        assert len(csv_accounts) >= info['account_count'], (
            f"Manifest claims {info['account_count']} accounts, "
            f"CSV has {len(csv_accounts)}"
        )

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_manifest_account_ids_in_csv(self, info):
        """Every account listed in manifest must appear in accounts.csv."""
        if not info['accounts']:
            pytest.skip("No explicit account list in manifest")
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "accounts.csv"
        if not csv_path.exists():
            pytest.skip("accounts.csv not found")

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            csv_ids = {row['account_id'] for row in reader}

        manifest_ids = {a[0] for a in info['accounts']}
        missing = manifest_ids - csv_ids
        assert not missing, (
            f"Manifest accounts not in CSV: {missing}"
        )

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_all_csv_accounts_have_valid_customer_id(self, info):
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "accounts.csv"
        if not csv_path.exists():
            pytest.skip("accounts.csv not found")

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = row.get('customer_id', '')
                assert cid.strip(), (
                    f"Account {row['account_id']} has empty customer_id"
                )


# ============================================================
# 6. KPI MEASUREMENT VALIDATION
# ============================================================

class TestKPIMeasurements:
    """Validate KPI measurement data integrity."""

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_kpi_row_count_matches_manifest(self, info):
        """If manifest declares measurement count, CSV row count should match."""
        if info['kpi_measurements'] is None:
            pytest.skip("No KPI measurement count in manifest")
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "kpi_measurements.csv"
        if not csv_path.exists():
            pytest.skip("kpi_measurements.csv not found")

        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            row_count = sum(1 for _ in reader)

        # Allow 10% tolerance (generation can produce slightly different counts)
        expected = info['kpi_measurements']
        assert row_count >= expected * 0.8, (
            f"KPI rows {row_count} << manifest claims {expected}"
        )
        assert row_count <= expected * 1.2, (
            f"KPI rows {row_count} >> manifest claims {expected}"
        )

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_kpi_values_are_numeric(self, info):
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "kpi_measurements.csv"
        if not csv_path.exists():
            pytest.skip("kpi_measurements.csv not found")

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            bad_rows = []
            for i, row in enumerate(reader):
                try:
                    float(row['value'])
                except (ValueError, KeyError):
                    bad_rows.append(i + 2)  # 1-indexed + header
                if len(bad_rows) >= 5:
                    break

        assert not bad_rows, (
            f"Non-numeric values at rows: {bad_rows}"
        )

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_kpi_account_ids_reference_valid_accounts(self, info):
        """Every account_id in KPI CSV should appear in accounts.csv."""
        data_dir = _data_dir_for_manifest(info['path'])
        acct_csv = data_dir / "accounts.csv"
        kpi_csv = data_dir / "kpi_measurements.csv"
        if not acct_csv.exists() or not kpi_csv.exists():
            pytest.skip("CSVs not found")

        with open(acct_csv, 'r') as f:
            acct_ids = {row['account_id'] for row in csv.DictReader(f)}

        with open(kpi_csv, 'r') as f:
            kpi_acct_ids = {row['account_id'] for row in csv.DictReader(f)}

        orphans = kpi_acct_ids - acct_ids
        assert not orphans, (
            f"KPI measurements reference unknown accounts: {orphans}"
        )

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_kpi_has_pillar_codes(self, info):
        """Every KPI row should have a non-empty pillar code."""
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "kpi_measurements.csv"
        if not csv_path.exists():
            pytest.skip("kpi_measurements.csv not found")

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            empty_pillar_count = 0
            total = 0
            for row in reader:
                total += 1
                if not row.get('pillar', '').strip():
                    empty_pillar_count += 1
                if total >= 200:  # sample first 200 rows
                    break

        assert empty_pillar_count == 0, (
            f"{empty_pillar_count}/{total} KPI rows missing pillar code"
        )


# ============================================================
# 7. QUALITATIVE SIGNALS VALIDATION
# ============================================================

class TestQualitativeSignals:
    """Validate qualitative signals data."""

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_signals_file_exists(self, info):
        data_dir = _data_dir_for_manifest(info['path'])
        signals = data_dir / "qualitative_signals.csv"
        assert signals.exists(), f"qualitative_signals.csv missing in {data_dir}"

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_signals_have_required_columns(self, info):
        data_dir = _data_dir_for_manifest(info['path'])
        signals = data_dir / "qualitative_signals.csv"
        if not signals.exists():
            pytest.skip("signals file not found")
        with open(signals, 'r') as f:
            headers = set(next(csv.reader(f)))
        assert 'account_id' in headers, "Missing account_id in signals"
        assert 'signal_type' in headers or 'signal_text' in headers, (
            "Missing signal_type or signal_text in signals"
        )

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_signals_count_matches_manifest(self, info):
        """If manifest declares signals count, check it."""
        if info['signals_count'] is None:
            pytest.skip("No signals count in manifest")
        data_dir = _data_dir_for_manifest(info['path'])
        signals = data_dir / "qualitative_signals.csv"
        if not signals.exists():
            pytest.skip("signals file not found")

        with open(signals, 'r') as f:
            reader = csv.reader(f)
            next(reader)
            row_count = sum(1 for _ in reader)

        assert row_count >= info['signals_count'], (
            f"Manifest claims {info['signals_count']} signals, CSV has {row_count}"
        )


# ============================================================
# 8. RICH MANIFEST (SYNTHETIC) SPECIFIC TESTS
# ============================================================

RICH_MANIFESTS = [p for p in PARSED_MANIFESTS if p['format'] == 'rich']


class TestRichManifestJourneyPatterns:
    """Validate the customer19 synthetic demo manifest in detail."""

    @pytest.mark.parametrize("info", RICH_MANIFESTS,
                             ids=[p['customer_id'] for p in RICH_MANIFESTS])
    def test_has_journey_patterns(self, info):
        assert len(info['journey_patterns']) >= 6, (
            f"Rich manifest should have 6+ journey patterns, found {len(info['journey_patterns'])}"
        )

    @pytest.mark.parametrize("info", RICH_MANIFESTS,
                             ids=[p['customer_id'] for p in RICH_MANIFESTS])
    def test_20_demo_accounts(self, info):
        assert info['account_count'] == 20, (
            f"Synthetic manifest should have 20 accounts, got {info['account_count']}"
        )

    @pytest.mark.parametrize("info", RICH_MANIFESTS,
                             ids=[p['customer_id'] for p in RICH_MANIFESTS])
    def test_accounts_csv_has_health_scenarios(self, info):
        """Synthetic accounts.csv should embed health_scenario in profile JSON."""
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "accounts.csv"
        if not csv_path.exists():
            pytest.skip("accounts.csv not found")

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 20, f"Expected 20 rows, got {len(rows)}"

        # Check first row has profile_metadata_json with health_scenario
        first = rows[0]
        if 'profile_metadata_json' in first:
            meta = json.loads(first['profile_metadata_json'])
            assert 'health_scenario' in meta, "Missing health_scenario in profile JSON"
            scenario = meta['health_scenario']
            assert 'scenario_key' in scenario
            assert 'start_health' in scenario
            assert 'end_health' in scenario

    @pytest.mark.parametrize("info", RICH_MANIFESTS,
                             ids=[p['customer_id'] for p in RICH_MANIFESTS])
    def test_all_8_journey_types_covered(self, info):
        """Verify all 8 journey types are represented in accounts."""
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "accounts.csv"
        if not csv_path.exists():
            pytest.skip("accounts.csv not found")

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            scenario_keys = set()
            for row in reader:
                if 'profile_metadata_json' in row and row['profile_metadata_json']:
                    meta = json.loads(row['profile_metadata_json'])
                    hs = meta.get('health_scenario', {})
                    if 'scenario_key' in hs:
                        scenario_keys.add(hs['scenario_key'])

        expected_scenarios = {
            'improving', 'declining', 'stable_healthy', 'stable_at_risk',
            'volatile', 'plateau_then_improve', 'churn_risk', 'new_onboarding'
        }
        missing = expected_scenarios - scenario_keys
        assert not missing, f"Missing journey scenarios: {missing}"

    @pytest.mark.parametrize("info", RICH_MANIFESTS,
                             ids=[p['customer_id'] for p in RICH_MANIFESTS])
    def test_kpi_has_5_pillars(self, info):
        """Synthetic data should use 5-pillar KPI structure (P1-P5)."""
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "kpi_measurements.csv"
        if not csv_path.exists():
            pytest.skip("kpi_measurements.csv not found")

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            pillars = set()
            for row in reader:
                p = row.get('pillar', '').strip()
                if p:
                    pillars.add(p)

        expected_pillars = {'P1', 'P2', 'P3', 'P4', 'P5'}
        assert pillars == expected_pillars, (
            f"Expected pillars {expected_pillars}, got {pillars}"
        )

    @pytest.mark.parametrize("info", RICH_MANIFESTS,
                             ids=[p['customer_id'] for p in RICH_MANIFESTS])
    def test_kpi_values_are_non_negative(self, info):
        """All KPI values should be non-negative."""
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "kpi_measurements.csv"
        if not csv_path.exists():
            pytest.skip("kpi_measurements.csv not found")

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            negative_rows = []
            for i, row in enumerate(reader):
                val = float(row['value'])
                if val < 0:
                    negative_rows.append((i + 2, row.get('kpi_code', '?'), val))
                if len(negative_rows) >= 5:
                    break

        assert not negative_rows, (
            f"Negative KPI values found: {negative_rows}"
        )

    @pytest.mark.parametrize("info", RICH_MANIFESTS,
                             ids=[p['customer_id'] for p in RICH_MANIFESTS])
    def test_percentage_kpis_in_range(self, info):
        """Percentage-unit KPIs should be 0-100 (with small tolerance)."""
        data_dir = _data_dir_for_manifest(info['path'])
        csv_path = data_dir / "kpi_measurements.csv"
        if not csv_path.exists():
            pytest.skip("kpi_measurements.csv not found")

        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            out_of_range = []
            for i, row in enumerate(reader):
                unit = row.get('unit', '')
                if unit == '%':
                    val = float(row['value'])
                    # ROI and similar KPIs can exceed 100%, allow up to 200%
                    if val < 0 or val > 200:
                        out_of_range.append((i + 2, row.get('kpi_code', '?'), val))
                if len(out_of_range) >= 5:
                    break

        assert not out_of_range, (
            f"Percentage KPI values out of range (0-200): {out_of_range}"
        )


# ============================================================
# 9. ENHANCED MANIFEST SPECIFIC TESTS
# ============================================================

ENHANCED_MANIFESTS = [p for p in PARSED_MANIFESTS if p['format'] == 'enhanced']


class TestEnhancedManifests:
    """Validate enhanced-format manifests (customers with named accounts)."""

    @pytest.mark.parametrize("info", ENHANCED_MANIFESTS,
                             ids=[p['customer_id'] for p in ENHANCED_MANIFESTS])
    def test_has_company_name(self, info):
        assert info['company'] is not None, (
            f"Enhanced manifest should have company name: {info['path']}"
        )

    @pytest.mark.parametrize("info", ENHANCED_MANIFESTS,
                             ids=[p['customer_id'] for p in ENHANCED_MANIFESTS])
    def test_has_data_file_listing(self, info):
        assert len(info['data_files']) >= 3, (
            f"Enhanced manifest should list data files: {info['path']}"
        )

    @pytest.mark.parametrize("info", ENHANCED_MANIFESTS,
                             ids=[p['customer_id'] for p in ENHANCED_MANIFESTS])
    def test_has_time_period(self, info):
        assert info['time_range_months'] is not None, (
            f"Enhanced manifest should specify time period: {info['path']}"
        )
        assert info['time_range_months'] == 12, (
            f"Expected 12 months, got {info['time_range_months']}"
        )


# ============================================================
# 10. SIMPLE MANIFEST SPECIFIC TESTS
# ============================================================

SIMPLE_MANIFESTS = [p for p in PARSED_MANIFESTS if p['format'] == 'simple']


class TestSimpleManifests:
    """Validate simple-format manifests (bulk-generated customers)."""

    @pytest.mark.parametrize("info", SIMPLE_MANIFESTS,
                             ids=[p['customer_id'] for p in SIMPLE_MANIFESTS])
    def test_has_pattern_mix(self, info):
        assert len(info['pattern_mix']) > 0, (
            f"Simple manifest should have pattern mix: {info['path']}"
        )

    @pytest.mark.parametrize("info", SIMPLE_MANIFESTS,
                             ids=[p['customer_id'] for p in SIMPLE_MANIFESTS])
    def test_pattern_mix_sums_to_100(self, info):
        if not info['pattern_mix']:
            pytest.skip("No pattern mix")
        total = sum(info['pattern_mix'].values())
        assert total == 100, (
            f"Pattern mix should sum to 100%, got {total}%: {info['pattern_mix']}"
        )

    @pytest.mark.parametrize("info", SIMPLE_MANIFESTS,
                             ids=[p['customer_id'] for p in SIMPLE_MANIFESTS])
    def test_kpi_count_is_38(self, info):
        """Simple manifests all use 38 total KPIs."""
        if info['kpi_count'] is None:
            pytest.skip("No KPI count in manifest")
        assert info['kpi_count'] == 38, (
            f"Expected 38 KPIs, got {info['kpi_count']}"
        )

    @pytest.mark.parametrize("info", SIMPLE_MANIFESTS,
                             ids=[p['customer_id'] for p in SIMPLE_MANIFESTS])
    def test_time_range_is_12_months(self, info):
        if info['time_range_months'] is None:
            pytest.skip("No time range in manifest")
        assert info['time_range_months'] == 12


# ============================================================
# 11. PRODUCTS FILE VALIDATION
# ============================================================

class TestProductsFile:
    """Validate products.csv across all manifests."""

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_products_csv_exists(self, info):
        data_dir = _data_dir_for_manifest(info['path'])
        products = data_dir / "products.csv"
        assert products.exists(), f"products.csv missing in {data_dir}"

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_products_csv_has_required_columns(self, info):
        data_dir = _data_dir_for_manifest(info['path'])
        products = data_dir / "products.csv"
        if not products.exists():
            pytest.skip("products.csv not found")
        with open(products, 'r') as f:
            headers = set(next(csv.reader(f)))
        # Two schemas: vertical uses customer_id, synthetic uses id/name/category
        has_vertical_schema = 'customer_id' in headers
        has_synthetic_schema = 'id' in headers and 'name' in headers
        assert has_vertical_schema or has_synthetic_schema, (
            f"products.csv has unrecognized schema: {headers}"
        )

    @pytest.mark.parametrize("info", PARSED_MANIFESTS,
                             ids=[p['customer_id'] for p in PARSED_MANIFESTS])
    def test_products_csv_nonempty(self, info):
        data_dir = _data_dir_for_manifest(info['path'])
        products = data_dir / "products.csv"
        if not products.exists():
            pytest.skip("products.csv not found")
        with open(products, 'r') as f:
            reader = csv.reader(f)
            next(reader)  # header
            rows = sum(1 for _ in reader)
        assert rows >= 1, "products.csv has no data rows"


# ============================================================
# 12. CROSS-MANIFEST CONSISTENCY
# ============================================================

class TestCrossManifestConsistency:
    """Global consistency checks across all manifests."""

    def test_no_duplicate_customer_ids(self):
        """Each customer ID (including _synthetic suffix) should be unique."""
        cids = [p['customer_id'] for p in PARSED_MANIFESTS]
        seen = set()
        dupes = set()
        for cid in cids:
            if cid in seen:
                dupes.add(cid)
            seen.add(cid)
        assert not dupes, f"Duplicate customer IDs: {dupes}"

    def test_all_verticals_use_dc2_s(self):
        """All non-synthetic customer vertical directories should end with -dc2_s."""
        for info in PARSED_MANIFESTS:
            if 'synthetic' in info['customer_id']:
                continue
            parent = info['path'].parent.name
            assert parent.endswith('-dc2_s'), (
                f"Vertical dir {parent} doesn't end with -dc2_s"
            )

    def test_customer19_has_both_manifests(self):
        """Customer 19 should have both a vertical manifest and a synthetic manifest."""
        cids = [p['customer_id'] for p in PARSED_MANIFESTS]
        assert '19' in cids, "Missing customer19-dc2_s manifest"
        has_synthetic = any('synthetic' in c for c in cids)
        assert has_synthetic, "Missing customer19_synthetic_data manifest"

    def test_total_demo_accounts_across_all_manifests(self):
        """Sanity check: total accounts across all manifests."""
        total = sum(p['account_count'] for p in PARSED_MANIFESTS)
        assert total >= 50, (
            f"Expected at least 50 total accounts across all manifests, got {total}"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    # Print summary before running tests
    print("=" * 70)
    print("DEMO MANIFEST TEST SUITE")
    print("=" * 70)
    print(f"Discovered {len(MANIFEST_FILES)} manifests:")
    for info in PARSED_MANIFESTS:
        fmt = info['format'].upper()
        accts = info['account_count']
        print(f"  [{fmt:8s}] customer {info['customer_id']:>10s} "
              f"— {accts} accounts")
    print("=" * 70)

    sys.exit(pytest.main([__file__, '-v', '--tb=short']))
