"""
Ingestion orchestration: PDF -> pages -> chunks -> embedded + indexed.

Repeatable and idempotent: chunk IDs are deterministic
(filename::page::chunk_index), so re-running ingestion on an unchanged
PDF simply overwrites the same vectors via `upsert`.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.ingestion.chunker import chunk_document
from app.ingestion.pdf_loader import extract_pdf
from app.retrieval.vector_store import upsert_chunks
from app.schemas.models import Chunk
from app.utils.logging import get_logger

logger = get_logger(__name__)


def derive_policy_name(pdf_path: Path) -> str:
    """
    Human-readable policy name from filename, e.g.
    'Notice_Period_Policy.pdf' -> 'Notice Period Policy'.
    """
    stem = pdf_path.stem
    name = re.sub(r"[_\-]+", " ", stem)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def ingest_pdf(pdf_path: Path) -> list[Chunk]:
    """Ingest a single PDF end-to-end and index it. Returns the chunks written."""
    policy_name = derive_policy_name(pdf_path)
    logger.info("Ingesting '%s' as policy '%s'", pdf_path.name, policy_name)

    pages = extract_pdf(pdf_path)
    chunks = chunk_document(pages, document_filename=pdf_path.name, policy_name=policy_name)

    if not chunks:
        logger.warning("No usable text extracted from %s — skipping index", pdf_path.name)
        return []

    upsert_chunks(chunks)
    logger.info("Indexed %d chunks for policy '%s'", len(chunks), policy_name)
    return chunks


def ingest_directory(docs_dir: Path) -> dict[str, int]:
    """Ingest every PDF in a directory. Returns {policy_name: chunk_count}."""
    docs_dir = Path(docs_dir)
    pdf_paths = sorted(docs_dir.glob("*.pdf"))

    if not pdf_paths:
        logger.warning("No PDFs found in %s", docs_dir)
        return {}

    summary: dict[str, int] = {}
    for pdf_path in pdf_paths:
        chunks = ingest_pdf(pdf_path)
        if chunks:
            summary[chunks[0].policy_name] = len(chunks)

    return summary
