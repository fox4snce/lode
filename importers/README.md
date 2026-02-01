# Conversation Importers

Separate importers for different conversation export formats.

## Files

- **`import_claude_conversations.py`** - Imports Claude conversations from JSON export
- **`import_openai_conversations.py`** - Imports OpenAI ChatGPT conversations from JSON export
- **`import_lode_conversations.py`** - Imports Lode JSON exports (round-trip from Lode export)

## Usage

### Claude Importer

```bash
python importers/import_claude_conversations.py [path_to_claude_json]
```

Default path: `data/claude/conversations.json`

**Claude Format:**
- Uses `uuid` as conversation_id
- Messages in `chat_messages` array
- ISO timestamp format (`created_at`, `updated_at`)
- Sender: `human` → `user`, `assistant` → `assistant`

### OpenAI Importer

```bash
python importers/import_openai_conversations.py [path_to_openai_json]
```

Default path: `data/conversations.json`

**OpenAI Format:**
- Uses `conversation_id` or `id` as conversation_id
- Messages in `mapping` structure with parent/child relationships
- Unix timestamp format (`create_time`, `update_time`)
- Roles: `user`, `assistant`, `system`

### Lode Importer

```bash
python importers/import_lode_conversations.py [path_to_lode_json] [db_path]
```

**Lode Format (v1.0):**
- Root object with `lode_export_format_version: "1.0"` identifier
- `conversation` object: conversation metadata (conversation_id, title, create_time, etc.)
- `messages` array: flat list of {message_id, role, content, create_time, parent_id}
- One conversation per file

**Directory import:** When using the Import page with source type "Lode", you can point at a folder. The job runner discovers top-level `.json` files, verifies each has the Lode identifier, and imports them in batch.

## Database Schema

Both importers write to the same database schema:
- **conversations** table: conversation metadata
- **messages** table: individual messages
- **ai_source** column: `'claude'`, `'gpt'`, or `'lode'` to distinguish sources

## Modifying Importers

Each importer is self-contained and can be modified independently:
- Change field mappings
- Add custom processing
- Handle different export formats
- Add validation or filtering

The importers are designed to be easily extensible for new formats.

