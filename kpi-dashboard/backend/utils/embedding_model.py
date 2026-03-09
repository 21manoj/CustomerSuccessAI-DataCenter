"""
Shared SentenceTransformer singleton.

All RAG modules MUST use get_embedding_model() instead of creating their own
SentenceTransformer instance. The model is ~110MB in memory — loading it once
saves ~110MB per additional RAG module / per-customer instance.

Usage:
    from utils.embedding_model import get_embedding_model
    model = get_embedding_model()
    embeddings = model.encode(["some text"])
"""

import threading

_model = None
_lock = threading.Lock()
MODEL_NAME = 'all-MiniLM-L6-v2'
EMBEDDING_DIMENSION = 384


def get_embedding_model():
    """Return the shared SentenceTransformer instance (lazy, thread-safe)."""
    global _model
    if _model is None:
        with _lock:
            if _model is None:  # double-check after acquiring lock
                from sentence_transformers import SentenceTransformer
                print(f"Loading shared SentenceTransformer model ({MODEL_NAME})...")
                _model = SentenceTransformer(MODEL_NAME)
                print(f"✅ Shared SentenceTransformer model loaded ({MODEL_NAME})")
    return _model
