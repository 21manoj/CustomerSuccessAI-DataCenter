# Module 07 — Adversarial Validation Worked Example

This directory is the artifact of the **spec-only adversarial rebuild** of
[Module 07 — Agent / MCP Tool Layer](../07-interface-mcp-tool-layer.md),
run 2026-08-07. A fresh agent was given ONLY the spec (no access to the origin
`kpi-dashboard/` code, no other modules) and asked to build a self-contained
implementation and PROVE any defects with executable tests.

- `impl.py` — a self-contained, spec-faithful implementation: a fake
  `FastMCP`/`FunctionTool`, in-memory `CustomerApiKey`/`Account` records, and
  faked Module 01/03 hooks. It follows the Build Prompt's literal pseudocode,
  including the parts that turned out to be defective.
- `test_spec.py` — pytest suite: 15 acceptance-criteria tests + 4
  defect-proving tests (`test_defect_*`), each of which runs the spec-as-written
  to demonstrate the failure and then the corrected version.

Run:

```bash
python3 -m pytest test_spec.py -q
```

Expected: **19 passed** (Python 3.9, pytest 7.4).

## The four defects this rebuild proved (all fixed in the spec)

1. **SEVERE** — `run_server` referenced but undefined and `MCP_TRANSPORT=http`
   never set in code → the natural entrypoint ships an HTTP server with auth
   skipped for all traffic (Gotcha 7's fix lived only in prose).
2. **SEVERE** — `extract_api_key`'s identity-blind `list(_session_api_keys
   .values())[-1]` fallback (copied verbatim from the origin `auth.py:176-178`)
   hands one tenant's key to an anonymous, session-less caller — a real
   cross-tenant data leak. **This bug is still live in the origin code.**
3. **MODERATE** — the "Expiry NULL" acceptance criterion tested Module 01's
   logic, not this module's (expiry is delegated) — no owning code here.
4. **MINOR** — `MCP_AUTH_REQUIRED`/`MCP_SERVER_API_KEY` frozen at import while
   `MCP_TRANSPORT` was read live, so a test/ops `setenv` was silently inert.

The two loudly-flagged NULL traps (`allowed_account_ids`, `expires_at`) were
**decoys** — handled correctly. See the spec's
[Validation Note](../07-interface-mcp-tool-layer.md#validation-note) for the
full write-up.
