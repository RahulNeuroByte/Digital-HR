"""
PDF text extraction.

Primary path: PyMuPDF (fast, works for normal text PDFs).
Fallback path: OCR (via ocr_fallback.py) for pages with little/no
extractable text (i.e. scanned/image-only PDFs or pages).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

from app.ingestion.ocr_fallback import ocr_extract_page
from app.utils.logging import get_logger

logger = get_logger(__name__)

# A page with fewer than this many extracted characters is treated as
# "no usable text" and routed to OCR.
MIN_USABLE_CHARS_PER_PAGE = 20


@dataclass
class PageExtraction:
    page_number: int  # 1-indexed, matches how a human would cite it
    text: str
    extraction_method: str  # "pymupdf" | "ocr"


def extract_pdf(pdf_path: Path) -> list[PageExtraction]:
    """Extract text from every page of a PDF, falling back to OCR per-page."""
    pages: list[PageExtraction] = []
    with fitz.open(pdf_path) as doc:
        for index, page in enumerate(doc):
            page_number = index + 1
            text = page.get_text("text") or ""

            if len(text.strip()) >= MIN_USABLE_CHARS_PER_PAGE:
                pages.append(PageExtraction(page_number, text, "pymupdf"))
                continue

            logger.info(
                "Page %s of %s has little/no extractable text — using OCR fallback",
                page_number,
                pdf_path.name,
            )
            try:
                ocr_text = ocr_extract_page(pdf_path, page_number)
                pages.append(PageExtraction(page_number, ocr_text, "ocr"))
            except Exception:  # pragma: no cover - OCR is a best-effort fallback
                logger.exception(
                    "OCR fallback failed for page %s of %s; keeping empty text",
                    page_number,
                    pdf_path.name,
                )
                pages.append(PageExtraction(page_number, "", "ocr"))

    return pages
