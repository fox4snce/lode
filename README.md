# Lode

A local-first desktop application for organizing, searching, and analyzing your AI conversation history.

## Features

- **Import Conversations**: Import conversations from OpenAI and Claude JSON exports
- **Full-Text Search**: Fast SQLite FTS5 search across all conversations
- **Analytics**: Track usage patterns, word counts, activity over time, and more
- **Organization**: Tag, bookmark, and annotate conversations with notes
- **Find Tools**: Extract code blocks, links, TODOs, questions, dates, decisions, and prompts
- **Export**: Export conversations in Markdown, CSV, or JSON formats
- **Local-First**: All data stored locally in SQLite - your conversations never leave your machine
- **Desktop App**: Native desktop application built with pywebview

## Installation

### Download Latest Release

**Pre-built Windows executable:** [Download from GitHub Releases](https://github.com/fox4snce/lode/releases/latest)

The latest release includes a Windows 64-bit executable with all dependencies included. Extract the ZIP file and run `Lode.exe`.

### Prerequisites (for Development)

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
- Start the FastAPI backend server
- Open a desktop window with the application interface

### First Run

1. **Initialize Database**: On first launch, you'll see the Welcome screen. Click "Initialize Database" to create the SQLite database and set up all necessary tables.
2. **Import Conversations**: After initialization, go to the Import screen and select your OpenAI or Claude JSON export file. The import process will add your conversations to the database.
3. **Explore**: Browse conversations, search, organize, and analyze your data

### Key Features

- **Main Screen**: Browse and view all your conversations
- **Search**: Use the search bar to find specific conversations or messages
- **Analytics**: View detailed analytics about your conversation usage
- **Find Tools**: Extract and browse code blocks, links, TODOs, and more
- **Export**: Export individual conversations or use bulk export features
- **Settings**: Manage your database, run integrity checks, and configure options

## Project Structure

```
lode/
├── app/                # Desktop launcher (pywebview)
├── backend/            # FastAPI backend application
├── database/           # Database schema creation scripts
├── docs/               # Documentation and assets
├── static/             # Static files (CSS, JS, images)
├── templates/          # Jinja2 HTML templates
├── tests/              # Test suite
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
- **Embeddings**: ONNX Runtime (for local embeddings)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions, please open an issue on GitHub.

Contact: support@simplychaos.org

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
