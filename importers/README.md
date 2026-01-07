# Conversation Importers

Separate importers for different conversation export formats.

## Files

- **`import_claude_conversations.py`** - Imports Claude conversations from JSON export
- **`import_openai_conversations.py`** - Imports OpenAI ChatGPT conversations from JSON export

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

## Database Schema

Both importers write to the same database schema:
- **conversations** table: conversation metadata
- **messages** table: individual messages
- **ai_source** column: `'claude'` or `'gpt'` to distinguish sources

## Modifying Importers

Each importer is self-contained and can be modified independently:
- Change field mappings
- Add custom processing
- Handle different export formats
- Add validation or filtering

The importers are designed to be easily extensible for new formats.

