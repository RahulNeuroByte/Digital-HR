"""Pydantic models used across ingestion, retrieval, and the LLM layer."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A single indexed unit of policy text."""

    id: str
    document: str  # source filename
    policy_name: str  # human-readable policy name
    page: int
    chunk_index: int
    extraction_method: Literal["pymupdf", "ocr"]
    text: str


class RetrievedChunk(Chunk):
    """A Chunk returned from the vector store, with a similarity score."""

    score: float


class PolicyMatch(BaseModel):
    """Result of policy-name detection on a user query."""

    matched: bool
    policy_name: Optional[str] = None
    match_type: Optional[Literal["exact", "normalized", "abbreviation", "fuzzy"]] = None
    confidence: float = 0.0


class Source(BaseModel):
    policy_name: str
    document: str
    page: int


class ChatAnswer(BaseModel):
    """Final structured answer returned to the Streamlit UI."""

    answer: str
    detected_policy: Optional[str] = None
    sources: list[Source] = Field(default_factory=list)
    grounded: bool = True
    no_answer: bool = False

    # Benchmark & Detailed Stage Latency Breakdown (in milliseconds)
    policy_detection_ms: float = 0.0
    embedding_init_ms: float = 0.0
    query_embedding_ms: float = 0.0
    chroma_init_ms: float = 0.0
    chroma_retrieval_ms: float = 0.0
    context_prep_ms: float = 0.0
    retrieval_ms: float = 0.0
    gemini_ttft_ms: float = 0.0
    total_latency_ms: float = 0.0
    quality_rating: Literal["High", "Medium", "Low", "N/A"] = "N/A"
    chunks_used: int = 0
    from_cache: bool = False
