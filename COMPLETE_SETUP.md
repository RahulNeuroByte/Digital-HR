# Digital HR — Complete Setup Guide (Windows)

This guide assumes you have never seen this project before and are
setting it up on a Windows machine.

## 1. Prerequisites

- **Windows 10/11**
- **Python 3.11** — [python.org/downloads](https://www.python.org/downloads/).
  During install, check "Add python.exe to PATH."
- **Git** (optional, only if you're cloning instead of copying the folder).
- Internet access (needed once, to download the embedding model and any
  pip packages).

## 2. Verify Python 3.11

Open **PowerShell** and run:
```powershell
py -3.11 --version
```
You should see `Python 3.11.x`. If this fails, reinstall Python 3.11 and
make sure "Add to PATH" was checked.

## 3. Create the virtual environment

From the project root (`Digital-HR/`):
```powershell
py -3.11 -m venv .venv
```

## 4. Activate it

```powershell
.\.venv\Scripts\Activate.ps1
```
If PowerShell blocks script execution:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```
If activation still won't work, you can always call the venv's Python
directly without activating:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 5. Install dependencies

```powershell
pip install -r requirements.txt
```
The first run will download the `all-MiniLM-L6-v2` embedding model
(a few hundred MB) — this requires internet access and only happens once
(it's cached locally after that).

### OCR dependencies (only needed if any policy PDF is a scanned image)
- Install **Tesseract OCR for Windows**:
  [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
  — during install, note the install path (e.g. `C:\Program Files\Tesseract-OCR`)
  and add it to your PATH.
- `ocrmypdf` is already in `requirements.txt`, but it also needs
  Ghostscript on Windows: [ghostscript.com/releases](https://www.ghostscript.com/releases/gsdnld.html).
- If you never plan to ingest scanned PDFs, you can skip this — the app
  degrades gracefully (empty text for that page + a warning in the log)
  rather than crashing.

## 6. Environment file setup

```powershell
copy .env.example .env
```
Open `.env` in a text editor and fill in the values described below.

## 7. Gemini API configuration

1. Get an API key from [Google AI Studio](https://aistudio.google.com/apikey).
2. In `.env`, set:
   ```
   GEMINI_API_KEY=your-key-here
   GEMINI_MODEL=gemini-2.0-flash
   ```
3. This is optional for testing — without a key, the app shows the top
   matching policy passages directly instead of an LLM-generated answer,
   so you can validate retrieval/routing without any cost.

## 8. Supabase project creation

**Not required for this POC build** (see README.md "Scope note"). If you
later want to add authentication and multi-user history:
1. Create a project at [supabase.com](https://supabase.com).
2. Copy the project URL and anon key into `.env` as `SUPABASE_URL` /
   `SUPABASE_ANON_KEY` (add these variables when you build that phase).
3. Follow section 3.4–3.6 and section 11 of
   `Digital_HR_Claude_Manus_Prompt.docx` for the schema and RLS design.

## 9. Supabase database SQL / RLS / Google OAuth / Phone OTP / TOTP

**Not required for this POC build.** These are documented as the "Future
improvements" phase in README.md and specified in full in
`Digital_HR_Claude_Manus_Prompt.docx` for whoever picks that phase up.

## 10. Add your policy PDFs

Place every HR policy PDF into the `docs/` folder. One is already there:
`Performance Improvement Plan (PIP) Policy.pdf`. Add the remaining 15 the
same way — no code changes needed, just drop the files in.

The policy name shown to users is derived from the filename (underscores/
hyphens become spaces), so name files clearly, e.g.
`Notice_Period_Policy.pdf` → shown as "Notice Period Policy".

## 11. Run ingestion

```powershell
python scripts\ingest_policies.py
```
You should see a summary like:
```
Ingestion complete. Indexed policies:
  - Performance Improvement Plan (PIP) Policy: 10 chunks
  ...
Total policies indexed: N
```

## 12. Rebuild the index (if needed)

If you change chunking/embedding settings and want a clean rebuild:
```powershell
python scripts\rebuild_index.py
```

## 13. Run Streamlit

```powershell
streamlit run app.py
```
This opens the app at `http://localhost:8501` in your browser.

## 14. Run tests

```powershell
pytest -v
```
All 12 tests (policy routing, chunking, cleaning) should pass without
needing a network connection or Gemini key.

## 15. Common Windows errors and fixes

| Error | Fix |
|---|---|
| `'py' is not recognized` | Reinstall Python 3.11 with "Add to PATH" checked. |
| PowerShell won't run `Activate.ps1` | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, or call `.\.venv\Scripts\python.exe` directly instead of activating. |
| `ModuleNotFoundError` for a package | Confirm the venv is activated (prompt should show `(.venv)`), then re-run `pip install -r requirements.txt`. |
| Embedding model download fails / times out | Check your internet connection and any corporate firewall/proxy blocking huggingface.co; retry — it's cached after the first successful download. |
| `ocrmypdf`/Tesseract errors | Only relevant if you have scanned PDFs — see step 5's OCR section. Otherwise safe to ignore (that page's text will just be empty). |
| Streamlit opens but shows "No policies indexed yet" | Run `python scripts\ingest_policies.py` before starting Streamlit. |

## 16. How to verify the full system end-to-end

1. `python scripts\health_check.py` — confirms config, vector store
   connectivity, indexed policy count, and (if configured) a live Gemini
   ping.
2. `streamlit run app.py`.
3. Ask a question naming a specific policy (e.g. "What is the PIP
   process?") — confirm the sidebar/caption shows the detected policy and
   the answer only cites that policy's pages.
4. Ask a question without naming a policy — confirm it searches across
   all indexed policies.
5. Ask an unrelated/unanswerable question — confirm you get the safe
   "couldn't find sufficient information" message, not a guess.
6. `pytest -v` — confirm all tests pass.

This build intentionally does not include login, so steps involving
authentication, profile updates, or user-isolation from the original
spec's acceptance test are not applicable — see README.md "Future
improvements" for what's needed to add them back.
