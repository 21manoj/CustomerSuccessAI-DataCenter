"""
Simulation Engine — Stateful, phase-aware data injection for CS Pulse.

Reads current DB state, decides per-account trajectory, generates
coherent KPI + signal data, uploads, and triggers processing.

Usage:
    python3 simulation_engine.py --customer-id 27 --phases 4 --base-url http://localhost
"""
