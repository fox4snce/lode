# Lode Development Setup

## Prerequisites

- Python 3.8+
- Node.js 18+ and npm
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

### 2. React Frontend

```bash
cd frontend
npm install
```

## Running in Development

### Option 1: Use Launcher (Recommended)

The launcher starts both FastAPI and Vite dev server:

```bash
python app/launcher.py
```

This will:
- Start FastAPI on a random free port (e.g., `127.0.0.1:8000`)
- Start Vite dev server on `localhost:5173`
- Open pywebview window pointing to Vite dev server
- Vite proxy forwards `/api/*` to FastAPI

### Option 2: Manual Start

**Terminal 1 - FastAPI:**
```bash
cd backend
python main.py
```

**Terminal 2 - Vite:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - pywebview (optional, for desktop window):**
```bash
python app/launcher.py
```

Or just open `http://localhost:5173` in a browser.

## Project Structure

```
gptParse/
├── backend/
│   ├── main.py          # FastAPI app
│   ├── db.py            # Database helpers
│   └── jobs.py          # Job system
├── frontend/
│   ├── src/
│   │   ├── screens/     # Screen components
│   │   ├── components/  # Reusable components
│   │   ├── api.ts       # API client
│   │   └── App.tsx      # Main app
│   └── package.json
├── app/
│   └── launcher.py      # Desktop launcher
└── requirements.txt
```

## API Endpoints

All endpoints are under `/api/`:

- `GET /api/health` - Health check
- `GET /api/setup/check` - Check if DB initialized
- `POST /api/setup/initialize` - Initialize database
- `GET /api/conversations` - List conversations
- `GET /api/conversations/{id}` - Get conversation
- `GET /api/conversations/{id}/messages` - Get messages (with windowing)
- `GET /api/search` - Full-text search
- `GET /api/jobs` - List jobs
- `GET /api/jobs/{id}` - Get job status
- `POST /api/jobs/import` - Start import job
- `POST /api/jobs/reindex` - Start reindex job
- `POST /api/jobs/{id}/cancel` - Cancel job
- `GET /api/state` - Get app state
- `POST /api/state` - Save app state

## Building for Production

```bash
# Build React app
cd frontend
npm run build

# Package with PyInstaller (see docs/packaging_notes.md)
pyinstaller Lode.spec
```

## Notes

- Database is created in user data directory when packaged
- In dev, database is in project root
- FastAPI binds to `127.0.0.1` only (local-only)
- Port is chosen at runtime (free port finder)

