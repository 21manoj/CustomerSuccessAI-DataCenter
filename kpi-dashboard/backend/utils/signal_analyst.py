# TODO: Layer A — Proactive LLM Signal Analyst
# See: backend/docs/ACTIONS_PIPELINE_PLAN.md — Layer A
#
# Trigger: health drops >10pts OR new ContextNode(severity=critical) ingested
# Input:   account_id, health_before, health_after, arc_type
# Output:  Notification(type=signal_insight) stored in DB
#
# Implementation Sprint: Sprint 2, Session 3 (after push infrastructure exists)
raise NotImplementedError("signal_analyst.py not yet implemented — see ACTIONS_PIPELINE_PLAN.md")
