#!/usr/bin/env python3
"""
Simulation Engine CLI — stateful, phase-aware data injection for CS Pulse.

Run from load-driver/ directory:
    python3 simulation_engine.py --customer-id 27 --email admin@x.io --phases 4 --base-url http://...
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from simulation.cli import main

if __name__ == '__main__':
    main()
