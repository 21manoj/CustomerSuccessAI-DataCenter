#!/usr/bin/env python3
"""
Tests for the Predictor v3 MCP tools — auth-path contract.

Regression coverage for the May 2026 schema/auth-wrapper mismatch on
`get_account_nrr_forecast`:

The MCP tool's `@mcp.tool` schema only declared `account_id` + `horizon`,
but the server-side wrapper `_require_account_auth(customer_id, account_id)`
requires BOTH `customer_id` and `account_id`. The MCP transport therefore
never passed `customer_id` and the auth call crashed with:

    _require_account_auth() missing 1 required positional argument: 'account_id'

The fix: add `customer_id: int` as the first required arg on the tool —
matching the convention used by every other account-scoped MCP tool
(`get_account_health`, `get_revenue_at_risk`, `get_crm_account_data`,
`get_outcome_roi_story`).

Run: python3 -m pytest tests/test_predictor_mcp_auth.py -v
"""

import inspect
import os
import sys
import types

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)
# mcp_server submodules use sibling imports (`from cs_pulse_mcp_server import ...`),
# so the mcp_server directory itself must be on sys.path.
sys.path.insert(0, os.path.join(BACKEND_DIR, 'mcp_server'))


def _install_fastmcp_stub():
    """Install a minimal fastmcp stub so cs_pulse_mcp_server can import
    in environments without fastmcp installed (local dev, fast CI).

    The decorator wraps the original function on `.fn`, mirroring
    fastmcp's real API — that's the attribute Ask AI uses via
    `getattr(_t, 'fn', _t)` to call the underlying impl.
    """
    if 'fastmcp' in sys.modules:
        return

    class _Tool:
        def __init__(self, fn):
            self.fn = fn

        def __call__(self, *args, **kwargs):
            return self.fn(*args, **kwargs)

    class _FastMCP:
        def __init__(self, *a, **kw):
            pass

        def tool(self, fn=None, **opts):
            if fn is None:
                return lambda f: _Tool(f)
            return _Tool(fn)

        def resource(self, *a, **kw):
            def deco(f):
                return f
            return deco

        def prompt(self, *a, **kw):
            def deco(f):
                return f
            return deco

    fm = types.ModuleType('fastmcp')
    fm.FastMCP = _FastMCP
    sys.modules['fastmcp'] = fm

    fm_exc = types.ModuleType('fastmcp.exceptions')

    class _ToolError(Exception):
        pass

    fm_exc.ToolError = _ToolError
    sys.modules['fastmcp.exceptions'] = fm_exc


_install_fastmcp_stub()


# ---------------------------------------------------------------------------
# Signature contract: the @mcp.tool schema MUST match _require_account_auth.
# ---------------------------------------------------------------------------


class TestAccountNrrForecastSchema:
    """The tool's declared parameters must include customer_id + account_id."""

    @pytest.fixture(autouse=True)
    def load_tool(self):
        from mcp_server import cs_pulse_predictor
        self.tool = cs_pulse_predictor.get_account_nrr_forecast
        # fastmcp wraps the original function on `.fn`; unwrap so inspect
        # sees the real signature.
        self.fn = getattr(self.tool, 'fn', self.tool)
        self.sig = inspect.signature(self.fn)
        self.params = self.sig.parameters

    def test_customer_id_is_a_parameter(self):
        assert 'customer_id' in self.params, (
            'get_account_nrr_forecast must declare customer_id — required '
            'by _require_account_auth(customer_id, account_id). Without it '
            'the MCP transport never passes customer_id and the auth call '
            'crashes.'
        )

    def test_account_id_is_a_parameter(self):
        assert 'account_id' in self.params

    def test_horizon_is_a_parameter(self):
        assert 'horizon' in self.params

    def test_customer_id_is_required(self):
        assert self.params['customer_id'].default is inspect.Parameter.empty, (
            'customer_id must be a required arg (no default) — matches '
            'get_account_health, get_revenue_at_risk, get_crm_account_data.'
        )

    def test_account_id_is_required(self):
        assert self.params['account_id'].default is inspect.Parameter.empty

    def test_horizon_has_default_12mo(self):
        assert self.params['horizon'].default == '12mo'

    def test_customer_id_precedes_account_id(self):
        """Convention: customer_id is the first positional arg, then account_id."""
        names = list(self.params.keys())
        assert names.index('customer_id') < names.index('account_id'), (
            f'Param order should be (customer_id, account_id, ...) — got {names}'
        )

    def test_signature_matches_other_account_scoped_tools(self):
        """Sanity: same shape as the existing account-scoped MCP tools."""
        from mcp_server import cs_pulse_mcp_server
        from mcp_server import cs_pulse_intelligence

        peer_tools = [
            cs_pulse_mcp_server.get_account_health,
            cs_pulse_intelligence.get_revenue_at_risk,
        ]
        for peer in peer_tools:
            peer_fn = getattr(peer, 'fn', peer)
            peer_params = list(inspect.signature(peer_fn).parameters.keys())
            assert peer_params[:2] == ['customer_id', 'account_id'], (
                f'Peer {peer_fn.__name__} param prefix unexpected: {peer_params}'
            )

        ours = list(self.params.keys())
        assert ours[:2] == ['customer_id', 'account_id']


# ---------------------------------------------------------------------------
# Auth-path: the tool MUST call _require_account_auth(customer_id, account_id).
# ---------------------------------------------------------------------------


class TestAccountNrrForecastAuthPath:
    """The tool's body must invoke _require_account_auth with both args."""

    def test_calls_require_account_auth_with_both_args(self):
        """Without monkey-patching the whole Flask stack, exercise the auth
        path by injecting fakes for the two helpers the tool reaches into.

        We verify:
          - `_require_account_auth` is called with `(customer_id, account_id)`,
            in that order — matching its signature.
          - `_validate_account_ownership` is called with the same pair so
            tenant isolation is enforced before inference.
          - When the auth helpers raise (e.g. wrong tenant), the tool
            surfaces the error and never invokes the Predictor.
        """
        from mcp_server import cs_pulse_predictor
        from mcp_server.cs_pulse_mcp_server import ToolError

        calls = {
            'auth': [],
            'validate': [],
            'predict': 0,
        }

        def fake_require_account_auth(customer_id, account_id, *a, **kw):
            calls['auth'].append((customer_id, account_id))

        def fake_validate_ownership(customer_id, account_id):
            calls['validate'].append((customer_id, account_id))
            return types.SimpleNamespace(account_id=account_id, customer_id=customer_id)

        class _NoOpAppContext:
            def __enter__(self): return self
            def __exit__(self, *a): return False

        class _FakeApp:
            def app_context(self): return _NoOpAppContext()

        def fake_predict(account_id, horizon='12mo'):
            calls['predict'] += 1
            return {
                'account_id': account_id,
                'horizon': horizon,
                'expected_nrr': {'point': 0.97, 'lower_90': 0.93, 'upper_90': 1.02},
            }

        # Monkey-patch the helpers the tool imports from cs_pulse_mcp_server.
        orig_auth = cs_pulse_predictor._require_account_auth
        orig_validate = cs_pulse_predictor._validate_account_ownership
        orig_app = cs_pulse_predictor._get_flask_app
        orig_check = cs_pulse_predictor._check_mcp_enabled
        cs_pulse_predictor._require_account_auth = fake_require_account_auth
        cs_pulse_predictor._validate_account_ownership = fake_validate_ownership
        cs_pulse_predictor._get_flask_app = lambda: _FakeApp()
        cs_pulse_predictor._check_mcp_enabled = lambda: None

        # Stub the predictor.inference module before the tool tries to import.
        pred_mod = types.ModuleType('predictor.inference')
        pred_mod.predict_for_account_id = fake_predict
        pred_pkg = types.ModuleType('predictor')
        pred_pkg.inference = pred_mod
        prior_pkg = sys.modules.get('predictor')
        prior_mod = sys.modules.get('predictor.inference')
        sys.modules['predictor'] = pred_pkg
        sys.modules['predictor.inference'] = pred_mod

        try:
            fn = cs_pulse_predictor.get_account_nrr_forecast.fn
            result = fn(customer_id=334, account_id=3237, horizon='12mo')

            assert calls['auth'] == [(334, 3237)], (
                f'_require_account_auth must be called with (customer_id, '
                f'account_id) in that order — got {calls["auth"]!r}'
            )
            assert calls['validate'] == [(334, 3237)], (
                f'_validate_account_ownership must be called with (customer_id, '
                f'account_id) — got {calls["validate"]!r}'
            )
            assert calls['predict'] == 1
            assert result['account_id'] == 3237
            assert result['horizon'] == '12mo'

            # And: if auth fails, the predictor is NEVER called.
            calls['auth'].clear()
            calls['validate'].clear()
            calls['predict'] = 0

            def deny_auth(customer_id, account_id, *a, **kw):
                raise ToolError('denied')

            cs_pulse_predictor._require_account_auth = deny_auth
            with pytest.raises(ToolError, match='denied'):
                fn(customer_id=334, account_id=3237, horizon='12mo')
            assert calls['predict'] == 0, (
                'Auth failure must short-circuit before inference.'
            )

        finally:
            cs_pulse_predictor._require_account_auth = orig_auth
            cs_pulse_predictor._validate_account_ownership = orig_validate
            cs_pulse_predictor._get_flask_app = orig_app
            cs_pulse_predictor._check_mcp_enabled = orig_check
            if prior_pkg is not None:
                sys.modules['predictor'] = prior_pkg
            else:
                sys.modules.pop('predictor', None)
            if prior_mod is not None:
                sys.modules['predictor.inference'] = prior_mod
            else:
                sys.modules.pop('predictor.inference', None)

    def test_invalid_horizon_rejected(self):
        """Schema enforces horizon ∈ {'renewal', '12mo'}."""
        from mcp_server import cs_pulse_predictor
        from mcp_server.cs_pulse_mcp_server import ToolError

        class _NoOpAppContext:
            def __enter__(self): return self
            def __exit__(self, *a): return False

        class _FakeApp:
            def app_context(self): return _NoOpAppContext()

        orig = (
            cs_pulse_predictor._require_account_auth,
            cs_pulse_predictor._validate_account_ownership,
            cs_pulse_predictor._get_flask_app,
            cs_pulse_predictor._check_mcp_enabled,
        )
        cs_pulse_predictor._require_account_auth = lambda *a, **kw: None
        cs_pulse_predictor._validate_account_ownership = lambda *a, **kw: None
        cs_pulse_predictor._get_flask_app = lambda: _FakeApp()
        cs_pulse_predictor._check_mcp_enabled = lambda: None

        # Stub predictor.inference so the import succeeds.
        pred_mod = types.ModuleType('predictor.inference')
        pred_mod.predict_for_account_id = lambda **kw: {}
        pred_pkg = types.ModuleType('predictor')
        pred_pkg.inference = pred_mod
        sys.modules['predictor'] = pred_pkg
        sys.modules['predictor.inference'] = pred_mod

        try:
            fn = cs_pulse_predictor.get_account_nrr_forecast.fn
            with pytest.raises(ToolError, match='horizon'):
                fn(customer_id=334, account_id=3237, horizon='nonsense')
        finally:
            (
                cs_pulse_predictor._require_account_auth,
                cs_pulse_predictor._validate_account_ownership,
                cs_pulse_predictor._get_flask_app,
                cs_pulse_predictor._check_mcp_enabled,
            ) = orig
            sys.modules.pop('predictor', None)
            sys.modules.pop('predictor.inference', None)


# ---------------------------------------------------------------------------
# Ask AI dispatcher: both branches forward customer_id to the tool.
# ---------------------------------------------------------------------------


class TestAskAiDispatchPassesCustomerId:
    """Source-level check that ask_ai_tools.py dispatches with customer_id."""

    @pytest.fixture(autouse=True)
    def load_source(self):
        path = os.path.join(BACKEND_DIR, 'ask_ai_tools.py')
        with open(path) as f:
            self.source = f.read()

    def test_input_schema_requires_customer_id(self):
        # The Ask AI tool schema must advertise customer_id so the LLM-side
        # contract matches the MCP tool's required args.
        import re
        block_start = self.source.index('"name": "get_account_nrr_forecast"')
        # Grab a generous slice — the schema spans ~20 lines.
        block = self.source[block_start:block_start + 1500]
        assert '"customer_id"' in block, (
            'Ask AI input_schema must declare customer_id as a property.'
        )
        # `required` is a JSON list — match flexibly so whitespace / quote
        # variations don't break the test.
        required_match = re.search(
            r'"required"\s*:\s*\[([^\]]+)\]', block, re.DOTALL,
        )
        assert required_match, 'required list not found in input_schema'
        required = required_match.group(1)
        assert 'customer_id' in required, (
            f'customer_id must be in required[] — got {required!r}'
        )
        assert 'account_id' in required, (
            f'account_id must be in required[] — got {required!r}'
        )

    def test_mcp_dispatch_passes_customer_id(self):
        # Branch 1: MCP-import path.
        marker = "elif tool_name == 'get_account_nrr_forecast':"
        first = self.source.index(marker)
        chunk = self.source[first:first + 600]
        assert 'customer_id=customer_id' in chunk, (
            'Ask AI MCP-dispatch branch must forward customer_id to the tool '
            "(otherwise it falls back to the same `_require_account_auth` "
            'crash that motivated this fix).'
        )

    def test_direct_dispatch_validates_tenant(self):
        # Branch 2: direct-call path bypasses the MCP wrapper, so it must
        # do its own customer ↔ account ownership check.
        marker = "elif tool_name == 'get_account_nrr_forecast':"
        second_start = self.source.index(marker, self.source.index(marker) + 1)
        chunk = self.source[second_start:second_start + 1200]
        assert 'customer_id=int(customer_id)' in chunk, (
            'Direct-dispatch branch must validate tenant ownership using '
            'the session-scoped customer_id.'
        )
