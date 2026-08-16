"""
Chunk cleaned page text into retrieval-sized pieces, preserving page
boundaries (a chunk never spans two PDF pages, so page-number citation
stays accurate).
"""
from __future__ import annotations

from app.ingestion.cleaner import clean_text
from app.ingestion.pdf_loader import PageExtraction
from app.schemas.models import Chunk

# Word-based sizing keeps this simple/dependency-free for a POC.
CHUNK_SIZE_WORDS = 220
CHUNK_OVERLAP_WORDS = 40


def _split_words(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    if len(words) <= size:
        return [" ".join(words)]

    chunks = []
    start = 0
    step = max(size - overlap, 1)
    while start < len(words):
        piece = words[start : start + size]
        chunks.append(" ".join(piece))
        if start + size >= len(words):
            break
        start += step
    return chunks


def chunk_document(
    pages: list[PageExtraction],
    document_filename: str,
    policy_name: str,
) -> list[Chunk]:
    """Turn extracted pages into a flat list of Chunk objects."""
    chunks: list[Chunk] = []
    running_index = 0

    for page in pages:
        cleaned = clean_text(page.text)
        if not cleaned:
            continue

        for piece in _split_words(cleaned, CHUNK_SIZE_WORDS, CHUNK_OVERLAP_WORDS):
            chunk_id = f"{document_filename}::p{page.page_number}::c{running_index}"
            chunks.append(
                Chunk(
                    id=chunk_id,
                    document=document_filename,
                    policy_name=policy_name,
                    page=page.page_number,
                    chunk_index=running_index,
                    extraction_method=page.extraction_method,  # type: ignore[arg-type]
                    text=piece,
                )
            )
            running_index += 1

    return chunks
