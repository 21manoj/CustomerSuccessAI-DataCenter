#!/usr/bin/env python3
"""
Migrate all KPI codes from letter-format (AI/CH/DV/EX/OS) to P-format (P1-P5).

Usage:
    python3 scripts/migrate_kpi_codes_to_p_format.py           # Dry-run (default)
    python3 scripts/migrate_kpi_codes_to_p_format.py --apply   # Apply changes
    python3 scripts/migrate_kpi_codes_to_p_format.py --rollback # Reverse migration

This script must be run from the backend/ directory.
"""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import Json

# Letter-format → P-format mapping
LETTER_TO_P = {'AI': 'P3', 'CH': 'P4', 'DV': 'P1', 'EX': 'P5', 'OS': 'P2'}
P_TO_LETTER = {v: k for k, v in LETTER_TO_P.items()}

LETTER_PREFIXES = tuple(f'{k}-' for k in LETTER_TO_P.keys())
P_PREFIXES = tuple(f'{v}-' for v in LETTER_TO_P.values())


def get_db_url():
    """Get database URL from environment or default."""
    return os.environ.get(
        'DATABASE_URL',
        'postgresql://dcuser:dcpass123@localhost:5432/cs_pulse_datacenter'
    )


def convert_kpi_code(code, mapping):
    """Convert a KPI code prefix using the given mapping."""
    if not code or not isinstance(code, str):
        return code
    parts = code.split('-', 1)
    if len(parts) == 2 and parts[0] in mapping:
        return f"{mapping[parts[0]]}-{parts[1]}"
    return code


def convert_json_keys(data, mapping):
    """Recursively convert JSON dict keys using the mapping."""
    if data is None:
        return None
    if isinstance(data, list):
        return [convert_kpi_code(item, mapping) if isinstance(item, str) else item for item in data]
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            new_key = mapping.get(k, k)  # Try direct pillar key mapping
            if new_key == k:
                new_key = convert_kpi_code(k, mapping)  # Try KPI code conversion
            if isinstance(v, dict):
                new_dict[new_key] = convert_json_keys(v, mapping)
            elif isinstance(v, list):
                new_dict[new_key] = convert_json_keys(v, mapping)
            else:
                new_dict[new_key] = v
        return new_dict
    return data


def audit(conn):
    """Print current state of KPI codes in the database."""
    cur = conn.cursor()

    print("\n=== AUDIT: Current KPI Code Formats ===\n")

    # dc2s_kpis
    cur.execute("SELECT DISTINCT kpi_code FROM dc2s_kpis ORDER BY kpi_code")
    codes = [r[0] for r in cur.fetchall()]
    letter_codes = [c for c in codes if c.split('-')[0] in LETTER_TO_P]
    p_codes = [c for c in codes if c.split('-')[0] in P_TO_LETTER]
    print(f"dc2s_kpis.kpi_code: {len(codes)} unique ({len(letter_codes)} letter-format, {len(p_codes)} P-format)")

    cur.execute("SELECT DISTINCT pillar FROM dc2s_kpis ORDER BY pillar")
    pillars = [r[0] for r in cur.fetchall()]
    print(f"dc2s_kpis.pillar:   {pillars}")

    # pillar_scores
    cur.execute("SELECT DISTINCT pillar_code FROM pillar_scores ORDER BY pillar_code")
    ps_pillars = [r[0] for r in cur.fetchall()]
    print(f"pillar_scores.pillar_code: {ps_pillars}")

    # kpi_scores
    cur.execute("SELECT COUNT(DISTINCT kpi_code) FROM kpi_scores")
    ks_count = cur.fetchone()[0]
    if ks_count > 0:
        cur.execute("SELECT DISTINCT kpi_code FROM kpi_scores ORDER BY kpi_code LIMIT 10")
        ks_sample = [r[0] for r in cur.fetchall()]
        print(f"kpi_scores.kpi_code: {ks_count} unique (sample: {ks_sample})")
    else:
        print(f"kpi_scores.kpi_code: 0 rows")

    # customer_configs JSON
    cur.execute("""
        SELECT customer_id, dc2s_pillar_weights, dc2s_enabled_kpis
        FROM customer_configs
        WHERE dc2s_pillar_weights IS NOT NULL
        LIMIT 3
    """)
    for row in cur.fetchall():
        cid, pw, ek = row
        pw_keys = list(pw.keys()) if pw else []
        ek_sample = ek[:3] if ek else []
        print(f"customer_configs[{cid}]: pillar_weights keys={pw_keys}, enabled_kpis sample={ek_sample}")

    print()


def migrate(conn, direction='forward', dry_run=True):
    """Run the migration."""
    if direction == 'forward':
        kpi_map = LETTER_TO_P  # AI→P3, CH→P4, etc.
        pillar_map = LETTER_TO_P
        desc = "Letter-format → P-format"
        src_prefixes = LETTER_PREFIXES
    else:
        kpi_map = P_TO_LETTER  # P3→AI, P4→CH, etc.
        pillar_map = P_TO_LETTER
        desc = "P-format → Letter-format (ROLLBACK)"
        src_prefixes = P_PREFIXES

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migration: {desc}")
    print("=" * 60)

    cur = conn.cursor()
    total_updates = 0

    # 1. dc2s_kpis.kpi_code
    for old_prefix, new_prefix in kpi_map.items():
        cur.execute(
            "SELECT COUNT(*) FROM dc2s_kpis WHERE kpi_code LIKE %s",
            (f'{old_prefix}-%',)
        )
        count = cur.fetchone()[0]
        if count > 0:
            print(f"  dc2s_kpis.kpi_code: {old_prefix}-* → {new_prefix}-* ({count} rows)")
            if not dry_run:
                cur.execute(
                    "UPDATE dc2s_kpis SET kpi_code = REPLACE(kpi_code, %s, %s) WHERE kpi_code LIKE %s",
                    (f'{old_prefix}-', f'{new_prefix}-', f'{old_prefix}-%')
                )
            total_updates += count

    # 2. dc2s_kpis.pillar
    for old_pillar, new_pillar in pillar_map.items():
        cur.execute("SELECT COUNT(*) FROM dc2s_kpis WHERE pillar = %s", (old_pillar,))
        count = cur.fetchone()[0]
        if count > 0:
            print(f"  dc2s_kpis.pillar: {old_pillar} → {new_pillar} ({count} rows)")
            if not dry_run:
                cur.execute("UPDATE dc2s_kpis SET pillar = %s WHERE pillar = %s", (new_pillar, old_pillar))
            total_updates += count

    # 3. kpi_scores.kpi_code
    for old_prefix, new_prefix in kpi_map.items():
        cur.execute("SELECT COUNT(*) FROM kpi_scores WHERE kpi_code LIKE %s", (f'{old_prefix}-%',))
        count = cur.fetchone()[0]
        if count > 0:
            print(f"  kpi_scores.kpi_code: {old_prefix}-* → {new_prefix}-* ({count} rows)")
            if not dry_run:
                cur.execute(
                    "UPDATE kpi_scores SET kpi_code = REPLACE(kpi_code, %s, %s) WHERE kpi_code LIKE %s",
                    (f'{old_prefix}-', f'{new_prefix}-', f'{old_prefix}-%')
                )
            total_updates += count

    # 4. pillar_scores.pillar_code
    for old_pillar, new_pillar in pillar_map.items():
        cur.execute("SELECT COUNT(*) FROM pillar_scores WHERE pillar_code = %s", (old_pillar,))
        count = cur.fetchone()[0]
        if count > 0:
            print(f"  pillar_scores.pillar_code: {old_pillar} → {new_pillar} ({count} rows)")
            if not dry_run:
                cur.execute("UPDATE pillar_scores SET pillar_code = %s WHERE pillar_code = %s", (new_pillar, old_pillar))
            total_updates += count

    # 5. health_scores JSON columns (contributing_pillars, pillar_weights)
    cur.execute("SELECT health_score_id, contributing_pillars, pillar_weights FROM health_scores WHERE contributing_pillars IS NOT NULL OR pillar_weights IS NOT NULL")
    hs_rows = cur.fetchall()
    hs_updated = 0
    for hs_id, cp, pw in hs_rows:
        new_cp = convert_json_keys(cp, pillar_map) if cp else cp
        new_pw = convert_json_keys(pw, pillar_map) if pw else pw
        if new_cp != cp or new_pw != pw:
            hs_updated += 1
            if not dry_run:
                cur.execute(
                    "UPDATE health_scores SET contributing_pillars = %s, pillar_weights = %s WHERE health_score_id = %s",
                    (Json(new_cp), Json(new_pw), hs_id)
                )
    if hs_updated:
        print(f"  health_scores JSON columns: {hs_updated} rows updated")
        total_updates += hs_updated

    # 6. customer_configs JSON columns
    cur.execute("""
        SELECT config_id, customer_id, dc2s_pillar_weights, dc2s_enabled_kpis, dc2s_kpi_overrides, dc2s_kpi_weights
        FROM customer_configs
    """)
    cc_rows = cur.fetchall()
    cc_updated = 0
    for cc_id, cid, pw, ek, ko, kw in cc_rows:
        new_pw = convert_json_keys(pw, pillar_map) if pw else pw
        new_ek = convert_json_keys(ek, kpi_map) if ek else ek
        new_ko = convert_json_keys(ko, kpi_map) if ko else ko
        new_kw = convert_json_keys(kw, kpi_map) if kw else kw
        if new_pw != pw or new_ek != ek or new_ko != ko or new_kw != kw:
            cc_updated += 1
            if not dry_run:
                cur.execute("""
                    UPDATE customer_configs
                    SET dc2s_pillar_weights = %s, dc2s_enabled_kpis = %s,
                        dc2s_kpi_overrides = %s, dc2s_kpi_weights = %s
                    WHERE config_id = %s
                """, (Json(new_pw), Json(new_ek), Json(new_ko), Json(new_kw), cc_id))
            # Log detail for first few
            if cc_updated <= 3:
                print(f"  customer_configs[{cid}]: pillar_weights keys {list((pw or {}).keys())} → {list((new_pw or {}).keys())}")
    if cc_updated:
        print(f"  customer_configs JSON columns: {cc_updated} rows updated")
        total_updates += cc_updated

    print(f"\nTotal updates: {total_updates}")

    if dry_run:
        print("\n[DRY RUN] No changes applied. Run with --apply to execute.")
        conn.rollback()
    else:
        conn.commit()
        print("\nMigration committed successfully.")


def main():
    parser = argparse.ArgumentParser(description='Migrate KPI codes to P-format')
    parser.add_argument('--apply', action='store_true', help='Apply changes (default: dry-run)')
    parser.add_argument('--rollback', action='store_true', help='Reverse migration (P-format → letter-format)')
    parser.add_argument('--audit-only', action='store_true', help='Only audit, no migration')
    args = parser.parse_args()

    conn = psycopg2.connect(get_db_url())

    try:
        audit(conn)

        if args.audit_only:
            return

        direction = 'rollback' if args.rollback else 'forward'
        dry_run = not args.apply

        migrate(conn, direction=direction, dry_run=dry_run)

        if not dry_run:
            print("\n=== POST-MIGRATION AUDIT ===")
            audit(conn)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
