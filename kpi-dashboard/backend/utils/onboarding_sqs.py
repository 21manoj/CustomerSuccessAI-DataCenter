"""
Optional SQS enqueue for async onboarding process-data.

Set ONBOARDING_SQS_URL (full queue URL) or AWS_SQS_ONBOARDING_QUEUE_URL.
Requires IAM permission sqs:SendMessage on that queue (e.g. EC2 instance profile).

If unset, process-data falls back to the in-process background thread.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def onboarding_queue_url() -> Optional[str]:
    return (
        os.environ.get("ONBOARDING_SQS_URL")
        or os.environ.get("AWS_SQS_ONBOARDING_QUEUE_URL")
        or ""
    ).strip() or None


def enqueue_process_data_job(customer_id: int) -> bool:
    """
    Send { "customer_id": <int>, "job": "process_data" } to the shared customer jobs queue.
    """
    from utils.customer_jobs_sqs import enqueue_customer_job

    return enqueue_customer_job({"job": "process_data", "customer_id": int(customer_id)})
