#!/usr/bin/env python3
"""
Unit tests for id_generator.py

These tests run WITHOUT a database — they validate the ID generation
logic, format correctness, time-ordering, and collision resistance.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from id_generator import (
    generate_id, generate_customer_id, generate_account_id,
    generate_user_id, generate_product_id, generate_kpi_id,
    generate_upload_id, extract_vertical, extract_entity_type,
    is_valid_prefixed_id, resolve_vertical_prefix, resolve_entity_prefix,
    _generate_uuid7, VERTICAL_PREFIXES, ENTITY_PREFIXES
)


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


def test_uuid7_format():
    """UUID v7 should be in standard 8-4-4-4-12 format."""
    print("\n[Test] UUID v7 format")
    uuid = _generate_uuid7()
    parts = uuid.split('-')
    check("Has 5 sections", len(parts) == 5, f"Got {len(parts)}: {uuid}")
    check("Section lengths 8-4-4-4-12",
          [len(p) for p in parts] == [8, 4, 4, 4, 12],
          f"Got {[len(p) for p in parts]}")
    check("All hex chars", all(c in '0123456789abcdef-' for c in uuid), uuid)
    check("Total length 36", len(uuid) == 36, f"Got {len(uuid)}")

    # Check version bits (byte 6, high nibble should be 7)
    hex_str = uuid.replace('-', '')
    version_nibble = int(hex_str[12], 16)
    check("Version nibble is 7", version_nibble == 7, f"Got {version_nibble}")

    # Check variant bits (byte 8, high 2 bits should be 10)
    variant_byte = int(hex_str[16:18], 16)
    check("Variant bits are 10xx", (variant_byte >> 6) == 2, f"Got {bin(variant_byte >> 6)}")


def test_uuid7_time_ordering():
    """UUIDs generated later should sort after earlier ones."""
    print("\n[Test] UUID v7 time ordering")
    ids = []
    for _ in range(10):
        ids.append(_generate_uuid7())
        time.sleep(0.002)  # Small delay to ensure different timestamps

    sorted_ids = sorted(ids)
    check("10 UUIDs are in creation order", ids == sorted_ids,
          f"Out of order at index {next((i for i in range(len(ids)) if ids[i] != sorted_ids[i]), '?')}")


def test_uuid7_uniqueness():
    """Rapid generation should not produce collisions."""
    print("\n[Test] UUID v7 uniqueness")
    ids = set()
    count = 1000
    for _ in range(count):
        ids.add(_generate_uuid7())
    check(f"{count} UUIDs are unique", len(ids) == count, f"Got {len(ids)} unique")


def test_prefixed_id_format():
    """Prefixed IDs should follow {vertical}_{entity}_{uuid7} format."""
    print("\n[Test] Prefixed ID format")

    test_cases = [
        ('saas', 'customer', 'saas_cust_'),
        ('datacenter', 'account', 'dc_acct_'),
        ('dc', 'account', 'dc_acct_'),
        ('msp', 'user', 'msp_usr_'),
        ('saas', 'product', 'saas_prod_'),
        ('dc', 'kpi', 'dc_kpi_'),
        ('msp', 'upload', 'msp_upl_'),
    ]

    for vertical, entity, expected_prefix in test_cases:
        pid = generate_id(vertical, entity)
        check(f"generate_id('{vertical}', '{entity}') starts with '{expected_prefix}'",
              pid.startswith(expected_prefix),
              f"Got: {pid}")


def test_convenience_helpers():
    """Convenience functions should generate correct prefixes."""
    print("\n[Test] Convenience helpers")

    check("generate_customer_id('dc') starts with dc_cust_",
          generate_customer_id('dc').startswith('dc_cust_'))
    check("generate_account_id('saas') starts with saas_acct_",
          generate_account_id('saas').startswith('saas_acct_'))
    check("generate_user_id('msp') starts with msp_usr_",
          generate_user_id('msp').startswith('msp_usr_'))
    check("generate_product_id('dc') starts with dc_prod_",
          generate_product_id('dc').startswith('dc_prod_'))
    check("generate_kpi_id('saas') starts with saas_kpi_",
          generate_kpi_id('saas').startswith('saas_kpi_'))
    check("generate_upload_id('msp') starts with msp_upl_",
          generate_upload_id('msp').startswith('msp_upl_'))


def test_extract_functions():
    """Extract functions should parse prefixed IDs correctly."""
    print("\n[Test] Extract functions")

    pid = generate_id('dc', 'account')
    check("extract_vertical returns 'dc'",
          extract_vertical(pid) == 'dc', f"Got: {extract_vertical(pid)}")
    check("extract_entity_type returns 'acct'",
          extract_entity_type(pid) == 'acct', f"Got: {extract_entity_type(pid)}")

    pid2 = generate_id('saas', 'customer')
    check("extract_vertical returns 'saas'",
          extract_vertical(pid2) == 'saas')
    check("extract_entity_type returns 'cust'",
          extract_entity_type(pid2) == 'cust')


def test_validation():
    """is_valid_prefixed_id should correctly validate IDs."""
    print("\n[Test] Validation")

    valid_id = generate_id('dc', 'account')
    check("Valid ID passes", is_valid_prefixed_id(valid_id))
    check("Empty string fails", not is_valid_prefixed_id(''))
    check("Random string fails", not is_valid_prefixed_id('not-a-uuid'))
    check("Integer fails", not is_valid_prefixed_id('123'))
    check("Partial prefix fails", not is_valid_prefixed_id('dc_'))
    check("Wrong vertical fails", not is_valid_prefixed_id('xyz_acct_019471a3-b5c2-7def-8a12-4b6e8f3d9c01'))
    check("Wrong entity fails", not is_valid_prefixed_id('dc_xyz_019471a3-b5c2-7def-8a12-4b6e8f3d9c01'))


def test_error_handling():
    """Invalid inputs should raise ValueError."""
    print("\n[Test] Error handling")

    try:
        resolve_vertical_prefix('invalid_vertical')
        check("Unknown vertical raises", False, "No exception raised")
    except ValueError:
        check("Unknown vertical raises ValueError", True)

    try:
        resolve_entity_prefix('invalid_entity')
        check("Unknown entity raises", False, "No exception raised")
    except ValueError:
        check("Unknown entity raises ValueError", True)


def test_all_verticals():
    """All registered verticals should produce valid IDs."""
    print("\n[Test] All verticals work")
    for vertical in VERTICAL_PREFIXES:
        pid = generate_id(vertical, 'customer')
        check(f"Vertical '{vertical}' produces valid ID",
              is_valid_prefixed_id(pid), pid)


def test_all_entity_types():
    """All registered entity types should produce valid IDs."""
    print("\n[Test] All entity types work")
    for entity in ENTITY_PREFIXES:
        pid = generate_id('dc', entity)
        check(f"Entity '{entity}' produces valid ID",
              pid.startswith('dc_'), pid)


def test_prefixed_id_sortable():
    """Prefixed IDs for same vertical+entity should be sortable by creation."""
    print("\n[Test] Prefixed IDs are time-sortable")
    ids = []
    for _ in range(10):
        ids.append(generate_id('dc', 'account'))
        time.sleep(0.002)

    sorted_ids = sorted(ids)
    check("10 prefixed IDs sort in creation order", ids == sorted_ids)


if __name__ == '__main__':
    print("=" * 60)
    print("  ID Generator Unit Tests")
    print("=" * 60)

    test_uuid7_format()
    test_uuid7_time_ordering()
    test_uuid7_uniqueness()
    test_prefixed_id_format()
    test_convenience_helpers()
    test_extract_functions()
    test_validation()
    test_error_handling()
    test_all_verticals()
    test_all_entity_types()
    test_prefixed_id_sortable()

    print("\n" + "=" * 60)
    print(f"  RESULT: {passed}/{passed + failed} tests passed")
    if failed == 0:
        print("  ALL TESTS PASSED")
    else:
        print(f"  {failed} TESTS FAILED")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
