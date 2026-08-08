# 07 — Agent / MCP Tool Layer

**Layer:** Interface

**Status:** ✅ Validated — see [Validation Note](#validation-note) at the bottom.
A spec-only fresh-agent rebuild (2026-08-07) proved four defects with executable
tests — two SEVERE, including a cross-tenant key-leak carried verbatim from the
origin `auth.py` — all fixed in the spec below.

## Purpose

Expose the whole platform — health scores, at-risk accounts, the context graph,
revenue analytics, onboarding — to external LLM agents (Claude Desktop, Claude
Code, Copilot Studio, ChatGPT) as a set of callable tools, over a standalone
server the client can point any assistant at. This is the layer that turns "a
dashboard a human logs into" into "a system an agent can reason over on the
client's behalf." Its whole job is a thin, safe boundary: every tool delegates
the actual thinking to the Intelligence modules and does three things of its own
— authenticate the caller, isolate the tenant, and return a self-describing
envelope. Get the boundary wrong and you either leak one client's data to
another (a tenant-isolation break is the worst possible outcome for a
multi-tenant SaaS) or expose zero tools because the server registered them onto
the wrong object.

## Boundary

**Owns:**
- The single server instance (one `FastMCP`), its two transports (stdio for
  local assistants, Streamable HTTP for remote ones), and the registration
  mechanism by which tool modules attach to it — including the `__main__`
  dual-instance fix (Gotcha 1).
- The **tool auth layer**: two-tier keys (server-level super-admin key +
  DB-backed per-customer scoped keys), the scope hierarchy (`read ⊂ write ⊂
  admin`), and the per-tool enforcement functions every tool calls
  (`require_auth`, `require_account_auth`, `require_read_key`,
  `require_cross_customer_auth`). Tenant isolation and account-level partner
  restriction live here.
- The **impl/tool separation convention**: every tool's logic lives in a plain
  callable `_<name>_impl(...)`; the `@mcp.tool`-decorated function is a thin
  wrapper. This is what makes a tool reusable by other tools and other
  in-process consumers without hitting the FunctionTool-not-callable trap
  (Gotcha 2).
- The **response envelope contract**: every tool response carries a `scope`
  field and, for any dollar figure, `arr_basis` / `arr_basis_value`, stamped by
  a shared helper so "every response is self-describing" is true by
  construction, not by convention.
- The **registry as the single source of truth** for what tools exist, and the
  parity check that keeps secondary consumers from drifting from it (Gotcha 3).
- The HTTP Bearer-token middleware and its context propagation (contextvar +
  session-id fallback, Gotcha 5).

**Explicitly does not own:**
- The business logic behind any tool — health scoring is Module 03, the context
  graph is Module 04, wizard orchestration is Module 05, signal processing is
  Module 06, ingestion/onboarding is Module 09. Every tool in this module
  **delegates** to one of those modules' `_impl` callables and adds nothing but
  auth + envelope. A tool that computes a health score itself is scope creep.
- The `CustomerApiKey` **table** — its schema (columns, hashing, expiry) is
  Module 01 (Data Model). This module consumes it and owns the *validation and
  enforcement logic*, not the DDL.
- The in-app "Ask AI" assistant and the internal `agent_tool_registry` — those
  are *consumers* of this layer, not part of it. This module owns the rule that
  they derive from the MCP registry rather than re-declaring tools (Gotcha 3);
  it does not own their UI or prompts.
- Feature-flag storage — Module 01 owns the toggle system; this module only
  reads `MCP_SERVER` to gate the whole server on/off.

## Dependencies

- **Module 01 (Data Model):**
  - `Customer`, `Account` for tenant scoping. `Account` is queried by
    `(account_id, customer_id)` together for ownership checks — an
    `account_id`-only lookup is a tenant-isolation hole (Gotcha 4).
  - `CustomerApiKey` with, at minimum, these fields this module reads:
    `key_prefix` (indexed, for DB lookup), `key_hash` (SHA-256 of the raw key —
    the raw key is never stored), `customer_id` (FK, NOT NULL), `scopes` (JSON
    list, e.g. `["read","write"]`; empty/NULL defaults to `["read"]`),
    `allowed_account_ids` (**JSON list, NULLABLE — NULL means ALL accounts, not
    none**, Gotcha 8), `expires_at` (**timestamp, NULLABLE — NULL means never
    expires**, Gotcha 8), `last_used_at`/`last_used_ip` (usage tracking). Module
    01 must expose a `validate_api_key(raw_key) -> CustomerApiKey | None` that
    does prefix lookup → hash compare → expiry check, and a
    `key_record.has_account_access(account_id) -> bool`.
- **Modules 03 / 04 / 05 / 06 / 09 (Intelligence + Ops):** each must expose its
  capability as a **plain importable callable** (a `_<name>_impl` or equivalent
  service function), NOT only as a decorated tool. If a capability exists only
  behind an `@mcp.tool` decorator, this layer cannot call it without the `.fn`
  workaround (Gotcha 2). State this expectation to those modules explicitly.
- **Feature toggles (Module 01):** a `feature_toggles.is_enabled(MCP_SERVER)`
  check; the server refuses all tools when off.

### Data Shapes

```
CustomerApiKey (owned by Module 01 — restated here for the fields this layer reads):
  key_prefix (string, indexed),
  key_hash (string — SHA-256 of raw key; raw key NEVER persisted),
  customer_id (FK, NOT NULL),
  scopes (JSON list of {"read","write","admin"}; NULL/empty → ["read"]),
  allowed_account_ids (JSON list, NULLABLE —
      NULL  => key may access ALL of the customer's accounts (default),
      [ids] => key is restricted to exactly those account_ids.
      Inverting this default locks every partner out or opens the whole
      portfolio — see Gotcha 8. Test the NULL case explicitly.),
  expires_at (timestamp, NULLABLE — NULL => never expires. Test NULL.),
  last_used_at (timestamp, nullable), last_used_ip (string, nullable)

Tool response envelope (EVERY tool return is a dict shaped by envelope()):
  scope (string, NOT NULL — one of:
      "account"        (data for one account_id),
      "portfolio"      (aggregated across all of a customer's accounts),
      "platform"       (cross-customer / catalog / debug, no single tenant),
      "node_traversal" (a context-graph path)),
  ...payload fields...,
  # present ONLY on responses carrying a dollar figure:
  arr_basis (string, e.g. "explicit" or "baseline_10m"),
  arr_basis_value (number — the ARR used for any scaling in this response)

Auth context (process/request state, not a DB row):
  _current_api_key_var  (contextvar, default "")  — set by HTTP middleware per request
  _current_session_id_var (contextvar, default "") — MCP session id
  _session_api_keys (dict: session_id -> raw_key) — survives async-task hops (Gotcha 5)
```

**Nullable-column rule (this module):** `allowed_account_ids` and `expires_at`
are both nullable and both have a NULL semantics that is the *permissive*
default (all accounts / never expires). Every enforcement path reading them must
handle NULL as that default, and an Acceptance Criterion must exercise the NULL
case — a restricted-key test passing proves nothing about the unrestricted
default (Gotcha 8).

## Engine vs. Config

**Engine (build once, an FDE rarely edits):**
- The server bootstrap: one `FastMCP` instance, the module-import registration
  loop, and the `__main__` `sys.modules` self-aliasing fix.
- The two transports and the HTTP Bearer middleware + `extract_api_key`
  contextvar/session propagation.
- The auth core: `validate_customer_key`, `validate_server_key`, `check_scope`,
  `_resolve_key`, `get_scoped_customer_id`, and the four public enforcers
  (`require_auth`, `require_account_auth`, `require_read_key`,
  `require_cross_customer_auth`).
- The `has_account_access` NULL-safe account restriction.
- The `envelope()` helper and the impl/tool separation convention.
- The registry parity check (`assert_registry_parity`) and deriving
  `tool_count` from the live registry.

**Config (an FDE fills in per client):**
- Which tool names are frictionless (`ONBOARDING_TOOLS`), which require write
  scope (`WRITE_TOOLS`), which are cross-customer (server-key-only).
- The scope hierarchy values if the client wants more/fewer tiers.
- `MCP_AUTH_REQUIRED` default, `MCP_SERVER_API_KEY`, the system-prompt markdown,
  transport/port, whether the query-param key fallback is enabled at all
  (Gotcha 6).
- The set of tools actually exposed (a dashboards-only engagement drops the
  wizard/graph tools entirely).

## Build Prompt

> Build the MCP tool layer that exposes this platform to external LLM agents.
> Six numbered pieces. Every helper is either defined below OR is an
> explicitly-named dependency hook whose contract Dependencies states —
> `module01_validate_api_key`, `module03_read_scores` (and the sibling
> `module0N_*` intelligence calls), `feature_toggles`/`FeatureToggle`, and the
> web framework (`Flask`, `db`, `Account`). There are no *undefined* helpers of
> this module's own. Follow the impl/tool separation in piece 4 for *every* tool
> without exception; it is the single thing that keeps tools reusable and
> auditable.
>
> Look at the origin system for patterns to follow, not reinvent:
> `kpi-dashboard/backend/mcp_server/cs_pulse_mcp_server.py` (server + core
> tools), `mcp_server/auth.py` (the auth core), `mcp_server/cs_pulse_*.py` (the
> per-domain tool modules). Use the `fastmcp` package (`FastMCP`, and
> `fastmcp.exceptions.ToolError`).
>
> 1. **Server instance + feature gate.** One module owns the single instance;
>    all tool modules import it.
>    ```
>    import os, logging
>    from fastmcp import FastMCP
>    from fastmcp.exceptions import ToolError
>
>    def load_system_prompt() -> str:
>        # Config: FDE ships the markdown; a missing file degrades to a default.
>        path = os.environ.get("CSPULSE_MCP_SYSTEM_PROMPT_PATH", "")
>        if path and os.path.isfile(path):
>            with open(path, encoding="utf-8") as f:
>                return f.read()
>        return ("CS Pulse MCP — health scoring, signal detection, context-graph "
>                "intelligence, revenue analytics. Every response carries a 'scope' "
>                "field; dollar figures carry 'arr_basis'/'arr_basis_value'.")
>
>    mcp = FastMCP("CS Pulse", instructions=load_system_prompt())
>
>    def check_mcp_enabled():
>        # Executable gate, not a comment: raises when the server toggle is off.
>        if not feature_toggles.is_enabled(FeatureToggle.MCP_SERVER):
>            raise ToolError("MCP Server is disabled. Enable via FEATURE_MCP_SERVER=true")
>    ```
>    A single minimal Flask app supplies DB context (do NOT import the full web
>    app — it drags in flask_login/flask_session). Cache it:
>    ```
>    _flask_app = None
>    def get_flask_app():
>        global _flask_app
>        if _flask_app is not None: return _flask_app
>        app = Flask(__name__)
>        url = os.environ.get("SQLALCHEMY_DATABASE_URI") or os.environ.get("DATABASE_URL")
>        if not url: raise ToolError("DATABASE_URL environment variable is required")
>        app.config["SQLALCHEMY_DATABASE_URI"] = url
>        db.init_app(app)
>        _flask_app = app
>        return app
>    ```
>
> 2. **Registration + the dual-instance fix (Gotcha 1).** Tool modules register
>    by import side-effect (`from server import mcp; @mcp.tool ...`). When the
>    server file is run directly it loads as `__main__`, so a submodule doing
>    `from server import mcp` would import a SECOND copy of the file with its own
>    `mcp`, and every tool would register onto the copy while the process serves
>    the original — exposing zero tools. Alias the module BEFORE importing any
>    tool module:
>    ```
>    TOOL_MODULES = ["cs_pulse_intelligence", "cs_pulse_revenue",
>        "cs_pulse_onboarding", "cs_pulse_admin", "cs_pulse_predictor",
>        "cs_pulse_executive", "cs_pulse_integrations", "cs_pulse_onboarding_agent"]
>
>    def register_tool_modules():
>        for name in TOOL_MODULES:
>            __import__(name)   # side-effect: @mcp.tool calls run
>
>    if __name__ == "__main__":
>        import sys
>        sys.modules["cs_pulse_mcp_server"] = sys.modules["__main__"]  # BEFORE imports
>        register_tool_modules()
>        # tool_count is DERIVED from the live registry, not a hardcoded number (Gotcha 3)
>        print(f"tools registered: {len(mcp._tool_manager._tools)}")
>        run_server(transport=sys.argv[1] if len(sys.argv) > 1 else "stdio")
>    else:
>        register_tool_modules()
>    ```
>    Assert after registration that the count is nonzero and matches the number
>    of `@mcp.tool` functions across the modules — a passing import that
>    registers nothing is the exact failure this fix prevents.
>
> 3. **The auth core.** Keys come from a request-scoped contextvar the HTTP
>    middleware sets (piece 6); stdio is a trusted local process. `extract_api_key`
>    must fall back to the session cache because FastMCP may run a tool in a new
>    asyncio task where the contextvar does not propagate (Gotcha 5):
>    ```
>    import contextvars    # os, logging already imported in piece 1
>    _current_api_key_var   = contextvars.ContextVar("_current_api_key",   default="")
>    _current_session_id_var= contextvars.ContextVar("_current_session_id",default="")
>    _session_api_keys: dict = {}          # session_id -> raw key
>
>    # Read env LIVE via accessors, not frozen into module constants at import —
>    # the test harness (and an ops kill switch) flip these per case, and a frozen
>    # constant makes a later setenv inert (Gotcha 9).
>    def auth_required() -> bool:
>        return os.environ.get("MCP_AUTH_REQUIRED", "true").lower() in ("true","1","yes")
>    def server_api_key() -> str:
>        return os.environ.get("MCP_SERVER_API_KEY", "")
>    if not auth_required():                 # import-time log = ops visibility only;
>        logging.getLogger(__name__).critical(  # enforcement reads auth_required() live
>            "MCP_AUTH_REQUIRED=false — API key enforcement DISABLED for ALL tools")
>
>    def extract_api_key():
>        k = _current_api_key_var.get("")
>        if k: return k
>        sid = _current_session_id_var.get("")
>        if sid and sid in _session_api_keys:    # session-id-keyed lookup only —
>            return _session_api_keys[sid]       # an identity-blind "last key"
>        # fallback (`list(_session_api_keys.values())[-1]`) hands one tenant's key
>        # to an anonymous, session-less caller: a cross-tenant leak (Gotcha 5). It
>        # is deliberately omitted here — absence is the enforcement.
>        return os.environ.get("CS_PULSE_API_KEY", "") or None
>
>    def validate_server_key(raw): return bool(server_api_key()) and raw == server_api_key()
>    def validate_customer_key(raw):        # delegates to Module 01's validator
>        if not raw: return None
>        return module01_validate_api_key(raw)   # prefix lookup + hash + expiry
>
>    def check_scope(key_record, required) -> bool:
>        scopes = key_record.scopes or ["read"]
>        if "admin" in scopes: return True
>        if required == "read" and "write" in scopes: return True
>        return required in scopes
>
>    def has_account_access(key_record, account_id) -> bool:
>        allowed = key_record.allowed_account_ids
>        if allowed is None:                 # NULL => ALL accounts (Gotcha 8)
>            return True
>        return int(account_id) in allowed
>    ```
>    The single resolver every enforcer funnels through. It returns the
>    `key_record` for a customer key, `None` for a trusted path (stdio, auth
>    disabled, or a valid server key), and RAISES otherwise:
>    ```
>    def resolve_key(customer_id, required_scope, api_key=None):
>        if not auth_required(): return None
>        if api_key is not None:
>            raw = api_key
>        else:
>            if os.environ.get("MCP_TRANSPORT", "stdio") != "http":
>                return None                 # stdio trusted
>            raw = extract_api_key()
>        if not raw:
>            raise ToolError("API key required. Pass Authorization: Bearer <key>.")
>        kr = validate_customer_key(raw)
>        if kr:
>            if kr.customer_id != int(customer_id):
>                raise ToolError(f"API key not authorized for customer {customer_id}.")
>            if not check_scope(kr, required_scope):
>                raise ToolError(f"API key lacks '{required_scope}' scope; has {kr.scopes}.")
>            return kr
>        if validate_server_key(raw):
>            return None                     # super-admin, cross-customer
>        raise ToolError("Invalid or expired API key.")
>    ```
>    The four public enforcers (each raises `ToolError` on failure; each is a
>    no-op on stdio via `resolve_key`):
>    ```
>    def require_auth(customer_id, required_scope="read", api_key=None):
>        resolve_key(customer_id, required_scope, api_key)
>
>    def require_account_auth(customer_id, account_id, required_scope="read", api_key=None):
>        kr = resolve_key(customer_id, required_scope, api_key)
>        if kr is None: return               # stdio or server key: unrestricted
>        if not has_account_access(kr, account_id):
>            raise ToolError(f"API key not authorized for account {account_id}; "
>                            f"restricted to {kr.allowed_account_ids}.")
>
>    def require_read_key(tool_name, api_key=None):
>        # For no-customer_id discovery tools (catalog/list). Closes the gap where
>        # an HTTP caller with NO key enumerates cross-tenant metadata.
>        if not auth_required(): return
>        if os.environ.get("MCP_TRANSPORT","stdio") != "http": return
>        raw = api_key if api_key is not None else extract_api_key()
>        if not raw: raise ToolError(f"API key required for '{tool_name}'.")
>        if validate_customer_key(raw) or validate_server_key(raw): return
>        raise ToolError("Invalid or expired API key.")
>
>    def require_cross_customer_auth(tool_name, api_key=None):
>        # Portfolio/cross-tenant tools: SERVER key only. The raise below
>        # rejects a valid customer-scoped key (tenant-enumeration guard).
>        if not auth_required(): return
>        if os.environ.get("MCP_TRANSPORT","stdio") != "http": return
>        raw = api_key if api_key is not None else extract_api_key()
>        if not raw: raise ToolError(f"'{tool_name}' requires a server-level key.")
>        if validate_server_key(raw): return
>        if validate_customer_key(raw):
>            raise ToolError(f"'{tool_name}' is cross-customer; a customer-scoped "
>                            f"key cannot call it. Use a server-level key.")
>        raise ToolError("Invalid or expired API key.")
>    ```
>    Tenant filtering for discovery tools that take no `customer_id`. An invalid
>    key must RAISE here, never return None — returning None means "unscoped =
>    show everything", which is a cross-tenant leak (Gotcha 4):
>    ```
>    def get_scoped_customer_id():
>        raw = extract_api_key()
>        if not raw: return None                       # stdio / no key: caller decides
>        if server_api_key() and raw == server_api_key(): return None  # super-admin
>        kr = validate_customer_key(raw)
>        if kr and kr.customer_id: return int(kr.customer_id)
>        raise PermissionError("Invalid or revoked API key")  # NOT None
>    ```
>
> 4. **The impl/tool separation — apply to EVERY tool (Gotcha 2).** A
>    `@mcp.tool`-decorated function is a `FunctionTool` object, not a plain
>    callable; another tool that calls it directly does not run the function.
>    So every tool's real work lives in a plain `_<name>_impl` that other code
>    (other tools, the in-app assistant, tests) calls directly. Ownership check
>    and envelope live in the impl:
>    ```
>    def validate_account_ownership(customer_id, account_id):
>        # (account_id, customer_id) together — an account_id-only lookup leaks
>        # across tenants (Gotcha 4).
>        acct = Account.query.filter_by(account_id=account_id,
>                                       customer_id=int(customer_id)).first()
>        if not acct:
>            raise ToolError(f"Account {account_id} not found for customer {customer_id}")
>        return acct
>
>    def envelope(scope, payload, arr_basis=None, arr_basis_value=None):
>        assert scope in ("account","portfolio","platform","node_traversal")
>        out = {"scope": scope, **payload}
>        if arr_basis is not None:
>            out["arr_basis"] = arr_basis
>            out["arr_basis_value"] = arr_basis_value
>        return out
>
>    def _get_account_health_impl(customer_id, account_id, api_key=None):
>        check_mcp_enabled()
>        require_account_auth(customer_id, account_id, "read", api_key)
>        with get_flask_app().app_context():
>            validate_account_ownership(customer_id, account_id)
>            # DELEGATE the scoring to Module 03 — this layer computes nothing:
>            health, pillars, status = module03_read_scores(account_id)
>            return envelope("account", {
>                "account_id": account_id, "health_score": round(health,1),
>                "status": status, "pillar_scores": pillars})
>
>    @mcp.tool
>    def get_account_health(customer_id: int, account_id: int) -> dict:
>        """Health score + pillar breakdown for one account.
>        customer_id is the TENANT; account_id is one of its accounts."""
>        return _get_account_health_impl(customer_id, account_id)
>    ```
>    When one tool needs another's result, call the impl, never the decorated
>    tool. If you only have the decorated object, reach its function via `.fn`:
>    ```
>    combined = _get_account_health_impl(cid, aid)     # preferred: the impl
>    # scorecard = get_csm_scorecard.fn(customer_id=cid)   # fallback: FunctionTool.fn
>    # scorecard = get_csm_scorecard(customer_id=cid)      # WRONG: does not run the function
>    ```
>
> 5. **Registry as single source of truth + parity (Gotcha 3).** The live
>    registry is authoritative; anything that needs "the list of tools" derives
>    it, never re-declares it. Provide a parity assertion for any secondary
>    consumer (in-app assistant, internal agent registry):
>    ```
>    def registered_tool_names() -> set:
>        return set(mcp._tool_manager._tools.keys())
>
>    def platform_instructions() -> dict:
>        require_read_key("get_platform_instructions")
>        return {"instructions": load_system_prompt(),
>                "tool_count": len(registered_tool_names())}   # derived, not 45
>
>    def assert_registry_parity(secondary_names: set):
>        live = registered_tool_names()
>        missing, extra = live - secondary_names, secondary_names - live
>        if missing or extra:
>            raise AssertionError(f"registry drift: missing={sorted(missing)} extra={sorted(extra)}")
>    ```
>
> 6. **HTTP Bearer middleware.** stdio needs none (trusted). For HTTP, wrap the
>    ASGI app: pull the token from `Authorization: Bearer`, cache it by
>    `mcp-session-id` (so a tool that runs in a spawned async task can still find
>    it, Gotcha 5), set the contextvars for the request, and reset them after.
>    A query-param fallback (`?api_key=`) is OPT-IN config and OFF by default —
>    URL-embedded keys leak into logs and history (Gotcha 6):
>    ```
>    class BearerAuthMiddleware:
>        def __init__(self, app, allow_query_param=False):
>            self.app = app; self.allow_query_param = allow_query_param
>        async def __call__(self, scope, receive, send):
>            if scope["type"] == "http":
>                headers = dict(scope.get("headers", []))
>                sid = headers.get(b"mcp-session-id", b"").decode()
>                auth = headers.get(b"authorization", b"").decode()
>                token = ""
>                if auth.startswith("Bearer "):
>                    token = auth[7:].strip()
>                    if sid: _session_api_keys[sid] = token
>                elif sid and sid in _session_api_keys:
>                    token = _session_api_keys[sid]
>                if not token and self.allow_query_param:
>                    from urllib.parse import parse_qs
>                    qs = parse_qs(scope.get("query_string", b"").decode())
>                    token = (qs.get("api_key",[""])[0] or qs.get("token",[""])[0]).strip()
>                    if token and sid: _session_api_keys[sid] = token
>                if token:
>                    t = _current_api_key_var.set(token)
>                    s = _current_session_id_var.set(sid) if sid else None
>                    try:    await self.app(scope, receive, send)
>                    finally:
>                        _current_api_key_var.reset(t)
>                        if s: _current_session_id_var.reset(s)
>                    return
>            await self.app(scope, receive, send)
>
>    def run_server(transport="stdio", host="0.0.0.0", port=8001,
>                   allow_query_param=False):
>        # Setting MCP_TRANSPORT is EXECUTABLE here — the enforcers gate the
>        # trusted-vs-enforced decision on it (Gotcha 7); leaving it to the
>        # ambient environment ships an HTTP server that skips auth.
>        if transport == "http":
>            os.environ["MCP_TRANSPORT"] = "http"
>            asgi = mcp.http_app()          # FastMCP's Streamable-HTTP ASGI app
>            wrapped = BearerAuthMiddleware(asgi, allow_query_param=allow_query_param)
>            import uvicorn
>            uvicorn.run(wrapped, host=host, port=port)
>        else:
>            os.environ["MCP_TRANSPORT"] = "stdio"
>            mcp.run(transport="stdio")
>    ```
>    `run_server` is the single entry to serving and is what piece 2's `__main__`
>    block calls; it sets `MCP_TRANSPORT` itself so no deployment can forget it.
>    `resolve_key` and the other enforcers gate their trusted-vs-enforced decision
>    on that variable — an HTTP server started any other way (with the variable
>    unset) takes the trusted stdio path and skips auth entirely (Gotcha 7). This
>    is the executable form of Gotcha 7's fix: the requirement is code here, not
>    prose in the Gotcha.

## Acceptance Criteria

- **Server registers all tools, and the count is derived.** After
  `register_tool_modules()`, `len(registered_tool_names())` equals the total
  number of `@mcp.tool` functions across all modules and is > 0.
  `platform_instructions()["tool_count"]` equals that same live number — assert
  they are equal, not that either equals a literal.
- **Dual-instance fix works.** Simulate the `__main__` path: load the server
  module under the name `__main__`, alias it into `sys.modules` under the
  canonical name, import a tool module that does `from <canonical> import mcp`,
  and assert the tool registered onto the *same* `mcp` the server serves
  (`registered_tool_names()` contains it). Then assert that WITHOUT the alias,
  the tool module gets a different `mcp` object (`mcp` identity differs) and the
  server's registry does NOT contain the tool — prove the bug the fix prevents.
- **A tool's `_impl` is directly callable; the decorated tool is not the
  function.** Assert `callable(_get_account_health_impl)` and that calling it
  returns an enveloped dict. Assert `type(get_account_health).__name__ ==
  "FunctionTool"` (or that `get_account_health` is not the raw function), and
  that `get_account_health.fn` is the underlying callable. A cross-tool call
  through the impl returns real data; document that calling the decorated object
  directly does not run the function.
- **Every tool response is enveloped.** For a representative account tool and a
  representative portfolio tool, assert `scope` is present and correct
  (`account` vs `portfolio`), and for a dollar-bearing response that both
  `arr_basis` and `arr_basis_value` are present. `envelope()` with an
  out-of-set scope raises.
- **Tenant isolation on account tools.** Given customer A owns account 1 and
  customer B owns account 2: `_get_account_health_impl(A, 2)` raises
  `ToolError` (ownership check), independent of auth. Assert the ownership query
  filters on `(account_id, customer_id)` together — an `account_id`-only lookup
  would return B's account to A.
- **Scope hierarchy.** With `MCP_TRANSPORT=http` and `MCP_AUTH_REQUIRED=true`:
  a `read`-scope key calls a read tool (ok) but a write tool raises; a `write`
  key calls both; an `admin` key calls everything. Assert each, driving real
  key records through `resolve_key`.
- **Customer isolation on keyed calls.** A customer-A key calling a tool with
  `customer_id=B` raises `ToolError` ("not authorized for customer B"), for
  every enforcer that takes a `customer_id`.
- **Cross-customer tools reject customer keys.** `require_cross_customer_auth`
  passes with the server key, raises with a *valid* customer key (not merely
  with an invalid one), and raises with no key.
- **`get_scoped_customer_id` fails closed.** No key → `None`; server key →
  `None`; valid customer key → that `customer_id`; **invalid/revoked key →
  raises `PermissionError`, never returns `None`.** Assert the invalid case
  explicitly — a `None` return there means "show all tenants".
- **Account restriction — both NULL and restricted (Gotcha 8).** A key with
  `allowed_account_ids = NULL` passes `require_account_auth` for *any* of its
  customer's accounts (NULL = all). A key with `allowed_account_ids = [1,3]`
  passes for 1 and 3 and raises for 2. Assert the NULL case — a restricted-key
  test passing says nothing about the default.
- **Expiry is delegated, not reimplemented here (Gotcha 8).** This module's auth
  core contains no `expires_at` read — `validate_customer_key` returns whatever
  `module01_validate_api_key` returns. Assert the *delegation contract*: when the
  Module-01 validator yields `None` for an expired key, every enforcer here
  rejects the call; when it yields a live record, they proceed. The NULL =
  never-expires and past-expiry semantics themselves are Module 01's Acceptance
  Criteria to prove — do not re-test them here (and do not add expiry logic to
  this layer to make a local test pass; that is the boundary violation).
- **stdio is trusted; http is enforced (Gotcha 7).** With `MCP_TRANSPORT`
  unset/stdio, `require_auth` with no key is a no-op (returns normally). With
  `MCP_TRANSPORT=http` and no key, the same call raises. A test suite that only
  runs the stdio path never exercises auth — the http path must be tested.
- **Kill switch logs and disables (Gotcha 7).** `MCP_AUTH_REQUIRED=false` makes
  every enforcer a no-op even over http; assert the module emits a CRITICAL log
  line at import when it is false.
- **Env is read live, not frozen (Gotcha 9).** After import with
  `MCP_AUTH_REQUIRED=true`, a test that sets `MCP_AUTH_REQUIRED=false` (via
  `monkeypatch.setenv`, no module reload) makes the next enforcer call a no-op —
  proving enforcement reads `auth_required()` live. Same for `server_api_key()`.
  A frozen module constant would fail this (the setenv is inert without a
  reload).
- **Async-task key propagation (Gotcha 5).** Set the token only in
  `_session_api_keys[sid]` with `_current_session_id_var` set to that same `sid`
  and `_current_api_key_var` empty (as if the contextvar were lost across an
  asyncio.Task hop), and assert `extract_api_key()` still returns it via the
  session-id-keyed fallback.
- **No cross-tenant key inheritance (Gotcha 5).** With one session
  authenticated (its key in `_session_api_keys` under its own `sid`), a NEW
  request with no `Authorization` header, no `mcp-session-id`, and both
  contextvars empty resolves to NO key: `extract_api_key()` returns `None`,
  `require_read_key` raises, and `get_scoped_customer_id()` returns `None`
  (or raises) — never the other session's `customer_id`. This is the leak the
  identity-blind "last session key" fallback caused; assert an anonymous,
  session-less caller cannot inherit an authenticated session's key even when
  one is cached.
- **Registry parity (Gotcha 3).** `assert_registry_parity(live_names)` passes;
  dropping one name from the secondary set raises `AssertionError` naming the
  missing tool; adding a phantom name raises naming the extra.
- **Feature gate.** With `MCP_SERVER` off, a tool's impl raises `ToolError`
  before doing any DB work.

## Reference Test Harness

1. **Registration + dual-instance** — an in-process harness that manipulates
   `sys.modules` to reproduce both the fixed and unfixed `__main__` paths and
   asserts registry membership and `mcp` identity in each. This is the one test
   that proves Gotcha 1; without the identity assertion a "tools registered"
   check passes even against the bug if the test imports the module the normal
   way.
2. **Auth matrix** — a fake `CustomerApiKey` record factory (scopes,
   `allowed_account_ids`, `expires_at`) and a driver that sets
   `MCP_TRANSPORT`/`MCP_AUTH_REQUIRED` per case. Cover the full grid:
   {stdio, http} × {no key, invalid key, customer key wrong tenant, customer
   key right tenant, server key} × {read tool, write tool, cross-customer tool,
   account-restricted tool}. Every cell asserts pass-or-raise, not just "no
   exception".
3. **NULL-case suite** — `allowed_account_ids=NULL` and `scopes=NULL` each on
   their own test, each asserting the permissive default, plus their non-NULL
   counterparts. Passing the restricted path proves nothing about NULL.
   (`expires_at=NULL` is Module 01's validator to test; here assert only that
   this layer delegates and re-implements no expiry logic — see the
   delegation AC.)
3b. **Cross-tenant leak guard (Gotcha 5)** — cache session A's key under sid A,
   then issue a session-less anonymous request (no header, no sid, empty
   contextvars) and assert `extract_api_key()` is `None` and
   `get_scoped_customer_id()` does not return A's `customer_id`. Then a mutation
   check: add the identity-blind `list(_session_api_keys.values())[-1]` fallback
   back into `extract_api_key` and assert this test FLIPS to a leak — proving
   the guard is load-bearing, not incidental.
4. **`get_scoped_customer_id` fail-closed** — the four cases, with the
   invalid-key case asserting `PermissionError` is raised (fail closed), not a
   `None` return.
5. **Impl/FunctionTool** — assert `.fn` reaches the callable, the impl is
   directly callable, and a cross-tool call via the impl returns data. Then a
   mutation check: rewrite one tool to call a sibling *decorated* tool directly
   and assert the behavior breaks (no data / TypeError) — proving the convention
   is load-bearing, not cosmetic.
6. **Envelope** — every tool under test returns a `scope`; the helper rejects an
   unknown scope; dollar responses carry `arr_basis`+`arr_basis_value`.
7. **Registry parity** — pass, missing-name, extra-name.

## Known Gotchas

**1. Running the server directly registers every tool onto a phantom second
instance, exposing zero tools**
*Symptom:* Started over stdio or http, the server comes up clean but an agent
sees no tools (or only the handful defined in the entrypoint file). No error —
the import "succeeded."
*Root cause:* The entrypoint file is loaded by Python as `__main__`. Each tool
module does `from cs_pulse_mcp_server import mcp`, which Python resolves by
importing the file *again* under its real name — a second module object with its
own, separate `FastMCP` instance. `@mcp.tool` decorators in the tool modules
register onto that second instance; the process serves the first. Two live
`mcp` objects, tools on the wrong one.
*Fix:* Before importing any tool module in the `__main__` block,
`sys.modules["cs_pulse_mcp_server"] = sys.modules["__main__"]`, so the
submodule imports resolve to the running instance. Assert post-registration
that `len(mcp._tool_manager._tools) > 0`. Cited: the fix and its comment live in
`cs_pulse_mcp_server.py:913-921`.

**2. A `@mcp.tool`-decorated function is not callable as a function**
*Symptom:* One tool calls another (`x = get_csm_scorecard(customer_id=cid)`) and
gets a `FunctionTool` object or a TypeError instead of the result — or the
in-app "Ask AI" assistant, reusing the same tools, silently gets nothing back.
*Root cause:* `@mcp.tool` replaces the function with a `FunctionTool` wrapper
object. Calling it is not calling the underlying function. Three inconsistent
workarounds grew in the origin system — `_process_data_impl()` (a separate plain
callable, the right pattern), `get_csm_scorecard.fn(...)` (reach into the
wrapper), and `getattr(complete_onboarding, "fn", complete_onboarding)`
(defensive) — which is itself evidence the trap is easy to hit.
*Fix:* Put every tool's logic in a plain `_<name>_impl(...)` that is the single
source of truth; the decorated tool is a one-line wrapper. Callers use the impl.
`.fn` is only a fallback when you hold a decorated object you didn't define.
Cited: `cs_pulse_onboarding.py:1089` (`_process_data_impl`) and `:2254` (the tool
delegating to it); `cs_pulse_admin.py:1351` (`.fn`); commits `a839c1a3e`
("invoke MCP tools via .fn for VPCS scorecard/capacity") and `4cc4f561c`
("route Ask AI through real MCP tool implementations").

**3. Multiple hand-maintained tool lists drift out of sync**
*Symptom:* A tool exists in the MCP server but the in-app assistant can't call
it (or calls a stale local reimplementation); a "45 tools" banner while the
server actually has ~69; a write tool that isn't in the write-scope set and so
is callable with a read key.
*Root cause:* The same conceptual list is written down in five places that don't
reference each other: the live `@mcp.tool` registry, `agent_tool_registry.py`
(explicitly "NOT MCP — internal platform tools"), `ask_ai_tools.py` (the in-app
assistant), `onboarding_tool_registry.py` (`ONBOARDING_TOOLS`), and auth's
hardcoded `WRITE_TOOLS`. Plus a literal `"tool_count": 45` and a docstring
saying `~69`. Each is updated by hand.
*Fix:* Treat `mcp._tool_manager._tools` as the single source of truth; derive
`tool_count` from it; make secondary consumers derive their list from it and
guard with a parity assertion in the test suite. Cited: the origin system has
`tests/test_ask_ai_mcp_parity.py` for exactly this, plus the standing backlog
item `backlog_auto_derive_ask_ai_tools_from_mcp.md`; the `45` literal is at
`cs_pulse_mcp_server.py:377`, the `~69` docstring at `:30`.

**4. Auth and tenant isolation are per-tool opt-in, so one forgetful tool is a
data leak**
*Symptom:* A newly added tool returns another tenant's accounts; or a
discovery tool with no `customer_id` enumerates every customer to an
unauthenticated HTTP caller; or a tool crashes inside the auth call because its
signature never took the `customer_id` the enforcer needs.
*Root cause:* There is no framework-level auth boundary — each tool must itself
call the right enforcer (`require_auth` / `require_account_auth` /
`require_read_key` / `require_cross_customer_auth`) and, for account tools, do
the `(account_id, customer_id)` ownership query. An `account_id`-only lookup
returns any tenant's account. `get_scoped_customer_id` returning `None` on an
invalid key means "unscoped → show all". A tool whose parameters omit
`customer_id` can't be authorized at all.
*Fix:* A fixed enforcement recipe per tool tier (account tools →
`require_account_auth` + ownership query; portfolio → `require_auth`; no-tenant
discovery → `require_read_key` + `get_scoped_customer_id` filtering;
cross-customer → `require_cross_customer_auth`), `get_scoped_customer_id` that
*raises* on an invalid key, and ownership queries keyed on both ids. Cited: the
`require_read_key` / `require_cross_customer_auth` enforcers were added
`Aug 4 2026` as "audit C-10 remediation" (`auth.py:372,405`; commit
`022a9d377`, "close MCP tool auth gaps (C-10)"); a tool crashing because it
lacked `customer_id` is commit `24afb74ed` ("add customer_id to
get_account_nrr_forecast — closes auth crash").

**5. The session-key cache that fixes async-task propagation becomes a
cross-tenant leak if it falls back to "any session's key"**
*Symptom:* Two failure modes from the same cache. (a) HTTP auth works for some
calls and fails ("API key required") for others with no pattern, under
concurrency. (b) Far worse: an anonymous, session-less request — no
`Authorization` header, no `mcp-session-id` — is silently authenticated *as some
other tenant*, and a discovery tool (`require_read_key` +
`get_scoped_customer_id`) scopes it to that tenant's data.
*Root cause:* The middleware stores the token in a `contextvars.ContextVar`,
which is copied into tasks at creation — but if FastMCP runs the tool in a task
spawned before the var was set, `contextvar.get()` is empty and the request
looks unauthenticated (mode a). The tempting fix is a "last resort" fallback
`return list(_session_api_keys.values())[-1]` — but `_session_api_keys` is a
process-global `session_id → key` map, so that line hands whatever key was cached
last to a caller with no identity at all (mode b). The comment excusing it —
"only 1 session typically active" — is false the moment two tenants connect.
*Fix:* Cache by `mcp-session-id` and have `extract_api_key` fall back to the
session cache **keyed by the current session id only**, then to env — with no
identity-blind `[-1]`. Test both: session-id-keyed propagation works with the
contextvar empty, AND an anonymous request with another session cached resolves
to no key. Cited: the origin `auth.py:166-178` shipped exactly the identity-blind
`list(_session_api_keys.values())[-1]` fallback (`:176-178`, "last resort — only
1 session typically active") — a real latent multi-tenant leak under concurrent
HTTP sessions, and the severe defect this module's adversarial validation
surfaced (spec-only fresh-agent rebuild, 2026-08-07).

**6. `?api_key=` in the URL leaks the key into logs, history, and screen shares**
*Symptom:* Long-lived customer keys turn up in nginx access logs, browser
history, and shared screenshots.
*Root cause:* A convenience fallback for connectors that only accept a single
URL string accepts the key as a query parameter; query strings are logged and
retained everywhere.
*Fix:* Keep it OFF by default (`allow_query_param=False`), enable only for
demo/dev keys, and rotate those keys after. Never accept a production key this
way. Cited: the origin fallback and its own warning comment,
`cs_pulse_mcp_server.py:993-1008` ("Apr 27 2026: query-param fallback... use
only for demo/dev keys; rotate post-demo").

**7. stdio is trusted, so auth is only real over HTTP — and only when
`MCP_TRANSPORT=http` is set**
*Symptom:* Auth "passes" in every local test yet the deployed HTTP server
enforces nothing; or the reverse — a correct key is rejected locally.
*Root cause:* Every enforcer treats a non-`http` `MCP_TRANSPORT` as a trusted
local process and returns without checking. That is correct for stdio (Claude
Desktop/Code run as a local subprocess) but means (a) a test suite that never
sets `MCP_TRANSPORT=http` never exercises a single auth branch, and (b) an HTTP
deployment that forgets to set it takes the trusted path and skips auth for real
traffic. Separately, `MCP_AUTH_REQUIRED=false` disables everything by design.
*Fix:* Set `MCP_TRANSPORT=http` in the HTTP startup path (not left to the
environment), test the http branch explicitly, and emit a CRITICAL log when
`MCP_AUTH_REQUIRED` is false so a misconfigured production server is loud. Cited:
the transport gate at `auth.py:113-115,314-316,388-390`; the kill-switch log at
`auth.py:51-57`.

**8. `allowed_account_ids = NULL` means "all accounts", not "no accounts"**
*Symptom:* Either every partner key is locked out of everything, or a restricted
key can read the whole portfolio — depending on which way the NULL got
misread.
*Root cause:* `allowed_account_ids` is nullable with a *permissive* default
(NULL = unrestricted). Code written against the restricted path treats absence
as denial (or the inverse), and single-tenant tests never exercise the NULL
default. The sibling column `expires_at` has the same shape (NULL = never
expires) but its enforcement lives in Module 01's validator, not here.
*Fix:* `has_account_access` returns `True` on NULL — own it here, test it here.
Keep expiry semantics in Module 01 (this layer only asserts it *delegates*, per
the delegation AC — adding expiry logic here to satisfy a local test is the
boundary violation, not the fix). Test the `allowed_account_ids` NULL case as
its own Acceptance Criterion — the non-NULL path passing proves nothing about
the default that most keys actually use. This is Module 05/06's nullable-column
lesson (a NULL path silently inverting an invariant while every non-NULL test
passes) recurring at the auth layer.

**9. Env vars frozen into module constants at import make a later `setenv`
inert — including a security kill switch**
*Symptom:* A test flips `MCP_AUTH_REQUIRED=false` (or an ops runbook flips it for
a break-glass window) and nothing changes; or a matrix suite believes it is
testing "auth on" while the process actually has it off. One env var
(`MCP_TRANSPORT`) responds to changes and the other (`MCP_AUTH_REQUIRED`) does
not, for no visible reason.
*Root cause:* `MCP_AUTH_REQUIRED` and `MCP_SERVER_API_KEY` were read once at
import into module-level constants, while `MCP_TRANSPORT` is read live inside
each enforcer. So a `monkeypatch.setenv` (or a live toggle) moves one and not the
others — and the doc's own Reference Test Harness promises "a driver that sets
`MCP_TRANSPORT`/`MCP_AUTH_REQUIRED` per case," which is only true for one of them.
*Fix:* Read both through live accessors (`auth_required()`, `server_api_key()`)
that hit `os.environ` on each call; keep the import-time CRITICAL log for ops
visibility while enforcement reads the value live. Then a `setenv` (test or ops)
takes effect with no module reload. Surfaced by this module's adversarial
validation (2026-08-07).

## Provenance

Origin files in the reference system:
`kpi-dashboard/backend/mcp_server/cs_pulse_mcp_server.py` (the single `FastMCP`
instance, the `__main__` dual-instance fix at `:913-921`, the HTTP Bearer
middleware and query-param fallback at `:943-1024`, core tools + `envelope`-style
`scope`/`arr_basis` responses, `_validate_account_ownership` at `:154`,
`get_scoped_customer_id` usage, the `45`/`~69` count drift at `:377`/`:30`);
`kpi-dashboard/backend/mcp_server/auth.py` (the entire auth core — two-tier keys,
`check_scope`, `resolve_key`/`_resolve_key`, the four enforcers,
`has_account_access`, contextvar+session propagation, `MCP_TRANSPORT`/
`MCP_AUTH_REQUIRED` gates, C-10 additions at `:372`/`:405`);
`kpi-dashboard/backend/mcp_server/cs_pulse_onboarding.py` (`_process_data_impl`
at `:1089`, tool→impl delegation at `:2254`, `.fn`/`getattr` workarounds at
`:425`); `kpi-dashboard/backend/mcp_server/cs_pulse_admin.py:1351` (`.fn`);
`kpi-dashboard/backend/agent_tool_registry.py`,
`kpi-dashboard/backend/ask_ai_tools.py`,
`kpi-dashboard/backend/mcp_server/onboarding_tool_registry.py` (the three
drifting registries); `kpi-dashboard/backend/tests/test_ask_ai_mcp_parity.py`
(the existing parity guard).

Commit provenance for the Gotchas: `a839c1a3e` (`.fn` for VPCS), `4cc4f561c`
(route Ask AI through real MCP impls), `022a9d377` (close MCP tool auth gaps
C-10), `24afb74ed` (missing `customer_id` → auth crash), `f27625fbb`
(get_team_capacity cold-start). Authored 2026-08-07 against the code at HEAD
`523be054f`, and validated the same day (see Validation Note).

## Validation Note

Validated 2026-08-07. A fresh agent, given ONLY this spec in isolation, built a
self-contained implementation (a fake `FastMCP`/`FunctionTool`, in-memory
`CustomerApiKey`/`Account` records, faked Module 01/03 hooks) and wrote pytest
tests that execute the spec's literal pseudocode. Result: **19 passed (15
acceptance criteria + 4 defect proofs)**, and **four real defects — two SEVERE**
— each demonstrated by a test that runs the spec-as-written and then the
corrected version. Sixth module in a row to hit multiple documented failure
shapes.

Notably, the two loudly-flagged NULL traps (`allowed_account_ids` NULL=all,
`expires_at` NULL=never) were **decoys** — the pseudocode handled both correctly
and both ACs passed. The real defects were in what the Build Prompt left
undefined and in one fallback the spec actively endorsed:

- **Defect 1 — SEVERE (shapes a+b+d).** The `__main__` entrypoint called
  `run_server(transport="http")`, but `run_server` was **referenced-but-never-
  defined** and nothing executed `os.environ["MCP_TRANSPORT"]="http"`. Every
  enforcer gates trusted-vs-enforced on `MCP_TRANSPORT != "http"`, so the natural
  `run_server` an FDE writes ships an HTTP server on which **auth is skipped for
  all traffic** — exactly Gotcha 7(b), whose fix lived only in Gotcha prose, not
  code. *Fixed:* `run_server` is now defined in Build Prompt piece 6 and sets
  `MCP_TRANSPORT` as executable code; the intro's "no undefined helpers" claim
  was corrected to enumerate the legitimate dependency hooks.
- **Defect 2 — SEVERE (shape a).** `extract_api_key`'s last-resort fallback
  `return list(_session_api_keys.values())[-1]` — copied verbatim from the origin
  and endorsed in the original Gotcha 5 — ignores session identity: once any
  session authenticates, a **new anonymous request** (no header, no session-id,
  empty contextvar) inherits that other tenant's key, and via
  `require_read_key`+`get_scoped_customer_id` gets scoped to a different
  customer's data. The proof scoped an anonymous caller to customer 100. This is
  the "leak one client's data to another" outcome the Purpose calls worst-
  possible. *Fixed:* the identity-blind fallback is removed from Build Prompt
  piece 3; `extract_api_key` now falls back only to the session-id-keyed cache
  then env; Gotcha 5 was rewritten around the leak; a new AC and harness item 3b
  (with a mutation check) prove an anonymous caller cannot inherit a cached key.
  **This bug is live in the origin `auth.py:176-178`** — see the flag below.
- **Defect 3 — MODERATE (shape c).** The "Expiry NULL case" AC required *this*
  module to prove NULL/past-expiry behavior, but Boundary assigns expiry to
  Module 01 and `validate_customer_key` merely delegates — the behavior had no
  owning code here. *Fixed:* the AC now tests the *delegation contract*
  (Module-01 validator returns `None` → this layer rejects), and the undefined
  helpers `run_server`/`load_system_prompt` are now defined.
- **Defect 4 — MINOR (shapes a+d).** `MCP_AUTH_REQUIRED`/`MCP_SERVER_API_KEY`
  were frozen into module constants at import while `MCP_TRANSPORT` was read
  live, so the Reference Test Harness's "sets `MCP_AUTH_REQUIRED` per case"
  driver was silently inert for that var (a suite could believe auth was on while
  it was off). *Fixed:* both now read live via `auth_required()`/`server_api_key()`
  accessors; new Gotcha 9 and a new AC cover it.

**Library-level note:** as with modules 05/06, the loudest, most-defended risks
(the NULL columns) were fine; the defects hid in an undefined helper, an
endorsed-but-wrong fallback, and a boundary the ACs didn't respect. The "prose
in a Gotcha instead of executable code in the Build Prompt" shape (Gotcha 7's fix
existing only as prose) recurred again — treat every Gotcha whose fix is a
requirement as needing a matching Build Prompt line, not just a warning.
