"""
Login dashboard-family routing consistency guard (Aug 22 2026).

Verification pass against 3 properties requested by the user found that
password-login and magic-link-login independently reimplemented the
"which dashboard shell does this customer see" classification and had
silently diverged:

  - password-login (app_v3_minimal.py's /api/login): unset vertical defaulted
    to 'saas_premium'; only the 5 known DC_VERTICALS aliases routed to the
    'datacenter' family, everything else (including healthcare_provider,
    manufacturing_iot) routed to 'saas'.
  - magic-link-login (/api/auth/verify-magic-link): unset vertical defaulted
    to 'dc2_s'; used a crude `'saas' in vertical.lower()` check, so ANY
    non-SaaS-named vertical (healthcare_provider, manufacturing_iot)
    routed to 'datacenter' instead.

Same customer, two login methods, two different dashboard shells.

Fix: both routes now call one shared _resolve_login_vertical_and_family()
in app_v3_minimal.py.

No DB/Flask app_context needed for the pure classification logic — this
tests the shared function directly with lightweight stand-ins for
User/Customer, avoiding a live DB.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def _get_resolver():
    import app_v3_minimal as app_module
    return app_module._resolve_login_vertical_and_family, app_module.DC_VERTICALS


def test_known_verticals_route_to_expected_family():
    resolve, _ = _get_resolver()
    cases = {
        'dc2_s': 'datacenter',
        'datacenter_v1': 'datacenter',
        'saas_premium': 'saas',
    }
    for vertical, expected_family in cases.items():
        user = SimpleNamespace(vertical=vertical, customer_id=None)
        frontend_vertical, family = resolve(user, customer=None)
        assert family == expected_family, f"{vertical}: expected {expected_family}, got {family}"


def test_new_verticals_get_a_consistent_family_not_forced_datacenter():
    """The exact live-audit failure: healthcare_provider and manufacturing_iot
    must not be force-routed to 'datacenter' just because they aren't
    SaaS-named — the magic-link path's old `'saas' in vertical.lower()`
    check did exactly that."""
    resolve, dc_verticals = _get_resolver()
    for vertical in ('healthcare_provider', 'manufacturing_iot'):
        assert vertical not in dc_verticals, (
            f"test assumption broken: {vertical} was added to DC_VERTICALS"
        )
        user = SimpleNamespace(vertical=vertical, customer_id=None)
        _frontend_vertical, family = resolve(user, customer=None)
        assert family == 'saas', (
            f"{vertical}: expected 'saas' (not in DC_VERTICALS), got {family!r} — "
            f"a non-DC vertical must not be force-routed to 'datacenter'"
        )


def test_unset_vertical_default_is_consistent():
    """Old bug: password-login defaulted unset vertical to 'saas_premium',
    magic-link defaulted to 'dc2_s' -- same customer, different login
    method, different default. Now both use the same default."""
    resolve, _ = _get_resolver()
    user = SimpleNamespace(vertical=None, customer_id=None)
    frontend_vertical, family = resolve(user, customer=None)
    assert frontend_vertical == 'saas_premium'
    assert family == 'saas'


def test_password_login_and_magic_link_now_call_the_same_function():
    """Structural guard: both routes must delegate to the shared resolver,
    not maintain their own independent classification logic."""
    import inspect
    import app_v3_minimal as app_module

    source = inspect.getsource(app_module)
    # Exactly one definition of the classification logic...
    assert source.count("def _resolve_login_vertical_and_family") == 1
    # ...and both routes call it (not reimplement it inline) -- 2 call
    # sites, excluding the def line itself (which also contains the
    # substring "_resolve_login_vertical_and_family(user").
    call_sites = source.count("= _resolve_login_vertical_and_family(user")
    assert call_sites == 2, (
        f"expected both /api/login and /api/auth/verify-magic-link to call "
        f"the shared resolver exactly once each, found {call_sites} call sites"
    )
    # The old crude check, as executable code (not just mentioned in this
    # function's own docstring explaining the bug it fixed), must be gone.
    magic_link_route_start = source.index("def verify_magic_link")
    magic_link_route_body = source[magic_link_route_start:magic_link_route_start + 3000]
    assert "'saas' in vertical.lower()" not in magic_link_route_body


def test_customer_fallback_used_when_user_vertical_unset():
    resolve, _ = _get_resolver()
    user = SimpleNamespace(vertical=None, customer_id=None)
    customer = SimpleNamespace(vertical='datacenter_v1')
    frontend_vertical, family = resolve(user, customer=customer)
    assert frontend_vertical == 'datacenter_v1'
    assert family == 'datacenter'
