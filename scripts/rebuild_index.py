"""
Wipe the ChromaDB collection and re-ingest every PDF in docs/ from scratch.
Use this if chunking/embedding logic changes and old vectors would be stale.

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\rebuild_index.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


def main() -> None:
    persist_dir = Path(settings.chroma_persist_directory)
    if persist_dir.exists():
        logger.info("Removing existing vector store at %s", persist_dir.resolve())
        shutil.rmtree(persist_dir)

    # Re-import after clearing so a fresh PersistentClient is created.
    from scripts.ingest_policies import main as ingest_main

    ingest_main()


if __name__ == "__main__":
    main()
