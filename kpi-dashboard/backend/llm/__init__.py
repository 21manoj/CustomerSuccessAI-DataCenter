"""
CS Pulse LLM Reasoning Layer (v0.9 BETA)

Gated behind WITH_LLM feature flag. Adds AI reasoning on top of
the deterministic pipeline — never replaces it.

Modules:
  tier1_inference  — Infer signals/outcomes/decisions from KPI patterns
  prompts/         — Prompt templates for each inference type
"""
