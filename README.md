# Digital-HR — Siya | Enterprise HR-India AI Policy Assistant

**Digital-HR** is an enterprise-grade HR Policy Assistant for **Coforge HR-India**, featuring **Siya** — an intelligent, warm, approachable, and professional AI HR colleague.

Siya provides instant, accurate, and grounded answers to employee HR policy questions, supports natural casual conversation, resolves context-aware follow-up questions, and dynamically generates downloadable HR policy PDF documents.

---

## 1. Project Title & Identity

* **Project Name**: Digital-HR
* **User-Facing AI Assistant Persona**: **Siya** (*AI HR Colleague & Policy Assistant*)
* **Organization Scope**: Coforge HR-India Employees

---

## 2. Project Overview

Finding specific information in lengthy corporate HR policy PDFs can be time-consuming and inefficient. **Digital-HR** solves this problem by providing a intelligent conversational interface powered by Retrieval-Augmented Generation (RAG).

Employees can:
- Ask questions about 16 official Coforge HR-India policy documents in plain English or natural Hinglish.
- Have friendly casual conversations with **Siya** without triggering robotic policy search errors.
- Ask context-aware follow-up questions (*"tell me more about it"*, *"what documents are required?"*).
- Download customized HR policy summary documents as PDFs directly from the chat interface.
- Use Google OAuth 2.0 or Guest Mode for seamless access.

---

## 3. Key Features

- 🤖 **Siya AI HR Persona**: Warm, intelligent, and human-like AI colleague.
- 📚 **16 Official Coforge HR Policies**: Pre-indexed vector embeddings in local persistent ChromaDB.
- ⚡ **Zero-Latency Intent Routing**: Automatically routes queries to Casual Chat, Policy List, PDF Document Generation, Out-of-Domain, or Grounded Policy Search.
- 🗣️ **Natural Hinglish & English Support**: Understands natural phrasing in both English and Hinglish (e.g. *"leave kaise apply karu?"*).
- 💬 **Context-Aware Follow-Up Engine**: Rewrites referential follow-up questions (*"it"*, *"this"*, *"that"*) using past conversation context.
- 📄 **Dynamic PDF Document Generation**: Generates A4 HR policy PDFs on demand using `fpdf2`.
- 🔐 **Dual Auth (Google OAuth 2.0 PKCE + Guest Mode)**: Secure sign-in via Supabase PKCE or instant Guest access.
- 💾 **Persistent Chat History & Bookmarks**: Save conversations, record feedback (👍 / 👎), and bookmark important answers in Supabase PostgreSQL.
- 🛡️ **Strict Policy Grounding**: Anti-hallucination guardrails enforce zero invented contact numbers, rates, or dates.
- 🙈 **Zero Source UI Leakage**: Policy source metadata remains active in backend memory for grounding but is completely hidden from user view.

---

## 4. Siya — AI Assistant Behavior

Siya is designed to behave like a supportive HR colleague:
- **No Static Response Templates**: Never uses forced openings (*"Hello! I'd be happy to help..."*), fixed closing boilerplate, or forced section headings.
- **Adaptive Length & Structure**: Adapts formatting to the user's question depth — simple queries get concise 1–3 sentence answers; detailed requests get structured breakdowns.
- **Casual Chat Mode**: Bypasses ChromaDB vector search for small talk (*"hii"*, *"how are you?"*, *"I'm bored"*, *"thanks"*, *"bye"*) to stream warm conversational replies.
- **Out-of-Scope Handling**: Non-HR queries (*"Who won yesterday's match?"*) receive dynamic, varied scope explanations rather than stock repetitive sentences.

---

## 5. Architecture

```text
User Input
    │
    ▼
Streamlit Frontend (app.py / app/ui/chat.py)
    │
    ▼
Intent Routing Engine (app/routing/intent_router.py)
    ├── GREETING / CASUAL_CHAT ────────► Gemini Direct Stream (Siya Persona)
    ├── OUT_OF_DOMAIN ─────────────────► Gemini Dynamic Scope Stream
    ├── POLICY_LIST ───────────────────► Policy Catalog Renderer (policy_catalog.py)
    ├── DOCUMENT_GENERATION ───────────► fpdf2 PDF Generator (pdf_generator.py)
    └── POLICY_QUERY / FOLLOW_UP
            │
            ▼
   Context Rewriter (retriever.py)
            │
            ▼
   Vector Search (ChromaDB / sentence-transformers)
            │
            ▼
   Evidence Validator (evidence_validator.py)
            │
            ▼
   Gemini Grounded LLM Stream (gemini_client.py)
            │
            ▼
   Streamed UI Response + Supabase History Persist
```

---

## 6. Technology Stack

- **Frontend**: Streamlit 1.42+ with custom Vanilla CSS design tokens.
- **Backend & Logic**: Python 3.11+.
- **AI / LLM**: Google Gemini 2.5 Flash (`google-genai` SDK).
- **Vector Database & RAG**: ChromaDB 0.6+ with `all-MiniLM-L6-v2` embeddings via `sentence-transformers`.
- **Database & Auth**: Supabase PostgreSQL with PKCE flow (`supabase-py`).
- **PDF Generation**: `fpdf2`.
- **Testing**: `pytest` (28 unit tests).

---

## 7. Project Structure

```text
Digital-HR/
├── app/
│   ├── config/          # Environment settings & pydantic configuration
│   ├── db/              # Supabase database manager & profile syncing
│   ├── llm/             # Gemini API client & prompt definitions
│   ├── retrieval/       # ChromaDB vector store, retriever, & policy catalog
│   ├── routing/         # Intent router & policy matcher
│   ├── schemas/         # Pydantic data models
│   ├── ui/              # Streamlit view modules (auth, chat, modals, state)
│   └── utils/           # PDF generator, text cleaner, logger, chunker
├── chroma_db/           # Local persistent ChromaDB vector index
├── docs/                # 16 Official Coforge HR Policy PDF documents
├── scripts/             # Document ingestion & verification scripts
├── static/              # Branding assets & Coforge logos
├── tests/               # Automated unit test suite (28 tests)
├── .env.example         # Environment variable template
├── .gitignore           # Git ignore file
├── app.py               # Streamlit application entry point
├── package.json         # Node package configuration
├── README.md            # Comprehensive documentation
└── requirements.txt     # Frozen Python dependencies
```

---

## 8. RAG Pipeline & Ingestion

1. **PDF Processing & Chunking**: Policy PDFs in `./docs` are read page by page, cleaned using regex, and split into overlapping text chunks with exact page traceability.
2. **Vector Storage**: Embeddings are calculated using `all-MiniLM-L6-v2` and stored in local ChromaDB at `./chroma_db`.
3. **Hybrid Retrieval**: Queries check exact policy matches first, falling back to top-K cosine similarity (default `TOP_K=5`, `SIMILARITY_THRESHOLD=0.35`).
4. **Context Construction & Grounding**: Retrieved chunks are passed into Gemini's system prompt to guarantee 100% grounded answers.

---

## 9. Conversation Context & Follow-Ups

- **Query Rewriter**: `resolve_conversational_context()` in `app/retrieval/retriever.py` inspects past chat turns to resolve pronouns (*"it"*, *"this"*, *"that"*).
- For example, if the previous question was about *Leave Policy* and the user asks *"tell me more about it"*, the system rewrites the query to *"Give detailed information about Leave Policy application process"*.

---

## 10. Authentication & Security

- **Google OAuth 2.0**: Configured using Supabase PKCE authorization code flow.
- **Guest Mode**: Allows instant usage without login; guest data operates strictly in temporary memory (`st.session_state`) and is never written to disk or database.
- **Data Isolation**: Database queries scope user threads strictly by `user_id`.

---

## 11. Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# Storage Paths
CHROMA_PERSIST_DIRECTORY=./chroma_db
DOCS_DIRECTORY=./docs

# Retrieval Parameters
TOP_K=5
SIMILARITY_THRESHOLD=0.35

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key_here
```

---

## 12. Local Setup Instructions (Windows)

1. **Clone Repository & Set Up Virtual Environment**:
   ```powershell
   git clone https://github.com/your-username/digital-hr-siya.git
   cd digital-hr-siya
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. **Install Dependencies**:
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   ```powershell
   copy .env.example .env
   # Edit .env with your actual credentials
   ```

4. **Ingest Policy Documents (Optional / Re-indexing)**:
   ```powershell
   python scripts/ingest_documents.py
   ```

5. **Run Streamlit Application**:
   ```powershell
   streamlit run app.py
   ```

---

## 13. How to Run Tests

Run the full automated test suite (28 tests):

```powershell
.\venv\Scripts\pytest.exe -v
```

---

## 14. Deployment Guidelines

- **Frontend / Host**: Can be deployed to Streamlit Community Cloud, AWS App Runner, GCP Cloud Run, or Azure App Service.
- **Environment Secrets**: Ensure `GEMINI_API_KEY`, `SUPABASE_URL`, and `SUPABASE_ANON_KEY` are configured in your deployment platform's secret manager.
- **Persistence**: Include `./chroma_db` directory or run `python scripts/ingest_documents.py` during build/startup.

---

## 15. Security & Privacy

- All sensitive keys are managed via environment variables and excluded via `.gitignore`.
- No actual secrets or credentials are committed to the repository.
- User data is completely isolated by unique Supabase user IDs.

---

## 16. Current Implementation Status

**STATUS: COMPLETED & PRODUCTION-READY**
- 28 / 28 Automated Unit Tests Passing
- Siya Conversational Persona Verified
- RAG Policy Retrieval Verified
- Google OAuth & Guest Mode Verified
