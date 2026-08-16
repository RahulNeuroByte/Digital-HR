"""
ChromaDB persistent vector store wrapper.

Uses Streamlit st.cache_resource to initialize the ChromaDB client, collection,
and policy metadata ONCE at application startup.
"""
from __future__ import annotations

import time
from functools import lru_cache
import chromadb

from app.config.settings import settings
from app.retrieval.embeddings import embed_query, embed_texts
from app.schemas.models import Chunk, RetrievedChunk
from app.utils.logging import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "hr_policies"


def _load_chroma_resources():
    settings.ensure_directories()
    client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )
    return client, collection


try:
    import streamlit as st

    @st.cache_resource(show_spinner=False)
    def _get_cached_chroma_resources():
        return _load_chroma_resources()

    @st.cache_resource(show_spinner=False)
    def list_indexed_policies() -> list[str]:
        _, collection = _get_cached_chroma_resources()
        result = collection.get(include=["metadatas"])
        names = {m["policy_name"] for m in result.get("metadatas", []) if m and "policy_name" in m}
        return sorted(names)
except Exception:
    @lru_cache(maxsize=1)
    def _get_cached_chroma_resources():
        return _load_chroma_resources()

    @lru_cache(maxsize=1)
    def list_indexed_policies() -> list[str]:
        _, collection = _get_cached_chroma_resources()
        result = collection.get(include=["metadatas"])
        names = {m["policy_name"] for m in result.get("metadatas", []) if m and "policy_name" in m}
        return sorted(names)


def _get_collection():
    _, collection = _get_cached_chroma_resources()
    return collection


def upsert_chunks(chunks: list[Chunk]) -> None:
    """Embed and (re)index a batch of chunks. Idempotent by chunk id."""
    if not chunks:
        return

    collection = _get_collection()
    texts = [c.text for c in chunks]
    vectors, _, _ = embed_texts(texts)

    collection.upsert(
        ids=[c.id for c in chunks],
        embeddings=vectors,
        documents=texts,
        metadatas=[
            {
                "document": c.document,
                "policy_name": c.policy_name,
                "page": c.page,
                "chunk_index": c.chunk_index,
                "extraction_method": c.extraction_method,
            }
            for c in chunks
        ],
    )
    try:
        list_indexed_policies.clear()
    except Exception:
        pass
    logger.info("Upserted %d chunks into '%s'", len(chunks), COLLECTION_NAME)


def query_with_metrics(
    query_text: str,
    top_k: int | None = None,
    policy_name: str | None = None,
) -> tuple[list[RetrievedChunk], dict[str, float]]:
    """
    Semantic search with detailed stage-by-stage latency tracking:
    - embedding_init_ms
    - query_embedding_ms
    - chroma_init_ms
    - chroma_retrieval_ms
    """
    t_chroma_init_0 = time.perf_counter()
    collection = _get_collection()
    t_chroma_init_1 = time.perf_counter()
    chroma_init_ms = (t_chroma_init_1 - t_chroma_init_0) * 1000.0

    vector, embed_init_ms, query_encode_ms = embed_query(query_text)

    where = {"policy_name": policy_name} if policy_name else None

    t_ret_0 = time.perf_counter()
    result = collection.query(
        query_embeddings=[vector],
        n_results=top_k or settings.top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    t_ret_1 = time.perf_counter()
    chroma_retrieval_ms = (t_ret_1 - t_ret_0) * 1000.0

    metrics = {
        "embedding_init_ms": embed_init_ms,
        "query_embedding_ms": query_encode_ms,
        "chroma_init_ms": chroma_init_ms,
        "chroma_retrieval_ms": chroma_retrieval_ms,
    }

    if not result["ids"] or not result["ids"][0]:
        return [], metrics

    retrieved: list[RetrievedChunk] = []
    for i, chunk_id in enumerate(result["ids"][0]):
        meta = result["metadatas"][0][i]
        distance = result["distances"][0][i]
        similarity = 1.0 - distance
        retrieved.append(
            RetrievedChunk(
                id=chunk_id,
                document=meta["document"],
                policy_name=meta["policy_name"],
                page=meta["page"],
                chunk_index=meta["chunk_index"],
                extraction_method=meta["extraction_method"],
                text=result["documents"][0][i],
                score=similarity,
            )
        )
    return retrieved, metrics


def query(
    query_text: str,
    top_k: int | None = None,
    policy_name: str | None = None,
) -> list[RetrievedChunk]:
    """Backward-compatible query wrapper."""
    chunks, _ = query_with_metrics(query_text, top_k, policy_name)
    return chunks
