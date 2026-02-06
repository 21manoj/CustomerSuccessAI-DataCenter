# Qualitative Signals Output Validation

## Summary of fixes

1. **Subject and summary**  
   The journey API now sets `subject` from signal content (first sentence or first 100 chars) instead of leaving it empty. The UI shows this as the timeline card title; `summary` remains the full content.

2. **Priority and critical count**  
   Priority is derived from sentiment and `sentiment_score` (same logic as `signals_query_helper`):
   - **Critical**: `sentiment = 'negative'` and `sentiment_score < -0.5`
   - **High**: negative, **Medium**: neutral, **Low**: positive  

   The "Critical" count on the Qualitative Signals tab is the number of signals with `priority === 'critical'`.

3. **Health impact**  
   `health_impact` is now set from `sentiment_score` (scaled -15 to +15) instead of 0.

4. **Response counts for validation**  
   `GET /api/journey/<account_id>` response includes in `summary`:
   - `total_signals`, `signals_positive`, `signals_negative`, `signals_neutral`, `signals_critical`  

   These match what the Qualitative Signals tab derives from the `signals` array.

## How to validate for an account (e.g. E2E UI Test Customer - Production)

- **Account**: "E2E UI Test Customer - Production" is `account_id = 102001` (customer 102).
- **UI**: Total Signals, Positive, Negative, Critical on the Qualitative Signals tab are computed from the `signals` array returned by `/api/journey/102001`.
- **Backend**: Signals come from (1) journey JSON weekly data and (2) `qualitative_signals` table (tenant-checked). They are merged and de-duplicated.
- **DB vs UI**: If the UI shows 12 total, 2 positive, 6 negative, 0 critical, that is correct for the **combined** set of signals actually returned (journey file + DB for that account). The DB may have more rows for 102001; only signals that pass tenant check and merge/dedup are in the response.

To compare with the database (optional):

```sql
-- Counts for account 102001
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE sentiment = 'positive') AS positive,
  COUNT(*) FILTER (WHERE sentiment = 'negative') AS negative,
  COUNT(*) FILTER (WHERE sentiment = 'neutral') AS neutral,
  COUNT(*) FILTER (WHERE sentiment = 'negative' AND sentiment_score < -0.5) AS critical
FROM qualitative_signals
WHERE account_id = 102001;
```

If the journey file has no signals and all signals come from the DB for 102001, the API counts should match this query. If the journey file also has signals, the API returns the merged set, so total can differ from the DB count.

## Timeline card display

- **Subject**: Short line from content (first sentence or first 100 chars).
- **Summary**: Full content below.
- **Week / Date / From**: From signal metadata.
- **Priority badge**: Critical / High / Medium / Low from derived `priority`.
- **Sentiment icon**: From `sentiment` (positive / negative / neutral).
