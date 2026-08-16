"""
Coforge Enterprise Sidebar: Brand identity, + New Conversation, grouped history (TODAY, YESTERDAY, OLDER), user profile.
Does NOT display raw PDF lists in sidebar; focuses strictly on user conversations.
"""
from __future__ import annotations

import streamlit as st
from app.ui.state import create_new_chat, set_active_chat, group_conversations_by_date
from app.db import db_manager


def render_sidebar() -> None:
    with st.sidebar:
        # Coforge Enterprise Brand Block
        st.markdown(
            """
            <div style='padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.12); margin-bottom: 14px;'>
                <div style='font-size: 0.85rem; font-weight: 700; color: #94A3B8; margin-bottom: 4px; letter-spacing: 0.5px;'>
                    <span style='color: #FF5B36; font-size: 1.05rem;'>Co</span><span style='color: #FFFFFF; font-size: 1.05rem;'>forge</span> &nbsp;•&nbsp; HR-India Policy Desk
                </div>
                <h2 style='color: #FFFFFF; margin: 2px 0 0; font-size: 1.45rem; font-weight: 700;'>
                    💬 Digital HR
                </h2>
                <p style='color: #94A3B8; font-size: 0.8rem; margin-top: 2px; margin-bottom: 0;'>Policy Intelligence Assistant</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        is_guest = st.session_state.get("is_guest", False)

        # 1. New Conversation Button
        if st.button("➕ New Conversation", use_container_width=True, type="primary"):
            create_new_chat()
            st.session_state.current_view = "chat"
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # 2. Local Chat History Search
        search = st.text_input(
            "Search history...",
            value=st.session_state.get("search_query", ""),
            placeholder="🔍 Search conversations...",
            label_visibility="collapsed",
        )
        st.session_state.search_query = search

        # 3. Categorized Recent Conversations (TODAY, YESTERDAY, OLDER)
        history_groups = group_conversations_by_date(filter_text=search)

        if not history_groups:
            st.caption("No conversations found.")
        else:
            active_id = st.session_state.get("active_chat_id")
            for group_name, threads in history_groups.items():
                group_heading = group_name.upper()
                st.markdown(
                    f"""
                    <div style='font-size: 0.72rem; font-weight: 700; color: #64748B; letter-spacing: 0.8px; margin: 12px 0 4px;'>
                        {group_heading}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                for thread in threads:
                    t_id = thread["id"]
                    t_title = thread.get("title", "Conversation")
                    is_active = (t_id == active_id and st.session_state.current_view == "chat")
                    prefix = "💬 " if not is_active else "👉 "
                    button_label = f"{prefix}{t_title}"

                    if st.button(button_label, key=f"chat_thread_{t_id}", use_container_width=True):
                        set_active_chat(t_id)
                        st.session_state.current_view = "chat"
                        st.rerun()

        st.markdown("<br><hr style='border-color: rgba(255,255,255,0.1);'><br>", unsafe_allow_html=True)

        # 4. Shortcuts
        if st.button("⭐ Saved Answers", use_container_width=True):
            if is_guest:
                st.toast("Sign in with Google to view saved answers.", icon="ℹ️")
            else:
                st.session_state.current_view = "saved"
                st.rerun()

        # 5. User Account Card
        profile = st.session_state.get("user_profile", {})
        user_name = profile.get("name", "User")
        user_role = "Guest Visitor" if is_guest else profile.get("role", "Employee")
        badge_bg = "rgba(255, 255, 255, 0.06)"

        st.markdown(
            f"""
            <div style='padding: 10px; border-radius: 8px; background-color: {badge_bg}; border: 1px solid rgba(255,255,255,0.08); margin-bottom: 12px;'>
                <div style='font-weight: 600; color: #FFFFFF; font-size: 0.92rem;'>👤 {user_name}</div>
                <div style='color: #94A3B8; font-size: 0.78rem;'>{user_role}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("👤 Profile", use_container_width=True):
                st.session_state.current_view = "profile"
                st.rerun()
        with col2:
            if st.button("🎨 Style", use_container_width=True):
                st.session_state.current_view = "personalization"
                st.rerun()

        col3, col4 = st.columns(2)
        with col3:
            if st.button("⚙ Settings", use_container_width=True):
                st.session_state.current_view = "settings"
                st.rerun()
        with col4:
            logout_label = "🚪 Exit Guest" if is_guest else "🚪 Logout"
            if st.button(logout_label, use_container_width=True):
                sp_client = db_manager.get_supabase_client()
                if sp_client:
                    try:
                        sp_client.auth.sign_out()
                    except Exception:
                        pass
                st.query_params.clear()
                st.session_state.clear()
                st.session_state.authenticated = False
                st.session_state.is_guest = False
                st.session_state.user_profile = {}
                st.session_state.conversations = {}
                st.session_state.saved_answers = []
                st.session_state.current_view = "login"
                st.rerun()
