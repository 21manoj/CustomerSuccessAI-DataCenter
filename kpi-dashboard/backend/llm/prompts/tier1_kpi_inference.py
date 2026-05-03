"""
Tier-1 KPI inference prompts.

Two prompts, selected by mode:

  FULL_INFERENCE_PROMPT
      Used in 2-CSV mode (accounts + KPIs only). Asks the LLM to
      derive SIGNAL + DECISION + OUTCOME nodes plus causal edges
      from KPI trajectories alone.

  EDGE_ENRICHMENT_PROMPT
      Used in 3-CSV / 4-CSV mode (accounts + KPIs + signals).
      Existing SIGNAL nodes are already in the graph. The LLM is
      asked for DECISION + OUTCOME nodes and the causal edges that
      connect existing signals to decisions to outcomes — no signal
      duplication.

Both prompts demand strict JSON output with per-edge `confidence`
in [0, 1]. The downstream writer applies the
`utils.provenance.is_trustworthy_edge` threshold to drop noisy
edges before persistence.
"""

FULL_INFERENCE_PROMPT = """\
You are an expert customer success analyst inferring causal structure
from KPI trajectories. The customer has uploaded ONLY accounts and
KPI measurements — no signals, decisions, or outcomes are recorded.

Your job is to read the KPI trajectory for one account, then output:
  1. signals  — observable events (e.g. usage drop, NPS spike)
  2. decisions — actions the CSM/exec team likely took
  3. outcomes — the realised end-state (renewed, churned, expanded)
  4. causal_edges — typed causal links between the above

ACCOUNT SUMMARY
{account_summary}

KPI TRAJECTORY (last 12 months)
{kpi_trajectory}

Return STRICT JSON in this shape:
{{
  "signals":  [{{"subtype": "...", "title": "...", "occurred_at": "YYYY-MM-DD",
                 "ref": "signal:1"}}],
  "decisions":[{{"subtype": "...", "title": "...", "occurred_at": "YYYY-MM-DD",
                 "ref": "decision:1"}}],
  "outcomes": [{{"subtype": "...", "title": "...", "occurred_at": "YYYY-MM-DD",
                 "revenue_impact": -250000, "revenue_impact_type": "at_risk",
                 "ref": "outcome:1"}}],
  "causal_edges": [
    {{"from_ref": "signal:1", "to_ref": "decision:1",
      "edge_type": "TRIGGERED", "confidence": 0.82, "lag_days": 7}}
  ]
}}

Rules:
- `confidence` must be in [0, 1]; reflect your true uncertainty.
- `edge_type` must be one of: LED_TO, TRIGGERED, CAUSED_BY, CORRELATES_WITH.
- For causal edges, `from_ref.occurred_at` MUST precede `to_ref.occurred_at`.
- Only emit edges you can defend from the KPI evidence; do NOT
  fabricate edges to flesh out the story.
- Output JSON only — no commentary.
"""


EDGE_ENRICHMENT_PROMPT = """\
You are an expert customer success analyst. The context graph already
contains SIGNAL nodes uploaded by the customer. Your job is NOT to
re-create those signals. Instead, infer:
  1. decisions — actions the CSM/exec team likely took in response
  2. outcomes — the realised end-state per account
  3. causal_edges — typed causal links between EXISTING signals and
     the decisions/outcomes you propose

ACCOUNT SUMMARY
{account_summary}

EXISTING SIGNAL NODES (already in the graph — do NOT duplicate)
{existing_signals}

KPI TRAJECTORY (last 12 months)
{kpi_trajectory}

Return STRICT JSON in this shape:
{{
  "decisions":[{{"subtype": "...", "title": "...", "occurred_at": "YYYY-MM-DD",
                 "ref": "decision:1"}}],
  "outcomes": [{{"subtype": "...", "title": "...", "occurred_at": "YYYY-MM-DD",
                 "revenue_impact": -250000, "revenue_impact_type": "at_risk",
                 "ref": "outcome:1"}}],
  "causal_edges": [
    {{"from_ref": "signal:7", "to_ref": "decision:1",
      "edge_type": "TRIGGERED", "confidence": 0.82, "lag_days": 14}}
  ]
}}

Rules:
- For causal_edges, `from_ref` may reference an EXISTING signal by
  its node_id (e.g. "node:1234") OR a positional alias (e.g.
  "signal:1" = first existing signal in `EXISTING SIGNAL NODES`).
- `confidence` must be in [0, 1]; reflect your true uncertainty.
  Edges with confidence < 0.6 will be dropped by the writer.
- `edge_type` must be one of: LED_TO, TRIGGERED, CAUSED_BY, CORRELATES_WITH.
- For causal edges, the source event MUST occur before the target.
- Output JSON only — no commentary.
"""


def render_full_prompt(*, account_summary: str, kpi_trajectory: str) -> str:
    """Render the full-inference prompt (2-CSV mode)."""
    return FULL_INFERENCE_PROMPT.format(
        account_summary=account_summary,
        kpi_trajectory=kpi_trajectory,
    )


def render_edge_enrichment_prompt(
    *, account_summary: str, existing_signals: str, kpi_trajectory: str,
) -> str:
    """Render the edge-enrichment prompt (3-CSV / 4-CSV mode)."""
    return EDGE_ENRICHMENT_PROMPT.format(
        account_summary=account_summary,
        existing_signals=existing_signals,
        kpi_trajectory=kpi_trajectory,
    )
