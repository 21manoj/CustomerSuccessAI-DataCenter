# Wizard B - Pattern Analysis Report

**Run ID:** test_run_20260120_182316
**Generated:** 2026-02-06 09:13:23

## Summary

- **Total Accounts Analyzed:** 19
- **Patterns Identified:** 3
- **Phase Transitions:** 7
- **Early Warning Rules:** 2

## Pattern Profiles

### PROACTIVE_GROWTH

- **Accounts:** 10
- **Health Trajectory:** 75.0 → 98.0
- **Average Events:** 144
- **CSM Investment:** $330,150
- **Financial Impact:** 40% ARR expansion

**Success Factors:**
- Average CSM investment: $330,150
- High engagement: 144 events/account
- Early health improvement: 10/10 accounts

### IGNORED_CHURN

- **Accounts:** 7
- **Health Trajectory:** 70.0 → 15.0
- **Average Events:** 31
- **CSM Investment:** $108,571
- **Financial Impact:** 100% ARR lost - churn

### CRISIS_RECOVERY

- **Accounts:** 2
- **Health Trajectory:** 90.1 → 94.9
- **Average Events:** 103
- **CSM Investment:** $503,000
- **Financial Impact:** 40% ARR expansion

## Early Warning Rules

### EW001: Health drops below 50 in first 20 weeks

- **Condition:** `health_score < 50 AND week_number <= 20`
- **Predicted Outcome:** churn
- **Lead Time:** 20 weeks
- **Confidence:** 100.0%

### EW002: Sustained negative sentiment (>60% of events)

- **Condition:** `negative_sentiment_ratio > 0.60`
- **Predicted Outcome:** churn
- **Lead Time:** 10 weeks
- **Confidence:** 100.0%

