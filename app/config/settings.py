"""
Central configuration for Digital HR.

All values are loaded from environment variables (via python-dotenv),
never hard-coded. Import `settings` anywhere in the app to read config.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Use an explicit path so the .env is always found regardless of which
# working directory Streamlit (or any other runner) is launched from.
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_ENV_FILE)


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    try:
        return float(value) if value else default
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    try:
        return int(value) if value else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    # Gemini
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"))

    @property
    def supabase_url(self) -> str:
        load_dotenv(dotenv_path=_ENV_FILE, override=True)
        return os.getenv("SUPABASE_URL", os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")).strip()

    @property
    def supabase_anon_key(self) -> str:
        load_dotenv(dotenv_path=_ENV_FILE, override=True)
        val = os.getenv(
            "SUPABASE_ANON_KEY",
            os.getenv(
                "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
                os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", os.getenv("SUPABASE_KEY", "")),
            ),
        )
        return val.strip() if val else ""

    google_client_id: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_ID", ""))
    google_client_secret: str = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_SECRET", ""))



    # Storage
    chroma_persist_directory: str = field(
        default_factory=lambda: os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
    )
    docs_directory: str = field(default_factory=lambda: os.getenv("DOCS_DIRECTORY", "./docs"))

    # Retrieval tuning
    top_k: int = field(default_factory=lambda: _get_int("TOP_K", 8))

    similarity_threshold: float = field(default_factory=lambda: _get_float("SIMILARITY_THRESHOLD", 0.35))
    policy_match_fuzzy_threshold: int = field(
        default_factory=lambda: _get_int("POLICY_MATCH_FUZZY_THRESHOLD", 85)
    )

    # Embeddings
    embedding_model_name: str = "all-MiniLM-L6-v2"

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)

    def ensure_directories(self) -> None:
        Path(self.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
        Path(self.docs_directory).mkdir(parents=True, exist_ok=True)


settings = Settings()
