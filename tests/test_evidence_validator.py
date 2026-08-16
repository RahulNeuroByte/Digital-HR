"""Unit tests for Evidence Validator & Source Consolidator."""
import pytest
from app.schemas.models import RetrievedChunk
from app.retrieval.evidence_validator import validate_and_consolidate_sources


def test_no_sources_when_no_answer():
    chunks = [
        RetrievedChunk(id="1", document="doc1.pdf", policy_name="Leave Policy", page=3, chunk_index=0, extraction_method="pymupdf", text="Leave rules", score=0.8)
    ]
    sources, primary = validate_and_consolidate_sources(chunks, "I couldn't find sufficient information", no_answer=True)
    assert sources == []
    assert primary is None


def test_consolidates_valid_sources():
    chunks = [
        RetrievedChunk(id="1", document="doc1.pdf", policy_name="Leave Policy", page=3, chunk_index=0, extraction_method="pymupdf", text="Leave entitlement rules", score=0.85),
        RetrievedChunk(id="2", document="doc1.pdf", policy_name="Leave Policy", page=5, chunk_index=1, extraction_method="pymupdf", text="Apply via iEngage portal", score=0.75),
    ]
    sources, primary = validate_and_consolidate_sources(chunks, "You can apply for leave through iEngage portal.", no_answer=False)
    assert len(sources) == 2
    assert primary == "Leave Policy"
