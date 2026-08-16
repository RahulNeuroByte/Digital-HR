# Digital HR - Task Tracker

## Phase 1 - Foundation
- [x] Project structure
- [x] Configuration (`app/config/settings.py`)
- [x] Logging
- [ ] Python virtual environment (user runs on their own Windows machine)
- [ ] Dependency installation (user runs on their own Windows machine)

## Phase 2 - Policy ingestion
- [x] PyMuPDF extraction — verified on real PIP Policy PDF
- [x] OCR fallback (code complete; not exercised — supplied PDF didn't need it)
- [x] Cleaning
- [x] Chunking (page-boundary-safe, 220/40 word overlap)
- [x] Metadata (document, policy_name, page, chunk_index, extraction_method)
- [x] Chroma indexing (code complete; blocked in build sandbox by network
      allowlist — needs user's machine to download the embedding model)
- [ ] Ingest remaining 15 PDFs (only PIP Policy supplied so far)

## Phase 3 - Retrieval
- [x] Embeddings wrapper (Sentence-Transformers, cached singleton)
- [x] Policy router (exact / normalized / abbreviation / RapidFuzz)
- [x] Policy metadata filtering (ChromaDB `where` clause)
- [x] Similarity threshold gate
- [x] No-answer handling (LLM never called if nothing clears threshold)

## Phase 4 - Gemini
- [x] Gemini client (`google-genai` SDK)
- [x] Grounded prompt (strict system instruction)
- [x] Extractive fallback when no API key configured
- [x] Source rendering (policy name + page)

## Phase 5 - Authentication
- [ ] NOT IN SCOPE for this POC (see BRAIN.md "Scope decision")

## Phase 6 - User data
- [ ] NOT IN SCOPE for this POC — chat history is Streamlit session-only

## Phase 7 - Streamlit
- [x] Chat UI
- [x] Sidebar (indexed policies list, new chat, config status)
- [x] Neon blue & white theme
- [x] Loading/error states (spinner + try/except around the full pipeline)
- [ ] Login (not in scope)
- [ ] Profile / Security pages (not in scope)

## Phase 8 - Testing
- [x] Policy-specific query routing — `tests/test_policy_router.py` (5 tests)
- [x] Cross-policy (no policy named) — covered in policy router tests
- [x] Chunking correctness — `tests/test_chunker.py` (4 tests)
- [x] Cleaning correctness — `tests/test_cleaner.py` (3 tests)
- [x] All 12 tests passing in the build sandbox
- [ ] Hallucination / no-answer test against live index (needs real
      ingestion run on user's machine)
- [ ] Authentication tests — not in scope

## Phase 9 - Documentation
- [x] README.md
- [x] COMPLETE_SETUP.md (Windows)
- [x] BRAIN.md
- [x] TASKS.md
