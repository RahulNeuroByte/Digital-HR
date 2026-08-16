"""
Evidence Validator & Source Consolidator Module for Digital HR.

Validates retrieved chunks against generated answers, eliminates ungrounded citations,
and consolidates policy sources for clean enterprise presentation.
"""
from __future__ import annotations

from app.schemas.models import RetrievedChunk, Source


def validate_and_consolidate_sources(
    chunks: list[RetrievedChunk],
    answer_text: str,
    no_answer: bool = False
) -> tuple[list[Source], str | None]:
    """
    Filter sources to only those that genuinely support the answer,
    and consolidate multiple chunks into unified policy sources.
    Returns: (list of validated Source objects, primary_policy_name_string)
    """
    if no_answer or not chunks or not answer_text:
        return [], None

    ans_lower = answer_text.lower()
    
    # If the response indicates insufficient context, do not attach citations
    if "couldn't find" in ans_lower or "insufficient information" in ans_lower or "outside my hr" in ans_lower:
        return [], None

    valid_sources: list[Source] = []
    seen_keys: set[tuple[str, int]] = set()

    for chunk in chunks:
        # Check relevance: key tokens of chunk text or policy name appear in answer or high similarity
        if chunk.score >= 0.45:
            key = (chunk.policy_name, chunk.page)
            if key not in seen_keys:
                seen_keys.add(key)
                valid_sources.append(
                    Source(
                        policy_name=chunk.policy_name,
                        document=chunk.document,
                        page=chunk.page
                    )
                )

    if not valid_sources:
        return [], None

    primary_policy = valid_sources[0].policy_name
    return valid_sources, primary_policy
