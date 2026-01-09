# Technical Documentation

This document contains technical details about embeddings, encryption, packaging, architecture, and recent changes.

---

## Project Structure

### Directory Organization

The project is organized into the following directories:

- **`backend/`**: FastAPI backend application
  - `main.py`: FastAPI app entry point and route definitions
  - `db.py`: Database connection and initialization helpers
  - `jobs.py`: Job system for async operations
  - `job_runner.py`: Background job execution (import, reindex)
  - `analytics_cache.py`: Server-side analytics caching
  - `routes/`: API route modules (conversations, jobs, messages)

- **`database/`**: Database schema creation scripts
  - All `create_*.py` files that define and create database tables
  - These are imported dynamically by `backend/db.py` during initialization

- **`tests/`**: Test files
  - All `test_*.py` files for unit and integration tests
  - `run_all_tests.py`: Test runner script
  - Tests import database creation scripts from `database/` directory

- **`templates/`**: Jinja2 HTML templates
  - `base.html`: Base template with menu bar
  - `main.html`: Main conversation viewer
  - `help.html`: Help documentation page
  - `about.html`: About page with author info
  - `fragments/`: HTMX partial templates

- **`static/`**: Static assets
  - `css/`: Stylesheets
  - `js/`: JavaScript files
  - `img/`: Images (e.g., `bitbrain.jpg`)

- **`docs/`**: Documentation
  - `images/`: Application icons
    - `lode.ico`: Window/titlebar icon
    - `master.png`: Windows taskbar icon (converted to .ico at runtime)
    - `lode.png`: Additional icon asset

- **`app/`**: Desktop application launcher
  - `launcher.py`: pywebview desktop launcher with icon handling

### Import Paths

When importing database creation scripts, add the `database/` directory to `sys.path`:

```python
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
database_dir = project_root / "database"
if str(database_dir) not in sys.path:
    sys.path.insert(0, str(database_dir))

from create_metadata_tables import create_metadata_tables
```

---

## Recent Important Changes

### Window Icons (January 2026)

- **Window Icon**: Uses `docs/images/lode.ico` for the application window titlebar
- **Taskbar Icon**: Uses `docs/images/master.png` (converted to .ico at runtime) for Windows taskbar
- **Implementation**: Icons are set via Win32 APIs after window creation (pywebview 6.x doesn't support `icon=` parameter)
- **Location**: `app/launcher.py` - `_set_windows_taskbar_icon_from_master_png()` function

### Analytics Caching (January 2026)

- **Server-Side Caching**: Analytics data is now cached in the `analytics_cache` table
- **Refresh Endpoint**: `POST /api/analytics/refresh` triggers full recalculation
- **Cache Keys**: Versioned (e.g., `top_words_v3`) to invalidate old cached data
- **Benefits**: Analytics only recalculate on demand, not on every tab click
- **Location**: `backend/analytics_cache.py`, `create_analytics_cache_tables.py`

### Search Improvements (January 2026)

- **FTS5 RowID Fix**: Fixed mismatch between FTS5 `rowid` and message/conversation `id` columns
- **Full Conversation Loading**: Conversations now load all messages (limit=50,000) when opened from search
- **Search Highlighting**: Search terms are highlighted in loaded conversations
- **Location**: `create_fts5_tables.py`, `templates/main.html`, `backend/main.py`

### Import System Improvements (January 2026)

- **File Upload Endpoint**: Added `POST /api/jobs/import-upload` for reliable file uploads
- **Path Resolution**: Backend resolves relative paths (project root, `data/`, `data/example_corpus/`)
- **Import Verification**: Pre/post import conversation count checks to verify actual import
- **Better Error Messages**: More descriptive errors for file not found and import failures
- **Location**: `backend/job_runner.py`, `templates/import.html`, `backend/main.py`

### Help and About Pages (January 2026)

- **Help Page**: Comprehensive help documentation with sidebar navigation
- **About Page**: Author bio, support email, Ko-fi link, and profile image
- **Styling**: Improved layout and organization
- **Location**: `templates/help.html`, `templates/about.html`, `static/css/main.css`

### Text Selection (January 2026)

- **Enabled**: Text selection and copy-paste enabled throughout the application
- **Implementation**: `text_select=True` in `webview.create_window()`
- **Location**: `app/launcher.py`

### Analytics Word Counting (January 2026)

- **Words Column**: Fixed empty "Words" column in Analytics -> Usage tab
- **Contraction Handling**: Fixed tokenization to keep contractions intact (e.g., "don't" not split to "don")
- **Stopword Filtering**: Uses `docs/words.md` to filter boring words from top words analytics
- **Contraction Filtering**: Common contractions (don't, won't, isn't, etc.) filtered from top words
- **Location**: `analytics.py`

### Wipe Imported Files (January 2026)

- **Database Deletion**: "Wipe Imported Files" now also deletes database entries (conversations, messages, tags, stats, hashes, import reports)
- **Parameter**: `wipe_database=True` by default
- **Location**: `wipe_imported_files.py`, `backend/main.py`, `templates/settings.html`

---

## Embeddings

### Overview

Embeddings are vector representations of text that measure relatedness. They're commonly used for:
- **Search** (where results are ranked by relevance to a query string)
- **Clustering** (where text strings are grouped by similarity)
- **Recommendations** (where items with related text strings are recommended)
- **Anomaly detection** (where outliers with little relatedness are identified)
- **Diversity measurement** (where similarity distributions are analyzed)
- **Classification** (where text strings are classified by their most similar label)

An embedding is a vector (list) of floating point numbers. The distance between two vectors measures their relatedness. Small distances suggest high relatedness and large distances suggest low relatedness.

### Implementation

The project uses:
- **Local embeddings**: ONNX models (e.g., `sentence-transformers/all-MiniLM-L6-v2`)
- **Vector database**: storyvectordb for storing and querying embeddings
- **Embedding generation**: `embeddings_onnx.py` for generating embeddings locally

### Usage

Embeddings are generated for conversations and messages to enable semantic search. The system can:
- Generate embeddings for new content
- Store embeddings in the vector database
- Query similar content using vector similarity

### Models

Currently using `sentence-transformers/all-MiniLM-L6-v2`:
- 384-dimensional vectors
- Fast inference with ONNX
- Good quality for semantic search

---

## Database Encryption

### Option 1: SQLCipher (Recommended)

SQLCipher provides transparent encryption for SQLite databases using AES-256.

#### Installation

**Windows:**
```bash
pip install pysqlcipher3
```

**macOS/Linux:**
```bash
# Install SQLCipher library first
# macOS: brew install sqlcipher
# Ubuntu: sudo apt-get install libsqlcipher-dev

pip install pysqlcipher3
```

#### Usage

**Create Encrypted Database:**
```python
from pysqlcipher3 import dbapi2 as sqlite3

conn = sqlite3.connect('conversations_encrypted.db')
conn.execute("PRAGMA key='your-secret-key-here'")
# Now use database normally
```

**Migrate Existing Database:**
```python
import sqlite3
from pysqlcipher3 import dbapi2 as sqlcipher

# Read from unencrypted database
plain_conn = sqlite3.connect('conversations.db')
plain_conn.backup(sqlcipher.connect('conversations_encrypted.db'))
plain_conn.close()

# Set encryption key
encrypted_conn = sqlcipher.connect('conversations_encrypted.db')
encrypted_conn.execute("PRAGMA key='your-secret-key-here'")
```

#### Security Notes

- Use a strong, unique key for each database
- Store the key securely (environment variable, keychain, etc.)
- Never commit encryption keys to version control
- Consider key rotation for long-term security

### Option 2: File-Level Encryption

For additional security, you can encrypt the entire database file using:
- **Windows**: BitLocker or EFS (Encrypting File System)
- **macOS**: FileVault
- **Linux**: LUKS or eCryptfs

This provides encryption at the filesystem level, independent of the application.

### Current Status

Encryption is **documented but not required** for MVP. The system works with standard SQLite databases. Encryption can be added later if needed.

---

## Packaging

### Windows Executable

The application can be packaged as a standalone Windows executable using PyInstaller.

#### Build Process

1. **Build Frontend** (if using React/Vite):
   ```bash
   cd frontend
   npm install
   npm run build
   ```
   This creates `frontend/dist/` with the production build.

2. **Package with PyInstaller**:
   Create `ChatVault.spec`:
   ```python
   # -*- mode: python ; coding: utf-8 -*-
   
   block_cipher = None
   
   a = Analysis(
       ['app/launcher.py'],
       pathex=[],
       binaries=[],
       datas=[
           ('frontend/dist', 'frontend/dist'),
       ],
       hiddenimports=[
           'backend.main',
           'backend.db',
           'backend.jobs',
           'uvicorn',
           'fastapi',
           'pywebview',
       ],
       hookspath=[],
       hooksconfig={},
       runtime_hooks=[],
       excludes=[],
       win_no_prefer_redirects=False,
       win_private_assemblies=False,
       cipher=block_cipher,
       noarchive=False,
   )
   
   pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
   
   exe = EXE(
       pyz,
       a.scripts,
       a.binaries,
       a.zipfiles,
       a.datas,
       [],
       name='ChatVault',
       debug=False,
       bootloader_ignore_signals=False,
       strip=False,
       upx=True,
       upx_exclude=[],
       runtime_tmpdir=None,
       console=False,  # No console window
       disable_windowed_traceback=False,
       argv_emulation=False,
       target_arch=None,
       codesign_identity=None,
       entitlements_file=None,
   )
   ```

   Build:
   ```bash
   pyinstaller ChatVault.spec
   ```

#### Database Location

The database is stored in:
- **Windows**: `%APPDATA%\ChatVault\conversations.db`
- This is handled by `backend/db.py`

#### File Structure in Executable

```
ChatVault.exe
├── (PyInstaller bootloader)
├── (Python runtime)
├── (All dependencies)
└── frontend/dist/
    ├── index.html
    └── assets/
        ├── index-*.js
        └── index-*.css
```

#### Port Management

- FastAPI binds to `127.0.0.1` only
- Port is chosen at runtime (free port finder)
- Frontend connects to FastAPI via proxy in dev, direct in production

#### Development vs Production

**Development:**
- FastAPI serves templates directly
- HTMX for dynamic updates
- pywebview launcher

**Production:**
- FastAPI serves static files from templates/
- Single port for everything
- No dev server needed

---

## Architecture

### Backend

- **Framework**: FastAPI
- **Database**: SQLite with FTS5 for full-text search
- **Templating**: Jinja2
- **Async Operations**: Background job system
- **API**: RESTful endpoints

### Frontend

- **Framework**: FastAPI + Jinja2 templates
- **Dynamic Updates**: HTMX
- **Styling**: CSS (main.css)
- **JavaScript**: Vanilla JS (main.js)
- **Desktop**: pywebview launcher

### Database Schema

#### Core Tables
- `conversations`: Main conversation data
- `messages`: Individual messages
- `conversation_stats`: Calculated statistics

#### Search Tables
- `messages_fts`: FTS5 index for messages
- `conversations_fts`: FTS5 index for conversations

#### Organization Tables
- `tags`: User-defined tags
- `conversation_tags`: Tag assignments
- `notes`: User notes on conversations
- `bookmarks`: Pinned messages
- `custom_titles`: Override conversation titles
- `folders`: Folder/project organization
- `stars`: Starred conversations

#### Management Tables
- `import_reports`: Import tracking
- `message_hashes`: Deduplication hashes
- `user_state`: Application state (last conversation, etc.)
- `jobs`: Background job tracking

### FTS5 Full-Text Search

FTS5 is SQLite's full-text search extension. The system uses:
- **External content tables**: FTS5 tables reference main tables
- **Triggers**: Automatically sync FTS5 with main tables on insert/update/delete
- **Rebuild**: Can rebuild FTS5 index to fix stale data

**Important**: FTS5 external-content tables require special handling:
- Use `INSERT INTO ... VALUES('delete', ...)` for deletes
- Use `INSERT INTO ... VALUES('rebuild')` to rebuild index
- Maintain `rowid = id` mapping for proper joins

### Job System

Background jobs handle long-running operations:
- **Import jobs**: Process conversation imports
- **Reindex jobs**: Rebuild FTS5 indexes
- **Stats calculation**: Calculate conversation statistics

Jobs are tracked in the `jobs` table with status, progress, and results.

---

## Performance Considerations

### Search Performance
- FTS5 indexing provides fast full-text search
- Index is automatically maintained via triggers
- Can rebuild index if needed

### Large Conversations
- Currently loads up to 50,000 messages at once
- Future: Virtual scrolling for better performance

### Database Size
- SQLite handles large databases well
- Consider vacuuming periodically for optimization
- FTS5 indexes can be rebuilt if corrupted

### Memory Usage
- pywebview embeds a browser engine (uses memory)
- Large conversations loaded into memory
- Consider pagination for very large datasets

---

## Security Considerations

### Data Storage
- Database stored locally (user's machine)
- No cloud sync (privacy-focused)
- Encryption optional (SQLCipher)

### Import Safety
- File validation before import
- Error handling for malformed data
- Import reports track failures

### Data Integrity
- Integrity checks detect data issues
- Deduplication prevents duplicate data
- Backup/restore capabilities (future)

---

## Dependencies

### Core
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `sqlite3`: Database (standard library)
- `pywebview`: Desktop app launcher

### Optional
- `pysqlcipher3`: Database encryption
- `onnxruntime`: Local embeddings
- `storyvectordb`: Vector database

### Development
- Python 3.8+
- Virtual environment recommended

---

## Troubleshooting

### FTS5 Search Issues
- **Problem**: Search returns false positives
- **Solution**: Rebuild FTS5 index using `create_fts5_tables.py`

### Import Failures
- **Problem**: Import claims success but nothing imported
- **Solution**: Check file path resolution, verify file format

### Text Selection Issues
- **Problem**: Can't copy/paste text in webview
- **Solution**: Ensure `text_select=True` in `webview.create_window()`

### Port Conflicts
- **Problem**: Port already in use
- **Solution**: Launcher automatically finds free port or kills old instance
