# Windows installation and launch

## Prerequisites

- Windows 10/11.
- Python 3.12. The installer selects Python 3.12 explicitly through the Python launcher, or accepts `python` only when it is exactly 3.12. Other versions are rejected because the pinned backend dependency set is verified with Python 3.12.
- Node.js 20.19+ or 22.12+ with npm.
- Ollama from [ollama.com/download](https://ollama.com/download) for local answers.
- Gemma 3 4B (`ollama pull gemma3:4b`); the installer offers this only when the local Ollama API is available and the model is missing.

## Install and run

1. Clone or download this repository.
2. Double-click `Install-FindMyThingy.bat` once. It creates `backend/.venv`, installs the locked frontend packages, creates local storage folders and copies `.env.example` files only when the target files do not exist. It then loads `all-MiniLM-L6-v2`, downloads it into the configured `storage/models/` cache if absent, and generates a verification embedding before reporting success. Model download progress is shown by the installer.
3. Double-click `Start-FindMyThingy.bat` whenever you want to use the app. The launcher selects free local ports (backend from 8080, frontend from 5173), starts and health-checks the backend and frontend, configures the frontend API URL and opens the browser.
4. Double-click `Stop-FindMyThingy.bat` when finished. It stops only recorded processes whose command lines still match this project. Ollama remains running because it may be shared by other local tools.

The first install may take time for Python packages, Node packages, the embedding model and Gemma. The embedding model download uses Hugging Face's resumable cache; if the first download fails or is interrupted, setup reports the problem and can be rerun when internet access is available. Subsequent embeddings load from the local cache and do not fetch model files. The launcher never pulls the Gemma model automatically. If Ollama is installed but not running, it tries `ollama.exe serve` from PATH or the standard per-user install path; otherwise open Ollama normally. The backend health indicator shows whether Gemma is available.

## Ports and logs

The default local addresses are `http://127.0.0.1:8080` (API) and `http://127.0.0.1:5173` (web UI). If either port is occupied, the launcher probes for another port and passes the selected API URL to Vite. It does not terminate processes that occupy those ports. Logs are written to ignored `storage/logs/`.

## Local data and privacy

Uploads, SQLite, ChromaDB and the embedding cache are stored under ignored `storage/`. The existing SQLite filename remains `storage/recall.sqlite3` for compatibility. Root `.env` and `frontend/.env` are local configuration. Do not share these files or the storage directory. Text extraction, embeddings and Gemma inference run locally; installing packages and the first download of the embedding/Gemma models requires internet access.

## Troubleshooting

- **Python or Node missing/unsupported:** install Python 3.12 and Node.js 20.19+ or 22.12+, close and reopen Explorer, then rerun the installer.
- **Embedding model setup failed:** check internet access and available disk space, then rerun `Install-FindMyThingy.bat`. The Hugging Face cache under `storage/models/` retains completed download files so the installer can retry an interrupted first setup.
- **Model unavailable:** open a terminal and run `ollama pull gemma3:4b`; then reopen Ollama.
- **Startup timeout:** inspect `storage/logs/backend-error.log` and `frontend-error.log`.
- **Port is in use:** no unrelated process is stopped; the launcher should choose a nearby free port. If no port can be found, close the conflicting local app and retry.
- **Dependencies changed:** rerun `Install-FindMyThingy.bat`; it uses `npm ci` from the lockfile and pip requirements.
- **Shutdown:** use `Stop-FindMyThingy.bat`; if Windows has already stopped a recorded process, the launcher safely skips that PID.

This is a local launcher for the development application, not a standalone desktop executable or signed installer.
