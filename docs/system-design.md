# System Design: AI Agent Long-Term Memory

## 1. Overview

This document outlines the comprehensive design for an AI agent long-term memory system based on the Zettelkasten note-taking method. The system combines a relational database for structured data (notes, links, tags) with a vector database for semantic search capabilities.

## 2. Technology Stack Decisions

### 2.1 Vector Database Choice: **Qdrant**

#### Rationale

| Criterion | Chroma | Qdrant | pgvector | LanceDB |
|-----------|--------|--------|----------|---------|
| **Deployment** | Embedded/Server | Server (Docker/Local) | Postgres Extension | Embedded |
| **Performance** | Good | Excellent | Excellent | Excellent |
| **Maturity** | Good | Excellent | Excellent | Good |
| **Python Support** | Excellent | Excellent | Excellent | Good |
| **Hybrid Search** | Yes | Yes | Yes | Yes |
| **Metadata Filtering** | Yes | Yes | Yes | Yes |
| **Setup Complexity** | Very Low | Low | High | Very Low |
| **Memory Overhead** | Medium | Low | High | Low |
| **ACID Compliance** | Partial | Yes | Yes | Yes |

**Why Qdrant?**

1. **Performance**: Rust-based implementation provides excellent query performance, crucial for real-time agent operations
2. **Lightweight Deployment**: Can run locally via Docker with minimal resource usage (~100MB base)
3. **Mature & Stable**: Battle-tested in production environments, excellent documentation and community
4. **Feature-Rich**: 
   - HNSW indexing for fast approximate search
   - Filtering by payload (metadata) - essential for tag-based queries
   - Hybrid search (dense + sparse vectors)
   - Snapshot support for backups
5. **Simple Architecture**: Clear separation of concerns (SQLite for relations, Qdrant for vectors)
6. **Python Client**: Excellent `qdrant-client` library with async support
7. **Scalability**: Can scale from local development to production deployment without code changes

**Alternative Consideration**: LanceDB could be used for a truly embedded solution (no server), but Qdrant offers better query performance and more mature filtering capabilities for our use case.

### 2.2 Relational Database: **SQLite**

SQLite is chosen for its simplicity, portability, and zero-configuration setup. Perfect for the Zettelkasten relational model.

### 2.3 ORM: **SQLAlchemy**

Industry-standard Python ORM with excellent SQLite support, type hints, and migration tools (Alembic).

### 2.4 Web Framework: **FastAPI**

Fast, modern Python framework with automatic OpenAPI documentation, async support, and built-in validation (Pydantic).

## 3. Database Schema

### 3.1 SQLite Schema (SQLAlchemy Models)

```python
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Integer, Boolean
from sqlalchemy.dialects.sqlite import UUID as SqliteUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Note(Base):
    __tablename__ = 'notes'

    id = Column(SqliteUUID, primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)  # Optional summary field
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    source_links = relationship("Link", foreign_keys="Link.source_id", back_populates="source")
    target_links = relationship("Link", foreign_keys="Link.target_id", back_populates="target")
    tags = relationship("NoteTag", back_populates="note")

    # Indexes
    __table_args__ = (
        Index('idx_notes_title', 'title'),
        Index('idx_notes_created_at', 'created_at'),
        Index('idx_notes_updated_at', 'updated_at'),
    )

class RelationType(Base):
    __tablename__ = 'relation_types'

    id = Column(SqliteUUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # Hex color for visualization (e.g., '#FF5733')
    is_bidirectional = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    links = relationship("Link", back_populates="relation_type")

    # Indexes
    __table_args__ = (
        Index('idx_relation_types_name', 'name'),
    )

class Link(Base):
    __tablename__ = 'links'

    id = Column(SqliteUUID, primary_key=True, default=uuid.uuid4)
    source_id = Column(SqliteUUID, ForeignKey('notes.id', ondelete='CASCADE'), nullable=False)
    target_id = Column(SqliteUUID, ForeignKey('notes.id', ondelete='CASCADE'), nullable=False)
    relation_type_id = Column(SqliteUUID, ForeignKey('relation_types.id', ondelete='RESTRICT'), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    source = relationship("Note", foreign_keys=[source_id], back_populates="source_links")
    target = relationship("Note", foreign_keys=[target_id], back_populates="target_links")
    relation_type = relationship("RelationType", back_populates="links")

    # Indexes
    __table_args__ = (
        Index('idx_links_source', 'source_id'),
        Index('idx_links_target', 'target_id'),
        Index('idx_links_relation_type_id', 'relation_type_id'),
        UniqueConstraint('source_id', 'target_id', 'relation_type_id', name='uq_link_source_target_type'),
    )

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(SqliteUUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    notes = relationship("NoteTag", back_populates="tag")

class NoteTag(Base):
    __tablename__ = 'note_tags'
    
    note_id = Column(SqliteUUID, ForeignKey('notes.id', ondelete='CASCADE'), primary_key=True)
    tag_id = Column(SqliteUUID, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    note = relationship("Note", back_populates="tags")
    tag = relationship("Tag", back_populates="notes")
    
    # Indexes
    __table_args__ = (
        Index('idx_note_tags_tag_id', 'tag_id'),
    )
```

### 3.2 Qdrant Collection Schema

Qdrant stores vectors with metadata (payloads). The schema for our embeddings collection:

```python
from qdrant_client.models import VectorParams, Distance, PayloadSchemaType

# Collection configuration
vector_size = 1536  # Adjust based on embedding model (e.g., OpenAI ada-002: 1536)
collection_name = "notes_embeddings"

# Vector configuration
vector_config = VectorParams(
    size=vector_size,
    distance=Distance.COSINE  # Cosine distance for semantic similarity
)

# Payload schema (metadata stored with each vector)
payload_schema = {
    "note_id": PayloadSchemaType.UUID,
    "title": PayloadSchemaType.KEYWORD,
    "created_at": PayloadSchemaType.DATETIME,
    "updated_at": PayloadSchemaType.DATETIME,
    "tags": PayloadSchemaType.KEYWORD,  # Array of tag names
    "content_length": PayloadSchemaType.INTEGER
}
```

## 4. Update Strategy: **updated_at with Soft Delete**

### Decision: Use `updated_at` timestamp with soft deletion

#### Rationale

**Options Considered:**
1. **Immutable notes (history records)**: Keep all versions as separate notes
   - Pros: Full history, no data loss
   - Cons: Complex queries, storage bloat, requires version management
   
2. **In-place updates with `updated_at`**: Update note in place, track last modified
   - Pros: Simple, storage-efficient, straightforward queries
   - Cons: No history unless explicitly tracked
   
3. **In-place updates with soft delete**: Mark old notes as deleted, create new versions
   - Pros: History preserved, clear current version, storage-efficient
   - Cons: Requires deletion queries for current data

**Choice: Option 2 (updated_at) with Optional History**

For the MVP, we'll use in-place updates with `updated_at`. This provides:
- Simplicity and clean API
- Storage efficiency
- Clear "current state" semantics
- Easy to implement

**History Support (Optional/Phase 2):**
If history tracking becomes important, we can add:
```sql
ALTER TABLE notes ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE notes ADD COLUMN is_current BOOLEAN DEFAULT TRUE;
ALTER TABLE notes ADD COLUMN previous_note_id UUID REFERENCES notes(id);
```

### 4.1 Vector Database Update Strategy

When a note is updated:
1. Update note in SQLite (new `updated_at` timestamp)
2. Delete old vector from Qdrant (or mark as outdated)
3. Generate new embedding
4. Insert new vector into Qdrant with updated `updated_at` in payload

**Alternative**: Update vector in place using Qdrant's `update_vectors` API. However, this requires the note's UUID in Qdrant to match SQLite, which can be done by using the SQLite UUID as the Qdrant point ID.

## 5. Markdown Sync Architecture

### 5.1 Design Goals

1. Bidirectional sync between SQLite and markdown files
2. Obsidian-compatible format for user convenience
3. Robust conflict resolution
4. Efficient change detection

### 5.2 File Structure

```
/notes/
├── .index.json          # Index file tracking sync state
├── {uuid}.md           # Note files named by UUID
└── _tags/              # Optional: Tag organization
    └── {tag_name}/
        └── {uuid}.md   # Symlinks to note files
```

### 5.3 Markdown File Format

```markdown
---
id: 550e8400-e29b-41d4-a716-446655440000
title: Understanding Neural Networks
tags: [ml, deep-learning, ai]
created_at: 2024-01-15T10:30:00Z
updated_at: 2024-01-20T14:45:00Z
---

# Understanding Neural Networks

Neural networks are computing systems inspired by biological neural networks...

## Key Concepts

[[550e8400-e29b-41d4-a716-446655440001]]  # Link to another note

This note is about fundamental concepts...
```

### 5.4 Sync Strategy

#### Sync Modes

**Mode 1: DB-Led (Default)**
- SQLite is source of truth
- Markdown files are generated/updated from DB
- File watcher triggers DB updates when files are edited

**Mode 2: File-Led (Optional)**
- Markdown files are source of truth
- DB is updated from file changes
- API operations write to files, which sync to DB

**Mode 3: Bidirectional with Conflict Resolution**
- Both DB and files can be updated independently
- Timestamps used for conflict resolution
- Manual resolution option for conflicts

#### Implementation: File Watcher (DB-Led)

Using `watchdog` library to monitor markdown directory:

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class MarkdownSyncHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.md'):
            # Parse markdown file
            # Compare timestamps with DB
            # Update DB if file is newer
            pass
    
    def on_created(self, event):
        # New file created
        # Insert into DB
        pass
    
    def on_deleted(self, event):
        # File deleted
        # Soft delete in DB
        pass
```

#### Conflict Resolution

When both DB and file are updated independently:

1. Compare `updated_at` timestamps
2. If timestamps equal (< 1s difference), prompt user
3. If one is newer, use that version
4. Keep backup of overwritten version

### 5.5 Index File (`.index.json`)

```json
{
  "version": "1.0",
  "last_sync": "2024-01-20T14:45:00Z",
  "notes": {
    "550e8400-e29b-41d4-a716-446655440000": {
      "file": "550e8400-e29b-41d4-a716-446655440000.md",
      "file_hash": "abc123...",
      "db_updated_at": "2024-01-20T14:45:00Z",
      "file_updated_at": "2024-01-20T14:45:00Z",
      "synced": true
    }
  }
}
```

## 6. System Architecture

### 6.1 Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │              REST API Layer                        │  │
│  │  • CRUD Operations                               │  │
│  │  • Search Endpoints                              │  │
│  │  • Link Management                               │  │
│  │  • Tag Operations                                │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                       │
│  ┌──────────────▼───────────────────────────────────┐  │
│  │              Business Logic Layer                 │  │
│  │  • Note Manager                                   │  │
│  │  • Link Manager                                   │  │
│  │  • Tag Manager                                    │  │
│  │  • Search Manager (Hybrid)                        │  │
│  │  • Embedding Manager                              │  │
│  │  • Markdown Sync Manager                          │  │
│  └───┬─────────────────────┬─────────────────────┬───┘  │
└──────┼─────────────────────┼─────────────────────┼──────┘
       │                     │                     │
       ▼                     ▼                     ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   SQLite    │      │   Qdrant    │      │  Markdown   │
│  (Relational)│      │ (Vector DB) │      │   Files     │
│             │      │             │      │             │
│ • notes     │      │ • Embeddings │      │ • .md files │
│ • links     │      │ • Search    │      │ • Obsidian  │
│ • tags      │      │ • Filter    │      │   format    │
└─────────────┘      └─────────────┘      └─────────────┘
```

### 6.2 Data Flow Examples

#### Example 1: Creating a Note

1. Agent calls `POST /api/notes` with note content
2. API validates request
3. Note Manager:
   - Generates UUID
   - Inserts note into SQLite
   - Generates embedding
   - Inserts vector into Qdrant
   - Creates markdown file
   - Updates `.index.json`
4. Returns note ID to agent

#### Example 2: Semantic Search

1. Agent calls `GET /api/notes/search?q=neural networks`
2. API validates request
3. Search Manager:
   - Generates query embedding
   - Queries Qdrant for similar vectors
   - Retrieves full note details from SQLite
   - Optionally filters by tags
   - Orders by similarity
4. Returns ranked notes to agent

#### Example 3: Finding Linked Notes

1. Agent calls `GET /api/notes/{id}/links`
2. API validates request
3. Link Manager:
   - Queries SQLite for source/target links
   - Retrieves related notes
   - Includes link metadata (relation type, description)
4. Returns network of connected notes

## 7. API Design

### 7.1 Endpoints

#### Notes
- `POST /api/notes` - Create note
- `GET /api/notes/{id}` - Get note by ID
- `GET /api/notes` - List notes (with pagination, filtering)
- `PUT /api/notes/{id}` - Update note
- `DELETE /api/notes/{id}` - Delete note (soft delete)

#### Links
- `POST /api/links` - Create link between notes
- `GET /api/notes/{id}/links` - Get links for a note
- `DELETE /api/links/{id}` - Delete link

#### Tags
- `POST /api/tags` - Create tag
- `GET /api/tags` - List tags
- `POST /api/notes/{id}/tags` - Add tag to note
- `DELETE /api/notes/{id}/tags/{tag_id}` - Remove tag from note

#### Search
- `GET /api/notes/search?q={query}&tags={tags}&limit={limit}` - Semantic search
- `GET /api/notes/graph` - Get knowledge graph representation

### 7.2 Request/Response Examples

#### Create Note

```python
# Request
POST /api/notes
{
    "title": "Understanding Neural Networks",
    "content": "Neural networks are computing systems inspired by biological neural networks...",
    "tags": ["ml", "deep-learning"]
}

# Response
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Understanding Neural Networks",
    "content": "...",
    "tags": ["ml", "deep-learning"],
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

#### Semantic Search

```python
# Request
GET /api/notes/search?q=how do neural networks learn&tags=ml&limit=5

# Response
{
    "results": [
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Understanding Neural Networks",
            "content": "...",
            "score": 0.95,
            "tags": ["ml", "deep-learning"]
        },
        {
            "id": "660e8400-e29b-41d4-a716-446655440001",
            "title": "Backpropagation Algorithm",
            "content": "...",
            "score": 0.89,
            "tags": ["ml"]
        }
    ],
    "total": 2
}
```

## 8. Implementation Phases

### Phase 1: Core Infrastructure (Week 1-2)
- [ ] Project structure setup
- [ ] SQLite database with SQLAlchemy models
- [ ] Qdrant client configuration
- [ ] Basic CRUD operations for notes
- [ ] Embedding generation (OpenAI or local model)

### Phase 2: Vector Search (Week 2-3)
- [ ] Semantic search implementation
- [ ] Vector insert/update/delete sync
- [ ] Filter by tags/metadata
- [ ] Performance optimization (HNSW parameters)

### Phase 3: Links & Tags (Week 3-4)
- [ ] Link management (create, query, delete)
- [ ] Tag management (create, assign, remove)
- [ ] Graph traversal queries
- [ ] Network analysis utilities

### Phase 4: Markdown Sync (Week 4-5)
- [ ] Markdown file generation
- [ ] File watcher implementation
- [ ] Bidirectional sync logic
- [ ] Conflict resolution
- [ ] Obsidian format compatibility

### Phase 5: FastAPI Layer (Week 5-6)
- [ ] API endpoint implementation
- [ ] Request/response models (Pydantic)
- [ ] Authentication (if needed)
- [ ] Rate limiting
- [ ] OpenAPI documentation

### Phase 6: Advanced Features (Week 6-8)
- [ ] Hybrid search (semantic + keyword)
- [ ] Knowledge graph visualization
- [ ] Note splitting for large content
- [ ] Batch operations
- [ ] Analytics & metrics

## 9. Configuration

### 9.1 Environment Variables

```bash
# Database
DATABASE_URL=sqlite:///./data/memory.db

# Vector DB
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=  # Optional, for remote deployment

# Embeddings
EMBEDDING_MODEL=openai:text-embedding-ada-002
OPENAI_API_KEY=sk-...
# Or local model:
# EMBEDDING_MODEL=sentence-transformers:all-MiniLM-L6-v2

# API
API_HOST=0.0.0.0
API_PORT=8000

# Markdown Sync
MARKDOWN_DIR=./notes
SYNC_MODE=db_led  # db_led, file_led, or bidirectional
SYNC_INTERVAL=1.0  # Seconds
```

### 9.2 Qdrant Configuration

```python
# HNSW index parameters
hnsw_config = {
    "m": 16,  # Max connections per layer
    "ef_construction": 64  # Candidate list size during index build
}

# Query parameters
hnsw_search_params = {
    "ef": 40  # Candidate list size during search (higher = better recall, slower)
}

# Optimization parameters
optimization_config = {
    "indexing_threshold": 20000  # Don't index until this many vectors
}
```

## 10. Performance Considerations

### 10.1 Vector Search Performance

- Use HNSW index for approximate nearest neighbor search
- Tune `ef` parameter based on recall/latency tradeoff
- Consider quantization for large-scale deployments
- Batch embeddings for efficiency

### 10.2 Database Performance

- Add indexes on frequently queried columns (already in schema)
- Use connection pooling for SQLite
- Consider read replicas for scaling (if needed)
- Optimize complex queries (graph traversals)

### 10.3 Sync Performance

- Debounce file system events
- Batch sync operations
- Use hash-based change detection
- Parallelize embedding generation

## 11. Security Considerations

### 11.1 API Security
- Input validation (Pydantic models)
- SQL injection prevention (ORM)
- Rate limiting
- CORS configuration

### 11.2 Data Security
- API key management (environment variables)
- Database encryption at rest (SQLCipher)
- Secure markdown file permissions
- Backup strategy

## 12. Backup & Recovery

### 12.1 SQLite Backup
```bash
# Online backup
sqlite3 memory.db ".backup memory_backup.db"

# Scheduled backups (cron)
0 2 * * * sqlite3 /path/to/memory.db ".backup /backups/memory_$(date +\%Y\%m\%d).db"
```

### 12.2 Qdrant Backup
```bash
# Create snapshot
curl -X PUT 'http://localhost:6333/collections/notes_embeddings/snapshots'

# Download snapshot
curl -O 'http://localhost:6333/collections/notes_embeddings/snapshots/{snapshot_name}'

# Load snapshot
curl -X PUT 'http://localhost:6333/collections/notes_embeddings/snapshots/upload'
```

### 12.3 Markdown Backup
```bash
# Git-based version control
cd /notes
git add .
git commit -m "Backup $(date)"
git push origin main
```

## 13. Monitoring & Observability

### 13.1 Metrics to Track
- Number of notes, links, tags
- Query latency (search, CRUD operations)
- Vector search recall/precision
- Sync status (DB ↔ Files)
- API request rates

### 13.2 Logging
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Request/response logging for API
- Sync operation logging

### 13.3 Health Checks
```python
# Health check endpoint
GET /api/health

# Response
{
    "status": "healthy",
    "database": "connected",
    "vector_db": "connected",
    "markdown_sync": "active",
    "version": "1.0.0"
}
```

## 14. Testing Strategy

### 14.1 Unit Tests
- SQLAlchemy model tests
- Business logic tests
- Utility function tests

### 14.2 Integration Tests
- API endpoint tests
- Database operations tests
- Vector search accuracy tests
- Markdown sync tests

### 14.3 Performance Tests
- Load testing (simulated concurrent agents)
- Search latency benchmarks
- Sync performance tests

## 15. Future Enhancements

### 15.1 Advanced Features
- Multi-modal notes (images, audio)
- Collaborative editing
- Real-time notifications (WebSockets)
- Advanced graph algorithms (PageRank, community detection)
- LLM-assisted note generation

### 15.2 Scalability
- Distributed deployment (multiple agents)
- Horizontal scaling (load balancing)
- Caching layer (Redis)
- Sharding for large-scale deployments

### 15.3 User Experience
- Web UI for manual note management
- Graph visualization interface
- Advanced search UI
- Note templates and schemas
