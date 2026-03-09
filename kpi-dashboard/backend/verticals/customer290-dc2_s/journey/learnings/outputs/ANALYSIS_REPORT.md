# Wizard B - Pattern Analysis Report

**Run ID:** outputs
**Generated:** 2026-03-06 22:37:02

## Summary

- **Total Accounts Analyzed:** 19
- **Patterns Identified:** 3
- **Phase Transitions:** 8
- **Early Warning Rules:** 2

## Pattern Profiles

### CRISIS_RECOVERY

- **Accounts:** 5
- **Health Trajectory:** 90.0 → 94.7
- **Average Events:** 103
- **CSM Investment:** $515,300
- **Financial Impact:** 40% ARR expansion

### PROACTIVE_GROWTH

- **Accounts:** 10
- **Health Trajectory:** 75.0 → 97.9
- **Average Events:** 148
- **CSM Investment:** $352,950
- **Financial Impact:** 40% ARR expansion

**Success Factors:**
- Average CSM investment: $352,950
- High engagement: 148 events/account
- Early health improvement: 10/10 accounts

### IGNORED_CHURN

- **Accounts:** 4
- **Health Trajectory:** 70.0 → 15.0
- **Average Events:** 26
- **CSM Investment:** $75,000
- **Financial Impact:** 100% ARR lost - churn

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

