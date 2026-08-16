"""
Account Views & Overlays: Profile, Personalization, Settings, and Saved Answers screens.
Includes smooth UX navigation, proper avatar image rendering, and immediate preference persistence.
"""
from __future__ import annotations

import streamlit as st
from app.ui.state import remove_saved_answer
from app.db import db_manager
from app.retrieval.cache import reset_semantic_cache


def _render_back_button() -> None:
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("← Return to Chat", key="back_to_chat_top", type="secondary"):
            st.session_state.current_view = "chat"
            st.rerun()


def _get_initials(name: str) -> str:
    """Generate clean 1-2 character initials for avatar fallback."""
    parts = [p for p in name.strip().split() if p]
    if not parts:
        return "👤"
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def render_profile_view() -> None:
    _render_back_button()
    st.markdown("## 👤 User Profile")
    st.caption("Manage your account details and organization profile.")

    is_guest = st.session_state.get("is_guest", False)

    if is_guest:
        st.info("ℹ️ You are viewing Digital HR in Guest Mode. Sign in with Google to save your profile edits permanently.")

    profile = st.session_state.get("user_profile") or {}
    user_name = profile.get("name") or ("Guest User" if is_guest else "Employee")
    avatar_val = profile.get("avatar") or profile.get("avatar_url") or ""

    if isinstance(avatar_val, str) and (avatar_val.startswith("http://") or avatar_val.startswith("https://")):
        avatar_html = f'<img src="{avatar_val}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 3px solid #FF5B36; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin: 0 auto 12px; display: block;" />'
    else:
        initials = _get_initials(user_name)
        avatar_html = f'''
        <div style="width: 80px; height: 80px; border-radius: 50%; background-color: #FF5B36; color: #FFFFFF; font-weight: 700; font-size: 1.8rem; display: flex; align-items: center; justify-content: center; margin: 0 auto 12px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            {initials}
        </div>
        '''

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown(
            f"""
            <div style='text-align: center; padding: 24px 16px; border: 1px solid #DCE2E8; border-radius: 12px; background-color: #FFFFFF;'>
                {avatar_html}
                <h3 style='margin: 8px 0 4px; color: #172033; font-size: 1.25rem; font-weight: 700;'>{user_name}</h3>
                <p style='color: #FF5B36; font-weight: 600; margin: 0 0 4px;'>{profile.get("role", "Guest Visitor" if is_guest else "Employee")}</p>
                <p style='color: #667085; font-size: 0.85rem; margin: 0;'>{profile.get("department", "Coforge HR Desk")}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        with st.form("profile_form"):
            st.markdown("### Profile Details")
            name = st.text_input("Full Name", value=profile.get("name", ""), disabled=is_guest)
            email = st.text_input("Corporate Email", value=profile.get("email", ""), disabled=True)
            location = st.text_input("Location / Office", value=profile.get("location", "India"), disabled=is_guest)
            auth_label = "Temporary Guest Session" if is_guest else "Google"
            st.text_input("Authentication", value=auth_label, disabled=True)

            btn_col1, btn_col2 = st.columns([2, 1])
            with btn_col1:
                saved = st.form_submit_button("💾 Save Profile Changes", type="primary", disabled=is_guest)

            if saved:
                st.session_state.user_profile["name"] = name
                st.session_state.user_profile["location"] = location

                user_id = profile.get("id")
                if user_id and not is_guest:
                    db_manager.update_user_profile(user_id, {
                        "name": name,
                        "location": location,
                    })

                st.toast("✅ Profile updated successfully!", icon="🎉")
                st.success("Profile details saved!")


def render_personalization_view() -> None:
    _render_back_button()
    st.markdown("## 🎨 Personalization & Preferences")
    st.caption("Customize AI response depth, interface theme, and language.")

    prefs = st.session_state.preferences

    st.markdown("### 💬 AI Response Style")
    style = st.radio(
        "Select your preferred answer depth:",
        ["Concise", "Balanced", "Detailed"],
        index=["Concise", "Balanced", "Detailed"].index(prefs.get("response_style", "Balanced")),
        help="Concise gives 2-3 sentence summaries; Balanced gives key bullet points; Detailed provides complete rate tables, clauses & exceptions."
    )

    st.markdown("---")
    st.markdown("### 🌓 Appearance & Theme")
    theme = st.radio(
        "Select interface theme:",
        ["Light", "Dark"],
        index=["Light", "Dark"].index(prefs.get("theme", "Light")),
    )

    st.markdown("---")
    st.markdown("### 🌐 Language")
    lang = st.selectbox("Preferred Language", ["English", "Hindi", "Spanish", "French"], index=0)

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 2])
    with c1:
        if st.button("💾 Save Preferences", type="primary", use_container_width=True):
            st.session_state.preferences["response_style"] = style
            st.session_state.preferences["theme"] = theme
            st.session_state.preferences["language"] = lang
            
            # Reset response cache safely without AttributeError
            reset_semantic_cache()
            
            st.toast(f"✅ Preferences saved! AI Style: {style}", icon="🎨")
            st.success(f"✨ Preferences updated! Your AI answers will now use **{style}** mode.")
    with c2:
        if st.button("💬 Return to Chat Desk", use_container_width=True):
            st.session_state.current_view = "chat"
            st.rerun()


def render_settings_view() -> None:
    _render_back_button()
    st.markdown("## ⚙ Settings & Security")
    st.caption("Manage security, privacy, and account preferences.")

    tab1, tab2, tab3, tab4 = st.tabs(["🔒 Security", "🔐 Privacy & Data", "🔔 Notifications", "💼 Account"])

    with tab1:
        st.markdown("### Password & Authentication")
        auth_method = st.session_state.user_profile.get("auth_method", "Google OAuth 2.0")
        st.markdown(f"**Authentication Method:** ✅ `{auth_method}`")
        st.caption("Password management is handled by your enterprise identity provider (Google Workspace).")

    with tab2:
        st.markdown("### Privacy & Data Controls")
        if st.button("🗑️ Clear Active Session History"):
            st.session_state.conversations = {}
            st.session_state.messages = []
            st.toast("Active conversation history cleared!", icon="🗑️")
            st.success("Active conversation history cleared!")

        if st.button("⭐ Clear Saved Answers"):
            st.session_state.saved_answers = []
            st.toast("Saved answers cleared!", icon="⭐")
            st.success("Saved answers cleared!")

    with tab3:
        st.markdown("### Notification Preferences")
        st.checkbox("Email policy update digests", value=True)
        st.checkbox("HR policy revision alerts", value=True)

    with tab4:
        st.markdown("### Account Tier & Plan")
        st.markdown("**Current Plan:** Coforge HR-India Policy Assistant")


def render_saved_answers_view() -> None:
    _render_back_button()
    st.markdown("## ⭐ Saved Answers")
    st.caption("Your bookmarked policy answers for quick reference.")

    is_guest = st.session_state.get("is_guest", False)

    if is_guest:
        st.info("ℹ️ You are in Guest Mode. Sign in with Google to view and save persistent policy bookmarks.")
        return

    saved = st.session_state.saved_answers

    if not saved:
        st.info("You haven't saved any answers yet. Click '⭐ Save Answer' on any response to bookmark it here!")
        return

    for item in saved:
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### 📄 {item.get('policy_name')}")
                st.caption(f"Saved on {item.get('saved_at')}")
                st.markdown(item.get("answer") or item.get("answer_text", ""))
                sources = item.get("sources", [])
                if sources:
                    source_str = ", ".join([f"{s.get('policy_name', 'Policy')} p.{s.get('page', '?')}" if isinstance(s, dict) else f"{s.policy_name} p.{s.page}" for s in sources])
                    st.caption("Sources: " + source_str)
            with col2:
                if st.button("Remove", key=f"del_saved_{item.get('id')}"):
                    remove_saved_answer(item.get("id"))
                    st.rerun()
            st.divider()
