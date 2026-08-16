"""
Digital HR - Streamlit entry point.

Enterprise AI Assistant UI with policy-aware grounded RAG pipeline.
"""
from __future__ import annotations

import streamlit as st

from app.config.settings import settings
from app.ui.auth import render_login_page
from app.ui.chat import render_chat
from app.ui.modal_views import (
    render_personalization_view,
    render_profile_view,
    render_saved_answers_view,
    render_settings_view,
)
from app.ui.sidebar import render_sidebar
from app.ui.state import init_session_state
from app.ui.theme import apply_theme

st.set_page_config(
    page_title="Digital-HR",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ensure data directories exist
settings.ensure_directories()


@st.cache_resource(show_spinner=False)
def warmup_system() -> bool:
    """
    Application startup warm-up hook:
    Loads SentenceTransformer model, ChromaDB collection, policy metadata,
    and Google GenAI client ONCE at app load time into RAM so the user never
    experiences a cold-start delay on their first prompt.
    """
    try:
        from app.retrieval.embeddings import get_embedding_model
        from app.retrieval.vector_store import _get_cached_chroma_resources, list_indexed_policies
        from app.llm.gemini_client import _get_client

        # 1. Warm up embedding model & PyTorch C++ kernels
        get_embedding_model()

        # 2. Warm up ChromaDB persistent client & collection
        _get_cached_chroma_resources()

        # 3. Warm up policy router metadata list
        list_indexed_policies()

        # 4. Warm up Google GenAI client TLS connection pool
        if settings.gemini_configured:
            _get_client()

        return True
    except Exception as exc:
        print(f"Startup warmup warning: {exc}")
        return False


# Execute system warm-up at startup
warmup_system()

# Initialize session state & local store
init_session_state()


# Apply active theme (Light / Dark)
current_theme = st.session_state.preferences.get("theme", "Light")
apply_theme(current_theme)

# Authentication Routing
if not st.session_state.get("authenticated", True):
    render_login_page()
else:
    # Render Navigation Sidebar
    render_sidebar()

    # Main Canvas View Router
    view = st.session_state.get("current_view", "chat")

    if view == "chat":
        render_chat()
    elif view == "profile":
        render_profile_view()
    elif view == "personalization":
        render_personalization_view()
    elif view == "settings":
        render_settings_view()
    elif view == "saved":
        render_saved_answers_view()
    else:
        render_chat()
