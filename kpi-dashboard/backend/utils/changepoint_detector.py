# TODO: Sprint 2 — Wizard B Predictive Risk Engine (Session 2)
# See: backend/docs/ACTIONS_PIPELINE_PLAN.md — Sprint 2, Session 2
#
# Input:   account_id, kpi_code (e.g. 'P1-KPI3'), lookback_weeks=12
# Process: scan per-KPI weekly values for slope inflection points
#          flag decay that hasn't yet propagated to L3 composite health score
# Output:  list of { kpi_code, change_point_week, severity, estimated_l3_lag_weeks }
#
# Value: "P1-KPI3 dropped 28% WoW — not yet in L3 health score.
#         Historical pattern: precedes composite health drop 6-8 weeks later."
#
# Algorithm: simple slope comparison (week N slope vs week N-4 slope)
#            future: ruptures library for proper PELT change-point detection
#
# Implementation Sprint: Sprint 2, Session 2
raise NotImplementedError("changepoint_detector.py not yet implemented — see ACTIONS_PIPELINE_PLAN.md")
