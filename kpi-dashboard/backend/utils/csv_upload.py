"""
Unified CSV Upload — single source of truth for all upload paths.

Every CSV upload in CS Pulse goes through ``_upload_csv_impl()``:
  - MCP ``upload_csv`` tool
  - Flask ``/api/onboarding/upload``
  - Flask V3 ``/api/upload``

All callers convert their input to a raw CSV string and delegate here.
File type resolution, validation, storage routing, and activity logging
are centralized — no duplicate logic across endpoints.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_SCHEMAS_PATH = Path(__file__).resolve().parent.parent / 'config' / 'csv_schemas.json'


# ═══════════════════════════════════════════════════════════════════════
# FileTypeRegistry — built once from csv_schemas.json
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class FileTypeInfo:
    """Metadata for a single CSV file type."""
    canonical_filename: str         # 'kpi_measurements.csv'
    model_category: str             # 'regular_model' | 'context_graph_model'
    storage_subdir: str             # 'data' | 'data/context_graph'
    required_columns: tuple[str, ...]
    optional_columns: tuple[str, ...]
    auto_generated: bool = False
    platform_curated: bool = False


# Alias → canonical filename mapping
# Covers every name used by MCP, Flask onboarding, Flask V3, and load-driver
_ALIASES: dict[str, str] = {
    # Short names (Flask onboarding FILE_TYPES)
    'accounts':                      'accounts.csv',
    'kpis':                          'kpi_measurements.csv',
    'kpi_measurements':              'kpi_measurements.csv',
    'kpi_data':                      'kpi_measurements.csv',
    'enhanced_signals':              'enhanced_qualitative_signals.csv',
    'signals':                       'enhanced_qualitative_signals.csv',
    'qualitative_signals':           'enhanced_qualitative_signals.csv',
    'products':                      'products.csv',
    # Context graph short names (Flask onboarding CONTEXT_GRAPH_FILE_TYPES)
    'stakeholders':                  'stakeholders.csv',
    'engagement_events':             'engagement_events.csv',
    'account_business_profiles':     'account_business_profiles.csv',
    'profiles':                      'account_business_profiles.csv',
    'outcomes':                      'outcomes.csv',
    'decisions':                     'decisions.csv',
    'signal_edges':                  'signal_edges.csv',
    'industry_benchmarks':           'industry_benchmarks.csv',
    # Flask V3 short names
    'customers':                     'accounts.csv',
}

_registry: dict[str, FileTypeInfo] | None = None


def _build_registry() -> dict[str, FileTypeInfo]:
    """Build registry from csv_schemas.json. Keyed by canonical filename."""
    if not _SCHEMAS_PATH.is_file():
        logger.warning("csv_schemas.json not found at %s — using empty registry", _SCHEMAS_PATH)
        return {}

    with open(_SCHEMAS_PATH) as f:
        schemas = json.load(f)

    reg: dict[str, FileTypeInfo] = {}

    # Regular model files → storage_subdir='data'
    for fname, spec in _flatten_model(schemas.get('regular_model', {})).items():
        reg[fname] = FileTypeInfo(
            canonical_filename=fname,
            model_category='regular_model',
            storage_subdir='data',
            required_columns=tuple(spec.get('required_columns', [])),
            optional_columns=tuple(spec.get('optional_columns', [])),
        )

    # Context graph model files → storage_subdir='data/context_graph'
    for fname, spec in _flatten_model(schemas.get('context_graph_model', {})).items():
        reg[fname] = FileTypeInfo(
            canonical_filename=fname,
            model_category='context_graph_model',
            storage_subdir='data/context_graph',
            required_columns=tuple(spec.get('required_columns', [])),
            optional_columns=tuple(spec.get('optional_columns', [])),
            auto_generated=bool(spec.get('auto_generated')),
            platform_curated=bool(spec.get('platform_curated')),
        )

    return reg


def _flatten_model(model: dict) -> dict[str, dict]:
    """Extract {filename: spec} from a model section (flat or nested)."""
    result: dict[str, dict] = {}
    result.update(model.get('files', {}))
    for sub_key in ('customer_provided', 'auto_generated', 'platform_curated'):
        sub = model.get(sub_key, {})
        for k, v in sub.items():
            if k.endswith('.csv') and k not in result:
                result[k] = v
    return result


def get_registry() -> dict[str, FileTypeInfo]:
    """Return the file type registry (built once, cached)."""
    global _registry
    if _registry is None:
        _registry = _build_registry()
    return _registry


def resolve_file_type(file_type: str) -> FileTypeInfo:
    """
    Resolve any file_type string to a FileTypeInfo.

    Accepts: canonical filename ('kpi_measurements.csv'), short name ('kpis'),
    alias ('kpi_data'), or filename without .csv ('kpi_measurements').
    """
    reg = get_registry()

    # Try exact canonical match
    ft = file_type if file_type.endswith('.csv') else f'{file_type}.csv'
    if ft in reg:
        return reg[ft]

    # Try alias
    alias_target = _ALIASES.get(file_type.lower().strip())
    if alias_target and alias_target in reg:
        return reg[alias_target]

    # Try without .csv suffix as alias
    bare = file_type.replace('.csv', '').lower().strip()
    alias_target = _ALIASES.get(bare)
    if alias_target and alias_target in reg:
        return reg[alias_target]

    available = sorted(reg.keys())
    raise ValueError(
        f"Unknown file_type '{file_type}'. "
        f"Available: {available}"
    )


# ═══════════════════════════════════════════════════════════════════════
# UploadResult — structured return value
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class UploadResult:
    """Structured result from _upload_csv_impl."""
    status: str = 'success'             # 'success' | 'validation_error' | 'error'
    customer_id: int = 0
    file_type: str = ''
    canonical_filename: str = ''
    file_path: str = ''                 # disk path (if storage_mode='disk')
    row_count: int = 0
    bytes_written: int = 0
    dry_run: bool = False
    valid: bool = True
    columns_found: list[str] = field(default_factory=list)
    required_columns: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    message: str = ''

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v or isinstance(v, (bool, int))}


# ═══════════════════════════════════════════════════════════════════════
# _upload_csv_impl — the single upload function
# ═══════════════════════════════════════════════════════════════════════

def _upload_csv_impl(
    customer_id: int,
    file_type: str,
    csv_content: str,
    *,
    dry_run: bool = False,
    storage_mode: str = 'disk',
    duplicate_strategy: str = 'skip',
    strict_mode: bool = False,
    strict_validation: bool = True,
    log_activity: bool = False,
) -> UploadResult:
    """
    Canonical CSV upload implementation.

    All upload paths (MCP tool, Flask onboarding, Flask V3) delegate here.

    Args:
        customer_id:        Target customer
        file_type:          Any recognized name (canonical, short, alias)
        csv_content:        Raw CSV string
        dry_run:            Validate only, do not persist
        storage_mode:       'disk' (for process_data pipeline) or 'db_direct' (V3 real-time)
        duplicate_strategy: For db_direct: 'skip', 'update', 'replace', 'error'
        strict_mode:        If True, reject disabled KPIs
        strict_validation:  If True (default), missing required columns → error.
                            If False, missing columns → warning (backward compat for load-driver).
        log_activity:       If True, write ActivityLog entry

    Returns:
        UploadResult with status, validation details, and file path.
    """
    # ── 1. Resolve file type ──
    try:
        info = resolve_file_type(file_type)
    except ValueError as e:
        return UploadResult(
            status='error',
            customer_id=customer_id,
            file_type=file_type,
            valid=False,
            errors=[str(e)],
        )

    # ── 2. Parse CSV and validate structure ──
    try:
        reader = csv.DictReader(io.StringIO(csv_content))
        headers = set(reader.fieldnames or [])
        rows = list(reader)
    except Exception as e:
        return UploadResult(
            status='error',
            customer_id=customer_id,
            file_type=file_type,
            canonical_filename=info.canonical_filename,
            valid=False,
            errors=[f"CSV parse error: {e}"],
        )

    required = set(info.required_columns)
    optional = set(info.optional_columns)
    all_known = required | optional

    missing_required = sorted(required - headers)
    unknown_columns = sorted(headers - all_known)

    errors: list[str] = []
    warnings: list[str] = []

    if missing_required:
        msg = f"Missing required columns: {missing_required}"
        if strict_validation:
            errors.append(msg)
        else:
            warnings.append(f"[non-strict] {msg} — file accepted anyway")
    if unknown_columns:
        warnings.append(f"Unknown columns (will be ignored): {unknown_columns}")
    if len(rows) == 0:
        errors.append("CSV has no data rows.")

    # ── 2b. Layer 1 structural validation (if csv_validator is available) ──
    try:
        from utils.csv_validator import validate_structure
        layer1 = validate_structure(csv_content, info.canonical_filename)
        if layer1 and not layer1.get('valid', True):
            for err in layer1.get('errors', []):
                if err not in errors:
                    errors.append(err)
            for warn in layer1.get('warnings', []):
                if warn not in warnings:
                    warnings.append(warn)
    except ImportError:
        pass  # csv_validator not yet built — fall through to basic validation

    valid = len(errors) == 0

    # ── 3. Dry run → return validation result ──
    if dry_run:
        return UploadResult(
            status='success' if valid else 'validation_error',
            customer_id=customer_id,
            file_type=file_type,
            canonical_filename=info.canonical_filename,
            dry_run=True,
            valid=valid,
            row_count=len(rows),
            columns_found=sorted(headers),
            required_columns=sorted(required),
            missing_required=missing_required,
            errors=errors,
            warnings=warnings,
        )

    if not valid:
        return UploadResult(
            status='validation_error',
            customer_id=customer_id,
            file_type=file_type,
            canonical_filename=info.canonical_filename,
            valid=False,
            row_count=len(rows),
            errors=errors,
            warnings=warnings,
        )

    # ── 4. DB-direct mode (V3 real-time) ──
    if storage_mode == 'db_direct':
        return _upload_db_direct(
            customer_id, info, csv_content, rows, headers,
            duplicate_strategy=duplicate_strategy,
            strict_mode=strict_mode,
            warnings=warnings,
        )

    # ── 5. Disk mode (default — process_data pipeline) ──
    return _upload_to_disk(
        customer_id, info, csv_content, rows,
        strict_mode=strict_mode,
        log_activity=log_activity,
        warnings=warnings,
    )


# ═══════════════════════════════════════════════════════════════════════
# Storage backends
# ═══════════════════════════════════════════════════════════════════════

def _upload_to_disk(
    customer_id: int,
    info: FileTypeInfo,
    csv_content: str,
    rows: list,
    *,
    strict_mode: bool = False,
    log_activity: bool = False,
    warnings: list[str] | None = None,
) -> UploadResult:
    """Write CSV to the customer's data directory on disk."""
    from models import Customer
    from extensions import db

    customer = db.session.get(Customer, int(customer_id))
    if not customer:
        return UploadResult(
            status='error',
            customer_id=customer_id,
            file_type=info.canonical_filename,
            canonical_filename=info.canonical_filename,
            valid=True,
            errors=[f"Customer {customer_id} not found."],
        )

    vertical = getattr(customer, 'vertical', 'dc2_s') or 'dc2_s'
    backend_dir = Path(__file__).resolve().parent.parent
    customer_dir = backend_dir / 'verticals' / f'customer{customer_id}-{vertical}'

    # Route to correct subdirectory
    data_dir = customer_dir / info.storage_subdir
    data_dir.mkdir(parents=True, exist_ok=True)

    file_path = data_dir / info.canonical_filename

    # Append mode: if file exists and has data, append new rows (skip header).
    # This preserves data from previous uploads (e.g., simulation phases,
    # incremental monthly loads) instead of overwriting.
    if file_path.exists() and file_path.stat().st_size > 0:
        lines = csv_content.split('\n')
        # Skip header (first line) and any trailing empty lines
        data_lines = [l for l in lines[1:] if l.strip()]
        if data_lines:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write('\n' + '\n'.join(data_lines) + '\n')
    else:
        file_path.write_text(csv_content, encoding='utf-8')

    byte_count = len(csv_content.encode('utf-8'))

    logger.info(
        "upload_csv: %s → %s (%d rows, %d bytes)",
        info.canonical_filename, file_path, len(rows), byte_count,
    )

    return UploadResult(
        status='success',
        customer_id=customer_id,
        file_type=info.canonical_filename,
        canonical_filename=info.canonical_filename,
        file_path=str(file_path),
        row_count=len(rows),
        bytes_written=byte_count,
        warnings=warnings or [],
        message=(
            f"Uploaded {info.canonical_filename} ({byte_count} bytes, {len(rows)} rows) "
            f"to {info.storage_subdir}/. Use process_data() to ingest into the database."
        ),
    )


def _upload_db_direct(
    customer_id: int,
    info: FileTypeInfo,
    csv_content: str,
    rows: list,
    headers: set,
    *,
    duplicate_strategy: str = 'skip',
    strict_mode: bool = False,
    warnings: list[str] | None = None,
) -> UploadResult:
    """
    Write CSV directly to PostgreSQL (V3 real-time path).

    Delegates to the per-type process functions in upload_api_v3_improved_duplicates.py.
    """
    try:
        from upload_api_v3_improved_duplicates import (
            process_kpi_upload,
            process_signal_upload,
            process_account_upload,
            process_product_upload,
        )
    except ImportError:
        return UploadResult(
            status='error',
            customer_id=customer_id,
            file_type=info.canonical_filename,
            canonical_filename=info.canonical_filename,
            errors=["DB-direct upload module not available."],
        )

    import pandas as pd

    df = pd.read_csv(io.StringIO(csv_content))

    # Map canonical filename to V3 processor
    processors = {
        'kpi_measurements.csv': process_kpi_upload,
        'enhanced_qualitative_signals.csv': process_signal_upload,
        'accounts.csv': process_account_upload,
        'products.csv': process_product_upload,
    }

    processor = processors.get(info.canonical_filename)
    if not processor:
        # Fall back to disk mode for unsupported types
        return _upload_to_disk(
            customer_id, info, csv_content, rows,
            strict_mode=strict_mode,
            warnings=(warnings or []) + [
                f"DB-direct not supported for {info.canonical_filename}; saved to disk instead."
            ],
        )

    try:
        result = processor(df, customer_id, strategy=duplicate_strategy)
        return UploadResult(
            status='success',
            customer_id=customer_id,
            file_type=info.canonical_filename,
            canonical_filename=info.canonical_filename,
            row_count=result.get('rows_processed', len(rows)),
            warnings=warnings or [],
            message=f"DB-direct upload: {result.get('rows_processed', len(rows))} rows processed "
                    f"with strategy '{duplicate_strategy}'.",
        )
    except Exception as e:
        return UploadResult(
            status='error',
            customer_id=customer_id,
            file_type=info.canonical_filename,
            canonical_filename=info.canonical_filename,
            errors=[f"DB-direct upload failed: {e}"],
            warnings=warnings or [],
        )
