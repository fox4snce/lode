# Lode API Documentation

## Interactive API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: `http://127.0.0.1:8000/docs` (or your configured port)
- **ReDoc**: `http://127.0.0.1:8000/redoc`

These provide:
- Complete endpoint listings
- Request/response schemas
- Try-it-out functionality
- Example requests and responses

## API Base URL

All API endpoints are prefixed with `/api/`:

- Base URL: `http://127.0.0.1:8000/api/` (default port, configurable in Settings)
- All endpoints return JSON unless otherwise specified

## Endpoints by Category

### Health & Setup

#### `GET /api/health`
Health check endpoint.

**Response:**
```json
{
  "status": "ok"
}
```

#### `GET /api/setup/check`
Check if database is initialized.

**Response:**
```json
{
  "initialized": true
}
```

#### `POST /api/setup/initialize`
Initialize the database (first-time setup).

**Response:**
```json
{
  "status": "initialized"
}
```

### Conversations

#### `GET /api/conversations`
List conversations with pagination and sorting.

**Query Parameters:**
- `sort`: `"newest"` | `"oldest"` | `"longest"` | `"most_messages"` (default: `"newest"`)
- `limit`: Number of results (default: 100)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "conversations": [
    {
      "conversation_id": "string",
      "title": "string",
      "ai_source": "gpt" | "claude",
      "create_time": 1234567890,
      "update_time": 1234567890,
      "message_count": 10,
      "word_count": 500
    }
  ],
  "total": 100
}
```

#### `GET /api/conversations/{conversation_id}`
Get a specific conversation.

**Response:**
```json
{
  "conversation_id": "string",
  "title": "string",
  "ai_source": "gpt" | "claude",
  "create_time": 1234567890,
  "update_time": 1234567890,
  "message_count": 10,
  "word_count": 500
}
```

#### `GET /api/conversations/{conversation_id}/messages`
Get messages for a conversation.

**Query Parameters:**
- `limit`: Number of messages (default: 1000)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "messages": [
    {
      "message_id": "string",
      "role": "user" | "assistant" | "system",
      "content": "string",
      "create_time": 1234567890
    }
  ],
  "total": 10
}
```

### Search

#### `GET /api/search`
Full-text search across conversations and messages.

**Query Parameters:**
- `q`: Search query (required)
- `limit`: Number of results (default: 50)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "results": [
    {
      "conversation_id": "string",
      "message_id": "string",
      "content": "string",
      "snippet": "string"
    }
  ],
  "total": 10
}
```

### Vector Database Search

#### `POST /api/vectordb/search`
Semantic search using vector embeddings.

**Request Body:**
```json
{
  "phrases": ["spacetime as a simulation", "quantum mechanics"],
  "top_k": 5,
  "min_similarity": 0.35,
  "filters": {
    "ai_source": "gpt",
    "type": "chunk"
  },
  "include_content": true,
  "include_debug": false
}
```

**Response:**
```json
{
  "results_by_phrase": [
    {
      "phrase": "spacetime as a simulation",
      "results": [
        {
          "similarity": 0.7557,
          "content": "chunk content...",
          "source": {
            "conversation_id": "string",
            "message_ids": ["msg1", "msg2"],
            "chunk_index": 0,
            "vectordb_row_id": 123
          },
          "metadata": {
            "title": "Conversation Title",
            "ai_source": "gpt",
            "type": "chunk"
          }
        }
      ]
    }
  ]
}
```

#### `GET /api/vectordb/status`
Get VectorDB status and statistics.

**Response:**
```json
{
  "vectordb_exists": true,
  "vectordb_path": "/path/to/conversations_vectordb.db",
  "stats": {
    "total_vectors": 1000,
    "unique_files": 500
  }
}
```

### Jobs

#### `GET /api/jobs`
List all jobs.

**Response:**
```json
{
  "jobs": [
    {
      "id": "job-uuid",
      "type": "import" | "reindex" | "vectordb-index",
      "status": "pending" | "running" | "completed" | "failed" | "cancelled",
      "progress": 50,
      "message": "Processing...",
      "created_at": "2024-01-01T00:00:00",
      "started_at": "2024-01-01T00:01:00",
      "completed_at": null
    }
  ]
}
```

#### `GET /api/jobs/{job_id}`
Get a specific job's status.

**Response:**
```json
{
  "id": "job-uuid",
  "type": "import",
  "status": "running",
  "progress": 50,
  "message": "Processing...",
  "result": {},
  "error": null
}
```

#### `POST /api/jobs/import`
Start an import job.

**Request Body:**
```json
{
  "file_path": "/path/to/export.json",
  "ai_source": "gpt" | "claude",
  "calculate_stats": true,
  "build_index": true
}
```

**Response:**
```json
{
  "job_id": "job-uuid"
}
```

#### `POST /api/jobs/vectordb-index`
Start a VectorDB indexing job.

**Request Body:**
```json
{
  "conversation_ids": ["conv1", "conv2"]  // Optional: null = all conversations
}
```

**Response:**
```json
{
  "job_id": "job-uuid"
}
```

#### `POST /api/jobs/{job_id}/cancel`
Cancel a running job.

**Response:**
```json
{
  "status": "cancelled"
}
```

### Organization

#### `POST /api/conversations/{conversation_id}/tags`
Add a tag to a conversation.

**Request Body:**
```json
{
  "tag": "important"
}
```

#### `DELETE /api/conversations/{conversation_id}/tags/{tag}`
Remove a tag from a conversation.

#### `POST /api/conversations/{conversation_id}/notes`
Add or update a note on a conversation.

**Request Body:**
```json
{
  "note": "This is a note"
}
```

#### `POST /api/conversations/{conversation_id}/stars`
Star/unstar a conversation.

**Request Body:**
```json
{
  "starred": true
}
```

#### `POST /api/conversations/{conversation_id}/custom-title`
Set a custom title for a conversation.

**Request Body:**
```json
{
  "title": "My Custom Title"
}
```

### Analytics

#### `GET /api/analytics/usage`
Get usage statistics.

#### `GET /api/analytics/streaks`
Get conversation streaks.

#### `GET /api/analytics/words`
Get word count statistics.

#### `GET /api/analytics/phrases`
Get most common phrases.

#### `GET /api/analytics/vocabulary`
Get vocabulary statistics.

#### `GET /api/analytics/ratios`
Get AI source ratios.

#### `GET /api/analytics/heatmap`
Get activity heatmap data.

### Export

#### `GET /api/export/conversation/{conversation_id}`
Export a conversation.

**Query Parameters:**
- `format`: `"markdown"` | `"csv"` | `"json"` (default: `"markdown"`)
- `include_timestamps`: boolean (default: true)
- `include_metadata`: boolean (default: true)

**Response:** File download or JSON/CSV content

#### `POST /api/export/conversations`
Export multiple conversations to a ZIP file.

**Request Body:**
```json
{
  "conversation_ids": ["conv1", "conv2", "conv3"],
  "format": "markdown" | "csv" | "json"
}
```

**Response:**
```json
{
  "file_path": "exports/conversations_20240101_120000.zip"
}
```

#### `GET /api/export/file/{file_path}`
Get exported file content for preview.

### Configuration

#### `GET /api/config/port`
Get configured server port.

**Response:**
```json
{
  "port": 8000
}
```

#### `POST /api/config/port`
Set server port (requires restart).

**Request Body:**
```json
{
  "port": 8001
}
```

**Response:**
```json
{
  "status": "saved",
  "port": 8001
}
```

### Application State

#### `GET /api/state`
Get application state (last conversation, scroll position, etc.).

**Response:**
```json
{
  "last_conversation_id": "string",
  "last_message_id": "string",
  "last_scroll_offset": 0
}
```

#### `POST /api/state`
Save application state.

**Request Body:**
```json
{
  "last_conversation_id": "string",
  "last_message_id": "string",
  "last_scroll_offset": 0
}
```

## Error Responses

All endpoints may return error responses in this format:

```json
{
  "detail": "Error message here"
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found
- `500`: Internal Server Error

## Authentication

Currently, the API has no authentication (runs on localhost only). All endpoints are accessible to any local process.

## Rate Limiting

No rate limiting is currently implemented.

## Notes

- The server runs on `127.0.0.1` only (localhost, not accessible from network)
- Default port is `8000`, configurable in Settings
- VectorDB API is integrated into the main FastAPI app (same port)
- All timestamps are Unix timestamps (seconds since epoch)
