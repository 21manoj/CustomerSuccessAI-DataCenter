#!/usr/bin/env python3
"""
MCP Server Security & RBAC Test Suite
======================================
Tests MCP server tools with the new RBAC system:
1. Core tools work with FEATURE_MCP_SERVER=true
2. _validate_account_ownership enforces tenant isolation
3. RBAC-aware account filtering respects allowed_account_ids
4. Contractor users get restricted access
5. Feature toggle gating works

Run from backend directory:
  FEATURE_MCP_SERVER=true python3 tests/test_mcp_security_rbac.py
"""

import sys
import os
import traceback

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Set env vars
if not os.environ.get('DATABASE_URL'):
    os.environ['DATABASE_URL'] = 'postgresql://dcuser:dcpass123@localhost:5432/cs_pulse_datacenter'
os.environ['FEATURE_MCP_SERVER'] = 'true'

# ── Stub out fastmcp so we can import cs_pulse_mcp_server on Python 3.9 ──
import types

class _ToolError(Exception):
    """Stub for fastmcp.exceptions.ToolError"""
    pass

class _FakeMCP:
    def __init__(self, *a, **kw): pass
    def tool(self, fn=None, **kw):
        if fn is not None:
            return fn
        def deco(f):
            return f
        return deco
    def resource(self, uri=None, **kw):
        def deco(f):
            return f
        return deco
    def prompt(self, fn=None, **kw):
        if fn is not None:
            return fn
        def deco(f):
            return f
        return deco

_fastmcp_pkg = types.ModuleType('fastmcp')
_fastmcp_pkg.__path__ = []
_fastmcp_pkg.FastMCP = _FakeMCP

_fastmcp_exc = types.ModuleType('fastmcp.exceptions')
_fastmcp_exc.ToolError = _ToolError

sys.modules['fastmcp'] = _fastmcp_pkg
sys.modules['fastmcp.exceptions'] = _fastmcp_exc

PASS = "\u2705 PASS"
FAIL = "\u274c FAIL"
SKIP = "\u23ed\ufe0f  SKIP"
results = []


def record(name, status, detail=""):
    results.append((name, status, detail))
    print(f"  {status}: {name}")
    if detail:
        for line in detail.split('\n'):
            print(f"         {line}")


def main():
    print()
    print("=" * 70)
    print("  MCP SERVER SECURITY & RBAC TEST SUITE")
    print(f"  {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # ── Initialize Flask app ──
    print("\n  Initializing Flask app...")
    from app_v3_minimal import app
    print("  \u2705 Flask app created")

    # ── Import MCP server ──
    print("  Importing MCP server module...")
    from mcp_server.cs_pulse_mcp_server import (
        list_accounts, get_account_health, get_at_risk_accounts,
        get_csm_daily_actions, get_playbook_recommendations,
        calculate_power_of_1, get_outcome_roi_story,
        get_crm_account_data, get_support_tickets, get_customer_feedback,
        _validate_account_ownership, _check_mcp_enabled,
    )
    print("  \u2705 MCP server module imported")

    # ── Determine test customer ──
    with app.app_context():
        from models import Customer, Account, User
        customer = Customer.query.first()
        if not customer:
            print("  \u274c No customers in database. Cannot test.")
            return

        customer_id = customer.customer_id
        accounts = Account.query.filter_by(customer_id=customer_id).all()
        if not accounts:
            print(f"  \u274c No accounts for customer {customer_id}. Cannot test.")
            return

        account = accounts[0]
        account_id = account.account_id
        print(f"\n  Test customer: {customer.customer_name} (ID: {customer_id})")
        print(f"  Test account:  {account.account_name} (ID: {account_id})")
        print(f"  Total accounts: {len(accounts)}")

    # ══════════════════════════════════════════════════════════════════
    # PHASE 1: Core MCP Tools (feature enabled)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─' * 70}")
    print("  PHASE 1: Core MCP Tools (FEATURE_MCP_SERVER=true)")
    print(f"{'─' * 70}")

    # Test 1: list_accounts
    try:
        result = list_accounts(customer_id)
        assert "accounts" in result, "Missing 'accounts' key"
        assert len(result["accounts"]) > 0, "No accounts returned"
        assert "scope" in result, "Missing 'scope' field"
        assert result["scope"] == "portfolio", f"Expected scope=portfolio, got {result['scope']}"
        record("list_accounts", PASS, f"Returned {len(result['accounts'])} accounts, scope={result['scope']}")
    except Exception as e:
        record("list_accounts", FAIL, f"Exception: {e}")

    # Test 2: get_account_health
    try:
        result = get_account_health(customer_id, account_id)
        assert "health_score" in result, "Missing 'health_score' key"
        assert "status" in result, "Missing 'status' key"
        assert "pillar_scores" in result or "pillars" in result, "Missing pillar scores key"
        health = result["health_score"]
        assert 0 <= health <= 100, f"Health score {health} out of range"
        record("get_account_health", PASS, f"Health={health:.1f}, status={result['status']}")
    except Exception as e:
        record("get_account_health", FAIL, f"Exception: {e}")

    # Test 3: get_at_risk_accounts
    try:
        result = get_at_risk_accounts(customer_id)
        assert "accounts" in result or "at_risk_accounts" in result, "Missing accounts key"
        assert "total_arr_at_risk" in result, "Missing 'total_arr_at_risk' key"
        accts = result.get("accounts") or result.get("at_risk_accounts", [])
        record("get_at_risk_accounts", PASS,
               f"Found {len(accts)} at-risk, ARR_at_risk=${result['total_arr_at_risk']:,.0f}")
    except Exception as e:
        record("get_at_risk_accounts", FAIL, f"Exception: {e}")

    # Test 4: get_csm_daily_actions
    try:
        result = get_csm_daily_actions(customer_id)
        assert "actions" in result or "daily_actions" in result, "Missing 'actions' key"
        actions = result.get("actions") or result.get("daily_actions", [])
        record("get_csm_daily_actions", PASS, f"Returned {len(actions)} actions")
    except Exception as e:
        record("get_csm_daily_actions", FAIL, f"Exception: {e}")

    # Test 5: calculate_power_of_1
    try:
        result = calculate_power_of_1(customer_id, "NRR", 1.0)
        assert "total_impact" in result or "revenue_impact" in result, "Missing impact key"
        impact = result.get("total_impact") or result.get("revenue_impact", 0)
        record("calculate_power_of_1", PASS, f"scope={result.get('scope', 'N/A')}, impact=${impact:,.0f}")
    except Exception as e:
        record("calculate_power_of_1", FAIL, f"Exception: {e}")

    # Test 6: get_crm_account_data
    try:
        result = get_crm_account_data(customer_id, account_id)
        assert "account_name" in result, "Missing 'account_name' key"
        record("get_crm_account_data", PASS, f"account={result.get('account_name')}")
    except Exception as e:
        record("get_crm_account_data", FAIL, f"Exception: {e}")

    # Test 7: get_support_tickets
    try:
        result = get_support_tickets(customer_id, account_id)
        assert "account_name" in result or "scope" in result, "Missing expected keys"
        record("get_support_tickets", PASS, f"scope={result.get('scope', 'N/A')}")
    except Exception as e:
        record("get_support_tickets", FAIL, f"Exception: {e}")

    # Test 8: get_customer_feedback
    try:
        result = get_customer_feedback(customer_id, account_id)
        assert "scope" in result or "account_name" in result, "Missing expected keys"
        record("get_customer_feedback", PASS, f"scope={result.get('scope', 'N/A')}")
    except Exception as e:
        record("get_customer_feedback", FAIL, f"Exception: {e}")

    # Test 9: get_playbook_recommendations
    try:
        result = get_playbook_recommendations(customer_id, account_id)
        assert "recommendations" in result or "playbooks" in result, "Missing expected keys"
        recs = result.get("recommendations") or result.get("playbooks", [])
        record("get_playbook_recommendations", PASS, f"{len(recs)} recommendations")
    except Exception as e:
        record("get_playbook_recommendations", FAIL, f"Exception: {e}")

    # ══════════════════════════════════════════════════════════════════
    # PHASE 2: Tenant Isolation (_validate_account_ownership)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─' * 70}")
    print("  PHASE 2: Tenant Isolation & Account Ownership")
    print(f"{'─' * 70}")

    # Test 10: Valid account ownership
    with app.app_context():
        try:
            acct = _validate_account_ownership(customer_id, account_id)
            assert acct is not None, "Should return account object"
            record("validate_ownership (valid)", PASS, f"Account {account_id} belongs to customer {customer_id}")
        except Exception as e:
            record("validate_ownership (valid)", FAIL, f"Exception: {e}")

    # Test 11: Invalid account (wrong customer)
    with app.app_context():
        try:
            # Use a fake customer ID that shouldn't own any account
            _validate_account_ownership(99999, account_id)
            record("validate_ownership (wrong customer)", FAIL, "Should have raised ToolError")
        except _ToolError:
            record("validate_ownership (wrong customer)", PASS, "ToolError raised correctly")
        except Exception as e:
            record("validate_ownership (wrong customer)", FAIL, f"Wrong exception: {type(e).__name__}: {e}")

    # Test 12: Invalid account ID
    with app.app_context():
        try:
            _validate_account_ownership(customer_id, 99999999)
            record("validate_ownership (invalid account)", FAIL, "Should have raised ToolError")
        except _ToolError:
            record("validate_ownership (invalid account)", PASS, "ToolError raised correctly")
        except Exception as e:
            record("validate_ownership (invalid account)", FAIL, f"Wrong exception: {type(e).__name__}: {e}")

    # Test 13: Cross-tenant isolation via tool
    try:
        get_account_health(99999, account_id)
        record("cross-tenant get_account_health", FAIL, "Should have raised ToolError")
    except _ToolError as e:
        record("cross-tenant get_account_health", PASS, f"Blocked: {e}")
    except Exception as e:
        record("cross-tenant get_account_health", FAIL, f"Wrong exception: {type(e).__name__}: {e}")

    # ══════════════════════════════════════════════════════════════════
    # PHASE 3: Feature Toggle Gating
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─' * 70}")
    print("  PHASE 3: Feature Toggle Gating")
    print(f"{'─' * 70}")

    # Test 14: MCP enabled check
    try:
        _check_mcp_enabled()
        record("_check_mcp_enabled (enabled)", PASS, "No exception — MCP is enabled")
    except Exception as e:
        record("_check_mcp_enabled (enabled)", FAIL, f"Exception: {e}")

    # Test 15: MCP disabled check
    try:
        from feature_toggles import feature_toggles, FeatureToggle
        # Temporarily disable
        feature_toggles.disable_feature(FeatureToggle.MCP_SERVER)
        try:
            _check_mcp_enabled()
            record("_check_mcp_enabled (disabled)", FAIL, "Should have raised ToolError")
        except _ToolError:
            record("_check_mcp_enabled (disabled)", PASS, "ToolError raised when disabled")
        except Exception as e:
            record("_check_mcp_enabled (disabled)", FAIL, f"Wrong exception: {type(e).__name__}: {e}")
        finally:
            # Re-enable
            feature_toggles.enable_feature(FeatureToggle.MCP_SERVER)
    except Exception as e:
        record("_check_mcp_enabled (disabled)", FAIL, f"Setup exception: {e}")

    # Test 16: Tool blocked when MCP disabled
    try:
        from feature_toggles import feature_toggles, FeatureToggle
        feature_toggles.disable_feature(FeatureToggle.MCP_SERVER)
        try:
            list_accounts(customer_id)
            record("list_accounts (MCP disabled)", FAIL, "Should have raised ToolError")
        except _ToolError:
            record("list_accounts (MCP disabled)", PASS, "Correctly blocked when disabled")
        except Exception as e:
            record("list_accounts (MCP disabled)", FAIL, f"Wrong exception: {type(e).__name__}: {e}")
        finally:
            feature_toggles.enable_feature(FeatureToggle.MCP_SERVER)
    except Exception as e:
        record("list_accounts (MCP disabled)", FAIL, f"Setup exception: {e}")

    # ══════════════════════════════════════════════════════════════════
    # PHASE 4: RBAC / User-Level Access Control
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─' * 70}")
    print("  PHASE 4: User-Level RBAC Integration")
    print(f"{'─' * 70}")

    with app.app_context():
        from models import User, db

        # Check if User model has RBAC fields
        try:
            user = User.query.first()
            has_allowed_account_ids = hasattr(user, 'allowed_account_ids') if user else hasattr(User, 'allowed_account_ids')
            has_is_contractor = hasattr(user, 'is_contractor') if user else hasattr(User, 'is_contractor')
            has_expires_at = hasattr(user, 'expires_at') if user else hasattr(User, 'expires_at')
            has_has_account_access = hasattr(user, 'has_account_access') if user else hasattr(User, 'has_account_access')

            if has_allowed_account_ids and has_is_contractor and has_expires_at:
                record("User model RBAC fields", PASS,
                       f"allowed_account_ids={has_allowed_account_ids}, "
                       f"is_contractor={has_is_contractor}, "
                       f"expires_at={has_expires_at}, "
                       f"has_account_access()={has_has_account_access}")
            else:
                record("User model RBAC fields", FAIL,
                       f"Missing fields: allowed_account_ids={has_allowed_account_ids}, "
                       f"is_contractor={has_is_contractor}, expires_at={has_expires_at}")
        except Exception as e:
            record("User model RBAC fields", FAIL, f"Exception: {e}")

        # Test: has_account_access() method
        if user and has_has_account_access:
            try:
                # Super admin should have access to all accounts
                if user.role in ('super_admin', 'admin') and not user.allowed_account_ids:
                    # No restrictions = full access
                    result = user.has_account_access(account_id)
                    record("has_account_access (admin, no restrictions)", PASS, f"Result={result}")
                else:
                    record("has_account_access (non-admin)", SKIP, f"User role={user.role}")
            except Exception as e:
                record("has_account_access", FAIL, f"Exception: {e}")
        else:
            record("has_account_access", SKIP, "No user or method not available")

        # Test: Check for contractor users created by our feature
        try:
            contractors = User.query.filter_by(is_contractor=True).all()
            record("Contractor users in DB", PASS, f"Found {len(contractors)} contractor(s)")
            for c in contractors[:3]:
                exp = c.expires_at.strftime('%Y-%m-%d') if c.expires_at else 'no-expiry'
                accts = c.allowed_account_ids or 'all'
                active = 'active' if c.active else 'inactive'
                print(f"           - {c.user_name} ({c.email}): {active}, expires={exp}, accounts={accts}")
        except Exception as e:
            record("Contractor users in DB", FAIL, f"Exception: {e}")

    # ══════════════════════════════════════════════════════════════════
    # PHASE 5: MCP + RBAC Gap Analysis
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─' * 70}")
    print("  PHASE 5: MCP + RBAC Integration Gap Analysis")
    print(f"{'─' * 70}")

    # Check if _validate_account_ownership accepts user_id parameter
    import inspect
    sig = inspect.signature(_validate_account_ownership)
    params = list(sig.parameters.keys())
    has_user_param = 'user_id' in params
    record("_validate_account_ownership has user_id param",
           PASS if has_user_param else FAIL,
           f"Parameters: {params}" + (" — RBAC-aware" if has_user_param else " — NOT RBAC-aware (gap)"))

    # Check if MCP server uses auth.require_api_key decorator
    try:
        from mcp_server import auth
        has_require_api_key = hasattr(auth, 'require_api_key')
        has_validate_api_key = hasattr(auth, 'validate_api_key')
        record("MCP auth module", PASS,
               f"require_api_key={has_require_api_key}, validate_api_key={has_validate_api_key}")
    except Exception as e:
        record("MCP auth module", FAIL, f"Exception: {e}")

    # Check _filter_accounts_by_user helper exists
    try:
        from mcp_server.cs_pulse_mcp_server import _filter_accounts_by_user
        sig = inspect.signature(_filter_accounts_by_user)
        params = list(sig.parameters.keys())
        record("_filter_accounts_by_user exists", PASS, f"Parameters: {params}")
    except ImportError:
        record("_filter_accounts_by_user exists", FAIL, "Function not found in MCP server")

    # Check user_id param on portfolio tools
    for tool_name in ['list_accounts', 'get_at_risk_accounts', 'get_csm_daily_actions',
                      'calculate_power_of_1', 'get_portfolio_roi_summary']:
        try:
            from mcp_server import cs_pulse_mcp_server as mcp_mod
            tool_fn = getattr(mcp_mod, tool_name)
            sig = inspect.signature(tool_fn)
            has_uid = 'user_id' in sig.parameters
            record(f"{tool_name} has user_id param",
                   PASS if has_uid else FAIL,
                   "RBAC-aware" if has_uid else "NOT RBAC-aware")
        except Exception as e:
            record(f"{tool_name} has user_id param", FAIL, f"Exception: {e}")

    # ══════════════════════════════════════════════════════════════════
    # PHASE 6: Live RBAC Enforcement (contractor filtering)
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'─' * 70}")
    print("  PHASE 6: Live RBAC Enforcement Tests")
    print(f"{'─' * 70}")

    with app.app_context():
        from models import User, Account, db
        from werkzeug.security import generate_password_hash
        from datetime import datetime, timedelta

        # Patch MCP server to use the test's Flask app (shares DB session)
        import mcp_server.cs_pulse_mcp_server as mcp_mod
        mcp_mod._flask_app = app

        all_accounts = Account.query.filter_by(customer_id=customer_id).all()
        if len(all_accounts) < 2:
            record("RBAC enforcement (setup)", SKIP, f"Need 2+ accounts, got {len(all_accounts)}")
        else:
            # Create temporary contractor users (committed so MCP tools can see them)
            restricted_account = all_accounts[0]
            unrestricted_account = all_accounts[1]
            created_user_ids = []

            test_contractor = User(
                customer_id=customer_id,
                user_name='_mcp_test_contractor',
                email='_mcp_test_contractor@test.com',
                password_hash=generate_password_hash('TestPass123!'),
                role='viewer',
                active=True,
                is_contractor=True,
                allowed_account_ids=[restricted_account.account_id],
                expires_at=datetime.utcnow() + timedelta(days=30),
                vertical='dc2_s',
            )
            db.session.add(test_contractor)
            db.session.commit()
            contractor_user_id = test_contractor.user_id
            created_user_ids.append(contractor_user_id)

            # Also create an expired contractor
            expired_contractor = User(
                customer_id=customer_id,
                user_name='_mcp_test_expired',
                email='_mcp_test_expired@test.com',
                password_hash=generate_password_hash('TestPass123!'),
                role='viewer',
                active=True,
                is_contractor=True,
                allowed_account_ids=[restricted_account.account_id],
                expires_at=datetime.utcnow() - timedelta(days=1),  # Already expired
                vertical='dc2_s',
            )
            db.session.add(expired_contractor)
            db.session.commit()
            expired_user_id = expired_contractor.user_id
            created_user_ids.append(expired_user_id)

            print(f"  Created test contractor (user_id={contractor_user_id}, "
                  f"allowed=[{restricted_account.account_id}])")
            print(f"  Created expired contractor (user_id={expired_user_id})")

            try:
                # Test 1: list_accounts with user_id filters results
                try:
                    result = list_accounts(customer_id, user_id=contractor_user_id)
                    accts_returned = result.get("accounts", [])
                    acct_ids = [a["account_id"] for a in accts_returned]
                    assert len(accts_returned) == 1, \
                        f"Expected 1 account, got {len(accts_returned)} (ids: {acct_ids})"
                    assert acct_ids[0] == restricted_account.account_id, \
                        f"Expected account {restricted_account.account_id}, got {acct_ids[0]}"
                    record("list_accounts (contractor RBAC)", PASS,
                           f"Returned 1/{len(all_accounts)} accounts (restricted)")
                except Exception as e:
                    record("list_accounts (contractor RBAC)", FAIL, f"Exception: {e}")

                # Test 2: list_accounts without user_id returns all
                try:
                    result = list_accounts(customer_id)
                    accts_returned = result.get("accounts", [])
                    assert len(accts_returned) == len(all_accounts), \
                        f"Expected {len(all_accounts)} accounts, got {len(accts_returned)}"
                    record("list_accounts (no user_id = all)", PASS,
                           f"Returned all {len(accts_returned)} accounts")
                except Exception as e:
                    record("list_accounts (no user_id = all)", FAIL, f"Exception: {e}")

                # Test 3: get_at_risk_accounts respects RBAC
                try:
                    result = get_at_risk_accounts(customer_id, user_id=contractor_user_id)
                    accts_returned = result.get("accounts", [])
                    for a in accts_returned:
                        assert a["account_id"] == restricted_account.account_id, \
                            f"Unexpected account {a['account_id']} in at-risk results"
                    record("get_at_risk_accounts (contractor RBAC)", PASS,
                           f"At-risk filtered: {len(accts_returned)} accounts")
                except Exception as e:
                    record("get_at_risk_accounts (contractor RBAC)", FAIL, f"Exception: {e}")

                # Test 4: get_account_health blocks unauthorized account
                try:
                    get_account_health(customer_id, unrestricted_account.account_id,
                                       user_id=contractor_user_id)
                    record("get_account_health (blocked account)", FAIL,
                           "Should have raised ToolError for unauthorized account")
                except _ToolError as e:
                    record("get_account_health (blocked account)", PASS,
                           f"Access denied: {e}")
                except Exception as e:
                    record("get_account_health (blocked account)", FAIL,
                           f"Wrong exception: {type(e).__name__}: {e}")

                # Test 5: get_account_health allows authorized account
                try:
                    result = get_account_health(customer_id, restricted_account.account_id,
                                                user_id=contractor_user_id)
                    assert "health_score" in result, "Missing health_score"
                    record("get_account_health (allowed account)", PASS,
                           f"Health={result['health_score']}")
                except Exception as e:
                    record("get_account_health (allowed account)", FAIL, f"Exception: {e}")

                # Test 6: Expired user gets empty list from list_accounts
                try:
                    result = list_accounts(customer_id, user_id=expired_user_id)
                    accts_returned = result.get("accounts", [])
                    assert len(accts_returned) == 0, \
                        f"Expired user should see 0 accounts, got {len(accts_returned)}"
                    record("list_accounts (expired user)", PASS,
                           "Expired contractor sees 0 accounts")
                except Exception as e:
                    record("list_accounts (expired user)", FAIL, f"Exception: {e}")

                # Test 7: Expired user blocked by _validate_account_ownership
                try:
                    _validate_account_ownership(customer_id, restricted_account.account_id,
                                                user_id=expired_user_id)
                    record("validate_ownership (expired user)", FAIL,
                           "Should have raised ToolError for expired user")
                except _ToolError as e:
                    record("validate_ownership (expired user)", PASS,
                           f"Blocked: {e}")
                except Exception as e:
                    record("validate_ownership (expired user)", FAIL,
                           f"Wrong exception: {type(e).__name__}: {e}")

                # Test 8: get_csm_daily_actions with user_id filters accounts
                try:
                    result = get_csm_daily_actions(customer_id, user_id=contractor_user_id)
                    actions = result.get("actions", [])
                    for action in actions:
                        assert action["account_id"] == restricted_account.account_id, \
                            f"Action for unauthorized account {action['account_id']}"
                    record("get_csm_daily_actions (contractor RBAC)", PASS,
                           f"All {len(actions)} actions for allowed accounts only")
                except Exception as e:
                    record("get_csm_daily_actions (contractor RBAC)", FAIL, f"Exception: {e}")

            finally:
                # Clean up test users from DB
                for uid in created_user_ids:
                    u = db.session.get(User, uid)
                    if u:
                        db.session.delete(u)
                db.session.commit()
                print(f"\n  Cleaned up {len(created_user_ids)} test contractors (deleted)")

    # ══════════════════════════════════════════════════════════════════
    # RESULTS SUMMARY
    # ══════════════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}")
    print("  RESULTS SUMMARY")
    print(f"{'=' * 70}")

    passed = sum(1 for _, s, _ in results if s == PASS)
    failed = sum(1 for _, s, _ in results if s == FAIL)
    skipped = sum(1 for _, s, _ in results if s == SKIP)

    for name, status, detail in results:
        if FAIL in status:
            print(f"  {status}: {name}  ({detail})")

    print(f"\n  Total: {len(results)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")

    if failed == 0:
        print(f"\n  \u2705 ALL TESTS PASSED")
    else:
        print(f"\n  \u274c {failed} FAILED — see details above")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
