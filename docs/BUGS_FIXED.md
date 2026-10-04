# Bugs fixed in this finalization pass

## Explicit chat memories did not persist

- **Before:** Memory extraction ran only after document upload. Asking chat to remember a personal fact fell through to document retrieval and could not create a durable personal memory.
- **Root cause:** There was no explicit remember-intent route or standalone persistent memory table.
- **Fix:** Detect common explicit remember/save phrases before retrieval; split straightforward fact lists; save with case-insensitive deduplication in a new `personal_memories` SQLite table; verify the row before confirming and return a clear storage error if persistence fails. List, delete and dashboard count include these records. Personal memory questions search saved facts first.
- **Files:** `backend/app/api/routes.py`, `backend/app/database/sqlite.py`, `backend/app/services/ollama.py`, `backend/app/core/config.py`, `frontend/src/App.tsx`.
- **Evidence:** Unit test covers save/list/deduplicate/delete and memory-first retrieval. Actual Gemma workflow and a real backend restart preserved the fact in isolated storage.

## Weak nearest document passages could be treated as relevant

- **Before:** The API accepted cosine distance up to 0.78 (`1 - distance >= 0.22`), allowing weak results to be passed to the model.
- **Root cause:** A low minimum similarity cutoff did not reject unrelated nearest neighbors; metric assumptions were implicit.
- **Fix:** Read `hnsw:space` from the actual Chroma collection (the existing collection is `cosine`); convert cosine/IP and L2 distances separately; require configurable `RETRIEVAL_MIN_SIMILARITY` (default 0.65); return a clear refusal and no citation when no passage qualifies.
- **Files:** `backend/app/services/vector_store.py`, `backend/app/core/config.py`, `backend/app/api/routes.py`, `.env.example`, `backend/tests/test_api.py`.
- **Evidence:** Metric conversion and weak-neighbor unit tests pass; real Gemma answered from the synthetic Project Aurora note and refused an unrelated capital question without citations.

## Memory Library omitted direct personal memories

- **Before:** The API returned only memories joined to documents, and dashboard counts omitted direct personal facts.
- **Root cause:** Memory records were assumed to always originate from document extraction.
- **Fix:** Merge saved personal facts and document-extracted memories in the API; show persisted facts in the existing library and include them in aggregate counts.
- **Files:** `backend/app/api/routes.py`, `frontend/src/App.tsx`.
- **Evidence:** API tests and live Gemma Memory Library checks passed.

## Chat UI implied answers could come only from documents

- **Before:** The composer/help copy described document search only, hiding explicit memory capture and personal-memory answers.
- **Fix:** Update the Ask page copy and loading state to mention saved facts and documents; update the Memory Library empty state and refresh after deletion.
- **Files:** `frontend/src/App.tsx`.
- **Evidence:** Final TypeScript/Vite production build passed. Browser-based visual checks could not run because the UI bridge was unavailable.

## Windows launch had fixed-port assumptions and incomplete process ownership

- **Before:** Running the app required separate terminals and fixed API/UI ports; the Windows Python venv shim could leave a child Uvicorn process behind.
- **Fix:** Add installer/start/stop batch entry points and PowerShell scripts; choose free ports, set the frontend API and CORS origin consistently, wait for health/HTTP checks, record owned PIDs, recognize the Uvicorn child process, and stop only matching app processes.
- **Files:** `Install-FindMyThingy.bat`, `Start-FindMyThingy.bat`, `Stop-FindMyThingy.bat`, `scripts/windows/*.ps1`, `backend/app/main.py`, `docs/WINDOWS_SETUP.md`, `README.md`.
- **Evidence:** Installer completed; launcher passed normal and occupied-port checks, reused process IDs on duplicate start and stopped its app process tree. Ollama was left running and its automatic startup path was not tested.

## First-time embedding model setup failed on an empty cache

- **Before:** `SentenceTransformer` always used `local_files_only=True`, so the first install could not obtain `all-MiniLM-L6-v2`; the Windows installer only created the model-cache directory and never verified a vector could be generated.
- **Fix:** Attempt local-only model loading first. If the model is not cached, download it into the configured local Hugging Face cache using its resumable cache, with an actionable error if the download is offline or fails. The Windows installer now initializes the model and generates a finite test vector before it reports success. Later operations use the local cache.
- **Documentation:** README and Windows setup docs describe the one-time download, cache location, internet requirement, retry behavior and local subsequent use.
- **Evidence:** A newly created empty isolated cache downloaded the model and produced a 384-dimensional vector. After clearing the in-process model cache, the model loaded again with Hugging Face offline mode. The isolated cache was deleted; the pre-existing user cache was not used for this test.

## Windows Python version selection did not match its requirement text

- **Before:** The installer forced `py -3.12` when the launcher was present, but its fallback accepted any Python 3.12+ interpreter. Documentation claimed 3.12 or newer despite dependencies only being exercised with 3.12.
- **Fix:** Select exactly Python 3.12 through the launcher; without it, accept `python` only if its detected major/minor is exactly 3.12. Update README and Windows prerequisites to state the supported version accurately.
- **Evidence:** The clean-install installer run selected Python 3.12 from the Python launcher and completed setup; PowerShell parser validation passed. See QA_REPORT.md for the run details.

## Paraphrased personal-memory questions missed saved facts

- **Before:** `_memory_hits()` required token overlap, so semantic equivalents such as “Which IDE do I normally use?” could miss “My preferred editor is VS Code.”
- **Fix:** Embed the question and saved memory content with the existing local SentenceTransformer, rank by cosine similarity, and return only results meeting a dedicated `0.4` memory threshold. An empty library avoids model initialization. Document vector search keeps its independent existing threshold. Explicit requests to list/recall memories continue to list recent saved records.
- **Evidence:** Backend tests pass for the VS Code and 18 November deadline paraphrases, a food-preference mismatch refusal, and an empty memory library. Actual Gemma integration also answered the IDE paraphrase with its saved-memory citation and refused an unrelated question.
