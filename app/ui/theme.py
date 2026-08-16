"""
Digital HR enterprise theme & styling system — Coforge Policy Intelligence.
Visual identity: Coforge Coral (#FF5B36), Intelligent Teal (#0F766E), Deep Navy (#101C2C), Warm Ivory (#F7F8F6).
"""
from __future__ import annotations

import streamlit as st


def apply_theme(theme_mode: str = "light") -> None:
    is_dark = theme_mode.lower() == "dark"

    if is_dark:
        bg_color = "#0B1220"
        sidebar_bg = "#0F172A"
        surface_bg = "#151F2E"
        surface_alt = "#1E293B"
        text_primary = "#F8FAFC"
        text_secondary = "#94A3B8"
        brand_coral = "#FF6B4A"
        brand_teal = "#2DD4BF"
        soft_teal_bg = "rgba(45, 212, 191, 0.1)"
        border_color = "#263447"
        user_msg_bg = "#1E293B"
        user_msg_text = "#F8FAFC"
    else:
        bg_color = "#F7F8F6"
        sidebar_bg = "#101C2C"
        surface_bg = "#FFFFFF"
        surface_alt = "#F1F4F8"
        text_primary = "#172033"
        text_secondary = "#667085"
        brand_coral = "#FF5B36"
        brand_teal = "#0F766E"
        soft_teal_bg = "rgba(15, 118, 110, 0.08)"
        border_color = "#DCE2E8"
        user_msg_bg = "#EAF0F6"
        user_msg_text = "#172033"

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :root {{
        --bg-color: {bg_color};
        --sidebar-bg: {sidebar_bg};
        --surface-bg: {surface_bg};
        --surface-alt: {surface_alt};
        --text-primary: {text_primary};
        --text-secondary: {text_secondary};
        --brand-coral: {brand_coral};
        --brand-teal: {brand_teal};
        --soft-teal-bg: {soft_teal_bg};
        --border-color: {border_color};
        --user-msg-bg: {user_msg_bg};
    }}

    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: {text_primary};
    }}

    .stApp {{
        background-color: {bg_color};
    }}

    /* Sidebar Styling (Deep Navy) */
    section[data-testid="stSidebar"] {{
        background-color: {sidebar_bg} !important;
        border-right: 1px solid {border_color} !important;
    }}

    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] h4, 
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label {{
        color: #F8FAFC !important;
    }}

    section[data-testid="stSidebar"] .stButton > button {{
        background-color: rgba(255, 255, 255, 0.05);
        color: #F8FAFC;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 8px;
        font-weight: 500;
        text-align: left;
        transition: all 0.18s ease;
    }}

    section[data-testid="stSidebar"] .stButton > button:hover {{
        background-color: rgba(255, 91, 54, 0.15);
        border-color: {brand_coral};
        color: #FFFFFF;
    }}

    section[data-testid="stSidebar"] button[kind="primary"] {{
        background-color: {brand_coral} !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 600 !important;
    }}

    section[data-testid="stSidebar"] input {{
        background-color: rgba(255, 255, 255, 0.08) !important;
        color: #F8FAFC !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
    }}

    /* Main Typography */
    h1, h2, h3, h4 {{
        color: {text_primary} !important;
        font-weight: 700 !important;
        letter-spacing: -0.3px;
    }}

    p, span, label {{
        color: {text_primary};
        line-height: 1.6;
    }}

    /* Chat Messages */
    .stChatMessage {{
        background-color: transparent !important;
        border: none !important;
        padding: 12px 0 !important;
    }}

    /* User Message Bubble */
    .stChatMessage[data-testid="stChatMessageUser"] {{
        background-color: {user_msg_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 12px 12px 2px 12px !important;
        padding: 14px 18px !important;
        color: {user_msg_text} !important;
        margin-left: 20% !important;
        margin-bottom: 16px !important;
    }}

    /* Assistant Message Surface */
    .stChatMessage[data-testid="stChatMessageAssistant"] {{
        background-color: {surface_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 12px 12px 12px 2px !important;
        padding: 18px 22px !important;
        margin-right: 5% !important;
        margin-bottom: 16px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}

    /* Floating Chat Input Composer */
    div[data-testid="stChatInput"] {{
        border-top: none !important;
        background: transparent !important;
    }}

    div[data-testid="stChatInput"] textarea {{
        border: 1.5px solid {border_color} !important;
        border-radius: 12px !important;
        background-color: {surface_bg} !important;
        color: {text_primary} !important;
        font-size: 0.98rem !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important;
        padding: 12px 16px !important;
    }}

    div[data-testid="stChatInput"] textarea:focus {{
        border-color: {brand_teal} !important;
        box-shadow: 0 0 0 2px {soft_teal_bg} !important;
    }}

    /* Buttons */
    .stButton > button {{
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s ease;
    }}

    /* Expanders & Cards */
    .stExpander {{
        border: 1px solid {border_color} !important;
        border-radius: 10px !important;
        background-color: {surface_bg} !important;
    }}

    /* Hide Streamlit default chrome */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
