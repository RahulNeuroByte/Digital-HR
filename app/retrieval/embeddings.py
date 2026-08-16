"""
Local embedding model wrapper (Sentence Transformers).

Cached via Streamlit st.cache_resource so the embedding model loads ONCE
at application startup and remains pre-heated in RAM for sub-50ms query encoding.
"""
from __future__ import annotations

import time
from functools import lru_cache
from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _load_model_uncached():
    from sentence_transformers import SentenceTransformer

    logger.info("Initializing embedding model: %s", settings.embedding_model_name)
    try:
        model = SentenceTransformer(settings.embedding_model_name, local_files_only=True)
    except Exception:
        logger.info("Local model files not found, downloading from HuggingFace...")
        model = SentenceTransformer(settings.embedding_model_name)
    
    # Pre-heat PyTorch C++ kernel and memory allocation with a dummy tensor pass
    try:
        model.encode(["warmup tensor pass"], show_progress_bar=False, normalize_embeddings=True)
    except Exception as e:
        logger.warning("Embedding model pre-heat pass warning: %s", e)
    
    return model


# Attempt Streamlit st.cache_resource, fallback to lru_cache for pytest/CLI runners
try:
    import streamlit as st
    @st.cache_resource(show_spinner=False)
    def get_embedding_model():
        return _load_model_uncached()
except Exception:
    @lru_cache(maxsize=1)
    def get_embedding_model():
        return _load_model_uncached()


def get_model_with_metrics() -> tuple[any, float]:
    """Get the cached embedding model and return initialization latency in ms (0.0 ms if cached)."""
    t0 = time.perf_counter()
    model = get_embedding_model()
    t1 = time.perf_counter()
    init_ms = (t1 - t0) * 1000.0
    return model, init_ms


def embed_texts(texts: list[str]) -> tuple[list[list[float]], float, float]:
    """
    Embed a batch of strings.
    Returns (vectors, init_ms, encode_ms).
    """
    if not texts:
        return [], 0.0, 0.0

    model, init_ms = get_model_with_metrics()
    
    t0 = time.perf_counter()
    vectors = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    t1 = time.perf_counter()
    encode_ms = (t1 - t0) * 1000.0

    return vectors.tolist(), init_ms, encode_ms


def embed_query(text: str) -> tuple[list[float], float, float]:
    """
    Embed a single query string.
    Returns (vector, init_ms, query_encode_ms).
    """
    vectors, init_ms, encode_ms = embed_texts([text])
    return vectors[0], init_ms, encode_ms
