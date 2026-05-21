#!/usr/bin/env python3
"""Post-deploy verification: CFO Phases 0–5. Delegates to verify_executive_phases_ec2."""

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.verify_executive_phases_ec2 import main as _main


if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--suite", "cfo"]
    sys.exit(_main())
