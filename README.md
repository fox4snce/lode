# Lode

A local-first desktop application for organizing, searching, and analyzing your AI conversation history.

## Features

- **Import Conversations**: Import conversations from OpenAI and Claude JSON exports
- **Full-Text Search**: Fast SQLite FTS5 search across all conversations
- **Vector Search**: Semantic search over your conversations (embedding-based). Build the index via Import or Settings.
- **Chat**: RAG chat over your data (OpenAI/Anthropic). Ask questions and get answers grounded in your imported conversations.
- **Analytics**: Track usage patterns, word counts, activity over time, and more
- **Organization**: Tag, bookmark, and annotate conversations with notes
- **Find Tools**: Extract code blocks, links, TODOs, questions, dates, decisions, and prompts
- **Export**: Export conversations in Markdown, CSV, or JSON formats
- **Local-First**: All data stored locally in SQLite - your conversations never leave your machine
- **Desktop App**: Native desktop application built with pywebview

## Installation

### Prerequisites

- Python 3.8 or higher
- Windows (primary platform), macOS/Linux (should work but not fully tested)

### Setup

1. **Clone the repository**
   ```bash
   git clone git@github.com:fox4snce/lode.git
   cd lode
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
   
   Windows:
   ```bash
   .venv\Scripts\activate
   ```
   
   macOS/Linux:
   ```bash
   source .venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

Simply run:
```bash
python app/launcher.py
```

This will:
- Start the FastAPI backend server (default port 8000; change in Settings → Server)
- Open a desktop window with the application interface

### First Run

1. **Initialize Database**: On first launch, you'll see the Welcome screen. Click "Initialize Database" to create the SQLite database and set up all necessary tables.
2. **Import Conversations**: After initialization, go to the Import screen and select your OpenAI or Claude JSON export file. The import process will add your conversations to the database.
3. **Explore**: Browse conversations, search, organize, and analyze your data

### Key Features

- **Main Screen**: Browse and view all your conversations (with in-app find)
- **Search**: Full-text search and Vector Search (semantic) across conversations
- **Chat**: Ask questions over your data (RAG with OpenAI or Anthropic)
- **Analytics**: View detailed analytics about your conversation usage
- **Find Tools**: Extract and browse code blocks, links, TODOs, and more
- **Export**: Export individual conversations or use bulk export features
- **Settings**: Server port, database integrity, deduplication, cleanup

## Project Structure

```
lode/
├── app/                # Desktop launcher (pywebview)
├── backend/            # FastAPI backend (routes, chat, vectordb, db, config)
├── database/           # Database schema creation scripts
├── docs/               # Documentation (API, release process)
├── static/             # Static files (CSS, JS, images)
├── templates/          # Jinja2 HTML templates
├── tests/              # Test suite
├── tools/              # Build and utility scripts
└── importers/          # Conversation import modules
```

## Development

For development setup and API documentation, see [README_DEV.md](README_DEV.md).

Run the test suite:
```bash
python tests/run_all_tests.py
```

## Packaging (Windows)

See [PACKAGING.md](PACKAGING.md).

## Technology Stack

- **Backend**: FastAPI, SQLite with FTS5
- **Frontend**: Jinja2 templates, HTMX, vanilla JavaScript
- **Desktop**: pywebview
- **Embeddings**: ONNX Runtime (local embeddings for Vector Search)
- **Chat**: LiteLLM (OpenAI, Anthropic)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions, please open an issue on GitHub.

Contact: support@simplychaos.org

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
