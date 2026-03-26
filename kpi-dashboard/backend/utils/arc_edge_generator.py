# TODO: Sprint 1 — Wizard A Arc Intelligence Engine (Session 1)
# See: backend/docs/ACTIONS_PIPELINE_PLAN.md — Sprint 1, Session 1
#
# Backend equivalent of load-driver's RefRegistry + generate_signal_edges_csv()
#
# Input:   account_id, arc_type, phase ('baseline'|'intervention')
# Process: query ContextNodes ordered by occurred_at → build in-DB ref map
#          apply ARC_TEMPLATES[arc_type][phase]['edge_topology'] against real node IDs
#          temporal check: from.occurred_at < to.occurred_at
# Output:  INSERT ContextEdge rows into DB
#
# Ref resolution:
#   signal:N   → Nth ContextNode(SIGNAL) by occurred_at for this account (1-indexed)
#   decision:N → Nth ContextNode(DECISION) by occurred_at for this account (1-indexed)
#   outcome:X  → ContextNode(OUTCOME) where outcome_type == X for this account
#
# ARC_TEMPLATES source: load-driver/scenarios/scenario_manifest.py
# Must stay in sync with load-driver ARC_TEMPLATES edge_topology definitions.
#
# Implementation Sprint: Sprint 1, Session 1
raise NotImplementedError("arc_edge_generator.py not yet implemented — see ACTIONS_PIPELINE_PLAN.md")
