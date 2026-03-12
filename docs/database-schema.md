# Database Schema

This document contains the detailed SQL schemas for both SQLite and Qdrant databases used in the AI Agent Memory System.

## SQLite Schema

### DDL (Data Definition Language)

```sql
-- Enable foreign key constraints
PRAGMA foreign_keys = ON;

-- Create notes table
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,  -- UUID stored as TEXT
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,  -- Optional summary field
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
    synced BOOLEAN DEFAULT FALSE  -- false = not yet embedded; true = Qdrant vector is current
);

-- Create indexes for notes
CREATE INDEX IF NOT EXISTS idx_notes_title ON notes(title);
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);
CREATE INDEX IF NOT EXISTS idx_notes_updated_at ON notes(updated_at);
CREATE INDEX IF NOT EXISTS idx_notes_synced ON notes(synced);

-- Create FTS5 virtual table for keyword search
-- Indexes: title + content only.
-- Tags are NOT included: they live in a normalized junction table and have their own
-- indexed lookup path. Denormalizing tags into FTS5 would complicate triggers and
-- create sync issues on tag add/remove without note update.
-- FTS5 is NOT fuzzy (no edit-distance). It provides:
--   - Full-text tokenization + BM25 ranking
--   - Prefix queries: "term*"
--   - Phrase queries: "exact phrase"
--   - Boolean: AND / OR / NOT
-- True typo-tolerance belongs in the calling agent or via semantic search (Qdrant).
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
    note_id UNINDEXED,
    title,
    content
);

-- Triggers to keep FTS5 in sync with notes table
CREATE TRIGGER IF NOT EXISTS notes_fts_insert AFTER INSERT ON notes BEGIN
    INSERT INTO notes_fts(note_id, title, content) VALUES (new.id, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS notes_fts_update AFTER UPDATE ON notes BEGIN
    DELETE FROM notes_fts WHERE note_id = old.id;
    INSERT INTO notes_fts(note_id, title, content) VALUES (new.id, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS notes_fts_delete AFTER DELETE ON notes BEGIN
    DELETE FROM notes_fts WHERE note_id = old.id;
END;

-- Create relation_types table
-- Note: `color` field removed — no UI layer exists to consume it.
CREATE TABLE IF NOT EXISTS relation_types (
    id TEXT PRIMARY KEY,  -- UUID
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_bidirectional BOOLEAN DEFAULT FALSE,
    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- Create index for relation_types
CREATE INDEX IF NOT EXISTS idx_relation_types_name ON relation_types(name);

-- Create buffer_notes table
CREATE TABLE IF NOT EXISTS buffer_notes (
    id TEXT PRIMARY KEY,  -- UUID
    content TEXT NOT NULL,
    meta TEXT,  -- JSON string: {"source": "user", "tags": ["idea"]}
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    updated_at DATETIME NOT NULL DEFAULT (datetime('now')),
    processed BOOLEAN DEFAULT FALSE,
    processed_at DATETIME  -- Set when marked as processed
);

-- Create indexes for buffer_notes
CREATE INDEX IF NOT EXISTS idx_buffer_unprocessed ON buffer_notes(processed, created_at);
CREATE INDEX IF NOT EXISTS idx_buffer_created_at ON buffer_notes(created_at);

-- Create links table
CREATE TABLE IF NOT EXISTS links (
    id TEXT PRIMARY KEY,  -- UUID
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation_type_id TEXT NOT NULL,  -- FK to relation_types
    description TEXT,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (source_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (relation_type_id) REFERENCES relation_types(id) ON DELETE RESTRICT
);

-- Create indexes for links
CREATE INDEX IF NOT EXISTS idx_links_source ON links(source_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON links(target_id);
CREATE INDEX IF NOT EXISTS idx_links_relation_type_id ON links(relation_type_id);

-- Create unique constraint for links
CREATE UNIQUE INDEX IF NOT EXISTS uq_link_source_target_type 
ON links(source_id, target_id, relation_type_id);

-- Create tags table
CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY,  -- UUID
    name TEXT NOT NULL UNIQUE,
    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- Create index for tags
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);

-- Create note_tags junction table
CREATE TABLE IF NOT EXISTS note_tags (
    note_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (note_id, tag_id),
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Create index for note_tags
CREATE INDEX IF NOT EXISTS idx_note_tags_tag_id ON note_tags(tag_id);

-- Create metadata table for tracking sync state
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

-- Insert initial metadata
INSERT OR IGNORE INTO metadata (key, value) VALUES ('schema_version', '1.0');
INSERT OR IGNORE INTO metadata (key, value) VALUES ('last_vector_sync', '0');
```

### Common Queries

#### Note Queries

```sql
-- Get note by ID
SELECT 
    n.*,
    GROUP_CONCAT(t.name) as tags
FROM notes n
LEFT JOIN note_tags nt ON n.id = nt.note_id
LEFT JOIN tags t ON nt.tag_id = t.id
WHERE n.id = ?
GROUP BY n.id;

-- List all notes with pagination
SELECT 
    n.*,
    GROUP_CONCAT(t.name) as tags
FROM notes n
LEFT JOIN note_tags nt ON n.id = nt.note_id
LEFT JOIN tags t ON nt.tag_id = t.id
GROUP BY n.id
ORDER BY n.updated_at DESC
LIMIT ? OFFSET ?;

-- Keyword search using FTS5 (title and content, ranked by relevance)
-- The `rank` column is provided by FTS5 automatically
SELECT
    n.*,
    GROUP_CONCAT(t.name) as tags
FROM notes n
JOIN notes_fts fts ON n.id = fts.note_id
LEFT JOIN note_tags nt ON n.id = nt.note_id
LEFT JOIN tags t ON nt.tag_id = t.id
WHERE notes_fts MATCH ?
GROUP BY n.id
ORDER BY rank
LIMIT ?;

-- Search notes by tags
SELECT 
    n.*,
    GROUP_CONCAT(t.name) as tags
FROM notes n
INNER JOIN note_tags nt ON n.id = nt.note_id
INNER JOIN tags t ON nt.tag_id = t.id
WHERE t.name IN (?)
GROUP BY n.id
HAVING COUNT(DISTINCT t.name) = ?
ORDER BY n.updated_at DESC;

-- Get notes updated since timestamp
SELECT 
    n.*,
    GROUP_CONCAT(t.name) as tags
FROM notes n
LEFT JOIN note_tags nt ON n.id = nt.note_id
LEFT JOIN tags t ON nt.tag_id = t.id
WHERE n.updated_at > ?
GROUP BY n.id
ORDER BY n.updated_at DESC;
```

#### Link Queries

```sql
-- Get links for a note (both incoming and outgoing)
SELECT 
    l.id,
    l.source_id,
    l.target_id,
    l.relation_type_id,
    rt.name as relation_name,
    rt.description as relation_description,

    rt.is_bidirectional,
    l.description as link_description,
    l.created_at,
    CASE 
        WHEN l.source_id = ? THEN 'outgoing'
        ELSE 'incoming'
    END as direction,
    CASE 
        WHEN l.source_id = ? THEN t2.title
        ELSE t1.title
    END as related_title,
    CASE 
        WHEN l.source_id = ? THEN t2.id
        ELSE t1.id
    END as related_id
FROM links l
INNER JOIN relation_types rt ON l.relation_type_id = rt.id
LEFT JOIN notes t1 ON l.source_id = t1.id
LEFT JOIN notes t2 ON l.target_id = t2.id
WHERE l.source_id = ? OR l.target_id = ?
ORDER BY l.created_at DESC;

-- Get outgoing links from a note
SELECT 
    l.id,
    l.source_id,
    l.target_id,
    l.relation_type_id,
    rt.name as relation_name,
    rt.description as relation_description,

    rt.is_bidirectional,
    l.description as link_description,
    l.created_at,
    t.id as target_note_id,
    t.title as target_note_title
FROM links l
INNER JOIN relation_types rt ON l.relation_type_id = rt.id
INNER JOIN notes t ON l.target_id = t.id
WHERE l.source_id = ?
ORDER BY l.created_at DESC;

-- Get incoming links to a note
SELECT 
    l.id,
    l.source_id,
    l.target_id,
    l.relation_type_id,
    rt.name as relation_name,
    rt.description as relation_description,

    rt.is_bidirectional,
    l.description as link_description,
    l.created_at,
    t.id as source_note_id,
    t.title as source_note_title
FROM links l
INNER JOIN relation_types rt ON l.relation_type_id = rt.id
INNER JOIN notes t ON l.source_id = t.id
WHERE l.target_id = ?
ORDER BY l.created_at DESC;

-- Get links by relation type
SELECT 
    l.id,
    l.source_id,
    l.target_id,
    l.relation_type_id,
    rt.name as relation_name,
    rt.description as relation_description,

    rt.is_bidirectional,
    l.description as link_description,
    l.created_at,
    source_note.title as source_title,
    source_note.content as source_content,
    target_note.title as target_title,
    target_note.content as target_content
FROM links l
INNER JOIN relation_types rt ON l.relation_type_id = rt.id
INNER JOIN notes source_note ON l.source_id = source_note.id
INNER JOIN notes target_note ON l.target_id = target_note.id
WHERE rt.name = ?
ORDER BY l.created_at DESC;

-- Check if link exists
SELECT COUNT(*) as exists
FROM links l
INNER JOIN relation_types rt ON l.relation_type_id = rt.id
WHERE l.source_id = ? AND l.target_id = ? AND rt.name = ?;
```

#### Tag Queries

```sql
-- List all tags with note counts
SELECT 
    t.*,
    COUNT(nt.note_id) as note_count
FROM tags t
LEFT JOIN note_tags nt ON t.id = nt.tag_id
GROUP BY t.id
ORDER BY t.name;

-- Get notes for a tag
SELECT 
    n.*,
    GROUP_CONCAT(t2.name) as tags
FROM notes n
INNER JOIN note_tags nt ON n.id = nt.note_id
INNER JOIN tags t ON nt.tag_id = t.id
LEFT JOIN note_tags nt2 ON n.id = nt2.note_id
LEFT JOIN tags t2 ON nt2.tag_id = t2.id
WHERE t.name = ?
GROUP BY n.id
ORDER BY n.updated_at DESC;

-- Get popular tags (most used)
SELECT 
    t.name,
    COUNT(nt.note_id) as usage_count
FROM tags t
INNER JOIN note_tags nt ON t.id = nt.tag_id
GROUP BY t.id
ORDER BY usage_count DESC
LIMIT ?;

-- Search tags by name
SELECT *
FROM tags
WHERE name LIKE ?
ORDER BY name
LIMIT ?;
```

#### Relation Type Queries

```sql
-- List all relation types with usage counts
SELECT 
    rt.*,
    COUNT(l.id) as link_count
FROM relation_types rt
LEFT JOIN links l ON rt.id = l.relation_type_id
GROUP BY rt.id
ORDER BY rt.name;

-- Get relation type by ID
SELECT *
FROM relation_types
WHERE id = ?;

-- Get relation type by name
SELECT *
FROM relation_types
WHERE name = ?;

-- Get popular relation types (most used)
SELECT 
    rt.name,
    rt.description,
    rt.is_bidirectional,
    COUNT(l.id) as usage_count
FROM relation_types rt
INNER JOIN links l ON rt.id = l.relation_type_id
GROUP BY rt.id
ORDER BY usage_count DESC
LIMIT ?;

-- Get bidirectional relation types
SELECT *
FROM relation_types
WHERE is_bidirectional = TRUE
ORDER BY name;

-- Search relation types by name
SELECT *
FROM relation_types
WHERE name LIKE ?
ORDER BY name
LIMIT ?;
```

#### Buffer Note Queries

```sql
-- Get all buffer notes
SELECT *
FROM buffer_notes
ORDER BY created_at DESC;

-- Get unprocessed buffer notes (for "dreaming" agent)
SELECT *
FROM buffer_notes
WHERE processed = FALSE
ORDER BY created_at;

-- Get processed buffer notes
SELECT *
FROM buffer_notes
WHERE processed = TRUE
ORDER BY created_at DESC;

-- Get buffer note by ID
SELECT *
FROM buffer_notes
WHERE id = ?;

-- Get buffer notes created after specific time
SELECT *
FROM buffer_notes
WHERE created_at > ?
ORDER BY created_at DESC;

-- Get buffer notes created within last N hours
SELECT *
FROM buffer_notes
WHERE datetime(created_at) > datetime('now', '-' || ? || ' hours')
ORDER BY created_at DESC;

-- Get buffer notes count
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN processed = TRUE THEN 1 ELSE 0 END) as processed_count,
    SUM(CASE WHEN processed = FALSE THEN 1 ELSE 0 END) as unprocessed_count
FROM buffer_notes;

-- Get oldest unprocessed buffer note
SELECT *
FROM buffer_notes
WHERE processed = FALSE
ORDER BY created_at ASC
LIMIT 1;

-- Get newest buffer notes (recent N)
SELECT *
FROM buffer_notes
ORDER BY created_at DESC
LIMIT ?;

-- Search buffer notes by content (keyword search)
SELECT *
FROM buffer_notes
WHERE content LIKE ?
ORDER BY created_at DESC;

-- Get buffer notes by metadata (JSON search)
SELECT *
FROM buffer_notes
WHERE meta LIKE ?
ORDER BY created_at DESC;

-- Delete processed buffer notes older than N days
DELETE FROM buffer_notes
WHERE processed = TRUE
AND datetime(created_at) < datetime('now', '-' || ? || ' days');

-- Mark buffer note as processed
UPDATE buffer_notes
SET processed = TRUE, processed_at = datetime('now'), updated_at = datetime('now')
WHERE id = ?;

-- Mark all buffer notes as processed
UPDATE buffer_notes
SET processed = TRUE, processed_at = datetime('now'), updated_at = datetime('now')
WHERE processed = FALSE;

-- Mark all unprocessed buffer notes older than N hours as processed
UPDATE buffer_notes
SET processed = TRUE, processed_at = datetime('now'), updated_at = datetime('now')
WHERE processed = FALSE
AND datetime(created_at) < datetime('now', '-' || ? || ' hours');
```

#### Graph Queries

```sql
-- Get connected notes (breadth-first, depth 1)
WITH RECURSIVE connected_notes AS (
    -- Base case: starting note
    SELECT 
        id, title, created_at, updated_at,
        0 as depth,
        '' as relation_type_name,
        '' as relation_type_id,
        id as origin_id
    FROM notes
    WHERE id = ?

    UNION ALL

    -- Recursive case: linked notes
    SELECT
        CASE
            WHEN l.source_id = cn.id THEN l.target_id
            ELSE l.source_id
        END as id,
        CASE
            WHEN l.source_id = cn.id THEN t2.title
            ELSE t1.title
        END as title,
        CASE
            WHEN l.source_id = cn.id THEN t2.created_at
            ELSE t1.created_at
        END as created_at,
        CASE
            WHEN l.source_id = cn.id THEN t2.updated_at
            ELSE t1.updated_at
        END as updated_at,
        cn.depth + 1 as depth,
        rt.name as relation_type_name,
        rt.id as relation_type_id,
        cn.origin_id
    FROM links l
    INNER JOIN relation_types rt ON l.relation_type_id = rt.id
    INNER JOIN connected_notes cn ON (l.source_id = cn.id OR l.target_id = cn.id)
    INNER JOIN notes t1 ON l.source_id = t1.id
    INNER JOIN notes t2 ON l.target_id = t2.id
    WHERE cn.depth < ?
)
SELECT DISTINCT *
FROM connected_notes
WHERE id NOT IN (SELECT origin_id FROM connected_notes)
ORDER BY depth, updated_at DESC;

-- Find shortest path between two notes
WITH RECURSIVE path AS (
    -- Base case: start note
    SELECT
        source_id as current_id,
        0 as steps,
        '|' || source_id || '|' as path,
        'start' as relation_type_name,
        l.relation_type_id
    FROM links l
    WHERE source_id = ?

    UNION ALL

    -- Recursive case: follow links
    SELECT
        CASE
            WHEN l.source_id = p.current_id THEN l.target_id
            ELSE l.source_id
        END as current_id,
        p.steps + 1 as steps,
        p.path ||
            CASE
                WHEN l.source_id = p.current_id THEN l.target_id
                ELSE l.source_id
            END || '|' as path,
        rt.name as relation_type_name,
        l.relation_type_id
    FROM path p
    INNER JOIN links l ON (l.source_id = p.current_id OR l.target_id = p.current_id)
    INNER JOIN relation_types rt ON l.relation_type_id = rt.id
    WHERE p.steps < 10  -- Max depth
        AND p.path NOT LIKE '%' ||
            CASE
                WHEN l.source_id = p.current_id THEN l.target_id
                ELSE l.source_id
            END || '%'
)
SELECT current_id, steps, relation_type
FROM path
WHERE current_id = ?
ORDER BY steps
LIMIT 1;

-- Get disconnected notes (notes without any links)
SELECT n.*
FROM notes n
LEFT JOIN links l ON n.id = l.source_id OR n.id = l.target_id
WHERE l.id IS NULL
ORDER BY n.updated_at DESC;

-- Get note clusters (groups of interconnected notes)
WITH RECURSIVE clusters AS (
    -- Base case: all notes as potential clusters
    SELECT 
        id as cluster_id,
        id as note_id,
        0 as depth
    FROM notes
    
    UNION ALL
    
    -- Recursive case: expand clusters through links
    SELECT 
        c.cluster_id,
        CASE 
            WHEN l.source_id = c.note_id THEN l.target_id
            ELSE l.source_id
        END as note_id,
        c.depth + 1
    FROM clusters c
    INNER JOIN links l ON c.source_id = c.note_id OR l.target_id = c.note_id
    WHERE c.depth < 5  -- Max depth
)
SELECT 
    cluster_id,
    MIN(n.title) as cluster_title,
    COUNT(DISTINCT note_id) as note_count
FROM clusters c
INNER JOIN notes n ON c.cluster_id = n.id
GROUP BY cluster_id
ORDER BY note_count DESC;
```

#### Metadata Queries

```sql
-- Get metadata value
SELECT value
FROM metadata
WHERE key = ?;

-- Update metadata
UPDATE metadata
SET value = ?, updated_at = datetime('now')
WHERE key = ?;

-- Get all metadata
SELECT * FROM metadata;
```

### Data Manipulation Examples

#### Insert Operations

```sql
-- Insert note
INSERT INTO notes (id, title, content, summary)
VALUES (?, ?, ?, ?);

-- Insert relation type
INSERT INTO relation_types (id, name, description, is_bidirectional)
VALUES (?, ?, ?, ?);

-- Insert link
INSERT INTO links (id, source_id, target_id, relation_type_id, description)
VALUES (?, ?, ?, ?, ?);

-- Insert tag (or ignore if exists)
INSERT OR IGNORE INTO tags (id, name)
VALUES (?, ?);

-- Associate tag with note
INSERT INTO note_tags (note_id, tag_id)
VALUES (?, ?);

-- Insert buffer note
INSERT INTO buffer_notes (id, content, meta)
VALUES (?, ?, ?);
```

#### Update Operations

```sql
-- Update note
UPDATE notes
SET title = ?, content = ?, summary = ?, updated_at = datetime('now')
WHERE id = ?;

-- Update relation type
UPDATE relation_types
SET name = ?, description = ?, is_bidirectional = ?
WHERE id = ?;

-- Update link
UPDATE links
SET relation_type_id = ?, description = ?
WHERE id = ?;

-- Update tag
UPDATE tags
SET name = ?
WHERE id = ?;

-- Update buffer note
UPDATE buffer_notes
SET content = ?, metadata = ?
WHERE id = ?;

-- Mark buffer note as processed
UPDATE buffer_notes
SET processed = TRUE
WHERE id = ?;
```

#### Delete Operations

```sql
-- Delete note (cascades to links and note_tags)
DELETE FROM notes WHERE id = ?;

-- Delete relation type (RESTRICT - will fail if links exist)
DELETE FROM relation_types WHERE id = ?;

-- Delete link
DELETE FROM links WHERE id = ?;

-- Delete tag (cascades to note_tags)
DELETE FROM tags WHERE id = ?;

-- Remove tag from note
DELETE FROM note_tags WHERE note_id = ? AND tag_id = ?;

-- Delete buffer note
DELETE FROM buffer_notes WHERE id = ?;

-- Delete all processed buffer notes
DELETE FROM buffer_notes WHERE processed = TRUE;

-- Delete processed buffer notes older than N days
DELETE FROM buffer_notes
WHERE processed = TRUE
AND datetime(created_at) < datetime('now', '-' || ? || ' days');
```

## Qdrant Schema

### Collection Configuration

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from typing import List, Dict, Any
import uuid

# Initialize client
client = QdrantClient(url="http://localhost:6333")

# Collection name
COLLECTION_NAME = "notes_embeddings"

# Vector configuration
VECTOR_SIZE = 1536  # Adjust based on your embedding model
VECTOR_CONFIG = VectorParams(
    size=VECTOR_SIZE,
    distance=Distance.COSINE  # Cosine distance for semantic similarity
)

# Create collection (or recreate if exists)
def create_collection():
    from qdrant_client.http.exceptions import UnexpectedResponse
    try:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VECTOR_CONFIG,
            optimizers_config={
                "indexing_threshold": 20000,  # Don't index until this many vectors
            },
            hnsw_config={
                "m": 16,  # Max connections per layer
                "ef_construction": 64,  # Candidate list size during index build
            }
        )
        print(f"Collection '{COLLECTION_NAME}' created successfully")
    except UnexpectedResponse as e:
        if e.status_code == 400:
            print(f"Collection '{COLLECTION_NAME}' already exists")
        else:
            raise

# Drop collection (use with caution!)
def drop_collection():
    client.delete_collection(COLLECTION_NAME)
    print(f"Collection '{COLLECTION_NAME}' deleted")

# Get collection info
def get_collection_info():
    info = client.get_collection(COLLECTION_NAME)
    return {
        "points_count": info.points_count,
        "segments_count": info.segments_count,
        "status": info.status,
        "optimizer_status": info.optimizer_status
    }
```

### Payload Schema

Each vector (point) in Qdrant stores the following payload:

```python
# Payload structure for a note embedding
payload_schema = {
    "note_id": str,  # UUID matching SQLite
    "title": str,
    "created_at": str,  # ISO 8601 datetime
    "updated_at": str,  # ISO 8601 datetime
    "tags": List[str],  # Array of tag names
    "content_length": int,
    "summary": str,  # Optional
}
```

### Vector Operations

#### Insert/Update Vectors

```python
def upsert_embedding(note_id: str, vector: List[float], payload: Dict[str, Any]):
    """
    Insert or update a vector embedding for a note.
    Uses note_id as the point ID for easy lookup.
    """
    point = PointStruct(
        id=note_id,  # Use SQLite note ID as point ID
        vector=vector,
        payload=payload
    )
    
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[point]
    )

def batch_upsert_embeddings(data: List[Dict[str, Any]]):
    """
    Batch insert/update multiple embeddings.
    
    Args:
        data: List of dicts with 'note_id', 'vector', and 'payload' keys
    """
    points = [
        PointStruct(
            id=item['note_id'],
            vector=item['vector'],
            payload=item['payload']
        )
        for item in data
    ]
    
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
```

#### Search Vectors

```python
def search_similar_notes(
    query_vector: List[float],
    limit: int = 10,
    score_threshold: float = 0.7,
    filter_tags: List[str] = None,
    min_content_length: int = None,
    max_content_length: int = None
) -> List[Dict[str, Any]]:
    """
    Search for similar notes using vector similarity.
    
    Args:
        query_vector: Embedding vector for the query
        limit: Maximum number of results
        score_threshold: Minimum similarity score (0-1)
        filter_tags: Filter by tags (must have ALL tags if multiple)
        min_content_length: Minimum content length
        max_content_length: Maximum content length
    
    Returns:
        List of dicts with note_id, score, and payload
    """
    search_filter = None
    
    # Build filter conditions
    conditions = []
    
    if filter_tags:
        # Must have ALL specified tags
        for tag in filter_tags:
            conditions.append(
                FieldCondition(
                    key="tags",
                    match=MatchValue(value=tag)
                )
            )
    
    if min_content_length is not None:
        from qdrant_client.models import Range
        conditions.append(
            FieldCondition(
                key="content_length",
                range=Range(gte=min_content_length)
            )
        )
    
    if max_content_length is not None:
        from qdrant_client.models import Range
        conditions.append(
            FieldCondition(
                key="content_length",
                range=Range(lte=max_content_length)
            )
        )
    
    if conditions:
        from qdrant_client.models import Filter
        if len(conditions) == 1:
            search_filter = Filter(must=[conditions[0]])
        else:
            search_filter = Filter(must=conditions)
    
    # Perform search
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=search_filter,
        limit=limit,
        score_threshold=score_threshold
    )
    
    # Format results
    formatted_results = []
    for result in results:
        formatted_results.append({
            "note_id": result.id,
            "score": result.score,
            "payload": result.payload
        })
    
    return formatted_results

def get_embedding_by_id(note_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific embedding by note ID.
    """
    results = client.retrieve(
        collection_name=COLLECTION_NAME,
        ids=[note_id]
    )
    
    if results:
        return {
            "note_id": results[0].id,
            "vector": results[0].vector,
            "payload": results[0].payload
        }
    return None
```

#### Delete Vectors

```python
def delete_embedding(note_id: str):
    """
    Delete a vector embedding for a note.
    """
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=[note_id]
    )

def batch_delete_embeddings(note_ids: List[str]):
    """
    Batch delete multiple vector embeddings.
    """
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=note_ids
    )
```

### Collection Management

```python
def create_snapshot():
    """
    Create a snapshot of the collection for backup.
    """
    snapshot_info = client.create_snapshot(collection_name=COLLECTION_NAME)
    return snapshot_info

def list_snapshots():
    """
    List all snapshots for the collection.
    """
    snapshots = client.list_snapshots(collection_name=COLLECTION_NAME)
    return snapshots

def delete_snapshot(snapshot_name: str):
    """
    Delete a specific snapshot.
    """
    client.delete_snapshot(collection_name=COLLECTION_NAME, snapshot_name=snapshot_name)

def recover_from_snapshot(snapshot_name: str):
    """
    Recover collection from a snapshot.
    """
    client.recover_snapshot(collection_name=COLLECTION_NAME, snapshot_name=snapshot_name)

def update_collection_config():
    """
    Update collection configuration (e.g., change HNSW parameters).
    """
    client.update_collection(
        collection_name=COLLECTION_NAME,
        optimizer_config={
            "indexing_threshold": 50000,  # Update threshold
        },
        hnsw_config={
            "m": 32,  # Update max connections
            "ef_construction": 128  # Update construction candidates
        }
    )

def set_search_params(ef: int):
    """
    Set search parameters for the current session.
    Higher ef = better recall, slower search.
    """
    from qdrant_client.models import HnswContext
    client.update_collection(
        collection_name=COLLECTION_NAME,
        hnsw_config={
            "context": HnswContext(context_ef=ef)
        }
    )
```

### Performance Optimization

```python
def optimize_collection():
    """
    Force optimization of the collection (build indexes if needed).
    """
    client.update_collection(
        collection_name=COLLECTION_NAME,
        optimizer_config={
            "flushing_interval_sec": 5,  # Flush every 5 seconds
            "optimizers_disabled": False,  # Enable optimizers
            "indexing_threshold": 20000,  # Index after 20k points
            "max_optimization_threads": 2  # Use 2 threads for optimization
        }
    )

def get_collection_stats():
    """
    Get detailed statistics about the collection.
    """
    info = client.get_collection(COLLECTION_NAME)
    
    return {
        "points_count": info.points_count,
        "segments_count": info.segments_count,
        "status": info.status,
        "config": {
            "params": info.config.params,
            "hnsw_config": info.config.hnsw_config,
            "optimizer_config": info.config.optimizer_config,
        },
        "optimizer_status": info.optimizer_status
    }
```

## Best Practices

### SQLite Best Practices

1. **Use transactions** for multi-step operations
2. **Enable WAL mode** for better concurrency:
   ```sql
   PRAGMA journal_mode=WAL;
   ```
3. **Use prepared statements** to prevent SQL injection
4. **Batch operations** for better performance
5. **Regular VACUUM** to reclaim space:
   ```sql
   VACUUM;
   ```
6. **Use EXPLAIN QUERY PLAN** to optimize queries:
   ```sql
   EXPLAIN QUERY PLAN SELECT * FROM notes WHERE title LIKE '%neural%';
   ```

### Qdrant Best Practices

1. **Batch insertions** for better performance
2. **Tune HNSW parameters** based on your use case:
   - Higher `m` = better recall, more memory
   - Higher `ef_construction` = better recall, slower indexing
   - Higher `ef` (search) = better recall, slower search
3. **Use filtering** for metadata queries
4. **Set appropriate indexing threshold** to delay index creation
5. **Use snapshots** for backups before major changes
6. **Monitor collection stats** for performance insights

### Cross-Database Consistency

1. **Always use the same UUID** for a note in both SQLite and Qdrant
2. **Update both databases atomically** using transactions
3. **Use the same timestamps** for synchronization
4. **Implement retry logic** for network operations
5. **Log all sync operations** for debugging
6. **Regularly verify consistency** between the two databases
