# Run Instructions for Lode

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

### 2. Run the Application

**Option A: Use Launcher (Recommended)**
```bash
python app/launcher.py
```

This will:
- Start FastAPI backend on `http://127.0.0.1:8000`
- Serve HTML templates directly from FastAPI
- Open pywebview desktop window pointing to FastAPI

**Option B: Manual Start (for debugging)**

Terminal 1 - FastAPI:
```bash
cd backend
python main.py
```

Then open `http://127.0.0.1:8000` in a browser, or run:
```bash
python app/launcher.py
```

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
If port 8000 is in use:
- FastAPI: Edit `app/launcher.py` to use a different port

### Module Not Found Errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` again
- Check that `backend/` and `app/` are in Python path

### Database Errors
- Database is created in project root in dev mode
- Check file permissions
- Ensure all table creation scripts are in project root

## Production Build

See `docs/packaging_notes.md` for Windows executable packaging instructions.
