"""
Poll async job status and download export artifacts (SQS worker pattern).
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, send_file

from auth_middleware import get_current_customer_id
from utils.async_job_storage import export_output_path, read_job_record

logger = logging.getLogger(__name__)

async_jobs_bp = Blueprint("async_jobs", __name__)


@async_jobs_bp.route("/api/jobs/status/<job_id>", methods=["GET"])
def job_status(job_id: str):
    cid = get_current_customer_id()
    if not cid:
        return jsonify({"error": "Authentication required"}), 401
    rec = read_job_record(job_id)
    if not rec:
        return jsonify({"error": "Unknown job"}), 404
    if int(rec.get("customer_id", -1)) != int(cid):
        return jsonify({"error": "Forbidden"}), 403
    return jsonify(rec)


@async_jobs_bp.route("/api/jobs/download/<job_id>", methods=["GET"])
def job_download(job_id: str):
    cid = get_current_customer_id()
    if not cid:
        return jsonify({"error": "Authentication required"}), 401
    rec = read_job_record(job_id)
    if not rec:
        return jsonify({"error": "Unknown job"}), 404
    if int(rec.get("customer_id", -1)) != int(cid):
        return jsonify({"error": "Forbidden"}), 403
    if rec.get("job") != "export_all_account_data":
        return jsonify({"error": "No download for this job type"}), 400
    if rec.get("in_progress"):
        return jsonify({"error": "Export still in progress"}), 409
    if rec.get("error"):
        return jsonify({"error": rec.get("error")}), 422
    path = export_output_path(job_id)
    if not path.is_file():
        logger.error("Export file missing for job_id=%s path=%s", job_id, path)
        return jsonify({"error": "Export file not found"}), 404
    fn = rec.get("download_filename") or f"export_{job_id}.xlsx"
    return send_file(
        path,
        as_attachment=True,
        download_name=fn,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
