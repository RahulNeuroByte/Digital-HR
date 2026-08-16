"""
Session state manager and local data storage for Digital HR.
Supports Authenticated Supabase user persistence via pure Python PKCE flow and temporary Guest mode.
Strictly purges mock user profiles and relies entirely on real Supabase OAuth credentials.
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta
import streamlit as st
from app.db import db_manager

logger = logging.getLogger(__name__)


def init_session_state() -> None:
    """Initialize default session state keys and process Supabase PKCE OAuth callbacks."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "is_guest" not in st.session_state:
        st.session_state.is_guest = False

    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {}

    if "conversations" not in st.session_state:
        st.session_state.conversations = {}

    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = None

    if "saved_answers" not in st.session_state:
        st.session_state.saved_answers = []

    if "feedback_log" not in st.session_state:
        st.session_state.feedback_log = []

    if "preferences" not in st.session_state:
        st.session_state.preferences = {
            "response_style": "Balanced",
            "theme": "Light",
            "language": "English",
        }

    if "current_view" not in st.session_state:
        st.session_state.current_view = "chat"

    if "search_query" not in st.session_state:
        st.session_state.search_query = ""

    # Supabase Client & PKCE Callback Processing
    sp_client = db_manager.get_supabase_client()
    raw_code = st.query_params.get("code")
    code = raw_code[0] if isinstance(raw_code, list) else raw_code
    if code:
        code = str(code).strip()

    oauth_code_detected = bool(code)
    has_query_error = bool(st.query_params.get("error"))

    user = None
    session = None

    # Step 1: Existing Active Supabase Session Check (restores valid session across reruns/refreshes)
    if sp_client:
        try:
            session = sp_client.auth.get_session()
            if session and hasattr(session, "user") and session.user:
                user = session.user
        except Exception as exc:
            logger.debug("No existing session recovered: %s", exc)

    # Step 2: PKCE Authorization Code Exchange (?code=...)
    if sp_client and not user and code:
        try:
            verifier = st.session_state.get("pkce_code_verifier")
            if verifier and hasattr(sp_client.auth, "_storage"):
                sp_client.auth._storage.set_item("supabase.auth.token-code-verifier", verifier)

            exchange_payload = {"auth_code": code}
            if verifier:
                exchange_payload["code_verifier"] = verifier

            res = sp_client.auth.exchange_code_for_session(exchange_payload)
            if res:
                user = getattr(res, "user", None) or (res.get("user") if isinstance(res, dict) else None)
                session = getattr(res, "session", None) or (res.get("session") if isinstance(res, dict) else None)

            if not user and hasattr(sp_client.auth, "get_user"):
                try:
                    usr_resp = sp_client.auth.get_user()
                    user = getattr(usr_resp, "user", None) or usr_resp
                except Exception:
                    pass

        except Exception as exc:
            logger.warning("Failed to exchange PKCE OAuth code for session (code may already be used): %s", exc)
            # Fallback: Check if session was already established on Supabase backend
            try:
                session = sp_client.auth.get_session()
                if session and hasattr(session, "user") and session.user:
                    user = session.user
            except Exception:
                pass

    code_exchange_success = bool(user)

    # Step 3: Handle Authenticated User Identity
    if user:
        user_id = getattr(user, "id", None) or user.get("id")
        user_email = getattr(user, "email", None) or user.get("email") or ""
        user_metadata = getattr(user, "user_metadata", {}) or user.get("user_metadata", {})

        user_name = (
            user_metadata.get("full_name")
            or user_metadata.get("name")
            or (user_email.split("@")[0] if user_email else "User")
        )
        avatar_url = user_metadata.get("avatar_url", "👤")

        # Requirement 12 Debug Logging (Safe non-secret boolean metrics)
        logger.info("OAuth code detected: %s", oauth_code_detected)
        logger.info("Code exchange success: %s", code_exchange_success)
        logger.info("Authenticated: True")
        logger.info("User ID exists: %s", bool(user_id))

        profile = db_manager.sync_user_profile(
            user_id=user_id,
            email=user_email,
            name=user_name,
            avatar_url=avatar_url,
        )
        st.session_state["user"] = user
        st.session_state["supabase_session"] = session
        st.session_state.user_profile = profile
        st.session_state.authenticated = True
        st.session_state.is_guest = False

        # Load persistent conversations and bookmarks strictly for user.id
        st.session_state.conversations = db_manager.load_user_conversations(user_id)
        st.session_state.saved_answers = db_manager.load_saved_answers(user_id)
        st.session_state.current_view = "chat"

        # Step 4: Clear OAuth query parameters ONLY AFTER session state is stored & committed
        if oauth_code_detected or has_query_error:
            st.query_params.clear()
            st.rerun()

    else:
        # Requirement 12 Debug Logging (Safe non-secret boolean metrics)
        logger.info("OAuth code detected: %s", oauth_code_detected)
        logger.info("Code exchange success: %s", code_exchange_success)
        logger.info("Authenticated: %s", bool(st.session_state.get("authenticated")))
        logger.info("User ID exists: %s", bool(st.session_state.get("user_profile", {}).get("id")))

    # Create initial sample thread if none exists
    if not st.session_state.conversations:
        create_new_chat()


def create_new_chat() -> str:
    """Create a new chat conversation thread and set it as active."""
    chat_id = str(uuid.uuid4())[:8]
    new_thread = {
        "id": chat_id,
        "title": "New Conversation",
        "created_at": datetime.now(),
        "policy_scope": None,
        "messages": [],
    }
    st.session_state.conversations[chat_id] = new_thread
    st.session_state.active_chat_id = chat_id
    st.session_state.messages = []  # active messages alias

    # Persist to Supabase if authenticated non-guest user
    if st.session_state.get("authenticated") and not st.session_state.get("is_guest"):
        user_id = st.session_state.user_profile.get("id")
        if user_id:
            db_manager.save_conversation(user_id, chat_id, new_thread["title"])

    return chat_id


def set_active_chat(chat_id: str) -> None:
    """Switch active chat thread."""
    if chat_id in st.session_state.conversations:
        st.session_state.active_chat_id = chat_id
        st.session_state.messages = st.session_state.conversations[chat_id]["messages"]


def auto_generate_title(question: str) -> str:
    """Locally generate a short concise title from the user prompt without LLM call."""
    cleaned = question.strip().capitalize()
    if len(cleaned) > 30:
        return cleaned[:28] + "..."
    return cleaned


def save_answer(answer_obj) -> None:
    """Save/bookmark an answer."""
    if st.session_state.get("is_guest"):
        st.toast("Sign in with Google to save answers.", icon="ℹ️")
        return

    for item in st.session_state.saved_answers:
        ans_text = getattr(answer_obj, "answer", item.get("answer"))
        if item.get("answer") == ans_text or item.get("answer_text") == ans_text:
            return  # already saved

    saved_item = {
        "id": str(uuid.uuid4())[:8],
        "policy_name": getattr(answer_obj, "detected_policy", "General HR") or "General HR",
        "answer": getattr(answer_obj, "answer", str(answer_obj)),
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "sources": getattr(answer_obj, "sources", []),
    }
    st.session_state.saved_answers.append(saved_item)

    # Persist to Supabase if authenticated non-guest
    user_id = st.session_state.user_profile.get("id")
    if user_id and not st.session_state.get("is_guest"):
        db_manager.save_answer_bookmark(user_id, answer_obj)


def remove_saved_answer(saved_id: str) -> None:
    """Remove a saved answer."""
    st.session_state.saved_answers = [
        s for s in st.session_state.saved_answers if s.get("id") != saved_id
    ]
    user_id = st.session_state.user_profile.get("id")
    if user_id and not st.session_state.get("is_guest"):
        db_manager.delete_saved_answer(user_id, saved_id)


def record_feedback(answer_text: str, is_helpful: bool, reason: str | None = None) -> None:
    """Record user feedback locally and in database."""
    st.session_state.feedback_log.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "helpful": is_helpful,
        "reason": reason,
        "answer_snippet": answer_text[:100],
    })
    user_id = st.session_state.user_profile.get("id")
    if user_id and not st.session_state.get("is_guest"):
        db_manager.record_user_feedback(user_id, is_helpful, reason, answer_text)


def group_conversations_by_date(filter_text: str = "") -> dict[str, list[dict]]:
    """Group conversation threads into Today, Yesterday, Previous 7 Days, and Older."""
    now = datetime.now()
    today_start = datetime(now.year, now.month, now.day)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=7)

    groups = {
        "Today": [],
        "Yesterday": [],
        "Previous 7 days": [],
        "Older": [],
    }

    query = filter_text.strip().lower()

    for chat_id, thread in reversed(list(st.session_state.conversations.items())):
        title = thread.get("title", "Conversation")
        if query and query not in title.lower():
            matched_msg = any(query in m.get("content", "").lower() for m in thread.get("messages", []) if isinstance(m, dict) and "content" in m)
            if not matched_msg:
                continue

        created = thread.get("created_at", now)
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created)
            except Exception:
                created = now

        if created >= today_start:
            groups["Today"].append(thread)
        elif created >= yesterday_start:
            groups["Yesterday"].append(thread)
        elif created >= week_start:
            groups["Previous 7 days"].append(thread)
        else:
            groups["Older"].append(thread)

    return {k: v for k, v in groups.items() if v}
