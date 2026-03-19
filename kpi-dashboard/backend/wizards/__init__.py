"""
DB-native wizard implementations.

Each wizard reads from PostgreSQL and writes results back to DB —
no filesystem scripts or subprocess calls.
"""

from wizards.wizard_a_journey_db import run_wizard_a
from wizards.wizard_b_pattern_db import run_wizard_b
from wizards.wizard_c_weight_calibrator_db import run_wizard_c

__all__ = ['run_wizard_a', 'run_wizard_b', 'run_wizard_c']
