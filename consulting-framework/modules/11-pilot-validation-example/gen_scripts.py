"""Helper generators used by cross-process determinism tests.

good_generate: spec-literal make_rng discipline (one random.Random(seed)).
bad_generate:  the Gotcha-2 anti-pattern -> per-KPI stream seeded from
               random.Random(seed + hash(kpi_code)). Reproducible in-process,
               NON-reproducible across processes with different PYTHONHASHSEED.
"""
import random

MANIFEST_CODES = ["P1-KPI1", "P2-KPI2", "P3-KPI3"]
MONTHS = 6


def good_generate(seed=42):
    rng = random.Random(seed)
    rows = []
    for code in MANIFEST_CODES:
        for m in range(MONTHS):
            rows.append(f"{code},{m},{rng.gauss(0, 1.0):.6f}")
    return "\n".join(rows)


def bad_generate(seed=42):
    rows = []
    for code in MANIFEST_CODES:
        rng = random.Random(seed + hash(code))  # Gotcha-2 killer
        for m in range(MONTHS):
            rows.append(f"{code},{m},{rng.gauss(0, 1.0):.6f}")
    return "\n".join(rows)


if __name__ == "__main__":
    import sys
    which = sys.argv[1] if len(sys.argv) > 1 else "good"
    out = good_generate() if which == "good" else bad_generate()
    import hashlib
    print(hashlib.sha256(out.encode()).hexdigest())
