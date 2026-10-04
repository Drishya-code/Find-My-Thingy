# Windows installation and launch

## Prerequisites

- Windows 10/11.
- Python 3.12 or newer and the Python launcher (`py`).
- Node.js 20.19+ or 22.12+ with npm.
- Ollama from [ollama.com/download](https://ollama.com/download) for local answers.
- Gemma 3 4B (`ollama pull gemma3:4b`); the installer offers this only when the local Ollama API is available and the model is missing.

## Install and run

1. Clone or download this repository.
2. Double-click `Install-FindMyThingy.bat` once. It creates `backend/.venv`, installs the locked frontend packages, creates local storage folders and copies `.env.example` files only when the target files do not exist.
3. Double-click `Start-FindMyThingy.bat` whenever you want to use the app. The launcher selects free local ports (backend from 8080, frontend from 5173), starts and health-checks the backend and frontend, configures the frontend API URL and opens the browser.
4. Double-click `Stop-FindMyThingy.bat` when finished. It stops only recorded processes whose command lines still match this project. Ollama remains running because it may be shared by other local tools.

The first install may take time for Python packages, Node packages, the embedding model and Gemma. The launcher never pulls a model automatically. If Ollama is installed but not running, it tries `ollama.exe serve` from PATH or the standard per-user install path; otherwise open Ollama normally. The backend health indicator shows whether Gemma is available.

## Ports and logs

The default local addresses are `http://127.0.0.1:8080` (API) and `http://127.0.0.1:5173` (web UI). If either port is occupied, the launcher probes for another port and passes the selected API URL to Vite. It does not terminate processes that occupy those ports. Logs are written to ignored `storage/logs/`.

## Local data and privacy

Uploads, SQLite, ChromaDB and the embedding cache are stored under ignored `storage/`. The existing SQLite filename remains `storage/recall.sqlite3` for compatibility. Root `.env` and `frontend/.env` are local configuration. Do not share these files or the storage directory. Text extraction, embeddings and Gemma inference run locally; installing packages or downloading models requires internet access.

## Troubleshooting

- **Python or Node missing:** install the prerequisites above, close and reopen Explorer, then rerun the installer.
- **Model unavailable:** open a terminal and run `ollama pull gemma3:4b`; then reopen Ollama.
- **Startup timeout:** inspect `storage/logs/backend-error.log` and `frontend-error.log`.
- **Port is in use:** no unrelated process is stopped; the launcher should choose a nearby free port. If no port can be found, close the conflicting local app and retry.
- **Dependencies changed:** rerun `Install-FindMyThingy.bat`; it uses `npm ci` from the lockfile and pip requirements.
- **Shutdown:** use `Stop-FindMyThingy.bat`; if Windows has already stopped a recorded process, the launcher safely skips that PID.

This is a local launcher for the development application, not a standalone desktop executable or signed installer.
