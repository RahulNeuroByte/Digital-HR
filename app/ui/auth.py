"""
Authentication UI: Google OAuth + Guest Mode sign-in for Digital HR.
Same layout as previous version — only the Google OAuth redirect
has been made environment-aware so it works both locally and
on Streamlit Cloud.
"""

from __future__ import annotations

import os

import streamlit as st
from app.config.settings import settings
from app.db import db_manager
from app.ui.state import create_new_chat


# Subtle constellation background (coral/teal/navy nodes)
_BG_CSS = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 650'%3E"
    "%3Cg opacity='0.4'%3E"
    "%3Ccircle cx='90' cy='70' r='3.5' fill='%23101C2C' opacity='0.35'/%3E"
    "%3Ccircle cx='250' cy='120' r='3' fill='%230F766E' opacity='0.4'/%3E"
    "%3Ccircle cx='170' cy='310' r='3.5' fill='%23101C2C' opacity='0.3'/%3E"
    "%3Ccircle cx='80' cy='500' r='3' fill='%23FF5B36' opacity='0.35'/%3E"
    "%3Ccircle cx='310' cy='480' r='3.5' fill='%23101C2C' opacity='0.3'/%3E"
    "%3Ccircle cx='400' cy='80' r='3' fill='%23101C2C' opacity='0.35'/%3E"
    "%3Ccircle cx='580' cy='70' r='3.5' fill='%230F766E' opacity='0.4'/%3E"
    "%3Ccircle cx='730' cy='130' r='3' fill='%23101C2C' opacity='0.3'/%3E"
    "%3Ccircle cx='890' cy='80' r='3.5' fill='%23FF5B36' opacity='0.35'/%3E"
    "%3Ccircle cx='820' cy='300' r='3' fill='%23101C2C' opacity='0.35'/%3E"
    "%3Ccircle cx='900' cy='500' r='3.5' fill='%230F766E' opacity='0.4'/%3E"
    "%3Ccircle cx='670' cy='480' r='3' fill='%23101C2C' opacity='0.3'/%3E"
    "%3Ccircle cx='490' cy='530' r='3.5' fill='%23101C2C' opacity='0.35'/%3E"
    "%3Ccircle cx='240' cy='210' r='3' fill='%23101C2C' opacity='0.3'/%3E"
    "%3Ccircle cx='740' cy='220' r='3.5' fill='%230F766E' opacity='0.35'/%3E"
    "%3Ccircle cx='490' cy='150' r='4' fill='%23FF5B36' opacity='0.45'/%3E"
    "%3Cline x1='90' y1='70' x2='250' y2='120' stroke='%23101C2C' stroke-width='0.8' opacity='0.15'/%3E"
    "%3Cline x1='250' y1='120' x2='400' y2='80' stroke='%230F766E' stroke-width='0.8' opacity='0.18'/%3E"
    "%3Cline x1='400' y1='80' x2='490' y2='150' stroke='%23FF5B36' stroke-width='1' opacity='0.22'/%3E"
    "%3Cline x1='490' y1='150' x2='580' y2='70' stroke='%23FF5B36' stroke-width='1' opacity='0.22'/%3E"
    "%3Cline x1='580' y1='70' x2='730' y2='130' stroke='%230F766E' stroke-width='0.8' opacity='0.18'/%3E"
    "%3Cline x1='730' y1='130' x2='890' y2='80' stroke='%23101C2C' stroke-width='0.8' opacity='0.15'/%3E"
    "%3Cline x1='170' y1='310' x2='240' y2='210' stroke='%23101C2C' stroke-width='0.8' opacity='0.15'/%3E"
    "%3Cline x1='240' y1='210' x2='490' y2='150' stroke='%230F766E' stroke-width='0.8' opacity='0.18'/%3E"
    "%3Cline x1='740' y1='220' x2='490' y2='150' stroke='%230F766E' stroke-width='0.8' opacity='0.18'/%3E"
    "%3Cline x1='820' y1='300' x2='740' y2='220' stroke='%23101C2C' stroke-width='0.8' opacity='0.15'/%3E"
    "%3Cline x1='80' y1='500' x2='310' y2='480' stroke='%23101C2C' stroke-width='0.8' opacity='0.15'/%3E"
    "%3Cline x1='310' y1='480' x2='490' y2='530' stroke='%23101C2C' stroke-width='0.8' opacity='0.15'/%3E"
    "%3Cline x1='490' y1='530' x2='670' y2='480' stroke='%23101C2C' stroke-width='0.8' opacity='0.15'/%3E"
    "%3Cline x1='670' y1='480' x2='900' y2='500' stroke='%23101C2C' stroke-width='0.8' opacity='0.15'/%3E"
    "%3C/g%3E%3C/svg%3E"
)


_CSS = f"""
<style>
.stApp {{
    background-color: #F7F8F6 !important;
    background-image: url("{_BG_CSS}") !important;
    background-repeat: no-repeat !important;
    background-position: center !important;
    background-size: cover !important;
}}

/* Guest button — white with border */
div[data-testid="stButton"] > button[kind="secondary"] {{
    background-color: #FFFFFF !important;
    color: #374151 !important;
    border: 1px solid #D1D5DB !important;
}}

div[data-testid="stButton"] > button[kind="secondary"]:hover {{
    background-color: #F9FAFB !important;
}}
</style>
"""


def _get_oauth_redirect_url() -> str:
    """
    Return the correct application URL for the current environment.

    Local:
        http://localhost:8501/

    Streamlit Cloud:
        APP_URL from Streamlit Secrets or environment variables.
    """
    app_url = ""
    try:
        if hasattr(st, "secrets") and "APP_URL" in st.secrets:
            app_url = str(st.secrets["APP_URL"]).strip()
    except Exception:
        pass

    if not app_url:
        app_url = os.getenv("APP_URL", "").strip()

    if not app_url:
        try:
            app_url = getattr(settings, "app_url", "")
        except Exception:
            app_url = ""

    if not app_url:
        app_url = "http://localhost:8501/"

    return app_url.rstrip("/") + "/"


def render_login_page() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)

    # Check for incoming Supabase OAuth error in query params
    error = st.query_params.get("error")
    error_desc = st.query_params.get("error_description") or st.query_params.get("error_code")
    if error:
        err_msg = str(error_desc or error).replace("+", " ")
        st.warning(
            f"⚠️ **Google Sign-In Notice**: Supabase returned an error: `{err_msg}`.\n\n"
            "**To fix Google Sign-In in 1 minute**:\n"
            "1. Open your [Supabase Dashboard](https://supabase.com/dashboard) → **Authentication** → **Providers** → Enable **Google**.\n"
            "2. Enter your Google OAuth `Client ID` and `Client Secret` in Supabase.\n"
            "3. Add `http://localhost:8501/` under **Authentication** → **URL Configuration** → **Redirect URLs**.\n\n"
            "👉 *Tip: Click **Continue as Guest** below to use Siya immediately without Google login!*"
        )

    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2.2, 1])

    with col2:
        # ── Card: branding + title + tagline ────────────────────────────────
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 25px;'>
                <div style='font-size: 0.95rem; font-weight: 700; color: #667085;
                            letter-spacing: 0.6px; margin-bottom: 4px;'>
                    <span style='color: #FF5B36; font-size: 1.08rem;'>Co</span><span
                          style='color: #172033; font-size: 1.08rem;'>forge</span>
                    &nbsp;•&nbsp; HR-India Policy Desk
                </div>

                <div style='color: #172033; margin: 4px 0 0; font-size: 2.2rem;
                            font-weight: 700; line-height: 1.2;'>
                    Digital-HR
                </div>

                <p style='color: #667085; font-size: 0.98rem; margin-top: 6px;
                          margin-bottom: 0; font-weight: 500;'>
                    Ask anything about Coforge HR-India policies
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sp_client = db_manager.get_supabase_client()
        is_configured = bool(
            sp_client
            and settings.supabase_url
            and settings.supabase_anon_key
        )

        google_oauth_url = None
        if is_configured:
            try:
                redirect_url = _get_oauth_redirect_url()
                oauth_res = sp_client.auth.sign_in_with_oauth(
                    {
                        "provider": "google",
                        "options": {
                            "redirect_to": redirect_url,
                            "query_params": {
                                "prompt": "select_account"
                            },
                        },
                    }
                )
                if oauth_res and hasattr(oauth_res, "url"):
                    google_oauth_url = oauth_res.url
                    # Preserve PKCE verifier if storage is accessible
                    try:
                        verifier = sp_client.auth._storage.get_item(
                            "supabase.auth.token-code-verifier"
                        )
                        if verifier:
                            st.session_state["pkce_code_verifier"] = verifier
                    except Exception:
                        pass
            except Exception:
                pass

        # ── Google Button ────────────────────────────────────────────────────
        if google_oauth_url:
            st.link_button(
                "🌐 Continue with Google",
                google_oauth_url,
                use_container_width=True,
                type="primary",
            )
        else:
            if st.button(
                "🌐 Continue with Google",
                use_container_width=True,
                type="primary",
            ):
                st.error(
                    "⚠️ Real Google OAuth authentication requires "
                    "SUPABASE_URL and SUPABASE_ANON_KEY in your .env "
                    "file with Google Provider enabled in the Supabase "
                    "Dashboard."
                )
                st.stop()

        # ── Divider ──────────────────────────────────────────────────────────
        st.markdown(
            """
            <div style='text-align: center; margin: 15px 0;
                        color: #94A3B8; font-weight: 500;'>
                ── or ──
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Guest Button ─────────────────────────────────────────────────────
        if st.button(
            "👤 Continue as Guest",
            use_container_width=True,
        ):

            st.session_state.authenticated = True
            st.session_state.is_guest = True

            st.session_state.user_profile = {
                "id": None,
                "name": "Guest User",
                "email": "Guest Session",
                "avatar": "👤",
                "role": "Guest Visitor",
                "department": "Temporary Workspace",
                "auth_method": "Guest Mode",
            }

            st.session_state.conversations = {}
            st.session_state.saved_answers = []
            st.session_state.current_view = "chat"

            create_new_chat()

            st.rerun()