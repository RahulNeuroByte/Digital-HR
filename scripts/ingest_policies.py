"""
Run this whenever you add/update PDFs in docs/.

Usage (Windows PowerShell, from the project root):
    .\\.venv\\Scripts\\python.exe scripts\\ingest_policies.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.settings import settings
from app.ingestion.indexer import ingest_directory
from app.utils.logging import get_logger

logger = get_logger(__name__)


def main() -> None:
    settings.ensure_directories()
    docs_dir = Path(settings.docs_directory)
    logger.info("Ingesting all PDFs from %s", docs_dir.resolve())

    summary = ingest_directory(docs_dir)

    if not summary:
        print(f"No PDFs were indexed. Check that PDF files exist in: {docs_dir.resolve()}")
        return

    print("\nIngestion complete. Indexed policies:")
    for name, count in summary.items():
        print(f"  - {name}: {count} chunks")
    print(f"\nTotal policies indexed: {len(summary)}")


if __name__ == "__main__":
    main()
