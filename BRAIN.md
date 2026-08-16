# BRAIN.md — Digital HR persistent working memory

**Last updated:** 2026-08-14

## Project objective
Employee-facing HR policy chatbot. Answers ONLY from indexed HR policy PDFs.
Core business rule: if a user names a policy explicitly, retrieval is
restricted to that policy; otherwise it searches across all indexed policies.

## Scope decision (important — do not silently reverse)
The original spec (`Digital_HR_Claude_Manus_Prompt.docx`) describes a full
production system: Supabase Auth (email/OTP/Google OAuth/TOTP MFA), per-user
profiles, persistent multi-user chat/search history with Row Level Security.

**Decision:** for this POC, the user explicitly asked to keep it simpler.
Supabase Auth, OAuth, MFA, profiles, and persistent multi-user history were
**intentionally omitted**. Chat history lives only in Streamlit
`session_state` (cleared on refresh / "New chat"). The retrieval + routing +
generation core was still built to the full spec's design so this can be
extended later — see "Next tasks" below for exactly what that extension
would touch.

## Architecture (as built)
```
PDF (docs/) → PyMuPDF extraction (OCR fallback per page if <20 chars)
            → clean_text() → word-based chunker (220 words, 40 overlap,
              never spans a page boundary)
            → Sentence-Transformers (all-MiniLM-L6-v2) embeddings
            → ChromaDB persistent collection "hr_policies"
              (metadata: document, policy_name, page, chunk_index, extraction_method)

User query  → policy_router.detect_policy() — exact → normalized → abbreviation
              → RapidFuzz fallback (threshold configurable, default 85)
            → vector_store.query(where={"policy_name": ...} if matched)
            → similarity_threshold filter (default 0.35, cosine)
            → if no chunks survive: safe no-answer, LLM is never called
            → else: gemini_client.generate_answer()
              - if GEMINI_API_KEY set: grounded Gemini call with strict
                system instruction (app/llm/prompts.py)
              - if not set: extractive fallback (shows top passages
                verbatim with citations, clearly labeled as non-LLM)
```

Policy-aware filtering is enforced at the ChromaDB query layer
(`where={"policy_name": ...}`), never by asking the LLM to "ignore"
irrelevant context.

## Technology decisions
- **Chunking:** simple word-count splitter (220/40 overlap), not a heavier
  library — kept dependency-free and easy to explain for a POC.
- **Policy name derivation:** from filename (underscores/hyphens → spaces).
  Works for the 16-PDF naming convention seen in the user's screenshot
  (e.g. `Notice_Period_Policy.pdf` → "Notice Period Policy").
- **Embedding model:** all-MiniLM-L6-v2 (local, free, no API key needed).
- **No-answer control:** similarity threshold gate BEFORE the LLM call, not
  inside the prompt — this is a hard code-level gate, not a soft instruction.

## Current implementation status: CORE COMPLETE
### Done
- Project structure (section 12 of the original spec, minus auth/db folders)
- `app/config/settings.py` — env-based config, no hard-coded secrets
- `app/utils/logging.py`
- `app/ingestion/{pdf_loader, ocr_fallback, cleaner, chunker, indexer}.py`
- `app/retrieval/{embeddings, vector_store, retriever}.py`
- `app/routing/policy_router.py`
- `app/llm/{prompts, gemini_client}.py` — with no-key extractive fallback
- `app/schemas/models.py` (Pydantic)
- `app/ui/{chat, sidebar}.py` + `app.py` (neon blue/white theme as requested)
- `scripts/{ingest_policies, rebuild_index, health_check}.py`
- `tests/{test_policy_router, test_chunker, test_cleaner}.py` — 12/12 passing
- `docs/` seeded with the one PDF supplied so far: "Performance Improvement
  Plan (PIP) Policy.pdf"

### Verified in the build sandbox
- PyMuPDF extraction on the real PIP Policy PDF: 8 pages, all machine-text
  (no OCR needed), 10 chunks produced.
- Policy router: exact, abbreviation ("PIP" → full name), fuzzy-typo, and
  no-match cases all pass against a 5-policy test set.
- Chunker/cleaner unit tests: 12/12 passing.
- ChromaDB + embeddings wiring is correct but **could not be executed to
  completion in the build sandbox** — the sandbox's network allowlist
  blocks huggingface.co (403), which is required to download
  all-MiniLM-L6-v2 on first run. This is a sandbox limitation only; it will
  download normally on a Windows machine with standard internet access.
  **Action for the user:** run `scripts/health_check.py` after `pip install`
  on your machine to confirm the model downloads and indexing completes.

### Not built (by scope decision, see above)
- Supabase Auth (email/password, phone/OTP, Google OAuth)
- TOTP/MFA
- User profiles
- Persistent, multi-user chat/search history + RLS
- Login/signup screens

## Known issues / things to watch
- Only 1 of 16 policy PDFs has been supplied and ingested so far (PIP Policy).
  Drop the remaining 15 into `docs/` and re-run
  `python scripts/ingest_policies.py` — no code changes needed.
- `ocr_fallback.py` requires `ocrmypdf` + Tesseract installed on the host
  machine; if absent, OCR pages just come back empty (logged as a warning,
  not a crash). Not tested against a real scanned PDF yet since the one
  supplied PDF didn't need OCR.
- `SIMILARITY_THRESHOLD` (default 0.35) has not been tuned against a mix of
  real policies yet — once more PDFs are ingested, sanity-check that
  legitimate questions aren't being rejected as "no answer" and irrelevant
  ones aren't slipping through.

## Next tasks (priority order)
1. User: install deps + add remaining 15 PDFs to `docs/`, run
   `scripts/ingest_policies.py`, run `scripts/health_check.py`.
2. Tune `SIMILARITY_THRESHOLD` / `TOP_K` against real multi-policy queries.
3. Get a Gemini API key and set `GEMINI_API_KEY` in `.env` to move off the
   extractive fallback.
4. (If/when needed) Add Supabase Auth + profiles + persistent history —
   the retrieval/routing/generation core does not need to change; only
   `app.py` (add login gate) and new `app/auth/`, `app/database/` modules
   per the original spec's section 3.4–3.6 and section 12 folder layout.

## Do not accidentally reverse
- Policy filtering happens at the ChromaDB metadata-filter layer, not via
  prompt instructions to the LLM.
- The no-answer path never calls the LLM at all when nothing clears the
  similarity threshold.
- Chunk IDs are deterministic (`filename::pN::cM`) so ingestion stays
  idempotent — don't switch to random/UUID ids.
