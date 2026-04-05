#!/usr/bin/env python3
"""
Long-poll SQS for long-running customer jobs (same queue as platform enqueue).

Job types (JSON body must include "job"):
  - process_data          — { "job", "customer_id" }
  - rehydrate_import      — { "job", "customer_id", "job_id", "staging_relpath", "original_filename"?, "user_id"? }
  - export_all_account_data — { "job", "customer_id", "job_id" }

Environment (required):
  ONBOARDING_SQS_URL or AWS_SQS_ONBOARDING_QUEUE_URL — full queue URL

Optional:
  AWS_REGION / AWS_DEFAULT_REGION (default us-east-1)
  ONBOARDING_PROGRESS_DIR / FLASK_INSTANCE_PATH — shared instance volume
  ONBOARDING_SQS_WAIT_SECONDS (default 20)
  ONBOARDING_SQS_VISIBILITY_TIMEOUT (default 900)
  ONBOARDING_WORKER_ONCE — process one message then exit

IAM: sqs:ReceiveMessage, sqs:DeleteMessage on the queue.

Run (inside image, not docker-entrypoint):
  python3 /app/backend/scripts/sqs_onboarding_worker.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("sqs_customer_jobs_worker")


def _queue_url() -> str:
    u = (
        os.environ.get("ONBOARDING_SQS_URL")
        or os.environ.get("AWS_SQS_ONBOARDING_QUEUE_URL")
        or ""
    ).strip()
    if not u:
        log.error("Set ONBOARDING_SQS_URL or AWS_SQS_ONBOARDING_QUEUE_URL")
        sys.exit(1)
    return u


def _receive_one(client, queue_url: str, wait_seconds: int):
    resp = client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=min(20, max(0, wait_seconds)),
        VisibilityTimeout=int(os.environ.get("ONBOARDING_SQS_VISIBILITY_TIMEOUT", "900")),
        AttributeNames=["ApproximateReceiveCount"],
    )
    msgs = resp.get("Messages") or []
    return msgs[0] if msgs else None


def _do_process_data(app, data: dict) -> None:
    from datetime import datetime as _dt

    from mcp_server.cs_pulse_onboarding import _process_data_impl
    from utils.onboarding_progress_file import write_progress

    customer_id = int(data["customer_id"])
    log.info("SQS job=process_data customer_id=%s", customer_id)

    write_progress(
        customer_id,
        {
            "in_progress": True,
            "started_at": _dt.utcnow().isoformat(),
            "current_step": "worker_starting",
            "steps_completed": [],
            "result": None,
            "error": None,
            "source": "sqs_worker",
        },
    )

    with app.app_context():
        try:
            result = _process_data_impl(customer_id)
            write_progress(
                customer_id,
                {
                    "in_progress": False,
                    "completed_at": _dt.utcnow().isoformat(),
                    "status": result.get("status", "unknown"),
                    "steps_completed": result.get("steps_completed", []),
                    "result": result,
                    "error": None,
                    "source": "sqs_worker",
                },
            )
            log.info("process_data finished customer_id=%s status=%s", customer_id, result.get("status"))
        except Exception as e:
            log.exception("process_data failed customer_id=%s", customer_id)
            write_progress(
                customer_id,
                {
                    "in_progress": False,
                    "completed_at": _dt.utcnow().isoformat(),
                    "status": "error",
                    "error": str(e),
                    "result": None,
                    "source": "sqs_worker",
                },
            )
            raise


def _do_rehydrate_import(app, data: dict) -> None:
    from datetime import datetime as _dt

    from utils.async_job_storage import write_job_record
    from utils.onboarding_progress_file import _instance_dir

    customer_id = int(data["customer_id"])
    job_id = data["job_id"]
    rel = data["staging_relpath"]
    orig = data.get("original_filename") or "import.xlsx"
    user_id = data.get("user_id")

    log.info("SQS job=rehydrate_import customer_id=%s job_id=%s", customer_id, job_id)

    base = _instance_dir()
    path = base / rel
    if not path.is_file():
        write_job_record(
            job_id,
            {
                "job": "rehydrate_import",
                "customer_id": customer_id,
                "in_progress": False,
                "completed": False,
                "error": f"staging file missing: {path}",
                "updated_at": _dt.utcnow().isoformat(),
            },
        )
        log.error("rehydrate staging missing %s", path)
        return

    raw = path.read_bytes()
    try:
        with app.app_context():
            from rehydration_api import _import_account_data_from_excel

            tup = _import_account_data_from_excel(
                customer_id, raw, user_id=user_id, original_filename=orig
            )
        payload = {}
        code = 500
        if isinstance(tup, tuple) and len(tup) == 2:
            resp, code = tup[0], tup[1]
            payload = resp.get_json(silent=True) or {}
        ok = 200 <= int(code) < 300
        write_job_record(
            job_id,
            {
                "job": "rehydrate_import",
                "customer_id": customer_id,
                "in_progress": False,
                "completed": bool(ok),
                "http_status": int(code),
                "result": payload if ok else None,
                "error": None if ok else (payload.get("error") if isinstance(payload, dict) else str(payload)),
            },
        )
        log.info("rehydrate_import finished job_id=%s ok=%s code=%s", job_id, ok, code)
    finally:
        path.unlink(missing_ok=True)


def _do_export_all_account_data(app, data: dict) -> None:
    import logging as _logging

    from export_api import build_all_account_export_workbook
    from utils.async_job_storage import export_output_path, write_job_record

    customer_id = int(data["customer_id"])
    job_id = data["job_id"]
    wlog = _logging.getLogger("sqs_worker.export")

    log.info("SQS job=export_all_account_data customer_id=%s job_id=%s", customer_id, job_id)

    with app.app_context():
        blob, filename, err = build_all_account_export_workbook(customer_id, wlog)

    if err or not blob:
        write_job_record(
            job_id,
            {
                "job": "export_all_account_data",
                "customer_id": customer_id,
                "in_progress": False,
                "completed": False,
                "error": err or "empty export",
            },
        )
        log.warning("export failed job_id=%s err=%s", job_id, err)
        return

    outp = export_output_path(job_id)
    outp.write_bytes(blob)
    write_job_record(
        job_id,
        {
            "job": "export_all_account_data",
            "customer_id": customer_id,
            "in_progress": False,
            "completed": True,
            "download_filename": filename,
            "error": None,
        },
    )
    log.info("export_all_account_data wrote job_id=%s bytes=%s", job_id, len(blob))


def _handle_message(app, body: str) -> None:
    data = json.loads(body)
    job = (data.get("job") or "process_data").strip()

    if job == "process_data":
        _do_process_data(app, data)
    elif job == "rehydrate_import":
        _do_rehydrate_import(app, data)
    elif job == "export_all_account_data":
        _do_export_all_account_data(app, data)
    else:
        log.error("Unknown SQS job type: %s", job)
        raise ValueError(f"unknown job: {job}")


def main() -> None:
    try:
        import boto3
    except ImportError:
        log.error("boto3 is required for the SQS worker")
        sys.exit(1)

    queue_url = _queue_url()
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    wait = int(os.environ.get("ONBOARDING_SQS_WAIT_SECONDS", "20"))
    once = os.environ.get("ONBOARDING_WORKER_ONCE", "").lower() in ("1", "true", "yes")

    os.environ.setdefault("PYTHONPATH", "/app/backend")
    if "/app/backend" not in os.environ.get("PYTHONPATH", ""):
        os.environ["PYTHONPATH"] = "/app/backend" + os.pathsep + os.environ.get("PYTHONPATH", "")

    sys.path.insert(0, "/app/backend")

    from app_v3_minimal import app

    client = boto3.client("sqs", region_name=region)
    log.info("SQS customer-jobs worker started queue=%s region=%s", queue_url, region)

    while True:
        try:
            msg = _receive_one(client, queue_url, wait)
            if not msg:
                if once:
                    log.info("ONBOARDING_WORKER_ONCE: no message, exiting")
                    return
                continue
            receipt = msg["ReceiptHandle"]
            body = msg.get("Body") or "{}"
            try:
                _handle_message(app, body)
                client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt)
            except Exception:
                log.warning("Message not deleted; will become visible again after visibility timeout")
                if once:
                    return
            if once:
                return
        except KeyboardInterrupt:
            log.info("Interrupted, exiting")
            return
        except Exception as e:
            log.exception("Worker loop error: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
