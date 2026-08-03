# Runbook — OpenAI → Voyage Embeddings Migration

**Change:** The RAG retrieval layer's embedding provider moved from OpenAI
`text-embedding-3-large` (3072-dim) to **Voyage AI `voyage-3-large` (1024-dim)**,
completing the all-Anthropic migration (generation already on Claude Sonnet 4.6;
Anthropic has no embeddings API, so Voyage — Anthropic's recommended partner — is used).

**Why this runbook exists:** the vector dimension changed (3072 → 1024). Qdrant
collections are dimension-locked, so **every existing collection holding old
vectors must be dropped and rebuilt.** Searches/inserts against a 3072-dim
collection with a 1024-dim query vector will error. This is a one-time,
**destructive** re-embed. The *code* is already migrated; this is the data step.

## What changed in code (already merged on `feature/anthropic-migration`)
- `embed_signals_qdrant.py` — `voyage-3-large`, dim 1024, `get_voyage_client()`, `voyage_key_utils`.
- `enhanced_rag_qdrant.py` — `voyage-3-large`, dim 1024, `_get_voyage_client()`, `_generate_embedding(input_type=…)`.
- `qdrant_feedback_loop.py` — Voyage embed for feedback vectors.
- `voyage_key_utils.py` — new key resolver (per-customer encrypted → `VOYAGE_API_KEY` env).
- `requirements-core.txt` — added `voyageai>=0.3.0`.

## Prerequisites
1. **Voyage API key** — set `VOYAGE_API_KEY` in the platform env (same place as `ANTHROPIC_API_KEY`).
   Get one at https://dashboard.voyageai.com. (Per-customer keys are also supported once a
   `voyage_api_key_encrypted` column is added to `CustomerConfig`; until then all tenants use the env key.)
2. `QDRANT_URL` + `QDRANT_API_KEY` reachable.
3. `DATABASE_URL` set (signal rows are read during re-embed).
4. New image built with `voyageai` installed (`pip install -r requirements.txt`).

## Procedure

> Run inside the platform container so Flask app context + DB are available.

### 1. Dry-run (no changes) — see what will be dropped
```bash
docker exec -e VOYAGE_API_KEY=$VOYAGE_API_KEY cspulse-platform \
  python scripts/migrate_embeddings_to_voyage.py --all --dry-run
```
Confirm the listed collections are the expected stale (non-1024d) ones.

### 2. Run the migration (drop stale collections + re-embed signals)
```bash
# All customers:
docker exec -e VOYAGE_API_KEY=$VOYAGE_API_KEY cspulse-platform \
  python scripts/migrate_embeddings_to_voyage.py --all

# Or a single tenant (e.g. 336):
docker exec -e VOYAGE_API_KEY=$VOYAGE_API_KEY cspulse-platform \
  python scripts/migrate_embeddings_to_voyage.py --customer-id 336
```
This (a) drops every collection whose vector size ≠ 1024, then (b) re-embeds
qualitative signals per customer via the migrated `embed_signals_qdrant`
(`recreate=True`), recreating the signals collection at 1024 dims with Voyage.

Equivalent signals-only path (already supported by the embed script):
```bash
docker exec cspulse-platform python embed_signals_qdrant.py --recreate
```

### 3. Lazy rebuilds
The **enhanced-RAG knowledge base** and **feedback** collections are left dropped;
they rebuild automatically at 1024 dims on the next RAG query/build. No action needed —
the first query after migration pays a one-time rebuild cost.

### 4. Verify
```bash
# Confirm no collection is still 3072-dim:
docker exec cspulse-platform python scripts/migrate_embeddings_to_voyage.py --all --dry-run
# (should report every collection as "already 1024d — keeping")
```
Then smoke-test a RAG path (executive Ask / signal analyst / governance RAG) and
confirm answers return without "key not configured" or dimension-mismatch errors.

## Rollback
There is no in-place rollback (old 3072 vectors are deleted). To revert:
1. `git revert` the migration commit (restores OpenAI embedding code), and
2. re-run the re-embed with the OpenAI code path + `OPENAI_API_KEY` to repopulate 3072-dim collections.
Keep `OPENAI_API_KEY` available until the Voyage migration is confirmed in production.

## Notes
- **`input_type` matters for retrieval quality:** corpus vectors are embedded with
  `input_type="document"`, query vectors with `input_type="query"` — Voyage uses this to
  asymmetrically optimize retrieval. This is wired into the migrated code.
- **Dimension option:** `voyage-3-large` supports 256/512/1024/2048 via `output_dimension`.
  We use the default 1024. If you change it, update `EMBEDDING_DIM` / `embedding_dimension`
  in the three modules **and** re-run this migration.
- **Cost attribution** for embeddings is not yet wired into `llm_usage_log` (was OpenAI-token based).
  Follow-up if per-tenant embedding cost tracking is needed.
