"""
Central configuration for Digital HR.

Configuration sources:
1. Streamlit Cloud Secrets (when running on Streamlit)
2. Environment variables
3. Local .env file

This allows the same application to run both locally and on Streamlit Cloud
without changing application code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Local .env
# ---------------------------------------------------------------------------
# Project root:
# D:/Digital-HR/.env
#
# parents[0] = app/config
# parents[1] = app
# parents[2] = Digital-HR
# ---------------------------------------------------------------------------

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

load_dotenv(dotenv_path=_ENV_FILE)


# ---------------------------------------------------------------------------
# Secret / configuration loader
# ---------------------------------------------------------------------------

def _get_secret(name: str, default: str = "") -> str:
    """
    Get a configuration value.

    Priority:
        1. Streamlit Secrets
        2. Environment variable / .env
        3. Default value

    This makes the application work both:
        - Locally using .env
        - On Streamlit Cloud using Settings -> Secrets
    """

    # ---------------------------------------------------------------
    # 1. Try Streamlit Secrets
    # ---------------------------------------------------------------
    try:
        import streamlit as st

        value = st.secrets.get(name)

        if value is not None:
            value = str(value).strip()

            if value:
                return value

    except Exception:
        # Streamlit may not be available when running scripts,
        # tests, ingestion scripts, etc.
        pass

    # ---------------------------------------------------------------
    # 2. Fall back to environment variable / local .env
    # ---------------------------------------------------------------
    value = os.getenv(name, default)

    return str(value).strip() if value is not None else default


# ---------------------------------------------------------------------------
# Numeric configuration helpers
# ---------------------------------------------------------------------------

def _get_float(name: str, default: float) -> float:
    value = _get_secret(name, str(default))

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_int(name: str, default: int) -> int:
    value = _get_secret(name, str(default))

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Application settings
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Settings:

    # =======================================================================
    # Gemini
    # =======================================================================

    gemini_api_key: str = field(
        default_factory=lambda: _get_secret("GEMINI_API_KEY")
    )

    gemini_model: str = field(
        default_factory=lambda: _get_secret(
            "GEMINI_MODEL",
            "gemini-3.5-flash-lite",
        )
    )

    # =======================================================================
    # Supabase
    # =======================================================================

    @property
    def supabase_url(self) -> str:
        """
        Supabase project URL.

        Supported names:
            SUPABASE_URL
            NEXT_PUBLIC_SUPABASE_URL
        """

        value = _get_secret("SUPABASE_URL")

        if not value:
            value = _get_secret("NEXT_PUBLIC_SUPABASE_URL")

        return value.strip() if value else ""

    @property
    def supabase_anon_key(self) -> str:
        """
        Supabase public/anonymous key.

        Supported names:
            SUPABASE_ANON_KEY
            NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
            NEXT_PUBLIC_SUPABASE_ANON_KEY
            SUPABASE_KEY
        """

        value = _get_secret("SUPABASE_ANON_KEY")

        if not value:
            value = _get_secret("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")

        if not value:
            value = _get_secret("NEXT_PUBLIC_SUPABASE_ANON_KEY")

        if not value:
            value = _get_secret("SUPABASE_KEY")

        return value.strip() if value else ""

    # =======================================================================
    # Google OAuth
    # =======================================================================

    google_client_id: str = field(
        default_factory=lambda: _get_secret("GOOGLE_CLIENT_ID")
    )

    google_client_secret: str = field(
        default_factory=lambda: _get_secret("GOOGLE_CLIENT_SECRET")
    )

    # =======================================================================
    # Storage
    # =======================================================================

    chroma_persist_directory: str = field(
        default_factory=lambda: _get_secret(
            "CHROMA_PERSIST_DIRECTORY",
            "./chroma_db",
        )
    )

    docs_directory: str = field(
        default_factory=lambda: _get_secret(
            "DOCS_DIRECTORY",
            "./docs",
        )
    )

    # =======================================================================
    # Retrieval tuning
    # =======================================================================

    top_k: int = field(
        default_factory=lambda: _get_int("TOP_K", 8)
    )

    similarity_threshold: float = field(
        default_factory=lambda: _get_float(
            "SIMILARITY_THRESHOLD",
            0.35,
        )
    )

    policy_match_fuzzy_threshold: int = field(
        default_factory=lambda: _get_int(
            "POLICY_MATCH_FUZZY_THRESHOLD",
            85,
        )
    )

    # =======================================================================
    # Embeddings
    # =======================================================================

    embedding_model_name: str = "all-MiniLM-L6-v2"

    # =======================================================================
    # Logging
    # =======================================================================

    log_level: str = field(
        default_factory=lambda: _get_secret(
            "LOG_LEVEL",
            "INFO",
        )
    )

    # =======================================================================
    # Status helpers
    # =======================================================================

    @property
    def gemini_configured(self) -> bool:
        """
        Returns True when a Gemini API key is available.
        """

        return bool(
            self.gemini_api_key
            and self.gemini_api_key.strip()
        )

    @property
    def supabase_configured(self) -> bool:
        """
        Returns True when both Supabase URL and anonymous key exist.
        """

        return bool(
            self.supabase_url
            and self.supabase_anon_key
        )

    @property
    def google_oauth_configured(self) -> bool:
        """
        Returns True when Google OAuth credentials exist.
        """

        return bool(
            self.google_client_id
            and self.google_client_secret
        )

    # =======================================================================
    # Directory management
    # =======================================================================

    def ensure_directories(self) -> None:
        """
        Ensure required application directories exist.
        """

        Path(
            self.chroma_persist_directory
        ).mkdir(
            parents=True,
            exist_ok=True,
        )

        Path(
            self.docs_directory
        ).mkdir(
            parents=True,
            exist_ok=True,
        )


# ---------------------------------------------------------------------------
# Global settings instance
# ---------------------------------------------------------------------------

settings = Settings()