# API Specification

Complete REST API specification for AI Agent Memory System.

## Base URL

```
http://localhost:8000/api
```

## Authentication

Configure via `API_KEY` environment variable. When set, all requests require `X-API-Key` header.

**Example with auth**:
```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/api/notes
```

## Common Response Format

### Success Response
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Note Title",
  "content": "Note content...",
  "created_at": "2024-01-20T14:30:00Z",
  "updated_at": "2024-01-20T14:30:00Z"
}
```

### Error Response
```json
{
  "error": "Error message",
  "detail": "Detailed error information"
}
```

## Endpoints

### Buffer Notes

Fast writes without embeddings. Used for short-term memory.

#### Create Buffer Note

**Endpoint**: `POST /api/buffer`

**Request Body**:
```json
{
  "content": "string (required)",
  "meta": {
    "source": "string (optional)",
    "tags": ["string"],
    "custom_field": "any"
  }
}
```

**Response**: BufferNote object

**Example**:
```bash
curl -X POST http://localhost:8000/api/buffer \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Remember: User prefers morning meetings",
    "metadata": {"source": "conversation", "importance": "high"}
  }'
```

#### List Buffer Notes

**Endpoint**: `GET /api/buffer?processed=false&limit=100&offset=0`

**Query Parameters**:
- `processed` (boolean, optional) - Filter by processed status
- `limit` (integer, optional, default: 100)
- `offset` (integer, optional, default: 0)

**Response**: Array of BufferNote objects

#### Get Buffer Note

**Endpoint**: `GET /api/buffer/{id}`

**Response**: BufferNote object

#### Delete Buffer Note

**Endpoint**: `DELETE /api/buffer/{id}`

**Response**: Success message

#### Mark Buffer Note as Processed

**Endpoint**: `POST /api/buffer/{id}/process`

**Response**: Success message

#### Export Buffer Notes

**Endpoint**: `GET /api/buffer/export`

**Response**: Markdown files (text/markdown)

### Notes

Full CRUD with embeddings for long-term memory.

#### Create Note

**Endpoint**: `POST /api/notes`

**Request Body**:
```json
{
  "title": "string (required)",
  "content": "string (required)",
  "summary": "string (optional)",
  "tags": ["string"] (optional)
}
```

**Response**: Note object with embedding generated

**Example**:
```bash
curl -X POST http://localhost:8000/api/notes \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Understanding Neural Networks",
    "content": "Neural networks are computing systems...",
    "summary": "Introduction to neural networks",
    "tags": ["ml", "deep-learning"]
  }'
```

#### List Notes

**Endpoint**: `GET /api/notes?tags=ml,ai&limit=20&offset=0&sort=updated_at&order=desc`

**Query Parameters**:
- `tags` (string, optional) - Comma-separated tag names
- `limit` (integer, optional, default: 20)
- `offset` (integer, optional, default: 0)
- `sort` (string, optional, default: updated_at) - created_at or updated_at
- `order` (string, optional, default: desc) - asc or desc

**Response**: Array of Note objects

#### Get Note

**Endpoint**: `GET /api/notes/get/{id}`

**Response**: Note object with tags and links

#### Update Note

**Endpoint**: `PATCH /api/notes/{id}`

**Request Body**:
```json
{
  "title": "string (optional)",
  "content": "string (optional)",
  "summary": "string (optional)",
  "tags": ["string"] (optional)
}
```

**Response**: Updated Note object (embedding regenerated)

#### Delete Note

**Endpoint**: `DELETE /api/notes/{id}`

**Response**: Success message

#### Search Notes

**Endpoint**: `GET /api/notes/search`

**Query Parameters**:
- `q` (string, optional) - Search query for semantic search
- `tags` (string, optional) - Comma-separated tag names
- `limit` (integer, optional, default: 10)
- `threshold` (float, optional, default: 0.7) - Minimum similarity score (0-1)
- `search_type` (string, optional, default: hybrid) - semantic, keyword, hybrid, graph
- `graph_depth` (integer, optional, default: 1) - For graph search: levels to traverse (1-3)
- `graph_start_id` (string, optional) - For graph search: starting note ID

**Search Types**:
- `semantic`: Vector similarity search (requires `q`)
- `keyword`: Fuzzy search on title and content (requires `q`)
- `hybrid`: Combined semantic + keyword (default, requires `q`)
- `graph`: Find connected notes (requires `graph_start_id`, optionally `q`)

**Response**:
```json
{
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Understanding Neural Networks",
      "content": "...",
      "score": 0.95,
      "tags": ["ml", "deep-learning"],
      "distance": 1  // For graph search
    }
  ],
  "total": 1
}
```

#### Get Note Links

**Endpoint**: `GET /api/notes/{id}/links?direction=all&limit=50`

**Query Parameters**:
- `direction` (string, optional, default: all) - incoming, outgoing, or all
- `limit` (integer, optional, default: 50)

**Response**: Array of Link objects with relation type details

### Links

Manage relationships between notes.

#### Create Link

**Endpoint**: `POST /api/notes/links`

**Request Body**:
```json
{
  "source_id": "uuid (required)",
  "target_id": "uuid (required)",
  "relation_type": "string (required)",
  "description": "string (optional)"
}
```

**Note**: If `relation_type` doesn't exist, it will be created automatically.

**Response**: Link object

#### Delete Link

**Endpoint**: `DELETE /api/notes/links/{id}`

**Response**: Success message

### Tags

Manage note tags.

#### List Tags

**Endpoint**: `GET /api/tags?limit=100&offset=0`

**Query Parameters**:
- `limit` (integer, optional, default: 100)
- `offset` (integer, optional, default: 0)

**Response**: Array of Tag objects with usage counts

#### Create Tag

**Endpoint**: `POST /api/tags`

**Request Body**:
```json
{
  "name": "string (required)"
}
```

**Response**: Tag object

#### Get Note Tags

**Endpoint**: `GET /api/notes/{id}/tags`

**Response**: Array of Tag objects

#### Add Tag to Note

**Endpoint**: `POST /api/notes/{id}/tags`

**Request Body**:
```json
{
  "tag_id": "uuid (required)"
}
```

**Response**: Success message

#### Remove Tag from Note

**Endpoint**: `DELETE /api/notes/{id}/tags/{tag_id}`

**Response**: Success message

### Relation Types

Manage link relationship types.

#### List Relation Types

**Endpoint**: `GET /api/relations`

**Response**: Array of RelationType objects with usage counts

#### Create Relation Type

**Endpoint**: `POST /api/relations`

**Request Body**:
```json
{
  "name": "string (required, unique)",
  "description": "string (optional)",
  "color": "string (optional, hex: #FF5733)",
  "is_bidirectional": "boolean (optional, default: false)"
}
```

**Response**: RelationType object

#### Get Relation Type

**Endpoint**: `GET /api/relations/{id}`

**Response**: RelationType object

#### Update Relation Type

**Endpoint**: `PUT /api/relations/{id}`

**Request Body**:
```json
{
  "name": "string (optional)",
  "description": "string (optional)",
  "color": "string (optional)",
  "is_bidirectional": "boolean (optional)"
}
```

**Response**: Updated RelationType object

#### Delete Relation Type

**Endpoint**: `DELETE /api/relations/{id}`

**Note**: Will fail if links exist using this relation type.

**Response**: Success message

### Export/Import

Manage markdown files for human viewing/editing.

#### Export All Notes

**Endpoint**: `GET /api/export`

**Response**: Markdown files (text/markdown)

#### Export Notes Only

**Endpoint**: `GET /api/export/notes`

**Response**: Markdown files (text/markdown)

#### Export Buffer Notes

**Endpoint**: `GET /api/export/buffer`

**Response**: Markdown files (text/markdown)

#### Import from Markdown

**Endpoint**: `POST /api/import`

**Request Body**:
```json
{
  "directory": "string (optional, default: ./notes)"
}
```

**Response**: Import results with success/error counts

### Admin

System management and monitoring.

#### Health Check

**Endpoint**: `GET /api/health`

**Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "vector_db": "connected",
  "version": "1.0.0"
}
```

#### System Statistics

**Endpoint**: `GET /api/stats`

**Response**:
```json
{
  "notes": {
    "total": 1000,
    "created_today": 5,
    "updated_today": 10
  },
  "links": {
    "total": 500
  },
  "tags": {
    "total": 50,
    "most_used": ["ml", "ai", "python"]
  },
  "buffer": {
    "total": 25,
    "unprocessed": 10,
    "processed": 15
  },
  "vector_db": {
    "points_count": 1000,
    "segments_count": 10
  }
}
```

#### Cleanup Processed Buffer Notes

**Endpoint**: `DELETE /api/buffer/processed`

**Query Parameters**:
- `days` (integer, optional, default: from env) - Delete processed notes older than N days

**Response**: Success message with count of deleted notes

#### Get Configuration

**Endpoint**: `GET /api/config`

**Response**: Current configuration values

#### Create Backup

**Endpoint**: `POST /api/admin/backup`

**Description**: Create backup of SQLite database and Qdrant snapshot

**Request Body**:
```json
{
  "name": "string (optional, default: auto-generated timestamp)"
}
```

**Response**:
```json
{
  "backup_id": "backup_20240120_143000",
  "sqlite_path": "./data/backups/memory_20240120_143000.db",
  "qdrant_snapshot": "snapshot-20240120-143000",
  "created_at": "2024-01-20T14:30:00Z"
}
```

#### List Backups

**Endpoint**: `GET /api/admin/backups`

**Response**:
```json
{
  "backups": [
    {
      "backup_id": "backup_20240120_143000",
      "sqlite_path": "./data/backups/memory_20240120_143000.db",
      "qdrant_snapshot": "snapshot-20240120-143000",
      "created_at": "2024-01-20T14:30:00Z",
      "size_mb": 1.5
    }
  ]
}
```

#### Restore Backup

**Endpoint**: `POST /api/admin/restore/{backup_id}`

**Description**: Restore from backup (stops services during restore)

**Response**: Success message

#### Purge and Re-embed All Notes

**Endpoint**: `POST /api/admin/reembed`

**Description**: Delete all vectors and regenerate embeddings with new model (configured in env)

**Warning**: Expensive operation - may take significant time and cost

**Request Body**:
```json
{
  "confirm": "string (required, must be 'I understand this will delete and regenerate all embeddings')"
}
```

**Response**:
```json
{
  "status": "started",
  "total_notes": 1000,
  "estimated_time_seconds": 300
}
```

#### Get Re-embed Status

**Endpoint**: `GET /api/admin/reembed/status`

**Response**:
```json
{
  "status": "in_progress",
  "total_notes": 1000,
  "processed": 450,
  "failed": 2,
  "progress_percent": 45
}
```

#### Sync Unprocessed Notes

**Endpoint**: `POST /api/admin/sync-embeddings`

**Description**: Generate embeddings for all notes where synced=false (background job trigger)

**Response**:
```json
{
  "status": "started",
  "pending_notes": 15
}
```

## Data Models

### Note
```json
{
  "id": "uuid",
  "title": "string",
  "content": "text",
  "summary": "string (optional)",
  "tags": ["string"],
  "created_at": "ISO 8601 datetime",
  "updated_at": "ISO 8601 datetime"
}
```

### BufferNote
```json
{
  "id": "uuid",
  "content": "text",
  "meta": {
    "source": "string",
    "tags": ["string"],
    "custom": "any"
  },
  "created_at": "ISO 8601 datetime",
  "processed": "boolean"
}
```

### Link
```json
{
  "id": "uuid",
  "source_id": "uuid",
  "target_id": "uuid",
  "relation_type_id": "uuid",
  "relation_type": {
    "id": "uuid",
    "name": "string",
    "description": "string",
    "color": "string",
    "is_bidirectional": "boolean"
  },
  "description": "string (optional)",
  "created_at": "ISO 8601 datetime"
}
```

### Tag
```json
{
  "id": "uuid",
  "name": "string",
  "note_count": "integer",
  "created_at": "ISO 8601 datetime"
}
```

### RelationType
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "color": "string",
  "is_bidirectional": "boolean",
  "link_count": "integer",
  "created_at": "ISO 8601 datetime"
}
```

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid input data |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Resource already exists (e.g., duplicate tag) |
| 422 | Unprocessable Entity - Validation failed |
| 500 | Internal Server Error |
