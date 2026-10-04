# QA report

Updated: 2026-10-05. This report records only checks actually run in the local Windows environment.

## Test environment and safety

- Windows PowerShell; Python 3.12; Node.js 24.21; npm 11.19; Vite 8.3.2.
- Ollama's local API reported `gemma3:4b` ready.
- The existing Chroma collection's metric was read-only inspected as `cosine`. No local library contents or user vectors were included in this report; no user documents, SQLite records or vectors were deleted or rewritten in this QA pass.
- Automated API tests used pytest temporary SQLite directories and a fake empty collection. Live-model checks used dedicated ignored paths under `storage/.qa-launcher` and `storage/.qa-port-retest`, synthetic files only, and deleted the synthetic records before shutdown.
- Test logs and temporary integration databases are removed at final cleanup. Real `storage/`, `.env` files, `backend/.venv`, `frontend/node_modules` and `frontend/dist` are preserved.

## Automated checks

- Backend: `python -m pytest -q -p no:cacheprovider --basetemp=C:\Find-My-Thingy\storage\.pytest-run-final4` from `backend` — **18 passed, 6 dependency deprecation warnings, 16.88s**.
- Frontend: `npm.cmd run build` from `frontend` — **passed**; TypeScript build succeeded, Vite transformed 1,904 modules and emitted the production bundle.
- Windows scripts: PowerShell parser accepted `install.ps1`, `start.ps1` and `stop.ps1` — **syntax OK**.
- Windows installer: executed successfully. Python requirements were already satisfied; `npm ci` added 47 packages, audited 48 and reported 0 vulnerabilities. It preserved existing `.env` files and did not pull a model.
- Initial pytest invocation using the default per-user temp path failed before executing tests because Windows denied access to that temp directory. Rerunning with the project-local isolated `--basetemp` passed.

## API and memory tests

The 18 automated cases cover PDF page extraction; PDF/Markdown/TXT upload; duplicate upload; invalid type and empty document rejection; size limit; upload rollback; document listing/detail/deletion; missing-resource and chat validation errors; dashboard counts; memory list, delete, deduplicate, multi-fact save, storage-failure messaging and retrieval before document search; cosine/L2/IP distance conversion; weak-match refusal; model refusal normalization; Ollama failure response; and localhost CORS.

## Live Gemma and persistence workflow

Against the isolated local app and actual `gemma3:4b`:

1. Health returned backend, SQLite, ChromaDB, Ollama and Gemma as ready.
2. Synthetic Project Aurora Markdown and algorithm study PDF uploads both indexed successfully.
3. “What is the deadline for Project Aurora?” returned “18 November 2026” and cited `test-project-notes.md`.
4. “What is the capital of Iceland?” returned the insufficient-information refusal with no citation.
5. “Remember that my demo project codename is Test Nebula.” persisted and confirmed the fact; it appeared in Memory Library.
6. “What is my demo project codename?” returned Test Nebula with a saved-memory citation, before document retrieval.
7. The memory and both synthetic documents were deleted and verified absent.
8. A separate synthetic memory survived a launcher-managed backend stop/start using the same isolated data directory, then was deleted.

## Windows launcher checks

- `Start-FindMyThingy.bat` / `Stop-FindMyThingy.bat` wrappers started and stopped the app on ports 8080/5173; API health and frontend HTTP checks passed and the browser URL opened.
- With ports 8080 and 5173 deliberately reserved, the launcher selected 8081 and 5174. The selected `127.0.0.1:5174` CORS preflight succeeded.
- A second launch reused the existing listener processes instead of starting duplicates.
- `Stop-FindMyThingy.bat`'s script stopped the recorded Vite and Uvicorn process tree and removed its launcher state. Ollama was left running.
- The installer, startup, port fallback, duplicate startup and shutdown were exercised. Auto-starting Ollama while its service is stopped was not exercised because the user's already-running Ollama service was left intact.

## Frontend and visual checks

- Production bundling and TypeScript compilation pass.
- The app's SPA routes (`/`, `/documents`, `/ask`, `/memories`, `/settings`) had returned HTTP 200 in the earlier finalization pass.
- The computer-use/browser bridge returned `Transport closed` during this pass, so I could not execute browser clicks or inspect screenshots at 1440×900, 1280×720, 768×1024 or 390×844. Visual responsiveness, keyboard navigation and upload interaction in a real browser remain **unverified**.
- No screenshots or demo recording were fabricated. Capture views listed in `docs/screenshots/README.md` from the running app before sharing.

## Remaining limitations

- Browser interaction and visual responsive review still need a working browser-control environment and human screenshot review.
- The actual Gemma workflow verified one grounded Markdown answer and an unrelated-question refusal; comprehensive multi-chunk answer quality and all question phrasings were not exhaustively measured.
- Upload/indexing runs synchronously. Scanned PDFs have no OCR.
- Optional memories extracted from uploaded documents remain best effort. Explicit “remember” facts are persisted separately and confirmed only after database verification.
- The app is a local development web app with a Windows launcher, not a packaged executable or signed installer.
- `ollama.exe` is present in the standard per-user install location on this machine but was not on PATH. The scripts now check that location. Auto-start with Ollama actually stopped remains unverified.

## Targeted source-audit correction pass — 2026-10-05

- Final backend regression suite: `python -m pytest -q -p no:cacheprovider --basetemp=..\storage\.pytest-targeted-final` from `backend` — **21 passed, 6 dependency/deprecation warnings, 73.61s**. New cases cover the VS Code IDE paraphrase, the 18 November deadline paraphrase, unrelated-question refusal, an empty memory library without model loading, and a clear response when memory embeddings are unavailable.
- Frontend: `npm.cmd run build` — **passed**; TypeScript and Vite transformed 1,904 modules and emitted the production bundle.
- Windows PowerShell parser: `install.ps1`, `start.ps1`, and `stop.ps1` — **syntax OK**.
- Empty-cache embedding test used a brand-new generated directory under ignored `storage/`, verified it was empty before model initialization, downloaded `all-MiniLM-L6-v2`, and generated a 384-dimensional vector. The model cache was cleared in-process and loaded again with `HF_HUB_OFFLINE=1` — **passed**. The generated cache directory was removed afterward; the existing model cache was not used as evidence for first-time setup.
- Actual Gemma 3 4B integration through FastAPI TestClient with isolated SQLite, ChromaDB, uploads and synthetic Project Starling Markdown — **passed**. Gemma answered the deadline question with the `qa-project.md` citation; answered the paraphrased “Which IDE do I normally use?” question with the saved VS Code fact citation; refused the unrelated Iceland-capital question with no sources; synthetic document and memory deletion succeeded.
- Clean Windows installer: a source-only project copy under ignored `.install-check/clean-win-targeted` started without `.env`, database, uploads, venv, or npm dependencies. The installer selected Python 3.12, installed backend dependencies into a new virtual environment, `npm ci` added 47 packages and reported 0 vulnerabilities, loaded the copied local model cache, generated a finite verification vector, and reported setup ready — **passed**. The first run exposed an argument-quoting issue in the new Python verification command; the installer was corrected to pass a here-string on stdin and rerun successfully.
- Windows launcher from that clean install: startup reported ready and the backend health check showed SQLite, ChromaDB, Ollama and Gemma healthy. The frontend returned HTTP 200 on retry (one immediate follow-up request timed out once); duplicate start reused both process IDs; stop removed launcher state and closed its ports — **passed**. With ports 8080/5173 reserved, it selected 8081/5174, backend and Gemma health passed, frontend returned HTTP 200 and CORS preflight passed; stop closed both fallback ports — **passed**.
- All disposable project copies, isolated data and copied test caches were removed afterward. The real application storage and original embedding cache were preserved.
- Browser automation remains **unverified**. The CUA browser bridge returned `Transport closed`; no browser screenshots, responsive inspection or click-through checks were performed.
