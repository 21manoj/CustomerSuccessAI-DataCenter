# Pilot validation artifact — do not treat as a reference implementation

What a fresh agent built from **only**
[`../06-intelligence-signal-processing.md`](../06-intelligence-signal-processing.md),
with an injected fake LLM client (no real API calls). 57 tests pass.

Several tests are executable **proofs the original spec was wrong** — e.g.
`test_literal_budget_gate_can_never_fire` (25 calls against a $0.01 cap, all
allowed, spend permanently 0.00),
`test_literal_urgency_rules_crash_on_null_content`,
`test_literal_model_version_comes_from_llm_output_not_from_the_caller`. Each
runs the spec's original literal pseudocode, demonstrates the failure, then
the corrected version.

`test_spec_now_defines_every_helper_its_build_prompt_calls` is an inverted
proof-of-defect test: it originally asserted the Build Prompt was MISSING
`record_usage`/`score_to_level`/`normalize`/`LLMUsageRecord`; now that the
spec is fixed it guards against those definitions being dropped again.

See the spec's Validation Note for the full finding list — this run hit all
four of the library's documented failure shapes.
