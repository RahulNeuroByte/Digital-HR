"""
Policy-name detection in a user's query.

Order of matching (deterministic first, fuzzy only as controlled fallback):
  1. Exact match against known policy names (case-insensitive).
  2. Normalized match (strip punctuation, collapse whitespace, drop
     "policy"/"the"/"a" filler words).
  3. Abbreviation match (e.g. "PIP" -> "Performance Improvement Plan (PIP) Policy").
  4. RapidFuzz partial-ratio fallback, only accepted above a configured
     confidence threshold, to catch minor typos.

This module never guesses when confidence is low — it's safer to fall
through to cross-policy search than to silently mis-route a query.
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz, process

from app.config.settings import settings
from app.schemas.models import PolicyMatch

_FILLER_WORDS = {"policy", "the", "a", "an", "of", "for"}


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t not in _FILLER_WORDS]
    return " ".join(tokens)


def _build_abbreviations(policy_names: list[str]) -> dict[str, str]:
    """Extract explicit (ABC) abbreviations from policy names, e.g. '(PIP)' -> full name."""
    abbrevs: dict[str, str] = {}
    for name in policy_names:
        for match in re.finditer(r"\(([A-Z]{2,})\)", name):
            abbrevs[match.group(1).lower()] = name
    return abbrevs


def detect_policy(query: str, known_policy_names: list[str]) -> PolicyMatch:
    """
    Attempt to detect an explicitly-named policy inside `query`.

    `known_policy_names` should come from the live index (vector_store.list_indexed_policies())
    so routing only ever matches policies that actually exist.
    """
    if not known_policy_names:
        return PolicyMatch(matched=False)

    normalized_query = _normalize(query)

    # 1. Exact (case-insensitive) substring match on the raw name.
    for name in known_policy_names:
        if name.lower() in query.lower():
            return PolicyMatch(matched=True, policy_name=name, match_type="exact", confidence=1.0)

    # 2. Normalized match — every significant token of a policy name appears in the query.
    for name in known_policy_names:
        normalized_name = _normalize(name)
        name_tokens = set(normalized_name.split())
        if name_tokens and name_tokens.issubset(set(normalized_query.split())):
            return PolicyMatch(matched=True, policy_name=name, match_type="normalized", confidence=0.95)

    # 3. Abbreviation match, e.g. user says "PIP policy".
    abbrevs = _build_abbreviations(known_policy_names)
    query_tokens = set(re.findall(r"[a-zA-Z]+", query.lower()))
    for token in query_tokens:
        if token in abbrevs:
            return PolicyMatch(
                matched=True, policy_name=abbrevs[token], match_type="abbreviation", confidence=0.9
            )

    # 4. RapidFuzz fallback for minor typos — only accept above threshold.
    best = process.extractOne(
        normalized_query, [_normalize(n) for n in known_policy_names], scorer=fuzz.partial_ratio
    )
    if best is not None:
        _, score, index = best
        if score >= settings.policy_match_fuzzy_threshold:
            return PolicyMatch(
                matched=True,
                policy_name=known_policy_names[index],
                match_type="fuzzy",
                confidence=score / 100,
            )

    return PolicyMatch(matched=False)
