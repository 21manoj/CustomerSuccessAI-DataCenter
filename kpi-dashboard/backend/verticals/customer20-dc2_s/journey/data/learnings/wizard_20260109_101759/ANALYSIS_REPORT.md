# Wizard B - Pattern Analysis Report

**Run ID:** wizard_20260109_101759
**Generated:** 2026-01-10 14:19:09

## Summary

- **Total Accounts Analyzed:** 10
- **Patterns Identified:** 3
- **Phase Transitions:** 8
- **Early Warning Rules:** 2

## Pattern Profiles

### PROACTIVE_GROWTH

- **Accounts:** 4
- **Health Trajectory:** 75.0 → 97.7
- **Average Events:** 134
- **CSM Investment:** $290,250
- **Financial Impact:** 40% ARR expansion

**Success Factors:**
- Average CSM investment: $290,250
- High engagement: 134 events/account
- Early health improvement: 4/4 accounts

### IGNORED_CHURN

- **Accounts:** 4
- **Health Trajectory:** 70.0 → 15.0
- **Average Events:** 25
- **CSM Investment:** $77,500
- **Financial Impact:** 100% ARR lost - churn

### CRISIS_RECOVERY

- **Accounts:** 2
- **Health Trajectory:** 90.0 → 94.1
- **Average Events:** 98
- **CSM Investment:** $411,250
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

