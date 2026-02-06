#!/usr/bin/env python3
"""
Unit tests for resolve_identifier.py

Tests the identifier resolution logic that accepts both legacy integer IDs
and new prefixed UUIDs during the migration period.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from resolve_identifier import _is_legacy_int


passed = 0
failed = 0


def check(name, condition, detail=''):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} -- {detail}")


def test_is_legacy_int():
    """Test integer detection for various input types."""
    print("\n[Test] _is_legacy_int detection")

    # True cases
    check("int 1", _is_legacy_int(1))
    check("int 9", _is_legacy_int(9))
    check("int 0", _is_legacy_int(0))
    check("int 42", _is_legacy_int(42))
    check("string '1'", _is_legacy_int('1'))
    check("string '9'", _is_legacy_int('9'))
    check("string '42'", _is_legacy_int('42'))

    # False cases
    check("UUID string", not _is_legacy_int('dc_cust_019471a3-b5c2-7def-8a12-4b6e8f3d9c01'))
    check("saas prefix", not _is_legacy_int('saas_acct_019471a3-b5c2-7def-8a12-4b6e8f3d9c01'))
    check("empty string", not _is_legacy_int(''))
    check("None", not _is_legacy_int(None))
    check("random string", not _is_legacy_int('hello'))
    check("float-like string", not _is_legacy_int('1.5'))


def test_resolve_imports():
    """Verify all resolve functions can be imported."""
    print("\n[Test] Resolve function imports")

    try:
        from resolve_identifier import resolve_customer
        check("resolve_customer importable", True)
    except ImportError as e:
        check("resolve_customer importable", False, str(e))

    try:
        from resolve_identifier import resolve_account
        check("resolve_account importable", True)
    except ImportError as e:
        check("resolve_account importable", False, str(e))

    try:
        from resolve_identifier import resolve_product
        check("resolve_product importable", True)
    except ImportError as e:
        check("resolve_product importable", False, str(e))

    try:
        from resolve_identifier import resolve_user
        check("resolve_user importable", True)
    except ImportError as e:
        check("resolve_user importable", False, str(e))

    try:
        from resolve_identifier import resolve_customer_id
        check("resolve_customer_id importable", True)
    except ImportError as e:
        check("resolve_customer_id importable", False, str(e))

    try:
        from resolve_identifier import get_customer_vertical
        check("get_customer_vertical importable", True)
    except ImportError as e:
        check("get_customer_vertical importable", False, str(e))


def test_none_handling():
    """All resolve functions should handle None gracefully."""
    print("\n[Test] None handling")

    from resolve_identifier import (
        resolve_customer, resolve_account, resolve_product,
        resolve_user, resolve_customer_id, get_customer_vertical
    )

    # These need a db instance, but we can test None input returns None
    # We'll mock db with a simple object
    class MockDB:
        class session:
            @staticmethod
            def get(model, id):
                return None

    mock_db = MockDB()
    check("resolve_customer(None) is None", resolve_customer(mock_db, None) is None)
    check("resolve_account(None) is None", resolve_account(mock_db, None) is None)
    check("resolve_product(None) is None", resolve_product(mock_db, None) is None)
    check("resolve_user(None) is None", resolve_user(mock_db, None) is None)
    check("resolve_customer_id(None) is None", resolve_customer_id(mock_db, None) is None)
    check("get_customer_vertical(None) is None", get_customer_vertical(mock_db, None) is None)


def test_legacy_int_passthrough():
    """Integer identifiers should be passed through to db.session.get."""
    print("\n[Test] Legacy int passthrough")

    from resolve_identifier import resolve_customer_id

    class MockDB:
        class session:
            @staticmethod
            def get(model, id):
                return None

    mock_db = MockDB()

    # resolve_customer_id with int should return the int directly
    check("resolve_customer_id(db, 1) == 1", resolve_customer_id(mock_db, 1) == 1)
    check("resolve_customer_id(db, 9) == 9", resolve_customer_id(mock_db, 9) == 9)
    check("resolve_customer_id(db, '42') == 42", resolve_customer_id(mock_db, '42') == 42)


if __name__ == '__main__':
    print("=" * 60)
    print("  Resolve Identifier Unit Tests")
    print("=" * 60)

    test_is_legacy_int()
    test_resolve_imports()
    test_none_handling()
    test_legacy_int_passthrough()

    print("\n" + "=" * 60)
    print(f"  RESULT: {passed}/{passed + failed} tests passed")
    if failed == 0:
        print("  ALL TESTS PASSED")
    else:
        print(f"  {failed} TESTS FAILED")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
