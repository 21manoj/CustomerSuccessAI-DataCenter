"""
QDRANT Signal Search — semantic vector search for CS Pulse signals.

Stores signal embeddings in per-customer QDRANT collections and provides
semantic search for the signal analyst's Quant+Qual+LLM composite pipeline.

Usage:
    from utils.qdrant_signal_search import SignalVectorStore
    store = SignalVectorStore(customer_id=451)
    store.index_signals()  # Build/rebuild index from DB signals
    results = store.search("champion departure budget pressure", account_id=852, top_k=5)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Embedding config — Voyage AI (Anthropic's embedding partner)
# Replaces OpenAI text-embedding-3-small to eliminate the OpenAI dependency.
# Voyage-3-lite: 512 dims, $0.02/1M tokens, optimized for retrieval.
# Fallback: OpenAI text-embedding-3-small if VOYAGE_API_KEY not set.
EMBEDDING_PROVIDER = os.environ.get('EMBEDDING_PROVIDER', 'voyage')  # 'voyage' or 'openai'
VOYAGE_MODEL = 'voyage-3-lite'
VOYAGE_DIM = 512
OPENAI_MODEL = 'text-embedding-3-small'
OPENAI_DIM = 1536
# Active config (resolved at module load)
EMBEDDING_MODEL = VOYAGE_MODEL if EMBEDDING_PROVIDER == 'voyage' else OPENAI_MODEL
EMBEDDING_DIM = VOYAGE_DIM if EMBEDDING_PROVIDER == 'voyage' else OPENAI_DIM
COLLECTION_PREFIX = 'cspulse_signals'


class SignalVectorStore:
    """Per-customer QDRANT collection for signal semantic search."""

    def __init__(self, customer_id: int):
        self.customer_id = customer_id
        self.collection_name = f'{COLLECTION_PREFIX}_{customer_id}'
        self._client = None
        self._embed_client = None
        self._provider = EMBEDDING_PROVIDER

    @property
    def client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                url = os.environ.get('QDRANT_URL')
                api_key = os.environ.get('QDRANT_API_KEY')
                if not url or not api_key:
                    raise ValueError('QDRANT_URL and QDRANT_API_KEY must be set')
                self._client = QdrantClient(url=url, api_key=api_key, timeout=10)
            except ImportError:
                raise ImportError('qdrant-client not installed. pip install qdrant-client')
        return self._client

    @property
    def embed_client(self):
        """Lazy-init embedding client (Voyage or OpenAI fallback)."""
        if self._embed_client is None:
            if self._provider == 'voyage':
                try:
                    import voyageai
                    api_key = os.environ.get('VOYAGE_API_KEY')
                    if not api_key:
                        logger.warning('VOYAGE_API_KEY not set — falling back to OpenAI embeddings')
                        self._provider = 'openai'
                        return self.embed_client  # Recurse to OpenAI path
                    self._embed_client = voyageai.Client(api_key=api_key)
                except ImportError:
                    logger.warning('voyageai not installed — falling back to OpenAI embeddings')
                    self._provider = 'openai'
                    return self.embed_client

            if self._provider == 'openai':
                try:
                    import openai
                    api_key = os.environ.get('OPENAI_API_KEY')
                    if not api_key:
                        raise ValueError('No embedding API key available (VOYAGE_API_KEY or OPENAI_API_KEY)')
                    self._embed_client = openai.OpenAI(api_key=api_key)
                except ImportError:
                    raise ImportError('openai not installed. pip install openai')

        return self._embed_client

    def _embed(self, text: str) -> list[float]:
        """Generate embedding vector for text using configured provider."""
        if self._provider == 'voyage':
            result = self.embed_client.embed(
                [text[:8000]],
                model=VOYAGE_MODEL,
                input_type='query',
            )
            return result.embeddings[0]
        else:
            resp = self.embed_client.embeddings.create(
                model=OPENAI_MODEL,
                input=text[:8000],
            )
            return resp.data[0].embedding

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        truncated = [t[:8000] for t in texts]
        if self._provider == 'voyage':
            # Voyage supports up to 128 inputs per batch
            all_embeddings = []
            batch_size = 128
            for i in range(0, len(truncated), batch_size):
                batch = truncated[i:i + batch_size]
                result = self.embed_client.embed(
                    batch,
                    model=VOYAGE_MODEL,
                    input_type='document',
                )
                all_embeddings.extend(result.embeddings)
            return all_embeddings
        else:
            resp = self.embed_client.embeddings.create(
                model=OPENAI_MODEL,
                input=truncated,
            )
            return [d.embedding for d in resp.data]

    def _signal_text(self, node) -> str:
        """Build searchable text from a ContextNode (any type: SIGNAL, DECISION, OUTCOME, STAKEHOLDER)."""
        parts = []
        if hasattr(node, 'title'):
            # ContextNode model object
            parts.append(node.title or '')
            parts.append(f'Node type: {node.node_type or "SIGNAL"}')
            parts.append(f'Subtype: {node.node_subtype or "unknown"}')
            props = node.properties or {}
            if props.get('content'):
                parts.append(props['content'])
            if props.get('sentiment'):
                parts.append(f'Sentiment: {props["sentiment"]}')
            if props.get('stakeholder_name'):
                parts.append(f'Stakeholder: {props["stakeholder_name"]}')
            if props.get('decision_maker_role'):
                parts.append(f'Decision maker: {props["decision_maker_role"]}')
            # Revenue context for OUTCOME nodes
            if node.revenue_impact:
                parts.append(f'Revenue impact: ${node.revenue_impact:,.0f}')
            if node.revenue_impact_type:
                parts.append(f'Impact type: {node.revenue_impact_type}')
        elif isinstance(node, dict):
            parts.append(node.get('title', ''))
            parts.append(f'Node type: {node.get("node_type", "SIGNAL")}')
            parts.append(f'Subtype: {node.get("node_subtype", "unknown")}')
            props = node.get('properties', {})
            if props.get('content'):
                parts.append(props['content'])
            if props.get('sentiment'):
                parts.append(f'Sentiment: {props["sentiment"]}')
        return '\n'.join(p for p in parts if p)

    def ensure_collection(self):
        """Create collection if it doesn't exist. Uses active provider's dimension."""
        from qdrant_client.models import Distance, VectorParams
        dim = VOYAGE_DIM if self._provider == 'voyage' else OPENAI_DIM
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            logger.info(f'Created QDRANT collection: {self.collection_name} (dim={dim}, provider={self._provider})')
        else:
            # Check if existing collection has wrong dimension (provider switch)
            try:
                info = self.client.get_collection(self.collection_name)
                existing_dim = info.config.params.vectors.size if info.config else None
                if existing_dim and existing_dim != dim:
                    logger.warning(
                        f'Collection {self.collection_name} has dim={existing_dim} but '
                        f'provider={self._provider} needs dim={dim}. Rebuilding collection.'
                    )
                    self.client.delete_collection(self.collection_name)
                    self.client.create_collection(
                        collection_name=self.collection_name,
                        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
                    )
                    logger.info(f'Rebuilt QDRANT collection: {self.collection_name} (dim={dim})')
            except Exception as e:
                logger.debug(f'Collection dimension check failed (non-fatal): {e}')

    def index_signals(self, limit: int = 500) -> int:
        """
        Index all SIGNAL ContextNodes for this customer into QDRANT.
        Idempotent: uses node_id as point ID (upsert).

        Returns count of signals indexed.
        """
        from models import ContextNode
        self.ensure_collection()

        # Index ALL context graph node types — not just SIGNAL.
        # DECISION and OUTCOME nodes are equally important for semantic search:
        # - "what signals led to this outcome?" needs OUTCOME embeddings
        # - "what decisions were made?" needs DECISION embeddings
        # - Causal chain queries span all types
        nodes = (
            ContextNode.query
            .filter_by(customer_id=self.customer_id)
            .filter(ContextNode.node_type.in_(['SIGNAL', 'DECISION', 'OUTCOME', 'STAKEHOLDER']))
            .order_by(ContextNode.occurred_at.desc())
            .limit(limit)
            .all()
        )

        if not nodes:
            logger.info(f'No context graph nodes to index for customer {self.customer_id}')
            return 0

        # Build texts and payloads
        texts = []
        payloads = []
        point_ids = []

        for n in nodes:
            text = self._signal_text(n)
            if not text.strip():
                continue

            texts.append(text)
            point_ids.append(n.node_id)
            payloads.append({
                'node_id': n.node_id,
                'account_id': n.account_id,
                'customer_id': n.customer_id,
                'node_type': n.node_type or 'SIGNAL',
                'node_subtype': n.node_subtype or '',
                'source': n.source or 'customer',
                'title': n.title or '',
                'properties': json.dumps(n.properties or {}),
                'sentiment': (n.properties or {}).get('sentiment', 'neutral'),
                'occurred_at': n.occurred_at.isoformat() if n.occurred_at else '',
                'confidence': float(n.confidence) if n.confidence else 1.0,
                'revenue_impact': float(n.revenue_impact) if n.revenue_impact else 0,
                'revenue_impact_type': n.revenue_impact_type or '',
                'tier': n.tier or 1,
            })

        # Batch embed
        logger.info(f'Embedding {len(texts)} signals for customer {self.customer_id}...')
        embeddings = self._embed_batch(texts)

        # Upsert into QDRANT
        from qdrant_client.models import PointStruct
        points = [
            PointStruct(id=pid, vector=emb, payload=pay)
            for pid, emb, pay in zip(point_ids, embeddings, payloads)
        ]

        # Upload in batches of 100
        batch_size = 100
        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=self.collection_name,
                points=points[i:i + batch_size],
            )

        logger.info(f'Indexed {len(points)} signals into {self.collection_name}')
        return len(points)

    def search(
        self,
        query: str,
        account_id: Optional[int] = None,
        top_k: int = 5,
        threshold: float = 0.3,
    ) -> list[dict]:
        """
        Semantic search for signals similar to the query.

        Args:
            query: Natural language description (e.g., "champion departure causing engagement drop")
            account_id: Filter to specific account (None = all accounts)
            top_k: Max results
            threshold: Minimum cosine similarity (0-1)

        Returns:
            List of dicts: [{node_id, account_id, title, subtype, sentiment, score, ...}]
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        try:
            query_vector = self._embed(query)
        except Exception as e:
            logger.warning(f'Embedding failed for query: {e}')
            return []

        # Build filter
        must_conditions = [
            FieldCondition(key='customer_id', match=MatchValue(value=self.customer_id))
        ]
        if account_id:
            must_conditions.append(
                FieldCondition(key='account_id', match=MatchValue(value=account_id))
            )

        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=Filter(must=must_conditions),
                limit=top_k * 2,  # Fetch extra for threshold filtering
                with_payload=True,
                with_vectors=False,
            )
        except Exception as e:
            logger.warning(f'QDRANT search failed: {e}')
            return []

        # Apply threshold and format results
        hits = []
        for r in results:
            if r.score < threshold:
                continue
            payload = r.payload or {}
            hits.append({
                'node_id': payload.get('node_id'),
                'account_id': payload.get('account_id'),
                'node_type': payload.get('node_type', 'SIGNAL'),
                'title': payload.get('title', ''),
                'subtype': payload.get('node_subtype', ''),
                'source': payload.get('source', 'customer'),
                'sentiment': payload.get('sentiment', 'neutral'),
                'occurred_at': payload.get('occurred_at', ''),
                'confidence': payload.get('confidence', 1.0),
                'revenue_impact': payload.get('revenue_impact', 0),
                'revenue_impact_type': payload.get('revenue_impact_type', ''),
                'score': round(r.score, 3),
                'properties': json.loads(payload.get('properties', '{}')) if isinstance(payload.get('properties'), str) else payload.get('properties', {}),
            })
            if len(hits) >= top_k:
                break

        return hits

    def delete_collection(self):
        """Delete the entire collection (for cleanup/rebuild)."""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f'Deleted QDRANT collection: {self.collection_name}')
        except Exception:
            pass

    def stats(self) -> dict:
        """Return collection stats."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                'collection': self.collection_name,
                'points_count': info.points_count,
                'vectors_count': info.vectors_count,
                'status': info.status.value if info.status else 'unknown',
            }
        except Exception as e:
            return {'collection': self.collection_name, 'error': str(e)}
