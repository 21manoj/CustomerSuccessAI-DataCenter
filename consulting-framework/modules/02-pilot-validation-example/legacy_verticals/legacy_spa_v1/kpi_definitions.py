"""
Legacy Tier-2 fallback fixture: a hand-written Python module predating the
JSON catalog format, kept only for a vertical that was onboarded before
Module 02 existed. New verticals must never be authored this way (Build
Prompt, Tier 2) — this fixture exists purely to exercise catalog_loader's
Tier 2 resolution path and its validation, which must run identically
whether the catalog came from JSON or from this legacy module shape.
"""

PILLARS = {
    "P1": {"name": "Treatment Quality", "weight_l2": 0.6},
    "P2": {"name": "Booking Efficiency", "weight_l2": 0.4},
}

KPIS = {
    "P1-KPI1": {
        "name": "Therapist Satisfaction Score",
        "pillar": "P1",
        "weight_l1": 1.0,
        "higher_is_better": True,
        "ranges": {
            "healthy": {"min": 85, "max": 100},
            "risk": {"min": 70, "max": 84.99},
            "critical": {"min": 0, "max": 69.99},
        },
    },
    "P2-KPI1": {
        "name": "No-Show Rate (%)",
        "pillar": "P2",
        "weight_l1": 1.0,
        "higher_is_better": False,
        "ranges": {
            "healthy": {"min": 0, "max": 5},
            "risk": {"min": 5.01, "max": 15},
            "critical": {"min": 15.01, "max": 100},
        },
    },
}
