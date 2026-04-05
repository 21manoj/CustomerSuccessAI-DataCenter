"""
JSON job status files under Flask instance path (shared Docker volume).

Used by SQS worker + GET /api/jobs/status/<job_id>.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _jobs_dir() -> Path:
    base = os.environ.get("ONBOARDING_PROGRESS_DIR") or os.environ.get("FLASK_INSTANCE_PATH")
    if base:
        p = Path(base) / "async_jobs"
    else:
        p = Path(__file__).resolve().parent.parent / "instance" / "async_jobs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def job_record_path(job_id: str) -> Path:
    return _jobs_dir() / f"{job_id}.json"


def write_job_record(job_id: str, data: Dict[str, Any]) -> None:
    path = job_record_path(job_id)
    try:
        rec = {"job_id": job_id, "updated_at": datetime.utcnow().isoformat(), **data}
        path.write_text(json.dumps(rec, default=str, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning("async job write failed %s: %s", path, e)


def read_job_record(job_id: str) -> Optional[Dict[str, Any]]:
    path = job_record_path(job_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("async job read failed %s: %s", path, e)
        return None


def export_output_path(job_id: str) -> Path:
    """Where async full-account export XLSX is written."""
    p = _jobs_dir() / "export_outputs"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{job_id}.xlsx"
