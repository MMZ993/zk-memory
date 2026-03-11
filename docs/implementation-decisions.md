# Implementation Decisions Summary

This document summarizes all key decisions made for the AI Agent Long-Term Memory system and provides the implementation roadmap.

## Executive Summary

We are building a Zettelkasten-inspired long-term memory system for AI agents that combines:
- **SQLite** for structured relational data (notes, links, tags)
- **Qdrant** for vector embeddings and semantic search
- **Markdown files** for user-friendly note editing with Obsidian compatibility
- **FastAPI** for a REST API that agents can interact with

## Key Decisions

### 1. Vector Database: **Qdrant**

**Decision**: Use Qdrant as the vector database.

**Rationale**:
- Excellent performance with HNSW indexing
- Lightweight Docker deployment (~100MB)
- Rust-based implementation for reliability
- Mature and stable with excellent documentation
- Strong Python client with async support
- Supports filtering by metadata (essential for tag-based queries)
- Hybrid search capabilities (dense + sparse vectors)
- Can scale from local dev to production

**Alternatives Considered**:
- **Chroma**: Good but less mature, Rust overhead for simple use case
- **pgvector**: Excellent but requires full Postgres installation (overkill)
- **LanceDB**: Embedded but less mature filtering capabilities

### 2. Relational Database: **SQLite**

**Decision**: Use SQLite with SQLAlchemy ORM.

**Rationale**:
- Zero-configuration setup
- Excellent for single-user / single-agent use case
- Perfect for Zettelkasten relational model
- Easy backup and portability (single file)
- Type-safe with SQLAlchemy

### 3. Update Strategy: **updated_at with In-Place Updates**

**Decision**: Use in-place updates with `updated_at` timestamp.

**Rationale**:
- Simplest implementation
- Storage-efficient
- Clear "current state" semantics
- Easy to query and understand
- History can be added later if needed

**Alternative Rejected**: Immutable notes with history records - too complex for MVP, adds storage overhead.

### 4. Web Framework: **FastAPI**

**Decision**: Use FastAPI for the REST API layer.

**Rationale**:
- Modern, fast Python framework
- Automatic OpenAPI documentation
- Built-in validation with Pydantic
- Async support for better performance
- Excellent developer experience

### 5. Markdown Sync: **DB-Led with File Watcher**

**Decision**: SQLite is the source of truth; markdown files are synced from DB.

**Rationale**:
- Clear single source of truth
- Prevents sync conflicts
- Simpler implementation
- File watcher provides real-time updates
- Obsidian-compatible format for user convenience

**Sync Modes**:
- **Phase 1**: DB-led (DB → Files only)
- **Phase 2**: Bidirectional with conflict resolution (optional)

## Database Schema Summary

### SQLite Schema

#### Tables

1. **notes**
   - `id` (UUID, PK)
   - `title` (String, NOT NULL)
   - `content` (Text, NOT NULL)
   - `summary` (Text, optional)
   - `created_at` (DateTime, NOT NULL)
   - `updated_at` (DateTime, NOT NULL)

2. **relation_types**
   - `id` (UUID, PK)
   - `name` (String, unique, NOT NULL)
   - `description` (Text, optional)
   - `color` (String, optional) - Hex color for visualization
   - `is_bidirectional` (Boolean, default FALSE)
   - `created_at` (DateTime, NOT NULL)

3. **links**
   - `id` (UUID, PK)
   - `source_id` (UUID, FK → notes)
   - `target_id` (UUID, FK → notes)
   - `relation_type_id` (UUID, FK → relation_types)
   - `description` (Text, optional)
   - `created_at` (DateTime, NOT NULL)

4. **tags**
   - `id` (UUID, PK)
   - `name` (String, unique, NOT NULL)
   - `created_at` (DateTime, NOT NULL)

5. **note_tags** (junction table)
   - `note_id` (UUID, PK, FK → notes)
   - `tag_id` (UUID, PK, FK → tags)
   - `created_at` (DateTime, NOT NULL)

6. **metadata** (for sync tracking)
   - `key` (String, PK)
   - `value` (String, NOT NULL)
   - `updated_at` (DateTime, NOT NULL)

### Qdrant Schema

#### Collection Configuration

- **Collection Name**: `notes_embeddings`
- **Vector Size**: 1536 (adjustable based on embedding model)
- **Distance Metric**: Cosine distance
- **Index Type**: HNSW
  - `m`: 16 (max connections per layer)
  - `ef_construction`: 64 (construction candidate list)
  - `ef`: 40 (search candidate list, tunable)

#### Payload Schema

Each vector stores:
- `note_id` (UUID) - matches SQLite
- `title` (String)
- `created_at` (ISO 8601 datetime)
- `updated_at` (ISO 8601 datetime)
- `tags` (Array of strings)
- `content_length` (Integer)
- `summary` (String, optional)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │              REST API Layer                        │  │
│  └──────────────┬───────────────────────────────────┘  │
│                 │                                       │
│  ┌──────────────▼───────────────────────────────────┐  │
│  │              Business Logic Layer                 │  │
│  └───┬─────────────────────┬─────────────────────┬───┘  │
└──────┼─────────────────────┼─────────────────────┼──────┘
       │                     │                     │
       ▼                     ▼                     ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   SQLite    │      │   Qdrant    │      │  Markdown   │
│  (Relational)│      │ (Vector DB) │      │   Files     │
└─────────────┘      └─────────────┘      └─────────────┘
```

## Implementation Roadmap

### Phase 1: Core Infrastructure (Week 1-2)

**Objectives**: Set up project structure, databases, and basic CRUD operations.

**Tasks**:
- [ ] Initialize Python project with FastAPI
- [ ] Set up virtual environment and dependencies
- [ ] Create SQLite database schema with SQLAlchemy
- [ ] Configure Qdrant client and collection
- [ ] Implement basic Note CRUD operations
- [ ] Set up embedding generation (OpenAI or local)
- [ ] Implement vector insert/update/delete sync
- [ ] Write unit tests for core operations

**Deliverables**:
- Working project structure
- SQLite database with notes table
- Qdrant collection with sample embeddings
- Basic API endpoints for CRUD

**Dependencies**:
```python
fastapi
uvicorn
sqlalchemy
alembic
qdrant-client
python-dotenv
openai  # or sentence-transformers
pytest
```

### Phase 2: Vector Search (Week 2-3)

**Objectives**: Implement semantic search with filtering.

**Tasks**:
- [ ] Implement semantic search endpoint
- [ ] Add search by tags filtering
- [ ] Add search by content length filtering
- [ ] Tune HNSW parameters for performance
- [ ] Add search result scoring
- [ ] Implement pagination for search results
- [ ] Write integration tests for search
- [ ] Add performance benchmarks

**Deliverables**:
- `/api/notes/search` endpoint
- Filtered search functionality
- Optimized query performance

### Phase 3: Links & Tags (Week 3-4)

**Objectives**: Implement relationship management between notes.

**Tasks**:
- [ ] Implement Link CRUD operations
- [ ] Implement Tag CRUD operations
- [ ] Add note-tag association management
- [ ] Implement graph traversal queries
- [ ] Add link by relation type filtering
- [ ] Implement network analysis utilities
- [ ] Add endpoints for getting connected notes
- [ ] Write tests for all operations

**Deliverables**:
- `/api/links` endpoints
- `/api/tags` endpoints
- `/api/notes/{id}/links` endpoint
- Graph query utilities

### Phase 4: Markdown Sync (Week 4-5)

**Objectives**: Implement bidirectional sync with markdown files.

**Tasks**:
- [ ] Design markdown file format (Obsidian-compatible)
- [ ] Implement markdown file generation from DB
- [ ] Set up file watcher (watchdog)
- [ ] Implement DB → File sync
- [ ] Implement File → DB sync
- [ ] Add conflict resolution logic
- [ ] Create index file for sync tracking
- [ ] Add note link format `[[uuid]]`
- [ ] Write tests for sync operations

**Deliverables**:
- Markdown files in Obsidian format
- Real-time bidirectional sync
- Conflict resolution mechanism

### Phase 5: FastAPI Layer (Week 5-6)

**Objectives**: Complete REST API with documentation.

**Tasks**:
- [ ] Implement all API endpoints
- [ ] Add Pydantic models for request/response
- [ ] Implement request validation
- [ ] Add error handling and custom exceptions
- [ ] Add CORS configuration
- [ ] Implement rate limiting
- [ ] Add OpenAPI documentation
- [ ] Add health check endpoint
- [ ] Write API integration tests

**Deliverables**:
- Complete REST API
- Auto-generated OpenAPI docs
- Production-ready endpoints

### Phase 6: Advanced Features (Week 6-8)

**Objectives**: Add advanced search and analytics.

**Tasks**:
- [ ] Implement hybrid search (semantic + keyword)
- [ ] Add knowledge graph visualization endpoint
- [ ] Implement note splitting for large content
- [ ] Add batch operations for efficiency
- [ ] Implement analytics and metrics
- [ ] Add query performance monitoring
- [ ] Implement backup and restore functionality
- [ ] Add configuration management
- [ ] Write comprehensive test suite

**Deliverables**:
- Hybrid search capabilities
- Knowledge graph API
- Batch operations
- Monitoring and analytics

## Technology Stack Details

### Core Dependencies

```python
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Database
sqlalchemy==2.0.23
alembic==1.12.1

# Vector Database
qdrant-client==1.7.0

# Embeddings
openai==1.3.7  # OR
sentence-transformers==2.2.2

# Utilities
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0

# File Watching
watchdog==3.0.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2

# Development
black==23.11.0
isort==5.12.0
mypy==1.7.1
```

### Project Structure

```
agents_memory/
├── README.md
├── requirements.txt
├── .env.example
├── alembic.ini
├── main.py                 # FastAPI app entry point
├── config.py               # Configuration management
├── docs/
│   ├── system-design.md
│   ├── database-schema.md
│   └── api-documentation.md
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── notes.py
│   │   │   ├── links.py
│   │   │   ├── tags.py
│   │   │   └── search.py
│   │   └── deps.py         # Dependencies
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py     # SQLAlchemy models
│   │   ├── schemas.py      # Pydantic schemas
│   │   └── enums.py        # Enum definitions
│   ├── services/
│   │   ├── __init__.py
│   │   ├── note_service.py
│   │   ├── link_service.py
│   │   ├── tag_service.py
│   │   ├── search_service.py
│   │   ├── embedding_service.py
│   │   └── sync_service.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py      # Database session
│   │   └── qdrant.py       # Qdrant client
│   └── utils/
│       ├── __init__.py
│       ├── embeddings.py   # Embedding generation
│       └── uuid.py         # UUID utilities
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   ├── test_services/
│   └── test_utils/
├── data/
│   ├── memory.db           # SQLite database
│   └── notes/              # Markdown files
│       └── .index.json     # Sync index
├── migrations/
│   └── versions/
└── scripts/
    ├── init_db.py          # Initialize databases
    ├── seed_data.py        # Seed test data
    └── backup.py           # Backup utilities
```

## Configuration

### Environment Variables

Create `.env` file:

```bash
# Application
APP_NAME=AI Agent Memory System
APP_VERSION=1.0.0
DEBUG=False

# API
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=sqlite:///./data/memory.db

# Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=notes_embeddings
QDRANT_API_KEY=  # Optional

# Embeddings
EMBEDDING_MODEL=openai:text-embedding-ada-002
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=sk-...

# Alternative: Local embeddings
# EMBEDDING_MODEL=sentence-transformers:all-MiniLM-L6-v2
# EMBEDDING_DIMENSION=384

# Markdown Sync
MARKDOWN_DIR=./data/notes
SYNC_MODE=db_led
SYNC_INTERVAL=1.0

# Performance
HNSW_M=16
HNSW_EF_CONSTRUCTION=64
HNSW_EF=40
INDEXING_THRESHOLD=20000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Performance Targets

### Query Performance

- **Note CRUD**: < 10ms
- **Semantic search (top 10)**: < 50ms
- **Link queries**: < 20ms
- **Tag queries**: < 15ms
- **Graph traversal (depth 2)**: < 100ms

### Scalability

- **Max notes**: 100,000+ (with Qdrant HNSW)
- **Max concurrent requests**: 100+ (with proper connection pooling)
- **Search latency**: < 100ms for 95th percentile
- **Vector indexing**: 20k points before auto-index

## Security Considerations

1. **API Security**
   - Input validation (Pydantic)
   - SQL injection prevention (SQLAlchemy ORM)
   - Rate limiting (slowapi)
   - CORS configuration

2. **Data Security**
   - API keys in environment variables
   - Database encryption at rest (SQLCipher optional)
   - Secure file permissions for markdown
   - Regular backups

3. **Operational Security**
   - HTTPS in production
   - Authentication/authorization (future)
   - Audit logging
   - Secure deployment practices

## Monitoring & Observability

### Metrics to Track

- Number of notes, links, tags
- Query latency (p50, p95, p99)
- Search recall/precision
- Sync status and errors
- API request rates and errors

### Logging

- Structured logging (JSON format)
- Request/response logging
- Error tracking
- Performance metrics

### Health Checks

- Database connectivity
- Vector DB connectivity
- Sync status
- System resources

## Backup Strategy

### SQLite Backup

```bash
# Daily automated backup
sqlite3 data/memory.db ".backup data/backups/memory_$(date +%Y%m%d).db"

# Keep last 30 days
find data/backups -name "memory_*.db" -mtime +30 -delete
```

### Qdrant Backup

```python
# Weekly snapshots
qdrant_client.create_snapshot(collection_name="notes_embeddings")
```

### Markdown Backup

```bash
# Git-based version control
cd data/notes
git add .
git commit -m "Auto-backup $(date)"
git push
```

## Testing Strategy

### Unit Tests
- Business logic
- Database models
- Utility functions

### Integration Tests
- API endpoints
- Database operations
- Vector search
- Markdown sync

### Performance Tests
- Load testing
- Search benchmarks
- Sync performance

## Next Steps

1. **Review and approve** this design document
2. **Set up development environment**
3. **Initialize project structure**
4. **Begin Phase 1 implementation**

## Questions for Discussion

1. **Embedding Model**: OpenAI (requires API key, costs money) or local (free, slower)?
2. **Markdown Sync Mode**: Start with DB-led (simpler) or bidirectional (more complex)?
3. **Authentication**: Add authentication from the start or add later?
4. **Deployment**: Docker-based deployment or manual setup?
5. **History Tracking**: Add history tracking in Phase 1 or defer to Phase 2?

## Appendix

### A. Quick Start Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Run migrations
alembic upgrade head

# Start API server
uvicorn main:app --reload

# Run tests
pytest

# Seed test data
python scripts/seed_data.py
```

### B. API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/notes | Create note |
| GET | /api/notes/{id} | Get note |
| GET | /api/notes | List notes |
| PUT | /api/notes/{id} | Update note |
| DELETE | /api/notes/{id} | Delete note |
| GET | /api/notes/search | Semantic search |
| GET | /api/notes/{id}/links | Get links |
| POST | /api/links | Create link |
| DELETE | /api/links/{id} | Delete link |
| GET | /api/tags | List tags |
| POST | /api/tags | Create tag |
| POST | /api/notes/{id}/tags | Add tag |
| DELETE | /api/notes/{id}/tags/{tag_id} | Remove tag |
| GET | /api/health | Health check |

### C. References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [OpenAI Embeddings](https://platform.openai.com/docs/guides/embeddings)
- [Sentence Transformers](https://www.sbert.net/)
- [Obsidian](https://obsidian.md/)
- [Zettelkasten Method](https://zettelkasten.de/)
