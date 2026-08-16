"""
OCR fallback for scanned/image-only PDF pages.

Uses ocrmypdf + Tesseract (both external tools). Only called when
pdf_loader detects a page with little/no extractable text — normal
text-based PDFs never hit this path.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import fitz

from app.utils.logging import get_logger

logger = get_logger(__name__)


def ocr_extract_page(pdf_path: Path, page_number: int) -> str:
    """
    Run OCR on a single page of a PDF and return the extracted text.

    Strategy: split out the single page into its own temp PDF, run
    `ocrmypdf --sidecar` to get plain text directly, then clean up.
    Requires ocrmypdf + tesseract to be installed on the host machine
    (see COMPLETE_SETUP.md for Windows install instructions).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        single_page_pdf = tmp_dir / "page.pdf"
        ocred_pdf = tmp_dir / "page_ocr.pdf"
        sidecar_txt = tmp_dir / "page.txt"

        with fitz.open(pdf_path) as src:
            single = fitz.open()
            single.insert_pdf(src, from_page=page_number - 1, to_page=page_number - 1)
            single.save(single_page_pdf)

        try:
            subprocess.run(
                [
                    "ocrmypdf",
                    "--force-ocr",
                    "--sidecar",
                    str(sidecar_txt),
                    str(single_page_pdf),
                    str(ocred_pdf),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            logger.warning(
                "ocrmypdf executable not found on PATH — install it to enable OCR "
                "fallback (see COMPLETE_SETUP.md). Returning empty text for this page."
            )
            return ""
        except subprocess.CalledProcessError as exc:
            logger.warning("ocrmypdf failed on page %s: %s", page_number, exc.stderr)
            return ""

        if sidecar_txt.exists():
            return sidecar_txt.read_text(encoding="utf-8", errors="ignore")
        return ""
