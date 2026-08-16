"""
Retrieval orchestration: combines policy routing with conversational context resolution,
Hinglish/informal query normalization, vector search, reranking, deduplication, and out-of-scope detection.
"""
from __future__ import annotations

import time
import re
from app.config.settings import settings
from app.retrieval import vector_store
from app.routing.policy_router import detect_policy
from app.schemas.models import PolicyMatch, RetrievedChunk
from app.utils.logging import get_logger

logger = get_logger(__name__)

OUT_OF_SCOPE_KEYWORDS = {
    "weather", "prime minister", "python code", "write code", "recipe", "cricket",
    "capital of", "who won", "movie", "song", "tell me a joke", "game", "president"
}

INFORMAL_MAPPING = [
    (r"\b(chutti|chhutti|leave kitni|carry forward|holiday)\b", "leave policy carry forward entitlement"),
    (r"\b(resign|resignation|notice kitna|notice period|probation)\b", "notice period policy resignation probation duration"),
    (r"\b(moonlighting|moonliting|part time job|second job)\b", "moonlighting policy secondary employment"),
    (r"\b(salary|deduct|allowance|shift rates)\b", "shift allowance policy per diem rates"),
    (r"\b(wfh|remote work|work from home)\b", "work from home remote work policy"),
    (r"\b(posh|harassment|complaint)\b", "prevention of sexual harassment posh policy"),
    (r"\b(laptop|it assets|security)\b", "it assets and security policy"),
    (r"\b(referral|bonus)\b", "employee referral policy"),
    (r"\b(education|reimbursement|tuition)\b", "higher education assistance policy"),
]


def is_out_of_scope(query: str) -> bool:
    """Check if query is completely outside company HR policies."""
    q_lower = query.lower().strip()
    return any(kw in q_lower for kw in OUT_OF_SCOPE_KEYWORDS)


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


def resolve_conversational_context(query: str, history: list[dict] | None = None) -> str:
    """
    Resolve pronouns ('it', 'this', 'that') and short follow-up questions using recent chat history.
    Example: 'give me detail information for it' after 'how to apply for leave' 
      -> 'how to apply for leave detailed information process'
    """
    if not history:
        return query

    q_clean = query.strip().lower()
    is_short = len(q_clean.split()) <= 10
    has_pronoun_or_link = any(
        kw in f" {q_clean} " for kw in [
            " it ", " this ", " that ", " for it ", " about it ", " probation ", " notice ", " leave ",
            " how many ", " what about ", " and ", " after ", " during ", " exception ",
            " carry forward ", " rules ", " eligibility ", " detail ", " details ", " more ",
            " explain ", " elaborate ", " process "
        ]
    )

    if is_short or has_pronoun_or_link:
        user_msgs = []
        assistant_policies = []

        for m in history:
            if isinstance(m, dict):
                if m.get("role") == "user" and m.get("content"):
                    user_msgs.append(m.get("content", ""))
                elif m.get("role") == "assistant" and m.get("answer"):
                    ans_obj = m.get("answer")
                    if hasattr(ans_obj, "detected_policy") and ans_obj.detected_policy:
                        assistant_policies.append(ans_obj.detected_policy)

        context_parts = []
        if user_msgs:
            # Add last user query
            context_parts.append(user_msgs[-1])
        if assistant_policies:
            # Add last detected policy
            context_parts.append(assistant_policies[-1])

        if context_parts:
            joined_ctx = " ".join(context_parts)
            logger.info("Resolved contextual query: '%s' -> '%s %s'", query, joined_ctx, query)
            return f"{joined_ctx} {query}"

    return query


def normalize_query_intent(query: str) -> str:
    """Locally normalize Hinglish, informal terms, and typos for Chroma vector retrieval."""
    q_lower = query.lower()
    additions = []
    for pattern, term in INFORMAL_MAPPING:
        if re.search(pattern, q_lower):
            additions.append(term)
    if additions:
        return f"{query} {' '.join(additions)}"
    return query


def _deduplicate_and_rerank_chunks(chunks: list[RetrievedChunk], scoped_policy: str | None) -> list[RetrievedChunk]:
    """
    Remove exact/near-duplicate chunks and boost chunks matching the detected policy scope.
    """
    seen_texts = set()
    reranked = []

    for chunk in chunks:
        norm = " ".join(chunk.text.split()).lower()
        if norm in seen_texts or len(norm) <= 10:
            continue
        seen_texts.add(norm)

        # Rerank boost if chunk policy matches detected policy scope
        score_boost = 0.15 if (scoped_policy and chunk.policy_name == scoped_policy) else 0.0
        adjusted_score = min(1.0, chunk.score + score_boost)
        chunk_copy = chunk.model_copy(deep=True)
        chunk_copy.score = adjusted_score
        reranked.append(chunk_copy)

    # Sort descending by adjusted relevance score
    reranked.sort(key=lambda c: c.score, reverse=True)
    return reranked


def retrieve(
    query: str,
    history: list[dict] | None = None
) -> tuple[list[RetrievedChunk], PolicyMatch, dict[str, float]]:
    """
    Run policy detection, contextual query resolution, semantic retrieval, deduplication, and reranking.
    """
    t0 = time.perf_counter()

    # Step 1: Resolve conversational follow-up context
    resolved_query = resolve_conversational_context(query, history)

    # Step 2: Normalize query (Hinglish, informal, typos)
    normalized_query = normalize_query_intent(resolved_query)

    # Step 3: Policy Detection
    known_policies = vector_store.list_indexed_policies()
    policy_match = detect_policy(normalized_query, known_policies)
    t1 = time.perf_counter()
    policy_detection_ms = (t1 - t0) * 1000.0

    scoped_policy = policy_match.policy_name if policy_match.matched else None

    # Step 4: Vector Retrieval from ChromaDB
    results, vstore_metrics = vector_store.query_with_metrics(
        normalized_query, top_k=settings.top_k, policy_name=scoped_policy
    )

    t_prep_0 = time.perf_counter()
    filtered = [r for r in results if r.score >= settings.similarity_threshold]
    reranked = _deduplicate_and_rerank_chunks(filtered, scoped_policy)
    t_prep_1 = time.perf_counter()
    context_prep_ms = (t_prep_1 - t_prep_0) * 1000.0

    total_retrieval_ms = (
        vstore_metrics.get("embedding_init_ms", 0.0)
        + vstore_metrics.get("query_embedding_ms", 0.0)
        + vstore_metrics.get("chroma_init_ms", 0.0)
        + vstore_metrics.get("chroma_retrieval_ms", 0.0)
        + context_prep_ms
    )

    metrics = {
        "policy_detection_ms": policy_detection_ms,
        "embedding_init_ms": vstore_metrics.get("embedding_init_ms", 0.0),
        "query_embedding_ms": vstore_metrics.get("query_embedding_ms", 0.0),
        "chroma_init_ms": vstore_metrics.get("chroma_init_ms", 0.0),
        "chroma_retrieval_ms": vstore_metrics.get("chroma_retrieval_ms", 0.0),
        "context_prep_ms": context_prep_ms,
        "retrieval_ms": total_retrieval_ms,
    }

    return reranked, policy_match, metrics
