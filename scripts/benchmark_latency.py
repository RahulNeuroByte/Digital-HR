"""
Benchmark script to measure latency of First Query vs Second Query
and output stage-by-stage performance breakdowns.

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\benchmark_latency.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.settings import settings
from app.retrieval.retriever import retrieve
from app.llm.gemini_client import generate_answer


def run_benchmark():
    print("Digital HR - Latency & Cold-Start Benchmark")
    print("=" * 60)

    # 1. Warm-up System (Simulates Application Startup)
    t_warm_0 = time.perf_counter()
    from app.retrieval.embeddings import get_embedding_model
    from app.retrieval.vector_store import _get_cached_chroma_resources, list_indexed_policies
    from app.llm.gemini_client import _get_client

    get_embedding_model()
    _get_cached_chroma_resources()
    list_indexed_policies()
    if settings.gemini_configured:
        _get_client()
    t_warm_1 = time.perf_counter()
    warmup_duration_ms = (t_warm_1 - t_warm_0) * 1000.0
    print(f"App Startup Warm-up Completed in: {warmup_duration_ms:.2f} ms")
    print("-" * 60)

    # Test Query 1 (First User Query after app startup)
    query_1 = "What is the notice period policy duration?"
    print(f"Running Query 1: '{query_1}'")
    t0 = time.perf_counter()
    chunks_1, policy_match_1, metrics_1 = retrieve(query_1)
    detected_policy_1 = policy_match_1.policy_name if policy_match_1.matched else None
    ans_1 = generate_answer(query_1, chunks_1, detected_policy_1, metrics_1)
    t1 = time.perf_counter()

    print(f"  - Policy Scope:               {ans_1.detected_policy or 'Cross-policy'}")
    print(f"  - Policy Detection Latency:    {ans_1.policy_detection_ms:.2f} ms")
    print(f"  - Embedding Model Init:        {ans_1.embedding_init_ms:.2f} ms")
    print(f"  - Query Embedding Encode:      {ans_1.query_embedding_ms:.2f} ms")
    print(f"  - ChromaDB Client Init:        {ans_1.chroma_init_ms:.2f} ms")
    print(f"  - ChromaDB Vector Retrieval:   {ans_1.chroma_retrieval_ms:.2f} ms")
    print(f"  - Context Prep & Dedup:        {ans_1.context_prep_ms:.2f} ms")
    print(f"  - Gemini TTFT / Generation:    {ans_1.gemini_ttft_ms:.2f} ms")
    print(f"  * TOTAL FIRST QUERY LATENCY:  {ans_1.total_latency_ms:.2f} ms ({ans_1.total_latency_ms/1000.0:.2f} s)")
    print("-" * 60)

    # Test Query 2 (Second User Query)
    query_2 = "What are the rules for moonlighting?"
    print(f"Running Query 2: '{query_2}'")
    t2 = time.perf_counter()
    chunks_2, policy_match_2, metrics_2 = retrieve(query_2)
    detected_policy_2 = policy_match_2.policy_name if policy_match_2.matched else None
    ans_2 = generate_answer(query_2, chunks_2, detected_policy_2, metrics_2)
    t3 = time.perf_counter()

    print(f"  - Policy Scope:               {ans_2.detected_policy or 'Cross-policy'}")
    print(f"  - Policy Detection Latency:    {ans_2.policy_detection_ms:.2f} ms")
    print(f"  - Embedding Model Init:        {ans_2.embedding_init_ms:.2f} ms")
    print(f"  - Query Embedding Encode:      {ans_2.query_embedding_ms:.2f} ms")
    print(f"  - ChromaDB Client Init:        {ans_2.chroma_init_ms:.2f} ms")
    print(f"  - ChromaDB Vector Retrieval:   {ans_2.chroma_retrieval_ms:.2f} ms")
    print(f"  - Context Prep & Dedup:        {ans_2.context_prep_ms:.2f} ms")
    print(f"  - Gemini TTFT / Generation:    {ans_2.gemini_ttft_ms:.2f} ms")
    print(f"  * TOTAL SECOND QUERY LATENCY: {ans_2.total_latency_ms:.2f} ms ({ans_2.total_latency_ms/1000.0:.2f} s)")
    print("=" * 60)


if __name__ == "__main__":
    run_benchmark()
