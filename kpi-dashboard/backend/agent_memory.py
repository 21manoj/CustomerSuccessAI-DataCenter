#!/usr/bin/env python3
"""
Agent Memory System — Persistent Semantic Memory for CS Pulse GrowthPulse
==========================================================================
Gives every agent persistent, per-account and per-customer memory with:
  1. Short-term buffer  — recent turns within a session
  2. Long-term episodic — past analysis snapshots, playbook outcomes
  3. Semantic index     — Qdrant-backed vector search over memories
  4. Entity state       — named entity facts (contacts, ARR, tier, …)
  5. Agent scratchpad   — working memory for multi-step reasoning chains

Storage backends:
  • SQLAlchemy (primary) — all memory records
  • Qdrant (semantic)    — vector-indexed subset for similarity search
"""

from __future__ import annotations

import json
import hashlib
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Boolean, JSON,
    Index, create_engine, func,
)
from sqlalchemy.orm import declarative_base, Session, sessionmaker

try:
    from utils.llm_budget_controller import can_call as _budget_can_call, record_usage as _budget_record
except Exception:
    _budget_can_call = None
    _budget_record = None

import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


# ============================================================
# MEMORY TYPES
# ============================================================

class MemoryType(str, Enum):
    SHORT_TERM = "short_term"       # Current session / conversation buffer
    EPISODIC = "episodic"           # Past analysis results, playbook outcomes
    ENTITY = "entity"               # Named-entity facts (contact, ARR, tier)
    SEMANTIC = "semantic"           # Free-form knowledge indexed by embedding
    SCRATCHPAD = "scratchpad"       # Agent working memory for reasoning chains


class MemoryScope(str, Enum):
    ACCOUNT = "account"             # Per-account memory
    CUSTOMER = "customer"           # Per-customer (tenant) memory
    GLOBAL = "global"               # Shared across all tenants (rare)
    AGENT = "agent"                 # Agent-specific state
    SHARED = "shared"               # Cross-agent shared intelligence (readable by all agents)


# ============================================================
# DATABASE MODEL
# ============================================================

class MemoryRecord(Base):
    """Persistent memory record stored in SQL."""
    __tablename__ = "agent_memory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, nullable=False, index=True)
    account_id = Column(String(128), nullable=True, index=True)
    agent_id = Column(String(64), nullable=True, index=True)

    memory_type = Column(String(32), nullable=False, index=True)
    scope = Column(String(32), nullable=False, default="account")
    namespace = Column(String(128), nullable=True)

    # Content
    key = Column(String(256), nullable=True)
    content = Column(Text, nullable=False)
    extra_metadata = Column("metadata", JSON, nullable=True)

    # Embedding
    embedding_id = Column(String(128), nullable=True)  # Qdrant point ID

    # Lifecycle
    importance = Column(Float, default=0.5)
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)
    is_archived = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_memory_customer_account", "customer_id", "account_id"),
        Index("ix_memory_type_scope", "memory_type", "scope"),
        Index("ix_memory_namespace_key", "namespace", "key"),
    )


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class MemoryEntry:
    """In-memory representation of a memory record."""
    memory_type: MemoryType
    scope: MemoryScope
    content: str
    customer_id: int
    account_id: Optional[str] = None
    agent_id: Optional[str] = None
    namespace: Optional[str] = None
    key: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    importance: float = 0.5
    ttl_hours: Optional[float] = None  # auto-expire after N hours

    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]


@dataclass
class MemorySearchResult:
    """Result from a memory search."""
    content: str
    memory_type: str
    scope: str
    namespace: Optional[str]
    key: Optional[str]
    metadata: Optional[Dict]
    importance: float
    similarity: Optional[float] = None  # set when vector-searched
    created_at: Optional[str] = None


@dataclass
class AgentState:
    """Serializable agent state — persisted between runs."""
    agent_id: str
    customer_id: int
    account_id: Optional[str]
    step: int = 0
    reasoning_chain: List[str] = field(default_factory=list)
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    status: str = "idle"
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================
# MEMORY STORE
# ============================================================

class MemoryStore:
    """
    Central memory store — SQL + optional Qdrant vector index.

    Usage:
        store = MemoryStore(db_url)
        store.remember(MemoryEntry(...))
        results = store.recall(customer_id=1, account_id='123', query='churn signals')
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        qdrant_client=None,
        qdrant_collection: str = "agent_memory_vectors",
    ):
        import os
        self.db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///agent_memory.db")
        self.engine = create_engine(self.db_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.qdrant = qdrant_client
        self.qdrant_collection = qdrant_collection

    # ──────────────────────── WRITE ────────────────────────

    def remember(self, entry: MemoryEntry) -> int:
        """Store a new memory. Returns the record ID."""
        session = self.SessionLocal()
        try:
            expires = None
            if entry.ttl_hours:
                expires = datetime.utcnow() + timedelta(hours=entry.ttl_hours)

            record = MemoryRecord(
                customer_id=entry.customer_id,
                account_id=entry.account_id,
                agent_id=entry.agent_id,
                memory_type=entry.memory_type.value,
                scope=entry.scope.value,
                namespace=entry.namespace,
                key=entry.key,
                content=entry.content,
                extra_metadata=entry.metadata,
                importance=entry.importance,
                expires_at=expires,
            )
            session.add(record)
            session.commit()
            record_id = record.id

            # Optionally index in Qdrant
            if self.qdrant and entry.memory_type in (
                MemoryType.EPISODIC, MemoryType.SEMANTIC
            ):
                self._index_in_qdrant(record_id, entry)

            return record_id
        finally:
            session.close()

    def remember_entity(
        self,
        customer_id: int,
        account_id: str,
        entity_key: str,
        value: str,
        metadata: Optional[Dict] = None,
    ) -> int:
        """Upsert a named-entity fact (contact name, tier, ARR, etc.)."""
        session = self.SessionLocal()
        try:
            existing = (
                session.query(MemoryRecord)
                .filter_by(
                    customer_id=customer_id,
                    account_id=account_id,
                    memory_type=MemoryType.ENTITY.value,
                    key=entity_key,
                    is_archived=False,
                )
                .first()
            )
            if existing:
                existing.content = value
                existing.extra_metadata = metadata
                existing.last_accessed = datetime.utcnow()
                existing.access_count += 1
                session.commit()
                return existing.id
            else:
                return self.remember(
                    MemoryEntry(
                        memory_type=MemoryType.ENTITY,
                        scope=MemoryScope.ACCOUNT,
                        content=value,
                        customer_id=customer_id,
                        account_id=account_id,
                        namespace="entity",
                        key=entity_key,
                        metadata=metadata,
                        importance=0.8,
                    )
                )
        finally:
            session.close()

    def save_agent_state(self, state: AgentState) -> int:
        """Persist agent state (scratchpad) for multi-step reasoning."""
        state.last_updated = datetime.utcnow().isoformat()
        return self.remember(
            MemoryEntry(
                memory_type=MemoryType.SCRATCHPAD,
                scope=MemoryScope.AGENT,
                content=json.dumps(asdict(state)),
                customer_id=state.customer_id,
                account_id=state.account_id,
                agent_id=state.agent_id,
                namespace="agent_state",
                key=state.agent_id,
                importance=1.0,
            )
        )

    # ──────────────────────── READ ─────────────────────────

    def recall(
        self,
        customer_id: int,
        account_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        namespace: Optional[str] = None,
        key: Optional[str] = None,
        limit: int = 20,
        min_importance: float = 0.0,
        include_expired: bool = False,
    ) -> List[MemorySearchResult]:
        """Recall memories by structured filters."""
        session = self.SessionLocal()
        try:
            q = session.query(MemoryRecord).filter(
                MemoryRecord.customer_id == customer_id,
                MemoryRecord.is_archived == False,
                MemoryRecord.importance >= min_importance,
            )
            if account_id:
                q = q.filter(MemoryRecord.account_id == account_id)
            if memory_type:
                q = q.filter(MemoryRecord.memory_type == memory_type.value)
            if namespace:
                q = q.filter(MemoryRecord.namespace == namespace)
            if key:
                q = q.filter(MemoryRecord.key == key)
            if not include_expired:
                q = q.filter(
                    (MemoryRecord.expires_at == None) |  # noqa: E711
                    (MemoryRecord.expires_at > datetime.utcnow())
                )

            records = (
                q.order_by(MemoryRecord.importance.desc(), MemoryRecord.created_at.desc())
                .limit(limit)
                .all()
            )

            # Bump access counts
            for r in records:
                r.access_count += 1
                r.last_accessed = datetime.utcnow()
            session.commit()

            return [self._record_to_result(r) for r in records]
        finally:
            session.close()

    def recall_entities(
        self, customer_id: int, account_id: str
    ) -> Dict[str, str]:
        """Return all entity facts as a key → value dict."""
        results = self.recall(
            customer_id=customer_id,
            account_id=account_id,
            memory_type=MemoryType.ENTITY,
            limit=100,
        )
        return {r.key: r.content for r in results if r.key}

    def load_agent_state(
        self, agent_id: str, customer_id: int, account_id: Optional[str] = None
    ) -> Optional[AgentState]:
        """Load the most recent agent state."""
        results = self.recall(
            customer_id=customer_id,
            account_id=account_id,
            memory_type=MemoryType.SCRATCHPAD,
            namespace="agent_state",
            key=agent_id,
            limit=1,
        )
        if not results:
            return None
        try:
            data = json.loads(results[0].content)
            return AgentState(**data)
        except Exception:
            return None

    def semantic_search(
        self,
        customer_id: int,
        query_embedding: List[float],
        account_id: Optional[str] = None,
        top_k: int = 10,
    ) -> List[MemorySearchResult]:
        """Vector-similarity search over indexed memories via Qdrant."""
        if not self.qdrant:
            logger.warning("Qdrant not configured — falling back to SQL recall")
            return self.recall(customer_id=customer_id, account_id=account_id, limit=top_k)

        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            filters = [FieldCondition(key="customer_id", match=MatchValue(value=customer_id))]
            if account_id:
                filters.append(FieldCondition(key="account_id", match=MatchValue(value=account_id)))

            hits = self.qdrant.search(
                collection_name=self.qdrant_collection,
                query_vector=query_embedding,
                query_filter=Filter(must=filters),
                limit=top_k,
            )

            results = []
            for hit in hits:
                payload = hit.payload or {}
                results.append(
                    MemorySearchResult(
                        content=payload.get("content", ""),
                        memory_type=payload.get("memory_type", "semantic"),
                        scope=payload.get("scope", "account"),
                        namespace=payload.get("namespace"),
                        key=payload.get("key"),
                        metadata=payload.get("metadata"),
                        importance=payload.get("importance", 0.5),
                        similarity=hit.score,
                        created_at=payload.get("created_at"),
                    )
                )
            return results
        except Exception as e:
            logger.error(f"Qdrant semantic search failed: {e}")
            return self.recall(customer_id=customer_id, account_id=account_id, limit=top_k)

    # ──────────────────────── MANAGE ───────────────────────

    def forget(self, record_id: int) -> bool:
        """Archive (soft-delete) a memory record."""
        session = self.SessionLocal()
        try:
            rec = session.query(MemoryRecord).filter_by(id=record_id).first()
            if rec:
                rec.is_archived = True
                session.commit()
                return True
            return False
        finally:
            session.close()

    def prune_expired(self) -> int:
        """Archive all expired memory records. Returns count pruned."""
        session = self.SessionLocal()
        try:
            now = datetime.utcnow()
            count = (
                session.query(MemoryRecord)
                .filter(
                    MemoryRecord.expires_at != None,  # noqa: E711
                    MemoryRecord.expires_at < now,
                    MemoryRecord.is_archived == False,
                )
                .update({"is_archived": True})
            )
            session.commit()
            return count
        finally:
            session.close()

    def consolidate(
        self,
        customer_id: int,
        account_id: Optional[str] = None,
        max_short_term: int = 50,
    ) -> int:
        """
        Memory consolidation: promote important short-term memories to
        episodic and archive low-importance old entries.
        """
        session = self.SessionLocal()
        try:
            promoted = 0

            # 1. Find high-importance short-term memories
            short_term = (
                session.query(MemoryRecord)
                .filter_by(
                    customer_id=customer_id,
                    memory_type=MemoryType.SHORT_TERM.value,
                    is_archived=False,
                )
                .filter(MemoryRecord.importance >= 0.7)
                .all()
            )
            for rec in short_term:
                rec.memory_type = MemoryType.EPISODIC.value
                promoted += 1

            # 2. Archive oldest short-term beyond max
            if account_id:
                excess = (
                    session.query(MemoryRecord)
                    .filter_by(
                        customer_id=customer_id,
                        account_id=account_id,
                        memory_type=MemoryType.SHORT_TERM.value,
                        is_archived=False,
                    )
                    .order_by(MemoryRecord.created_at.desc())
                    .offset(max_short_term)
                    .all()
                )
                for rec in excess:
                    rec.is_archived = True

            session.commit()
            return promoted
        finally:
            session.close()

    def get_memory_stats(self, customer_id: int) -> Dict[str, Any]:
        """Return memory usage statistics for a customer."""
        session = self.SessionLocal()
        try:
            total = session.query(MemoryRecord).filter_by(
                customer_id=customer_id, is_archived=False
            ).count()
            by_type = {}
            for mt in MemoryType:
                count = session.query(MemoryRecord).filter_by(
                    customer_id=customer_id,
                    memory_type=mt.value,
                    is_archived=False,
                ).count()
                by_type[mt.value] = count

            return {
                "customer_id": customer_id,
                "total_active": total,
                "by_type": by_type,
            }
        finally:
            session.close()

    # ──────────────────────── PRIVATE ──────────────────────

    def _record_to_result(self, r: MemoryRecord) -> MemorySearchResult:
        return MemorySearchResult(
            content=r.content,
            memory_type=r.memory_type,
            scope=r.scope,
            namespace=r.namespace,
            key=r.key,
            metadata=r.extra_metadata,
            importance=r.importance,
            similarity=None,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )

    def _index_in_qdrant(self, record_id: int, entry: MemoryEntry):
        """Index a memory entry in Qdrant for semantic search."""
        try:
            import openai as _openai
            import os

            oai_key = os.getenv("OPENAI_API_KEY")
            if not oai_key:
                return

            _cid = getattr(entry, 'customer_id', 0) or 0
            # Budget check (fail-open)
            try:
                if _budget_can_call and not _budget_can_call(_cid, 'agent_memory'):
                    return
            except Exception:
                pass

            client = _openai.OpenAI(api_key=oai_key)
            resp = client.embeddings.create(
                model="text-embedding-3-small",
                input=entry.content[:8000],
            )
            embedding = resp.data[0].embedding

            # Record usage (fail-open)
            try:
                if _budget_record:
                    _budget_record(_cid, 'agent_memory',
                                   tokens_in=resp.usage.total_tokens, tokens_out=0,
                                   model='text-embedding-3-small')
            except Exception:
                pass

            from qdrant_client.models import PointStruct

            self.qdrant.upsert(
                collection_name=self.qdrant_collection,
                points=[
                    PointStruct(
                        id=record_id,
                        vector=embedding,
                        payload={
                            "customer_id": entry.customer_id,
                            "account_id": entry.account_id,
                            "memory_type": entry.memory_type.value,
                            "scope": entry.scope.value,
                            "namespace": entry.namespace,
                            "key": entry.key,
                            "content": entry.content[:2000],
                            "metadata": entry.metadata,
                            "importance": entry.importance,
                            "created_at": datetime.utcnow().isoformat(),
                        },
                    )
                ],
            )
        except Exception as e:
            logger.warning(f"Failed to index memory in Qdrant: {e}")


# ============================================================
# CONVENIENCE HELPERS
# ============================================================

_global_store: Optional[MemoryStore] = None


def get_memory_store() -> MemoryStore:
    """Get or create the global MemoryStore singleton."""
    global _global_store
    if _global_store is None:
        import os
        _global_store = MemoryStore(db_url=os.getenv("DATABASE_URL"))
    return _global_store


def remember_analysis_result(
    customer_id: int,
    account_id: str,
    analysis_type: str,
    result_summary: str,
    metadata: Optional[Dict] = None,
    importance: float = 0.7,
) -> int:
    """Store an analysis result as episodic memory."""
    store = get_memory_store()
    return store.remember(
        MemoryEntry(
            memory_type=MemoryType.EPISODIC,
            scope=MemoryScope.ACCOUNT,
            content=result_summary,
            customer_id=customer_id,
            account_id=account_id,
            namespace="analysis",
            key=analysis_type,
            metadata=metadata,
            importance=importance,
        )
    )


def remember_playbook_outcome(
    customer_id: int,
    account_id: str,
    playbook_id: str,
    outcome: str,
    kpi_improvements: Optional[Dict] = None,
    importance: float = 0.8,
) -> int:
    """Store a playbook execution outcome as episodic memory."""
    store = get_memory_store()
    return store.remember(
        MemoryEntry(
            memory_type=MemoryType.EPISODIC,
            scope=MemoryScope.ACCOUNT,
            content=outcome,
            customer_id=customer_id,
            account_id=account_id,
            namespace="playbook_outcome",
            key=playbook_id,
            metadata={"kpi_improvements": kpi_improvements} if kpi_improvements else None,
            importance=importance,
        )
    )


def get_account_context(customer_id: int, account_id: str) -> Dict[str, Any]:
    """
    Build a rich context object for an account by combining:
      - entity facts  (ARR, tier, CSM, contacts…)
      - recent episodic memories  (last 10 analyses / outcomes)
      - short-term buffer (last 5 turns)
    """
    store = get_memory_store()

    entities = store.recall_entities(customer_id, account_id)

    episodes = store.recall(
        customer_id=customer_id,
        account_id=account_id,
        memory_type=MemoryType.EPISODIC,
        limit=10,
    )

    short_term = store.recall(
        customer_id=customer_id,
        account_id=account_id,
        memory_type=MemoryType.SHORT_TERM,
        limit=5,
    )

    return {
        "entities": entities,
        "recent_episodes": [
            {"content": e.content, "namespace": e.namespace, "key": e.key}
            for e in episodes
        ],
        "short_term": [
            {"content": s.content, "created_at": s.created_at}
            for s in short_term
        ],
    }


def memory_stats_to_dict(customer_id: int) -> Dict:
    """Return memory stats suitable for an API response."""
    store = get_memory_store()
    return store.get_memory_stats(customer_id)
