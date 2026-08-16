"""
Supabase Database Service Layer for Digital HR.
Handles persistent user profiles, conversations, messages, saved answers, preferences, and feedback.
Provides graceful fallbacks if Supabase is unconfigured or offline.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from app.config.settings import settings

logger = logging.getLogger(__name__)

_sp_client: Any = None


def get_supabase_client() -> Any:
    """Lazy initialize and return singleton Supabase client configured with PKCE flow."""
    global _sp_client
    if _sp_client is not None:
        return _sp_client

    if settings.supabase_url and settings.supabase_anon_key:
        try:
            from supabase import create_client, ClientOptions
            options = ClientOptions(flow_type="pkce")
            _sp_client = create_client(settings.supabase_url, settings.supabase_anon_key, options=options)
            return _sp_client
        except Exception as exc:
            logger.warning(f"Failed to initialize Supabase client: {exc}")
            return None
    return None



def sync_user_profile(user_id: str, email: str, name: str, avatar_url: str) -> Dict[str, Any]:
    """Fetch existing profile or create a new one on first login."""
    client = get_supabase_client()
    user_name = name or (email.split("@")[0] if email else "User")
    clean_profile = {
        "id": user_id,
        "email": email,
        "name": user_name,
        "avatar": avatar_url or "👤",
        "avatar_url": avatar_url or "👤",
        "role": "Employee",
        "department": "Organization Member",
        "location": "India",
        "country": "India",
        "auth_method": "Google OAuth 2.0",
    }

    if not client:
        return clean_profile

    try:
        res = client.table("profiles").select("*").eq("id", user_id).execute()
        if res.data and len(res.data) > 0:
            profile = res.data[0]
            # Ensure name/email from Google OAuth are up to date
            profile["name"] = profile.get("name") or user_name
            profile["email"] = profile.get("email") or email
            profile["avatar"] = profile.get("avatar_url") or avatar_url or "👤"
            return profile
        else:
            # Create new profile row
            client.table("profiles").insert(clean_profile).execute()
            return clean_profile
    except Exception as exc:
        logger.warning(f"Error syncing profile with Supabase: {exc}")
        return clean_profile



def update_user_profile(user_id: str, updates: Dict[str, Any]) -> bool:
    """Update profile fields in Supabase database."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        client.table("profiles").update(updates).eq("id", user_id).execute()
        return True
    except Exception as exc:
        logger.warning(f"Failed to update profile in Supabase: {exc}")
        return False


def load_user_conversations(user_id: str) -> Dict[str, Dict[str, Any]]:
    """Load all conversations and associated messages for an authenticated user."""
    client = get_supabase_client()
    if not client:
        return {}

    try:
        res_convs = client.table("conversations").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        if not res_convs.data:
            return {}

        convs_dict = {}
        for conv in res_convs.data:
            c_id = conv["id"]
            # Fetch messages for conversation
            res_msgs = client.table("messages").select("*").eq("conversation_id", c_id).order("timestamp", desc=False).execute()
            messages = []
            if res_msgs.data:
                for m in res_msgs.data:
                    if m["role"] == "user":
                        messages.append({"role": "user", "content": m["content"]})
                    else:
                        messages.append({
                            "role": "assistant",
                            "answer": {
                                "answer": m["content"],
                                "detected_policy": m.get("detected_policy"),
                                "sources": m.get("sources", []),
                            }
                        })
            convs_dict[c_id] = {
                "id": c_id,
                "title": conv.get("title", "Conversation"),
                "created_at": conv.get("created_at"),
                "policy_scope": conv.get("policy_scope"),
                "messages": messages,
            }
        return convs_dict
    except Exception as exc:
        logger.warning(f"Failed to load user conversations from Supabase: {exc}")
        return {}


def save_conversation(user_id: str, conv_id: str, title: str, policy_scope: Optional[str] = None) -> bool:
    """Upsert a conversation header into Supabase."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        data = {
            "id": conv_id,
            "user_id": user_id,
            "title": title,
            "policy_scope": policy_scope,
        }
        client.table("conversations").upsert(data).execute()
        return True
    except Exception as exc:
        logger.warning(f"Failed to save conversation in Supabase: {exc}")
        return False


def save_message(
    user_id: str,
    conv_id: str,
    role: str,
    content: str,
    detected_policy: Optional[str] = None,
    sources: Optional[List[Any]] = None,
) -> bool:
    """Save a user or assistant message to Supabase."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        data = {
            "conversation_id": conv_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "detected_policy": detected_policy,
            "sources": sources if isinstance(sources, list) else None,
        }
        client.table("messages").insert(data).execute()
        return True
    except Exception as exc:
        logger.warning(f"Failed to save message in Supabase: {exc}")
        return False


def load_saved_answers(user_id: str) -> List[Dict[str, Any]]:
    """Load user's saved/bookmarked policy answers."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        res = client.table("saved_answers").select("*").eq("user_id", user_id).order("saved_at", desc=True).execute()
        return res.data or []
    except Exception as exc:
        logger.warning(f"Failed to load saved answers: {exc}")
        return []


def save_answer_bookmark(user_id: str, answer_obj: Any) -> bool:
    """Save/bookmark an answer to Supabase."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        data = {
            "user_id": user_id,
            "policy_name": getattr(answer_obj, "detected_policy", None) or "General HR",
            "answer_text": getattr(answer_obj, "answer", str(answer_obj)),
            "sources": [s.model_dump() if hasattr(s, "model_dump") else s for s in getattr(answer_obj, "sources", [])],
        }
        client.table("saved_answers").insert(data).execute()
        return True
    except Exception as exc:
        logger.warning(f"Failed to bookmark answer: {exc}")
        return False


def delete_saved_answer(user_id: str, saved_id: str) -> bool:
    """Delete a saved answer from Supabase."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        client.table("saved_answers").delete().eq("id", saved_id).eq("user_id", user_id).execute()
        return True
    except Exception as exc:
        logger.warning(f"Failed to delete saved answer: {exc}")
        return False


def record_user_feedback(user_id: str, helpful: bool, reason: Optional[str] = None, answer_snippet: str = "") -> bool:
    """Save user feedback to Supabase."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        data = {
            "user_id": user_id,
            "helpful": helpful,
            "reason": reason,
            "answer_snippet": answer_snippet[:100],
        }
        client.table("feedback").insert(data).execute()
        return True
    except Exception as exc:
        logger.warning(f"Failed to save user feedback: {exc}")
        return False
