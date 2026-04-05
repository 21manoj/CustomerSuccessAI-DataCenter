"""
Persist onboarding process-data progress to the Flask instance directory.

Used when SQS worker runs in a separate container: Gunicorn workers and the
worker share the same `instance` Docker volume so GET /api/onboarding/status/*
can read progress written by the worker.

Also written from the in-process thread path so status polls hit any worker.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _instance_dir() -> Path:
    env = os.environ.get("ONBOARDING_PROGRESS_DIR") or os.environ.get("FLASK_INSTANCE_PATH")
    if env:
        p = Path(env)
    else:
        p = Path(__file__).resolve().parent.parent / "instance"
    p.mkdir(parents=True, exist_ok=True)
    return p


def progress_path(customer_id: int) -> Path:
    return _instance_dir() / f"onboarding_progress_{int(customer_id)}.json"


def write_progress(customer_id: int, data: Dict[str, Any]) -> None:
    path = progress_path(customer_id)
    try:
        path.write_text(json.dumps(data, default=str, indent=2), encoding="utf-8")
    except OSError as e:
        logger.warning("Could not write onboarding progress file %s: %s", path, e)


def read_progress(customer_id: int) -> Optional[Dict[str, Any]]:
    path = progress_path(customer_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Could not read onboarding progress file %s: %s", path, e)
        return None


def delete_progress(customer_id: int) -> None:
    path = progress_path(customer_id)
    try:
        if path.is_file():
            path.unlink()
    except OSError as e:
        logger.warning("Could not delete onboarding progress file %s: %s", path, e)
