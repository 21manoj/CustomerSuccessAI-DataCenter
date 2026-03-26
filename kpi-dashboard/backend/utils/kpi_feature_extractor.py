# TODO: Sprint 2 — Wizard B Predictive Risk Engine (Session 1)
# See: backend/docs/ACTIONS_PIPELINE_PLAN.md — Sprint 2, Session 1
#
# Input:   account_id, lookback_days=90
# Output:  normalized feature vector (list[float]) for KMeans clustering
#
# Feature vector (22 dimensions):
#   [health_now, health_30d, health_60d, health_90d,       # health snapshots
#    slope_14d, slope_30d, slope_60d,                       # health velocity
#    p1_score, p2_score, p3_score, p4_score, p5_score,      # pillar scores
#    p1_delta_30d, p2_delta_30d, p3_delta_30d,              # pillar velocity
#    p4_delta_30d, p5_delta_30d,
#    signal_count_critical_30d, signal_count_positive_30d,  # signal mix
#    days_to_renewal, arr_normalized]                        # account context
#
# Normalization: min-max per dimension across all accounts in customer pool
#
# Implementation Sprint: Sprint 2, Session 1
raise NotImplementedError("kpi_feature_extractor.py not yet implemented — see ACTIONS_PIPELINE_PLAN.md")
