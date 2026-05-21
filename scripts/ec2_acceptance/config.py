"""Environment-driven config for EC2 / remote acceptance runs."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AcceptanceConfig:
    base_url: str
    email: str
    password: str
    customer_id: int
    timeout_sec: int = 120

    @property
    def base_url_normalized(self) -> str:
        return self.base_url.rstrip("/")


def load_config() -> AcceptanceConfig:
    """Load config from environment (see scripts/.env.acceptance.example)."""
    base = (
        os.environ.get("CS_PULSE_BASE_URL")
        or os.environ.get("ACCEPTANCE_BASE_URL")
        or "http://3.94.106.197"
    )
    email = (
        os.environ.get("CS_PULSE_EMAIL")
        or os.environ.get("ACCEPTANCE_EMAIL")
        or "dc2s_super@test.com"
    )
    password = (
        os.environ.get("CS_PULSE_PASSWORD")
        or os.environ.get("ACCEPTANCE_PASSWORD")
        or "DC2_Super_2024!"
    )
    cust = (
        os.environ.get("ACCEPTANCE_CUSTOMER_ID")
        or os.environ.get("PERSONA_GRADING_CUSTOMER_ID")
        or "334"
    )
    timeout = int(os.environ.get("ACCEPTANCE_TIMEOUT_SEC", "120"))
    return AcceptanceConfig(
        base_url=base,
        email=email,
        password=password,
        customer_id=int(cust),
        timeout_sec=timeout,
    )
