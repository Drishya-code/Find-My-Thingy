# Find My Thingy project status

Updated: 2026-10-04

## Phase 0 — Environment inspection

- Node.js 24.21.0 and npm 11.19.0 found.
- Python 3.12.14 is available from the Codex bundled runtime; Python is not on the shell PATH.
- Ollama API at `http://localhost:11434` returned `gemma3:4b` in its model list.
- Python urllib sent an actual prompt to Gemma and received the requested test sentinel.
- Project is tracked on the existing main branch; the existing origin remote is left unchanged.

## Implemented

- FastAPI backend, health, document, chat, memory and dashboard endpoints.
- SQLite metadata/activity/memory storage, persistent ChromaDB, local embeddings, PDF/text extraction and chunking services.
- Local Ollama chat integration with source metadata constructed outside the model.
- React/Vite UI for dashboard, documents, Ask Find My Thingy, memory library and local settings. Account/profile/plan UI has been removed.
- Drag/drop and picker upload with transfer progress, duplicate detection, filtering, document deletion and memory deletion.
- Structured Gemma memory extraction with source document/page references.
- `.env.example`, frontend API environment example, private-data ignores and setup/architecture documentation.
- Synthetic demo document, recording plan, screenshot checklist and local DEV submission draft with personal-story placeholders.

## Validation

- `GET /api/health`: backend, SQLite, ChromaDB, Ollama and `gemma3:4b` all reported healthy.
- Backend pytest suite: 10 passed (including upload size, indexing rollback, refusal and CORS cases).
- `npm.cmd ci` in frontend: passed (48 packages audited, 0 vulnerabilities) after stopping only the project Vite previews that held native Windows modules.
- `npm.cmd run build` in frontend after the clean install: passed (Vite 8.3.2; 1,904 modules transformed).
- Direct frontend dependencies are pinned to exact versions resolved in the lockfile; backend requirements are version-pinned.
- Live local API health: backend, SQLite, ChromaDB, Ollama and Gemma 3 4B all reported ready.
- Live Gemma walkthrough with synthetic demo note: upload/index succeeded (1 chunk); question about binary search returned a grounded answer with one source named `demo-sample.md`; an unrelated capital question was refused; memory extraction returned one entry.
- The temporary integration document was deleted; final live dashboard returned to 0 documents, 0 memories and 0 chunks.
- UI route checks for /, /documents, /ask, /memories and /settings returned HTTP 200 from the running Vite SPA.
- Isolated restart check with its own disposable DATA_DIR: uploaded document and Chroma vector remained available after backend stop/start, and the post-restart grounded answer still cited demo-sample.md. The isolated data was deleted after the check.
- Source scan found no account, profile, workspace, plan, subscription, sign-in or avatar terms in the frontend.

## Known limitations

- Scanned PDFs are not OCR processed.
- Upload processing is synchronous. The browser shows file transfer progress, then waits for local indexing and optional memory extraction to finish.
- The model can decline a question despite useful evidence; the answer is still grounded and citations remain tied to retrieved chunks.
- No authentication or multi-user mode is included; Find My Thingy is intended for a trusted local device.
- Visual browser/mobile inspection could not be completed because the desktop browser-control bridge failed to initialize. Mobile CSS was adjusted so every navigation icon remains available at narrow widths; capture and review the listed screenshots before publishing.
- The isolated restart sample produced no memory entry on that run (memory extraction is best effort). A separate live Gemma upload extracted one memory, and automated tests cover memory deletion.
- `python -m pip check`: no broken requirements found.

## Follow-up memory and Windows launch work — 2026-10-04

- Added explicit “remember that…”, “don't forget…” and save-for-later intent handling before document retrieval. Personal facts are stored in a separate case-insensitive-deduplicated `personal_memories` SQLite table in the existing `recall.sqlite3`, are verified before confirmation, appear in Memory Library/dashboard counts and persist across backend restarts.
- Chat now searches personal and document-extracted memories before document chunks. Retrieval relevance conversion uses the existing Chroma `recall_chunks` collection's verified `cosine` metric; minimum relevance defaults to 0.65 and is configurable through `RETRIEVAL_MIN_SIMILARITY`. Weak hits now produce a refusal without unrelated sources.
- Added synthetic TXT/Markdown/PDF/large-PDF fixtures, Windows install/start/stop scripts, Windows setup instructions, QA report and bug-fix log. Root `storage/` is now ignored wholesale; local user databases, Chroma vectors, uploads, models and launcher logs remain local.
- Final backend suite: **18 passed** (6 dependency deprecation warnings; 16.88 seconds). Frontend production build passed (TypeScript; Vite transformed 1,904 modules). `pip check` reported no broken requirements. PowerShell scripts parsed successfully.
- The Windows installer ran successfully: Python dependencies were already satisfied; npm installed 47 packages, audited 48 and reported 0 vulnerabilities. The local Gemma model was detected through Ollama's API.
- Actual isolated Gemma QA: synthetic Markdown/PDF ingestion; Project Aurora deadline answered with the correct filename citation; unrelated capital question refused without a source; explicit memory saved/listed/retrieved/deleted; synthetic docs deleted. A separate saved fact survived a launcher-managed backend restart.
- Windows launcher QA: actual batch wrapper startup/shutdown on 8080/5173; occupied-port fallback to 8081/5174; selected-origin CORS; duplicate invocation reused existing processes; stop terminated the app's backend process tree and frontend.
- Browser bridge returned `Transport closed`, so interactive browser E2E, screenshots and visual checks at the requested desktop/tablet/mobile sizes remain unverified. Ollama was already running; auto-start with its service stopped remains unverified. See [docs/QA_REPORT.md](docs/QA_REPORT.md).
- No changes were committed, pushed, published or made public. Local user data and all prior uncommitted project changes were preserved.

## Test record

- Automated tests use mocks for embeddings and Ollama where appropriate; they do not replace real-model checks.
- Real local Gemma and the full retrieval workflow were exercised against a synthetic Markdown sample in this finalization pass. Automated tests use mocks where appropriate and do not replace real-model checks.
