"""
Legacy Tier-2 fixture with a deliberately broken weight sum, used to prove
that catalog validation runs identically on the Tier-2 (legacy module) path,
not just the Tier-1 (JSON file) path. This is deliberately not called out
anywhere in the spec's own examples, which only illustrate validation being
skipped on an admin-UI write path vs. a JSON-file load path -- extending
that same "validate on every load, every path" rule to Tier 2 is this
implementation's own interpretation, flagged in the validation report.
"""

PILLARS = {
    "P1": {"name": "Treatment Quality", "weight_l2": 0.6},
    "P2": {"name": "Booking Efficiency", "weight_l2": 0.3},
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
}
