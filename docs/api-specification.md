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
    "meta": {"source": "conversation", "importance": "high"}
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

**Response**: Updated BufferNote object (with `processed=true` and `processed_at` set)

#### Cleanup Processed Buffer Notes

**Endpoint**: `DELETE /api/buffer/cleanup`

> **Implementation note**: Register `/cleanup` route *before* `/{id}`, otherwise the literal string `"cleanup"` will be matched as a buffer note ID.

**Description**: Deletes processed buffer notes older than `BUFFER_RETENTION_DAYS`. If `BUFFER_RETENTION_DAYS=0`, cleanup is disabled and returns `{"deleted": 0, "disabled": true}`.

**Response**:
```json
{
  "deleted": 5
}
```

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

**Endpoint**: `GET /api/notes/{id}`

> **Implementation note**: Register the `/search` route *before* `/{id}` in FastAPI, otherwise the literal string `"search"` will be matched as a note ID.

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
- `keyword`: Full-text search using SQLite FTS5 on title and content (requires `q`)
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
  "name": "string (required)"
}
```

**Note**: If the tag doesn't exist it will be created automatically. Returns the tag object (including its UUID).

**Response**: Tag object

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

**Response**: Single JSON array of all notes (with tags) — `Content-Type: application/json`

#### Export Notes Only

**Endpoint**: `GET /api/export/notes`

**Response**: Single JSON array of notes — `Content-Type: application/json`

#### Export Buffer Notes

**Endpoint**: `GET /api/export/buffer`

**Response**: Single JSON array of buffer notes — `Content-Type: application/json`

> **Note**: Export returns JSON, not markdown files. Markdown rendering is a client/agent concern. The DB is the source of truth; there is no markdown import/export pathway in the API.

#### Import from Markdown

**Endpoint**: Not implemented. Import is done via the database directly or via `POST /api/notes` in bulk. A server-side directory path over HTTP is not a safe or clean primitive.

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
    "synced": 985,
    "unsynced": 15,
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

#### Get Configuration

**Endpoint**: `GET /api/config`

**Response**: Safe subset of current configuration — never exposes secrets.
```json
{
  "embedding_provider": "openai",
  "embedding_model": "text-embedding-ada-002",
  "embedding_dimension": 1536,
  "embedding_mode": "async",
  "buffer_retention_days": 7,
  "debug": false,
  "version": "1.0.0"
}
```

> **Never include**: `api_key`, `openai_api_key`, `qdrant_api_key`, `database_url`, or any credential field.

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
  "total_notes": 1000
}
```

#### Get Re-embed Status

**Endpoint**: `GET /api/admin/reembed/status`

**Response**:
```json
{
  "status": "in_progress"  // or "finished" or "idle"
}
```

> Status is stored in the `metadata` table (`key = "reembed_status"`). Simple: `idle` → `in_progress` → `finished`.

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
  "updated_at": "ISO 8601 datetime",
  "synced": "boolean"
}
```

> `synced=false` means the note has not been embedded yet (just created, or prior embedding failed). `synced=true` means the vector in Qdrant is up to date.

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
  "updated_at": "ISO 8601 datetime",
  "processed": "boolean",
  "processed_at": "ISO 8601 datetime | null"
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
