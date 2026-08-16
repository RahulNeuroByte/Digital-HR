"""
Gemini grounded-generation client with token streaming and latency metrics.

Uses Streamlit st.cache_resource to initialize the GenAI Client once at app load.
"""
from __future__ import annotations

import time
from functools import lru_cache
from typing import Generator, Callable

from app.config.settings import settings
from app.llm.prompts import SIYA_SYSTEM_INSTRUCTION, SYSTEM_INSTRUCTION, build_user_prompt, build_casual_chat_prompt, build_out_of_domain_prompt
from app.retrieval.cache import semantic_cache
from app.schemas.models import ChatAnswer, RetrievedChunk, Source
from app.utils.logging import get_logger

logger = get_logger(__name__)


def generate_casual_chat_stream(prompt_text: str) -> Generator[str, None, None]:
    """Stream casual AI colleague responses as Siya without vector RAG retrieval."""
    if not settings.gemini_configured:
        yield "Hey! I'm Siya, your AI HR colleague. How can I help you today?"
        return
    try:
        client = _get_client()
        response_stream = client.models.generate_content_stream(
            model=settings.gemini_model,
            contents=prompt_text,
            config={
                "system_instruction": SIYA_SYSTEM_INSTRUCTION,
                "temperature": 0.7,
                "max_output_tokens": 400,
            },
        )
        for chunk in response_stream:
            text_part = chunk.text or ""
            if text_part:
                yield text_part
    except Exception:
        yield "Hey there! I'm Siya, your AI HR colleague. How can I help you today?"


def calculate_quality_rating(chunks: list[RetrievedChunk]) -> str:
    """Classify retrieval quality based on highest similarity score."""
    if not chunks:
        return "N/A"
    top_score = max(c.score for c in chunks)
    if top_score >= 0.70:
        return "High"
    elif top_score >= 0.50:
        return "Medium"
    return "Low"

NO_CONTEXT_MESSAGE = (
    "I couldn't find sufficient information to answer this from the available "
    "HR policy documents."
)


def _load_genai_client():
    from google import genai

    logger.info("Initializing Google GenAI Client...")
    return genai.Client(api_key=settings.gemini_api_key)


try:
    import streamlit as st

    @st.cache_resource(show_spinner=False)
    def _get_client():
        return _load_genai_client()
except Exception:
    @lru_cache(maxsize=1)
    def _get_client():
        return _load_genai_client()


def _sources_from_chunks(chunks: list[RetrievedChunk]) -> list[Source]:
    seen = set()
    sources = []
    for c in chunks:
        key = (c.policy_name, c.page)
        if key not in seen:
            seen.add(key)
            sources.append(Source(policy_name=c.policy_name, document=c.document, page=c.page))
    return sources


def _extractive_fallback(chunks: list[RetrievedChunk]) -> str:
    """Used only when no GEMINI_API_KEY is configured."""
    lines = [
        "*(No GEMINI_API_KEY configured — showing relevant passages instead of LLM answer.)*\n"
    ]
    for c in chunks:
        lines.append(f"{c.text}\n")
    return "\n".join(lines)


def generate_answer_stream_with_container(
    question: str,
    chunks: list[RetrievedChunk],
    detected_policy: str | None,
    retrieval_metrics: dict[str, float] | None = None,
    on_complete: Callable[[ChatAnswer], None] | None = None,
) -> Generator[str, None, None]:
    """
    Yields tokens for streaming and calls on_complete(ChatAnswer) when done.
    """
    response_style = "Balanced"
    try:
        import streamlit as st
        response_style = st.session_state.get("preferences", {}).get("response_style", "Balanced")
    except Exception:
        pass

    # 1. Check semantic cache first (keyed with response_style)
    cache_key = f"{question}_{response_style}"
    cached_ans = semantic_cache.get(cache_key, detected_policy)
    if cached_ans:
        yield cached_ans.answer
        if on_complete:
            on_complete(cached_ans)
        return

    t_start = time.perf_counter()
    metrics = retrieval_metrics or {}
    quality_rating = calculate_quality_rating(chunks)

    policy_detection_ms = metrics.get("policy_detection_ms", 0.0)
    embedding_init_ms = metrics.get("embedding_init_ms", 0.0)
    query_embedding_ms = metrics.get("query_embedding_ms", 0.0)
    chroma_init_ms = metrics.get("chroma_init_ms", 0.0)
    chroma_retrieval_ms = metrics.get("chroma_retrieval_ms", 0.0)
    context_prep_ms = metrics.get("context_prep_ms", 0.0)
    retrieval_ms = metrics.get("retrieval_ms", 0.0)

    if not chunks:
        total_ms = (time.perf_counter() - t_start) * 1000.0 + retrieval_ms
        no_ans = ChatAnswer(
            answer=NO_CONTEXT_MESSAGE,
            detected_policy=detected_policy,
            no_answer=True,
            grounded=False,
            policy_detection_ms=policy_detection_ms,
            embedding_init_ms=embedding_init_ms,
            query_embedding_ms=query_embedding_ms,
            chroma_init_ms=chroma_init_ms,
            chroma_retrieval_ms=chroma_retrieval_ms,
            context_prep_ms=context_prep_ms,
            retrieval_ms=retrieval_ms,
            total_latency_ms=total_ms,
            quality_rating="N/A",
            chunks_used=0,
        )
        yield NO_CONTEXT_MESSAGE
        if on_complete:
            on_complete(no_ans)
        return

    sources = _sources_from_chunks(chunks)

    if not settings.gemini_configured:
        text = _extractive_fallback(chunks)
        yield text
        total_ms = (time.perf_counter() - t_start) * 1000.0 + retrieval_ms
        ans = ChatAnswer(
            answer=text,
            detected_policy=detected_policy,
            sources=sources,
            grounded=True,
            policy_detection_ms=policy_detection_ms,
            embedding_init_ms=embedding_init_ms,
            query_embedding_ms=query_embedding_ms,
            chroma_init_ms=chroma_init_ms,
            chroma_retrieval_ms=chroma_retrieval_ms,
            context_prep_ms=context_prep_ms,
            retrieval_ms=retrieval_ms,
            gemini_ttft_ms=0.0,
            total_latency_ms=total_ms,
            quality_rating=quality_rating,
            chunks_used=len(chunks),
        )
        if on_complete:
            on_complete(ans)
        return

    ttft_ms = 0.0
    first_chunk = True
    full_response_parts = []

    # Map response_style to max_output_tokens
    style_lower = (response_style or "Balanced").lower()
    if "concise" in style_lower:
        max_tokens = 350
    elif "detail" in style_lower:
        max_tokens = 2000
    else:
        max_tokens = 850

    try:
        client = _get_client()
        prompt = build_user_prompt(question, chunks, response_style=response_style)
        response_stream = client.models.generate_content_stream(
            model=settings.gemini_model,
            contents=prompt,
            config={
                "system_instruction": SYSTEM_INSTRUCTION,
                "temperature": 0.1,
                "max_output_tokens": max_tokens,
            },
        )


        for chunk in response_stream:
            text_part = chunk.text or ""
            if text_part:
                if first_chunk:
                    ttft_ms = (time.perf_counter() - t_start) * 1000.0
                    first_chunk = False
                full_response_parts.append(text_part)
                yield text_part

        answer_text = "".join(full_response_parts) or NO_CONTEXT_MESSAGE
        total_ms = (time.perf_counter() - t_start) * 1000.0 + retrieval_ms

        ans = ChatAnswer(
            answer=answer_text,
            detected_policy=detected_policy,
            sources=sources,
            grounded=True,
            policy_detection_ms=policy_detection_ms,
            embedding_init_ms=embedding_init_ms,
            query_embedding_ms=query_embedding_ms,
            chroma_init_ms=chroma_init_ms,
            chroma_retrieval_ms=chroma_retrieval_ms,
            context_prep_ms=context_prep_ms,
            retrieval_ms=retrieval_ms,
            gemini_ttft_ms=ttft_ms,
            total_latency_ms=total_ms,
            quality_rating=quality_rating,
            chunks_used=len(chunks),
        )
        semantic_cache.put(question, detected_policy, ans)
        if on_complete:
            on_complete(ans)

    except Exception:
        logger.exception("Gemini streaming call failed — falling back to extractive passages")
        fallback_text = (
            "The AI model is temporarily unavailable. Here are the most relevant "
            "policy passages instead:\n\n" + _extractive_fallback(chunks)
        )
        yield fallback_text
        total_ms = (time.perf_counter() - t_start) * 1000.0 + retrieval_ms
        ans = ChatAnswer(
            answer=fallback_text,
            detected_policy=detected_policy,
            sources=sources,
            grounded=True,
            policy_detection_ms=policy_detection_ms,
            embedding_init_ms=embedding_init_ms,
            query_embedding_ms=query_embedding_ms,
            chroma_init_ms=chroma_init_ms,
            chroma_retrieval_ms=chroma_retrieval_ms,
            context_prep_ms=context_prep_ms,
            retrieval_ms=retrieval_ms,
            gemini_ttft_ms=0.0,
            total_latency_ms=total_ms,
            quality_rating=quality_rating,
            chunks_used=len(chunks),
        )
        if on_complete:
            on_complete(ans)


def generate_answer(
    question: str,
    chunks: list[RetrievedChunk],
    detected_policy: str | None,
    retrieval_metrics: dict[str, float] | None = None,
) -> ChatAnswer:
    """Non-streaming version for backward compatibility and tests."""
    completed_answer = None

    def store_answer(ans: ChatAnswer):
        nonlocal completed_answer
        completed_answer = ans

    for _ in generate_answer_stream_with_container(
        question, chunks, detected_policy, retrieval_metrics, on_complete=store_answer
    ):
        pass

    return completed_answer or ChatAnswer(answer=NO_CONTEXT_MESSAGE, no_answer=True, grounded=False)
