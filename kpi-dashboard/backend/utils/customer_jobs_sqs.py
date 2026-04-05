"""
SQS queue for long-running customer jobs (process-data, rehydrate, export).

Uses the same queue URL env vars as onboarding:
  ONBOARDING_SQS_URL or AWS_SQS_ONBOARDING_QUEUE_URL

Message body: JSON object with required string field "job" and job-specific keys.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def customer_jobs_queue_url() -> Optional[str]:
    return (
        os.environ.get("ONBOARDING_SQS_URL")
        or os.environ.get("AWS_SQS_ONBOARDING_QUEUE_URL")
        or ""
    ).strip() or None


def customer_jobs_sqs_configured() -> bool:
    return customer_jobs_queue_url() is not None


def enqueue_customer_job(body: Dict[str, Any]) -> bool:
    """
    Send JSON message to the customer jobs queue.
    body must include "job" (e.g. process_data, rehydrate_import, export_all_account_data).
    """
    url = customer_jobs_queue_url()
    if not url:
        return False
    if not body.get("job"):
        logger.error("enqueue_customer_job: missing job type in body")
        return False
    try:
        import boto3
    except ImportError:
        logger.error("boto3 not installed; cannot enqueue SQS message")
        return False

    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
    try:
        client = boto3.client("sqs", region_name=region)
        client.send_message(QueueUrl=url, MessageBody=json.dumps(body, default=str))
        logger.info("Enqueued customer job job=%s keys=%s", body.get("job"), list(body.keys()))
        return True
    except Exception as e:
        logger.error("SQS send_message failed: %s", e, exc_info=True)
        return False
