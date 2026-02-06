"""
UUID v7 ID Generator for CS Pulse Multi-Vertical System

Generates globally unique, time-sortable, vertical-identifiable IDs.

Format: {vertical_prefix}_{entity_prefix}_{uuid7}
Example: dc_cust_019471a3-b5c2-7def-8a12-4b6e8f3d9c01

UUID v7 properties:
- Time-ordered (sortable by creation time)
- No B-tree index fragmentation (unlike UUID v4)
- No central sequence generator needed (multi-region safe)
- Collision-resistant (timestamp + 74 bits of randomness)

Usage:
    from id_generator import generate_id, generate_customer_id

    # Generic
    new_id = generate_id('dc', 'account')    # "dc_acct_019471a3-b5c2-..."

    # Convenience helpers
    cust_id = generate_customer_id('saas')    # "saas_cust_019471a3-..."
    acct_id = generate_account_id('dc')       # "dc_acct_019471a3-..."
"""

import os
import time
import struct


# ============================================================
# Vertical Prefixes
# ============================================================
VERTICAL_PREFIXES = {
    'saas': 'saas',
    'datacenter': 'dc',
    'data_center': 'dc',
    'dc': 'dc',
    'msp': 'msp',
}

# ============================================================
# Entity Prefixes
# ============================================================
ENTITY_PREFIXES = {
    'customer': 'cust',
    'account': 'acct',
    'user': 'usr',
    'product': 'prod',
    'kpi': 'kpi',
    'upload': 'upl',
    'health_trend': 'htrend',
    'kpi_time_series': 'kts',
    'kpi_reference_range': 'kref',
    'playbook_trigger': 'ptrig',
    'playbook_execution': 'pexec',
    'playbook_report': 'prep',
    'feature_toggle': 'ftog',
    'query_audit': 'qaud',
    'activity_log': 'alog',
    'workflow_config': 'wfcfg',
    'account_note': 'anote',
    'account_snapshot': 'asnap',
    'customer_config': 'ccfg',
}

# Valid verticals for validation
VALID_VERTICALS = {'saas', 'dc', 'msp'}


def _generate_uuid7() -> str:
    """
    Generate a UUID v7 string (RFC 9562).

    Layout (128 bits):
      - Bits 0-47:   Unix timestamp in milliseconds
      - Bits 48-51:  Version (0b0111 = 7)
      - Bits 52-63:  Random (12 bits)
      - Bits 64-65:  Variant (0b10)
      - Bits 66-127: Random (62 bits)

    Returns:
        Standard UUID string like "019471a3-b5c2-7def-8a12-4b6e8f3d9c01"
    """
    # 48-bit millisecond timestamp
    timestamp_ms = int(time.time() * 1000)

    # 10 bytes of randomness
    rand_bytes = os.urandom(10)

    # Build the 16-byte UUID
    # Bytes 0-5: timestamp (big-endian, 48 bits)
    ts_bytes = struct.pack('>Q', timestamp_ms)[2:]  # Take last 6 bytes of 8-byte int

    # Bytes 6-7: version (4 bits) + random (12 bits)
    rand_a = struct.unpack('>H', rand_bytes[0:2])[0]
    rand_a = (rand_a & 0x0FFF) | 0x7000  # Set version bits to 0111
    ver_rand = struct.pack('>H', rand_a)

    # Bytes 8-15: variant (2 bits) + random (62 bits)
    rand_b = bytearray(rand_bytes[2:10])
    rand_b[0] = (rand_b[0] & 0x3F) | 0x80  # Set variant bits to 10

    uuid_bytes = ts_bytes + ver_rand + bytes(rand_b)

    # Format as standard UUID string
    hex_str = uuid_bytes.hex()
    return f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:32]}"


def resolve_vertical_prefix(vertical: str) -> str:
    """
    Resolve a vertical name to its short prefix.

    Args:
        vertical: Vertical name ('saas', 'datacenter', 'dc', 'msp')

    Returns:
        Short prefix ('saas', 'dc', 'msp')

    Raises:
        ValueError: If vertical is not recognized
    """
    key = vertical.lower().strip()
    if key in VERTICAL_PREFIXES:
        return VERTICAL_PREFIXES[key]
    raise ValueError(
        f"Unknown vertical '{vertical}'. "
        f"Valid verticals: {sorted(VERTICAL_PREFIXES.keys())}"
    )


def resolve_entity_prefix(entity_type: str) -> str:
    """
    Resolve an entity type to its short prefix.

    Args:
        entity_type: Entity type ('customer', 'account', etc.)

    Returns:
        Short prefix ('cust', 'acct', etc.)

    Raises:
        ValueError: If entity type is not recognized
    """
    key = entity_type.lower().strip()
    if key in ENTITY_PREFIXES:
        return ENTITY_PREFIXES[key]
    raise ValueError(
        f"Unknown entity type '{entity_type}'. "
        f"Valid types: {sorted(ENTITY_PREFIXES.keys())}"
    )


def generate_id(vertical: str, entity_type: str) -> str:
    """
    Generate a prefixed UUID v7 for any entity.

    Args:
        vertical: Vertical name ('saas', 'datacenter', 'dc', 'msp')
        entity_type: Entity type ('customer', 'account', 'user', etc.)

    Returns:
        Prefixed UUID like "dc_acct_019471a3-b5c2-7def-8a12-4b6e8f3d9c01"
    """
    v_prefix = resolve_vertical_prefix(vertical)
    e_prefix = resolve_entity_prefix(entity_type)
    uuid7 = _generate_uuid7()
    return f"{v_prefix}_{e_prefix}_{uuid7}"


def extract_vertical(prefixed_id: str) -> str:
    """
    Extract the vertical from a prefixed UUID.

    Args:
        prefixed_id: e.g. "dc_acct_019471a3-..."

    Returns:
        Vertical prefix: "dc", "saas", "msp"
    """
    parts = prefixed_id.split('_', 2)
    if len(parts) < 2:
        raise ValueError(f"Invalid prefixed ID format: '{prefixed_id}'")
    return parts[0]


def extract_entity_type(prefixed_id: str) -> str:
    """
    Extract the entity type prefix from a prefixed UUID.

    Args:
        prefixed_id: e.g. "dc_acct_019471a3-..."

    Returns:
        Entity prefix: "acct", "cust", "usr", etc.
    """
    parts = prefixed_id.split('_', 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid prefixed ID format: '{prefixed_id}'")
    return parts[1]


def is_valid_prefixed_id(prefixed_id: str) -> bool:
    """Check if a string looks like a valid prefixed UUID."""
    try:
        parts = prefixed_id.split('_', 2)
        if len(parts) != 3:
            return False
        vertical, entity, uuid_part = parts
        if vertical not in VALID_VERTICALS:
            return False
        if entity not in ENTITY_PREFIXES.values():
            return False
        # Basic UUID format check (8-4-4-4-12)
        uuid_sections = uuid_part.split('-')
        if len(uuid_sections) != 5:
            return False
        return True
    except Exception:
        return False


# ============================================================
# Convenience helpers (one per entity type)
# ============================================================

def generate_customer_id(vertical: str) -> str:
    return generate_id(vertical, 'customer')

def generate_account_id(vertical: str) -> str:
    return generate_id(vertical, 'account')

def generate_user_id(vertical: str) -> str:
    return generate_id(vertical, 'user')

def generate_product_id(vertical: str) -> str:
    return generate_id(vertical, 'product')

def generate_kpi_id(vertical: str) -> str:
    return generate_id(vertical, 'kpi')

def generate_upload_id(vertical: str) -> str:
    return generate_id(vertical, 'upload')
