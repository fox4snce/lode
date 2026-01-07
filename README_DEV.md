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
- Start FastAPI on `http://127.0.0.1:8000`
- Serve HTML templates directly from FastAPI
- Open pywebview desktop window pointing to FastAPI

### Option 2: Manual Start

**Terminal 1 - FastAPI:**
```bash
cd backend
python main.py
```

Then open `http://127.0.0.1:8000` in a browser, or run:
```bash
python app/launcher.py
```

## Project Structure

```
gptParse/
├── backend/
│   ├── main.py          # FastAPI app
│   ├── db.py            # Database helpers
│   └── jobs.py          # Job system
├── templates/           # Jinja2 HTML templates
│   ├── base.html
│   ├── main.html
│   └── fragments/      # HTMX fragments
├── static/              # Static files (CSS/JS)
│   ├── css/
│   └── js/
├── app/
│   └── launcher.py      # Desktop launcher
└── requirements.txt
```

## API Endpoints

All endpoints are under `/api/`:

- `GET /api/health` - Health check
- `GET /api/setup/check` - Check if DB initialized
- `POST /api/setup/initialize` - Initialize database
- `GET /api/conversations` - List conversations (returns HTML fragment if HTMX request)
- `GET /api/conversations/{id}` - Get conversation (returns HTML fragment if HTMX request)
- `GET /api/conversations/{id}/messages` - Get messages (returns HTML fragment if HTMX request)
- `GET /api/search` - Full-text search
- `GET /api/jobs` - List jobs
- `GET /api/jobs/{id}` - Get job status
- `POST /api/jobs/import` - Start import job
- `POST /api/jobs/reindex` - Start reindex job
- `POST /api/jobs/{id}/cancel` - Cancel job
- `GET /api/state` - Get app state
- `POST /api/state` - Save app state

## HTML Routes

- `GET /` - Main entry (redirects to welcome or main)
- `GET /welcome` - Welcome screen (first-time setup)
- `GET /main` - Main application screen

## Notes

- Database is created in user data directory when packaged
- In dev, database is in project root
- FastAPI binds to `127.0.0.1` only (local-only)
- Uses Jinja2 for server-side rendering
- Uses HTMX for dynamic interactions (no JavaScript framework needed)
