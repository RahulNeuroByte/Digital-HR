"""
Main Chat UI for Siya: Welcome hero, policy exploration chips, conversation stream, response feedback,
intent-based routing (casual chat, policy catalog, document generation, out-of-domain, follow-ups).
"""
from __future__ import annotations

import random
from datetime import datetime
import streamlit as st

from app.db import db_manager
from app.llm.gemini_client import (
    generate_answer_stream_with_container,
    generate_casual_chat_stream
)
from app.llm.prompts import build_casual_chat_prompt, build_out_of_domain_prompt
from app.retrieval.retriever import retrieve
from app.routing.intent_router import classify_intent, QueryIntent
from app.retrieval.policy_catalog import format_policy_catalog_response
from app.utils.pdf_generator import generate_answer_pdf
from app.schemas.models import ChatAnswer
from app.ui.state import auto_generate_title, save_answer, record_feedback
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Candidate policy questions derived 100% strictly from official HR policy documents
POLICY_EXPLORER_QUESTIONS = [
    ("Leave & Attendance Policy", "How many leaves can I carry forward in India?"),
    ("Shift Allowance Policy", "What are the shift allowance rates for night shifts?"),
    ("Notice Period Policy", "What is the notice period duration during probation?"),
    ("Moonlighting Policy", "What are the rules regarding secondary employment or moonlighting?"),
    ("Retirement Policy", "What is the retirement age and superannuation benefit policy?"),
    ("Travel & Conveyance Policy", "What are the domestic travel allowance and per diem rates?"),
    ("Medical Insurance Policy", "What is the medical insurance coverage for dependents?"),
    ("POSH Policy", "What is the process for lodging a complaint under POSH policy?"),
    ("Remote Work Policy", "What are the guidelines for remote work and WFH approval?"),
    ("Referral Policy", "What is the employee referral bonus structure?"),
    ("Higher Education Policy", "What is the tuition reimbursement policy for higher education?"),
    ("IT Security Policy", "What are the guidelines for handling company laptop and IT assets?"),
    ("PIP Policy", "What is the PIP process and evaluation duration?"),
    ("Maternity Leave Policy", "What is the maternity leave entitlement in India?"),
    ("Paternity Leave Policy", "What is the paternity leave duration and eligibility criteria?"),
    ("Bereavement Leave Policy", "How many days of bereavement leave are granted for immediate family?"),
    ("Relocation Policy", "What relocation expenses and initial accommodation are covered?"),
    ("Performance Appraisal Policy", "What is the annual performance review cycle and rating scale?"),
    ("Hybrid Work Policy", "What is the mandatory office attendance policy per week?"),
    ("Gratuity Policy", "What is the minimum service requirement to claim gratuity?"),
]


def _get_thread_suggested_questions(thread_id: str, force_refresh: bool = False) -> list[tuple[str, str]]:
    """Return 4 dynamically randomized candidate policy questions for the thread."""
    cache_key = f"explore_questions_{thread_id}"
    if force_refresh or cache_key not in st.session_state:
        st.session_state[cache_key] = random.sample(
            POLICY_EXPLORER_QUESTIONS, min(4, len(POLICY_EXPLORER_QUESTIONS))
        )
    return st.session_state[cache_key]



def _render_source_ux(answer: ChatAnswer, msg_idx: int) -> None:
    """Disabled source UI — policy source metadata is strictly hidden from user view."""
    return None


def _render_explainability(answer: ChatAnswer) -> None:
    """Render developer-only benchmark breakdown if debug mode is explicitly enabled in session state."""
    if not st.session_state.get("debug_mode", False):
        return

    with st.expander("🛡️ Developer Benchmark Metrics (Debug Mode)"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Detected Policy Scope", answer.detected_policy or "Cross-policy")
        with col2:
            st.metric("Evidence Chunks", answer.chunks_used)
        with col3:
            st.metric("Retrieval Quality", answer.quality_rating)
        with col4:
            st.metric("Total Latency", f"{answer.total_latency_ms:.2f} ms")


def _render_response_actions(answer: ChatAnswer, msg_idx: int) -> None:
    """Render interactive response feedback & bookmarking bar."""
    col1, col2, col3, col4 = st.columns([1, 1, 1.5, 4.5])
    is_guest = st.session_state.get("is_guest", False)

    with col1:
        if st.button("👍", key=f"helpful_{msg_idx}", help="Helpful"):
            record_feedback(answer.answer, True)
            st.toast("Thank you for your feedback!", icon="👍")

    with col2:
        if st.button("👎", key=f"unhelpful_{msg_idx}", help="Not helpful"):
            st.session_state[f"show_feedback_reason_{msg_idx}"] = True

    with col3:
        if st.button("⭐ Save Answer", key=f"save_{msg_idx}"):
            if is_guest:
                st.toast("Sign in with Google to save answers.", icon="ℹ️")
            else:
                save_answer(answer)
                st.toast("Answer saved to your bookmarks!", icon="⭐")

    # Feedback reason selector popup
    if st.session_state.get(f"show_feedback_reason_{msg_idx}"):
        reason = st.selectbox(
            "Why was this answer not helpful?",
            ["Incorrect answer", "Not relevant", "Missing information", "Other"],
            key=f"reason_sel_{msg_idx}",
        )
        if st.button("Submit Feedback", key=f"sub_reason_{msg_idx}"):
            record_feedback(answer.answer, False, reason)
            st.session_state[f"show_feedback_reason_{msg_idx}"] = False
            st.toast("Feedback recorded.", icon="✅")
            st.rerun()


def _render_assistant_message(answer: ChatAnswer, msg_idx: int) -> None:
    # Header Identity — Siya Persona
    st.markdown(
        """
        <div style='display: flex; align-items: center; gap: 8px; margin-bottom: 8px;'>
            <span style='font-weight: 700; color: #172033; font-size: 1.02rem;'>Siya</span>
            <span style='background-color: rgba(37, 99, 235, 0.08); color: #2563EB; padding: 2px 8px; border-radius: 12px; font-size: 0.72rem; font-weight: 600;'>AI HR Colleague</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(answer.answer)
    
    _render_response_actions(answer, msg_idx)
    _render_explainability(answer)


def render_chat() -> None:
    # Strict CSS rule: Hide all policy source expanders/details elements & disable heading anchor links
    st.markdown(
        """
        <style>
        a.anchor-link,
        .stMarkdown a.anchor-link,
        [data-testid="stMarkdownContainer"] a.anchor-link {
            display: none !important;
            pointer-events: none !important;
            visibility: hidden !important;
        }
        div[data-testid="stChatMessage"] details,
        div[data-testid="stChatMessage"] [data-testid="stExpander"],
        div[data-testid="stChatMessage"] div:has(> summary) {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Ensure active conversation messages alias is synced
    active_id = st.session_state.get("active_chat_id")
    if not active_id or active_id not in st.session_state.conversations:
        from app.ui.state import create_new_chat
        active_id = create_new_chat()

    thread = st.session_state.conversations[active_id]
    messages = thread["messages"]
    is_guest = st.session_state.get("is_guest", False)

    # Guest Notification Banner
    if is_guest:
        st.info("💡 You're chatting with Siya in Guest Mode. Sign in with Google to save your conversations permanently.")

    # Render Welcome Hero if empty thread
    if not messages:
        hour = datetime.now().hour
        if hour < 12:
            greeting_time = "Good morning"
        elif hour < 17:
            greeting_time = "Good afternoon"
        else:
            greeting_time = "Good evening"

        if is_guest:
            greeting_heading = "Hi, I'm Siya 👋"
        else:
            user_name = st.session_state.get("user_profile", {}).get("name", "User")
            greeting_heading = f"{greeting_time}, {user_name}! I'm Siya 👋"

        st.markdown(
            f"""
            <div style='text-align: center; padding: 28px 20px 22px; background-color: #FFFFFF; border: 1px solid #DCE2E8; border-radius: 16px; margin-bottom: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.03);'>
                <div style='font-size: 0.85rem; font-weight: 700; color: #667085; margin-bottom: 6px; letter-spacing: 0.5px;'>
                    <span style='color: #FF5B36; font-size: 1.05rem;'>Co</span><span style='color: #172033; font-size: 1.05rem;'>forge</span> &nbsp;•&nbsp; HR-India Policy Desk
                </div>
                <div style='color: #172033; font-size: 2.1rem; margin-top: 4px; margin-bottom: 0px; font-weight: 700; line-height: 1.2;'>
                    {greeting_heading}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_hdr1, col_hdr2 = st.columns([5, 1])
        with col_hdr1:
            st.markdown("<div style='color: #172033; font-size: 1.15rem; font-weight: 700; margin-bottom: 10px;'>Explore HR Policies</div>", unsafe_allow_html=True)
        with col_hdr2:
            if st.button("🔄 Shuffle", key=f"shuffle_q_{active_id}", help="Randomize sample policy questions"):
                _get_thread_suggested_questions(active_id, force_refresh=True)
                st.rerun()

        candidate_questions = _get_thread_suggested_questions(active_id)
        c1, c2 = st.columns(2)

        with c1:
            cat1, q1 = candidate_questions[0]
            if st.button(f"🛡️ {q1}", key=f"exp_btn_0_{active_id}", use_container_width=True, help=cat1):
                st.session_state["pending_sample_query"] = q1
                st.rerun()

            cat2, q2 = candidate_questions[1]
            if st.button(f"🛡️ {q2}", key=f"exp_btn_1_{active_id}", use_container_width=True, help=cat2):
                st.session_state["pending_sample_query"] = q2
                st.rerun()

        with c2:
            cat3, q3 = candidate_questions[2]
            if st.button(f"🛡️ {q3}", key=f"exp_btn_2_{active_id}", use_container_width=True, help=cat3):
                st.session_state["pending_sample_query"] = q3
                st.rerun()

            cat4, q4 = candidate_questions[3]
            if st.button(f"🛡️ {q4}", key=f"exp_btn_3_{active_id}", use_container_width=True, help=cat4):
                st.session_state["pending_sample_query"] = q4
                st.rerun()

    # Render existing conversation messages
    for idx, message in enumerate(messages):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                _render_assistant_message(message["answer"], idx)
            else:
                st.markdown(message["content"])

    # Check for pending sample question OR chat_input submission
    pending_query = st.session_state.pop("pending_sample_query", None)
    input_text = st.chat_input("Chat with Siya about HR policies or anything else…")

    question = pending_query or input_text

    if not question:
        st.caption("💡 *Tip: Mention a policy name (e.g. 'Leave Policy') to search that document directly.*")
        return


    # Update thread title locally if first question
    if not thread["messages"]:
        thread["title"] = auto_generate_title(question)
        if not is_guest and st.session_state.get("authenticated"):
            user_id = st.session_state.user_profile.get("id")
            if user_id:
                db_manager.save_conversation(user_id, active_id, thread["title"])

    # Append User Message
    messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    if not is_guest and st.session_state.get("authenticated"):
        user_id = st.session_state.user_profile.get("id")
        if user_id:
            db_manager.save_message(user_id, active_id, "user", question)

    # ── INTENT ROUTING ENGINE ────────────────────────────────────────────────
    intent = classify_intent(question, history=messages)

    # 1. CASUAL CHAT & GREETINGS (BYPASS RAG — DYNAMIC SIYA RESPONSE)
    if intent in (QueryIntent.GREETING, QueryIntent.CASUAL_CHAT):
        logger.info("USER MESSAGE: '%s' | INTENT: %s | ROUTE: CASUAL | RAG: SKIPPED", question, intent.value)
        with st.chat_message("assistant"):
            chat_prompt = build_casual_chat_prompt(question, history=messages)
            stream_gen = generate_casual_chat_stream(chat_prompt)
            full_text = st.write_stream(stream_gen)
            answer = ChatAnswer(answer=full_text or "Hey there! How can I help you today?", no_answer=False, grounded=False)
            _render_response_actions(answer, len(messages))
        messages.append({"role": "assistant", "answer": answer})
        return

    # 2. OUT OF DOMAIN INTENT (DYNAMIC SIYA SCOPE EXPLANATION — NO RAG)
    if intent == QueryIntent.OUT_OF_DOMAIN:
        logger.info("USER MESSAGE: '%s' | INTENT: %s | ROUTE: OUT_OF_DOMAIN | RAG: SKIPPED", question, intent.value)
        with st.chat_message("assistant"):
            ood_prompt = build_out_of_domain_prompt(question)
            stream_gen = generate_casual_chat_stream(ood_prompt)
            full_text = st.write_stream(stream_gen)
            answer = ChatAnswer(answer=full_text or "I'm Siya, your Coforge HR colleague! That topic is outside my HR-policy knowledge.", no_answer=True, grounded=False)
            _render_response_actions(answer, len(messages))
        messages.append({"role": "assistant", "answer": answer})
        return

    # 3. POLICY CATALOG INTENT
    if intent == QueryIntent.POLICY_LIST:
        logger.info("USER MESSAGE: '%s' | INTENT: %s | ROUTE: POLICY_LIST | RAG: SKIPPED", question, intent.value)
        catalog_msg = format_policy_catalog_response(question)
        answer = ChatAnswer(answer=catalog_msg, no_answer=False, grounded=True)
        with st.chat_message("assistant"):
            st.markdown(catalog_msg)
            _render_response_actions(answer, len(messages))
        messages.append({"role": "assistant", "answer": answer})
        return

    # 4. DOCUMENT GENERATION (PDF) INTENT
    if intent == QueryIntent.DOCUMENT_GENERATION:
        logger.info("USER MESSAGE: '%s' | INTENT: %s | ROUTE: DOC_GEN | RAG: SKIPPED", question, intent.value)
        last_ans_text = ""
        last_policy_name = thread.get("policy_scope", "HR-India Policy Desk")
        for m in reversed(messages):
            if m.get("role") == "assistant" and m.get("answer"):
                ans_obj = m.get("answer")
                last_ans_text = ans_obj.answer
                if ans_obj.detected_policy:
                    last_policy_name = ans_obj.detected_policy
                break

        if not last_ans_text:
            last_ans_text = "Coforge HR-India policy summary requested by employee."

        pdf_bytes = generate_answer_pdf(
            title="Digital HR Policy Information",
            content=last_ans_text,
            policy_name=last_policy_name
        )

        doc_msg = "Here is your requested HR policy document formatted for download:"
        answer = ChatAnswer(answer=doc_msg, no_answer=False, grounded=True)

        with st.chat_message("assistant"):
            st.markdown(doc_msg)
            st.download_button(
                label="📄 Download HR Policy PDF Document",
                data=pdf_bytes,
                file_name="Digital_HR_Policy_Summary.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            _render_response_actions(answer, len(messages))
        messages.append({"role": "assistant", "answer": answer})
        return

    # 5. POLICY QUERY / CONVERSATIONAL FOLLOW-UP (GROUNDED RAG RETRIEVAL)
    logger.info("USER MESSAGE: '%s' | INTENT: %s | ROUTE: RAG | RAG: EXECUTED", question, intent.value)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Siya is thinking..."):
                # Pass recent conversation messages for follow-up context resolution
                chunks, policy_match, metrics = retrieve(question, history=messages)
                detected_policy = policy_match.policy_name if policy_match.matched else None
                thread["policy_scope"] = detected_policy

            captured_answer: list[ChatAnswer] = []

            def on_complete(ans: ChatAnswer):
                ans._raw_chunks = chunks
                captured_answer.append(ans)

            # Stream tokens live to UI
            stream_gen = generate_answer_stream_with_container(
                question, chunks, detected_policy, metrics, on_complete=on_complete
            )
            st.write_stream(stream_gen)

            answer = captured_answer[0] if captured_answer else ChatAnswer(answer="")
            answer._raw_chunks = chunks
            msg_idx = len(messages)

            _render_response_actions(answer, msg_idx)

            # Persist assistant message to DB for authenticated users
            if not is_guest and st.session_state.get("authenticated"):
                user_id = st.session_state.user_profile.get("id")
                if user_id:
                    sources_list = [s.model_dump() if hasattr(s, "model_dump") else s for s in answer.sources]
                    db_manager.save_message(user_id, active_id, "assistant", answer.answer, detected_policy, sources_list)

        except Exception as exc:
            answer = ChatAnswer(
                answer=f"Something went wrong answering that question: {exc}",
                no_answer=True,
                grounded=False,
            )
            st.error(answer.answer)

    messages.append({"role": "assistant", "answer": answer})
