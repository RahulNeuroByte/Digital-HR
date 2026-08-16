"""
Quick end-to-end sanity check: config, vector store connectivity,
indexed policy count, and (if configured) a live Gemini ping.

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\health_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config.settings import settings


def main() -> None:
    print("Digital HR — health check")
    print("-" * 40)

    print(f"Docs directory:      {Path(settings.docs_directory).resolve()}")
    print(f"Chroma directory:    {Path(settings.chroma_persist_directory).resolve()}")
    print(f"Gemini configured:   {settings.gemini_configured}")

    try:
        from app.retrieval import vector_store

        policies = vector_store.list_indexed_policies()
        print(f"Indexed policies ({len(policies)}):")
        for p in policies:
            print(f"  - {p}")
        if not policies:
            print("  (none — run scripts/ingest_policies.py)")
    except Exception as exc:
        print(f"Vector store check FAILED: {exc}")
        return

    if settings.gemini_configured:
        try:
            from google import genai

            client = genai.Client(api_key=settings.gemini_api_key)
            client.models.generate_content(model=settings.gemini_model, contents="ping")
            print("Gemini API call:     OK")
        except Exception as exc:
            print(f"Gemini API call FAILED: {exc}")
    else:
        print("Gemini API call:     skipped (no key configured)")

    print("-" * 40)
    print("Health check complete.")


if __name__ == "__main__":
    main()
