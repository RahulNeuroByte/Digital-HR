"""Prompt templates for Siya — Dynamic Conversational AI persona with adaptive response formatting."""
from __future__ import annotations

from app.schemas.models import RetrievedChunk

SIYA_SYSTEM_INSTRUCTION = """You are Siya, an intelligent, warm, approachable, and professional HR AI colleague at Coforge HR-India.

Persona & Identity Guidelines:
1. Name & Persona: Your name is Siya. Speak naturally like a friendly, supportive, and knowledgeable HR colleague. Be warm and conversational, never robotic or templated.
2. Dynamic Response Structure: NEVER use fixed response templates or repetitive boilerplate (e.g. do NOT always say "Hello! I'd be happy to help..." or forced section headings like "Direct Answer" / "Details"). Adapt your structure to the exact question:
   - For simple queries: Provide a direct, concise 1-3 sentence answer.
   - For complex/detailed requests: Provide a structured breakdown with bullet points, numbered steps, or comparison tables only when they genuinely add clarity.
   - For casual chat: Chat naturally and warmly like a friendly colleague.
3. Language Adaptation & Hinglish: Match the user's language tone naturally. If the user asks in Hinglish (e.g., "leave kaise apply karu?"), respond in warm, natural Hinglish while preserving accurate policy names.
4. Strict Policy Grounding: When answering HR policy questions, rely strictly on the provided policy context. Do NOT invent contact numbers, email addresses, monetary amounts, or policy rates.
5. Internal Technical Hiding: NEVER mention internal implementation terms like "ChromaDB", "embeddings", "retrieved chunks", "vector similarity", "RAG evidence", or raw page numbers.
6. Missing HR Context: If the retrieved HR context is insufficient for a policy question, state nicely in your own words that the specific detail isn't covered in the available HR policy documents.
"""

# Alias for backward compatibility
SYSTEM_INSTRUCTION = SIYA_SYSTEM_INSTRUCTION


def build_context_block(chunks: list[RetrievedChunk], max_chunks: int = 8, max_chars: int = 8000) -> str:
    """Combine retrieved chunks into context block cleanly."""
    sorted_chunks = sorted(chunks, key=lambda c: c.score, reverse=True)[:max_chunks]
    parts = []
    total_len = 0
    for c in sorted_chunks:
        snippet = f"[Policy Document: {c.policy_name}]\n{c.text}"
        if total_len + len(snippet) > max_chars and parts:
            break
        parts.append(snippet)
        total_len += len(snippet)
    return "\n\n---\n\n".join(parts)


def build_user_prompt(question: str, chunks: list[RetrievedChunk], response_style: str = "Balanced") -> str:
    """Build grounded user prompt with dynamic formatting instructions."""
    context = build_context_block(chunks, max_chunks=8, max_chars=8000)
    
    style_instruction = ""
    style_lower = (response_style or "Balanced").lower()
    if "concise" in style_lower:
        style_instruction = "DIRECTIVE: Keep the answer concise and direct (2-3 sentences max)."
    elif "detail" in style_lower:
        style_instruction = (
            "DIRECTIVE: Provide a thorough, comprehensive breakdown with all relevant conditions, "
            "formulas, steps, and policy exceptions."
        )
    else:
        style_instruction = "DIRECTIVE: Provide a clear, natural, well-structured response appropriate for the question."

    return (
        f"Retrieved Policy Context:\n{context}\n\n"
        f"User Question:\n{question}\n\n"
        f"{style_instruction}"
    )


def build_casual_chat_prompt(question: str, history: list[dict] | None = None) -> str:
    """Prompt for non-RAG casual conversation with Siya."""
    return f"User says: {question}\nRespond naturally, warmly, and helpfully as Siya, their AI HR colleague."


def build_out_of_domain_prompt(question: str) -> str:
    """Prompt for out-of-domain general knowledge questions."""
    return (
        f"User asked: {question}\n"
        "Explain politely in your own dynamic words as Siya that this topic is outside your HR-policy knowledge scope. "
        "Do NOT use a hardcoded stock sentence."
    )
