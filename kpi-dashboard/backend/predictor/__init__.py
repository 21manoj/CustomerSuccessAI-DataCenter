"""NRR Predictor v3 — Phase 1.

Two artifacts per A2 in PLAN_nrr_predictor_v3.md:
  - wizards/wizard_d_predictor_calibrator.py   (offline GLMM fit, quarterly)
  - backend/predictor/                         (per-account inference, on demand)

This package is the inference side. Calibration coefficients are fit by
Wizard D, persisted to the predictor_calibrations table, and read by
inference.py at request time.
"""
