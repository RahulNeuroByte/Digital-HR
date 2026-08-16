from app.ingestion.chunker import _split_words, chunk_document
from app.ingestion.pdf_loader import PageExtraction


def test_split_words_respects_size_and_overlap():
    words = [f"word{i}" for i in range(500)]
    text = " ".join(words)
    pieces = _split_words(text, size=200, overlap=40)

    assert len(pieces) > 1
    # every piece should be <= size words
    for piece in pieces:
        assert len(piece.split()) <= 200


def test_short_text_returns_single_chunk():
    text = "This is a short policy paragraph."
    pieces = _split_words(text, size=200, overlap=40)
    assert pieces == [text]


def test_chunk_document_preserves_page_numbers():
    pages = [
        PageExtraction(page_number=1, text="Eligibility rules for leave.", extraction_method="pymupdf"),
        PageExtraction(page_number=2, text="Notice period is thirty days.", extraction_method="pymupdf"),
    ]
    chunks = chunk_document(pages, document_filename="Notice Period Policy.pdf", policy_name="Notice Period Policy")

    pages_seen = {c.page for c in chunks}
    assert pages_seen == {1, 2}
    assert all(c.policy_name == "Notice Period Policy" for c in chunks)


def test_chunk_document_skips_empty_pages():
    pages = [
        PageExtraction(page_number=1, text="", extraction_method="pymupdf"),
        PageExtraction(page_number=2, text="Some real content here.", extraction_method="pymupdf"),
    ]
    chunks = chunk_document(pages, document_filename="x.pdf", policy_name="X")
    assert len(chunks) == 1
    assert chunks[0].page == 2
