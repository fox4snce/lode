# Run Instructions for ChatVault

## Quick Start (Development)

### 1. Install Dependencies

**Python:**
```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # macOS/Linux

# Install Python dependencies
pip install -r requirements.txt
```

**Node.js:**
```bash
cd frontend
npm install
cd ..
```

### 2. Run the Application

**Option A: Use Launcher (Recommended)**
```bash
python app/launcher.py
```

This will:
- Start FastAPI backend on `http://127.0.0.1:8000`
- Start Vite dev server on `http://localhost:5173`
- Open pywebview desktop window pointing to Vite dev server
- Vite proxies `/api/*` requests to FastAPI

**Option B: Manual Start (for debugging)**

Terminal 1 - FastAPI:
```bash
cd backend
python main.py
```

Terminal 2 - Vite:
```bash
cd frontend
npm run dev
```

Then open `http://localhost:5173` in a browser, or run:
```bash
python app/launcher.py
```
(It will detect Vite is already running)

### 3. First Run Flow

1. **Welcome Screen**: If database not initialized, click "Initialize Database"
2. **Import Screen**: After initialization, import your first conversations
   - Select source type (OpenAI or Claude)
   - Browse for JSON export file
   - Choose options (calculate stats, build index)
   - Click "Import" (creates a job)
3. **Main Shell**: View conversations, search, organize

## Troubleshooting

### Port Already in Use
If port 8000 or 5173 is in use:
- FastAPI: Edit `app/launcher.py` to use a different port
- Vite: Edit `frontend/vite.config.ts` to use a different port
- Update Vite proxy target if FastAPI port changes

### Module Not Found Errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` again
- Check that `backend/` and `app/` are in Python path

### Frontend Build Errors
- Ensure Node.js 18+ is installed
- Run `cd frontend && npm install` again
- Check `frontend/package.json` for correct dependencies

### Database Errors
- Database is created in project root in dev mode
- Check file permissions
- Ensure all table creation scripts are in project root

## Production Build

See `docs/packaging_notes.md` for Windows executable packaging instructions.

