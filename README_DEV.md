# Lode Development Setup

## Prerequisites

- Python 3.8+
- Windows (primary), macOS/Linux (should work but not tested)

## Setup

### 1. Python Backend

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running in Development

### Option 1: Use Launcher (Recommended)

The launcher starts FastAPI and opens a desktop window:

```bash
python app/launcher.py
```

This will:
- Start FastAPI on `http://127.0.0.1:<port>` (default 8000; change in Settings → Server)
- Serve HTML templates directly from FastAPI
- Open pywebview desktop window pointing to FastAPI

### Option 2: Manual Start

**Terminal 1 - FastAPI** (from project root):
```bash
python -c "import uvicorn; from backend.main import app; uvicorn.run(app, host='127.0.0.1', port=8000)"
```

Then open `http://127.0.0.1:8000` in a browser, or run the launcher in a second terminal.

## Project Structure

```
lode/
├── app/
│   └── launcher.py      # Desktop launcher (pywebview)
├── backend/             # FastAPI backend
│   ├── main.py          # FastAPI app entry point
│   ├── db.py            # Database connection and initialization
│   ├── config.py        # Server port and config
│   ├── feature_flags.py # Pro/core feature gating
│   ├── jobs.py          # Job system
│   ├── job_runner.py    # Background job execution (import, reindex, vectordb index)
│   ├── analytics_cache.py
│   ├── routes/          # API route modules (chat, vectordb)
│   ├── chat/            # Chat (RAG, history, storage, context)
│   ├── llm/             # LiteLLM service (OpenAI, Anthropic)
│   └── vectordb/        # Vector DB service and indexer
├── database/            # Database schema creation scripts
├── docs/                # Documentation (API.md, RELEASE_PROCESS.md)
├── templates/           # Jinja2 HTML templates (main, chat, vectordb_search, help, etc.)
├── static/              # CSS, JS, images
├── tests/               # Test suite (run_all_tests.py)
├── tools/               # Build and utility scripts (build_windows_exe.py, etc.)
├── importers/           # OpenAI/Claude import modules
└── requirements.txt
```

## API Endpoints

All endpoints are under `/api/`. Full reference: [docs/API.md](docs/API.md).

- **Health & setup**: `GET /api/health`, `GET /api/setup/check`, `POST /api/setup/initialize`
- **Config**: `GET /api/config/port`, `POST /api/config/port` (server port)
- **Conversations**: `GET /api/conversations`, `GET /api/conversations/{id}`, `GET /api/conversations/{id}/messages`, `GET /api/search`
- **Jobs**: `GET /api/jobs`, `GET /api/jobs/{id}`, `POST /api/jobs/import`, `POST /api/jobs/reindex`, `POST /api/jobs/vectordb-index`, `POST /api/jobs/{id}/cancel`
- **State**: `GET /api/state`, `POST /api/state`
- **Vector DB**: `POST /api/vectordb/search`, `GET /api/vectordb/status` (semantic search; see Help → Vector Search for request schema)
- **Chat**: `GET /api/chat/providers`, `GET /api/chat/settings`, `POST /api/chat/save-settings`, `POST /api/chat/save-history`, `POST /api/chat/completion`, `POST /api/chat/completion-stream`, `POST /api/chat/test-model`

## HTML Routes

- `GET /` - Main entry (redirects to welcome or main)
- `GET /welcome` - Welcome screen (first-time setup)
- `GET /main` - Main application screen
- `GET /import`, `GET /analytics`, `GET /find-tools`, `GET /export`, `GET /settings`, `GET /help`, `GET /about`
- `GET /vectordb-search` - Vector Search (semantic search UI)
- `GET /chat` - Chat (RAG over your data)

## Notes

- Database is created in user data directory when packaged; in dev, database is in project root
- Server port is configurable (Settings → Server); default 8000
- FastAPI binds to `127.0.0.1` only (local-only)
- Uses Jinja2 for server-side rendering and HTMX for dynamic interactions
- Interactive API docs: `/docs` (Swagger), `/redoc`, `/openapi.json`
