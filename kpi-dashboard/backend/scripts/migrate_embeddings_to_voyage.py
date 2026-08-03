#!/usr/bin/env python3
"""Re-embed migration: OpenAI text-embedding-3-large (3072d) -> Voyage voyage-3-large (1024d).

The embedding *code* is already migrated to Voyage. Because the vector
dimension changed (3072 -> 1024), every existing Qdrant collection holding
old vectors is now incompatible and MUST be dropped and rebuilt — Qdrant
rejects inserts/searches whose vector size differs from the collection.

This script is the destructive re-embed step. It:
  1. Drops every Qdrant collection whose vector size != 1024
     (i.e. all collections still on the old 3072-dim OpenAI embeddings).
  2. Re-embeds qualitative signals for the requested customers via the
     already-migrated embed_signals_qdrant.embed_and_upload_signals(recreate=True),
     which recreates the signals collection at 1024 dims using Voyage.
  3. Leaves the enhanced-RAG knowledge-base + feedback collections dropped;
     they rebuild lazily (at 1024 dims) on the next query/build.

Prerequisites:
  VOYAGE_API_KEY   — Voyage AI key (env, or per-customer in CustomerConfig)
  QDRANT_URL / QDRANT_API_KEY — Qdrant Cloud
  DATABASE_URL     — so signal rows can be read

Usage (inside the platform container / app context):
  python scripts/migrate_embeddings_to_voyage.py --all
  python scripts/migrate_embeddings_to_voyage.py --customer-id 336
  python scripts/migrate_embeddings_to_voyage.py --all --drop-only      # only drop stale collections
  python scripts/migrate_embeddings_to_voyage.py --all --dry-run        # show what would change

This is the runbook's automation; see
docs/RUNBOOK_voyage_embeddings_migration.md for the full procedure.
"""

import argparse
import os
import sys

TARGET_DIM = 1024  # voyage-3-large default output dimension


def _qdrant_client():
    from qdrant_client import QdrantClient
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    if not url or not api_key:
        print("ERROR: QDRANT_URL and QDRANT_API_KEY must be set.", file=sys.stderr)
        sys.exit(2)
    return QdrantClient(url=url, api_key=api_key, timeout=60)


def _collection_dim(client, name):
    """Return the configured vector size for a collection, or None if unknown."""
    try:
        info = client.get_collection(name)
        vectors = info.config.params.vectors
        # Single unnamed vector config exposes .size; named configs are a dict.
        size = getattr(vectors, "size", None)
        if size is None and isinstance(vectors, dict):
            sizes = {getattr(v, "size", None) for v in vectors.values()}
            size = next(iter(sizes)) if len(sizes) == 1 else None
        return size
    except Exception as e:
        print(f"  ! could not read dim for {name}: {e}")
        return None


def drop_stale_collections(client, dry_run=False):
    """Drop every collection whose vector size != TARGET_DIM."""
    dropped = []
    collections = client.get_collections().collections
    print(f"Found {len(collections)} Qdrant collection(s).")
    for c in collections:
        dim = _collection_dim(client, c.name)
        if dim == TARGET_DIM:
            print(f"  = {c.name}: already {TARGET_DIM}d — keeping")
            continue
        print(f"  x {c.name}: dim={dim} != {TARGET_DIM} — {'WOULD DROP' if dry_run else 'DROPPING'}")
        if not dry_run:
            try:
                client.delete_collection(c.name)
                dropped.append(c.name)
            except Exception as e:
                print(f"    ! failed to drop {c.name}: {e}")
    return dropped


def reembed_signals(customer_ids, dry_run=False):
    """Re-embed qualitative signals for each customer with Voyage (recreate=True)."""
    from embed_signals_qdrant import embed_and_upload_signals, get_qdrant_client
    qclient = get_qdrant_client()
    for cid in customer_ids:
        print(f"\n--- Re-embedding signals for customer {cid} ---")
        if dry_run:
            print("  (dry-run) would recreate signals collection at 1024d and re-embed")
            continue
        try:
            embed_and_upload_signals(customer_id=cid, qdrant_client=qclient, recreate=True)
        except TypeError:
            # Older signature without an injectable client.
            embed_and_upload_signals(customer_id=cid, recreate=True)
        except Exception as e:
            print(f"  ! re-embed failed for customer {cid}: {e}")


def _active_customers():
    from embed_signals_qdrant import get_active_customers
    return get_active_customers()


def main():
    ap = argparse.ArgumentParser(description="Re-embed OpenAI->Voyage (3072->1024)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="Process all active customers")
    g.add_argument("--customer-id", type=int, help="Process a single customer")
    ap.add_argument("--drop-only", action="store_true",
                    help="Only drop stale (non-1024d) collections; skip re-embed")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would change without modifying Qdrant")
    args = ap.parse_args()

    if not os.getenv("VOYAGE_API_KEY"):
        print("WARNING: VOYAGE_API_KEY not set — per-customer keys must exist or re-embed will fail.")

    client = _qdrant_client()

    print("=" * 64)
    print("STEP 1 — drop stale (non-1024d) collections")
    print("=" * 64)
    dropped = drop_stale_collections(client, dry_run=args.dry_run)
    print(f"\nDropped {len(dropped)} collection(s).")

    if args.drop_only:
        print("\n--drop-only: skipping re-embed. Enhanced-RAG/feedback rebuild lazily on next query.")
        return 0

    customer_ids = [args.customer_id] if args.customer_id else _active_customers()
    print("\n" + "=" * 64)
    print(f"STEP 2 — re-embed signals for {len(customer_ids)} customer(s) with Voyage")
    print("=" * 64)
    reembed_signals(customer_ids, dry_run=args.dry_run)

    print("\nDone. Enhanced-RAG knowledge-base + feedback collections rebuild")
    print("lazily (at 1024d) on the next query/build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
