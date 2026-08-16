"""
Intent Classification Module for Siya (Digital HR).

Classifies incoming user queries into discrete intent categories:
- GREETING: Friendly greetings ("hi", "hii", "hii siya", "hello", "good morning").
- CASUAL_CHAT: Casual conversation ("how are you", "i am bored", "who are you", "thanks", "bye").
- POLICY_LIST: Catalog requests for available HR policies.
- DOCUMENT_GENERATION: PDF document export requests.
- OUT_OF_DOMAIN: Unrelated topics ("cricket match", "weather", "python code").
- FOLLOW_UP: Short referential follow-up questions ("it", "this", "tell me more").
- POLICY_QUERY: Grounded HR policy inquiry.
"""
from __future__ import annotations

import re
from enum import Enum


class QueryIntent(str, Enum):
    GREETING = "GREETING"
    CASUAL_CHAT = "CASUAL_CHAT"
    POLICY_LIST = "POLICY_LIST"
    DOCUMENT_GENERATION = "DOCUMENT_GENERATION"
    OUT_OF_DOMAIN = "OUT_OF_DOMAIN"
    FOLLOW_UP = "FOLLOW_UP"
    POLICY_QUERY = "POLICY_QUERY"


# Policy listing patterns
POLICY_LIST_PATTERNS = [
    r"\b(list|show|give|what|all|name[s]?|get)\b.*\b(policy|policies)\b",
    r"\b(all|available|different|16|company)\s+(hr\s+)?polic(y|ies)\b",
    r"\bwhat\s+(are\s+)?(the\s+)?(available\s+)?(hr\s+)?polic(y|ies)\b",
    r"\bwhich\s+polic(y|ies)\b",
    r"\bpolic(y|ies)\s+(list|names|catalog|directory)\b",
]

# PDF document export patterns
DOC_GEN_PATTERNS = [
    r"\b(pdf|download|export|generate|make|create|save)\b.*\b(pdf|file|document|download)\b",
    r"\bgive\s+(this\s+)?in\s+(a\s+)?pdf\b",
    r"\bdownload\s+(this|answer|response|file)\b",
]

# Non-HR out of domain topics (general knowledge/sports/coding)
OUT_OF_DOMAIN_PATTERNS = [
    r"\b(build|make|create|code|develop)\b.*\b(chatbot|bot|ai|app|website)\b",
    r"\b(weather|prime minister|cricket|capital of|who won|movie|song|joke|game|president|python code|match|score)\b",
    r"\bhow\s+can\s+i\s+make\s+a\s+chatbot\b",
    r"\bwrite\s+code\b",
]

# Robust Greeting Patterns (catches hi, hii, hiii, hey, heyy, hello, helloo, greetings, good morning/night, namaste + optional siya)
GREETING_PATTERNS = [
    r"^(h+[i+e+y+o+]+|h[ea]+llo+|h[ea]+y+|greetings|good\s*(morning|afternoon|evening|night)|namaste|ssup)(\s+siya)?[\!\.\?\s]*$",
    r"^(hi|hii|hiii|hiiii|hey|heyy|heyyy|hello|helloo|greetings)\s+(siya|there|team)?[\!\.\?\s]*$",
]

# Casual conversation / small talk patterns
CASUAL_CHAT_PATTERNS = [
    r"\b(how\s+are\s+you|what\s+are\s+you\s+doing|who\s+are\s+you|what\s+is\s+your\s+name|i\s+am\s+bored|im\s+bored|i\s+am\s+tired|im\s+tired|whats\s+up|what\s+up|kaise\s+ho|kaisa\s+chal\s+raha|boring\s+day)\b",
    r"\b(thanks|thank\s+you|bye|goodbye|see\s+you|take\s+care|cheers|good\s+night|gn|tc)\b",
    r"\b(can\s+we\s+talk|let[s\']?\s+chat|tell\s+me\s+something|say\s+something|who\s+made\s+you)\b",
]

# Follow-up indicators
FOLLOW_UP_INDICATORS = [
    " it", " this", " that", " above", " previous", "more details", "detailed info",
    "explain more", "tell me more", "elaborate", "what about", "how about",
    "give details", "give detail", "for it", "about it", "process for it",
]

# Specific HR domain keywords
HR_KEYWORDS = [
    "leave", "pip", "notice", "probation", "salary", "allowance", "posh",
    "wfh", "remote", "conveyance", "travel", "insurance", "medical", "referral",
    "education", "reimbursement", "laptop", "it assets", "shift", "retirement",
    "maternity", "paternity", "policy", "policies", "hr", "claim", "voucher", "iengage",
    "car", "vehicle", "scheme", "entitlement", "deduction", "superannuation", "resignation"
]


def classify_intent(query: str, history: list[dict] | None = None) -> QueryIntent:
    """
    Classify user query intent deterministically.
    Ensures casual chat and greetings NEVER trigger ChromaDB HR policy fallbacks.
    """
    q_clean = query.strip().lower()

    # 1. Check greetings first (flexible regex for hi, hii, hii siya, hello, hey)
    for pattern in GREETING_PATTERNS:
        if re.search(pattern, q_clean):
            return QueryIntent.GREETING

    # 2. Document generation intent check
    for pattern in DOC_GEN_PATTERNS:
        if re.search(pattern, q_clean):
            return QueryIntent.DOCUMENT_GENERATION

    # 3. Policy list catalog intent check
    for pattern in POLICY_LIST_PATTERNS:
        if re.search(pattern, q_clean):
            return QueryIntent.POLICY_LIST

    # 4. Casual chat check (small talk, how are you, who are you, thanks, bye)
    for pattern in CASUAL_CHAT_PATTERNS:
        if re.search(pattern, q_clean):
            return QueryIntent.CASUAL_CHAT

    # 5. Check explicit HR keywords
    has_hr_keyword = any(kw in q_clean for kw in HR_KEYWORDS)

    # 6. Follow-up check using history context (if recent message was assistant answer)
    if history and len(history) > 0:
        is_short = len(q_clean.split()) <= 10
        has_followup_signal = any(kw in f" {q_clean}" for kw in FOLLOW_UP_INDICATORS)
        if is_short or has_followup_signal:
            has_prev_assistant = any(
                isinstance(m, dict) and m.get("role") == "assistant" for m in history
            )
            if has_prev_assistant and has_hr_keyword:
                return QueryIntent.FOLLOW_UP
            elif has_prev_assistant and not has_hr_keyword:
                # If short follow-up after assistant answer, check context
                last_user_msgs = [m.get("content", "") for m in history if isinstance(m, dict) and m.get("role") == "user"]
                if last_user_msgs and any(kw in last_user_msgs[-1].lower() for kw in HR_KEYWORDS):
                    return QueryIntent.FOLLOW_UP

    # 7. Out of domain check
    for pattern in OUT_OF_DOMAIN_PATTERNS:
        if re.search(pattern, q_clean):
            return QueryIntent.OUT_OF_DOMAIN

    # 8. If explicitly contains HR terms -> POLICY_QUERY
    if has_hr_keyword:
        return QueryIntent.POLICY_QUERY

    # 9. Fallback for unclassified short / non-HR queries: Treat as CASUAL_CHAT
    # (NEVER send unknown small talk to ChromaDB RAG to avoid "I couldn't find sufficient information"!)
    if len(q_clean.split()) <= 6:
        return QueryIntent.CASUAL_CHAT

    return QueryIntent.POLICY_QUERY
