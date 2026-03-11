# Project Structure

Directory layout, file organization, and bash scripts for AI Agent Memory System.

## Directory Layout

```
agents_memory/
├── README.md
├── requirements.txt
├── .env.example
├── .env                    # Configuration (not in git)
├── Dockerfile
├── docker-compose.yml
├── main.py                  # FastAPI application entry point
├── config.py                # Configuration management
│
├── docs/                    # Documentation
│   ├── database-schema.md
│   ├── api-specification.md
│   ├── configuration.md
│   ├── project-structure.md   # This file
│   └── implementation-guide.md
│
├── app/                     # Application code
│   ├── __init__.py
│   │
│   ├── api/                 # API routes
│   │   ├── __init__.py
│   │   ├── buffer.py        # Buffer note endpoints
│   │   ├── notes.py         # Note endpoints
│   │   ├── links.py         # Link endpoints
│   │   ├── tags.py          # Tag endpoints
│   │   ├── relations.py     # Relation type endpoints
│   │   ├── search.py        # Search endpoints
│   │   ├── export.py        # Export/import endpoints
│   │   ├── admin.py         # Admin endpoints
│   │   └── deps.py         # FastAPI dependencies
│   │
│   ├── models/              # Data models
│   │   ├── __init__.py
│   │   ├── database.py      # SQLAlchemy models
│   │   ├── schemas.py       # Pydantic schemas
│   │   └── enums.py        # Enum definitions
│   │
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── note_service.py
│   │   ├── buffer_service.py
│   │   ├── link_service.py
│   │   ├── tag_service.py
│   │   ├── relation_service.py
│   │   ├── search_service.py
│   │   ├── embedding_service.py
│   │   └── export_service.py
│   │
│   ├── db/                  # Database clients
│   │   ├── __init__.py
│   │   ├── session.py       # SQLAlchemy session
│   │   └── qdrant.py        # Qdrant client
│   │
│   └── utils/               # Utility functions
│       ├── __init__.py
│       ├── embeddings.py   # Embedding generation
│       └── markdown.py      # Markdown parsing/serialization
│
├── scripts/                 # Bash scripts for human operations
│   ├── export-notes.sh
│   ├── sync-notes.sh
│   ├── delete-note.sh
│   ├── manage-tags.sh
│   ├── manage-links.sh
│   ├── export-buffer.sh
│   ├── upload-buffer.sh
│   └── backup.sh
│
├── data/                    # Data directory
│   ├── memory.db           # SQLite database
│   ├── notes/              # Markdown exports
│   │   └── .index.json   # Export index
│   ├── buffer/            # Buffer exports (optional)
│   └── backups/           # Database backups
│
├── tests/                   # Tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   ├── test_services/
│   └── test_utils/
│
└── migrations/              # Database migrations
    └── versions/
```

## File Descriptions

### Application Files

| File/Directory | Purpose |
|---------------|---------|
| `main.py` | FastAPI application entry point, route registration |
| `config.py` | Load and validate environment variables |
| `requirements.txt` | Python dependencies |

### Documentation

| File | Purpose |
|-------|---------|
| `docs/database-schema.md` | SQL schemas, SQLAlchemy models, queries |
| `docs/api-specification.md` | REST API endpoints, request/response formats |
| `docs/configuration.md` | Environment variables, Docker configuration |
| `docs/project-structure.md` | This file - directory layout |
| `docs/implementation-guide.md` | Step-by-step implementation guide |

### Application Code

#### API Routes (`app/api/`)

| File | Purpose |
|------|---------|
| `buffer.py` | Buffer note CRUD, processing endpoints |
| `notes.py` | Note CRUD, search endpoints |
| `links.py` | Link management endpoints |
| `tags.py` | Tag management endpoints |
| `relations.py` | Relation type management endpoints |
| `search.py` | Semantic search endpoints |
| `export.py` | Markdown export/import endpoints |
| `admin.py` | Health check, stats, cleanup endpoints |
| `deps.py` | FastAPI dependencies (database sessions, etc.) |

#### Models (`app/models/`)

| File | Purpose |
|------|---------|
| `database.py` | SQLAlchemy ORM models (Note, Link, Tag, etc.) |
| `schemas.py` | Pydantic models for request/response validation |
| `enums.py` | Enum definitions (relation types, etc.) |

#### Services (`app/services/`)

| File | Purpose |
|------|---------|
| `note_service.py` | Note CRUD business logic |
| `buffer_service.py` | Buffer note CRUD, processing logic |
| `link_service.py` | Link creation, deletion, retrieval |
| `tag_service.py` | Tag management |
| `relation_service.py` | Relation type management |
| `search_service.py` | Semantic search, filtering |
| `embedding_service.py` | Embedding generation (OpenAI/local) |
| `export_service.py` | Markdown export/import, formatting |

#### Database (`app/db/`)

| File | Purpose |
|------|---------|
| `session.py` | SQLAlchemy session factory, context manager |
| `qdrant.py` | Qdrant client initialization, collection management |

#### Utils (`app/utils/`)

| File | Purpose |
|------|---------|
| `embeddings.py` | Embedding generation utilities |
| `markdown.py` | Markdown parsing, frontmatter handling |

### Bash Scripts (`scripts/`)

#### export-notes.sh

Export all permanent notes to markdown files.

**Usage**:
```bash
./scripts/export-notes.sh
```

**Environment Variables**:
- `API_BASE` - API base URL (default: http://localhost:8000)
- `OUTPUT_DIR` - Output directory (default: ./notes)

#### sync-notes.sh

Import markdown files and sync with database.

**Usage**:
```bash
./scripts/sync-notes.sh [directory]
```

**Arguments**:
- `directory` - Input directory (default: ./notes)

**Environment Variables**:
- `API_BASE` - API base URL (default: http://localhost:8000)
- `INPUT_DIR` - Input directory (default: ./notes)

#### delete-note.sh

Delete a specific note.

**Usage**:
```bash
./scripts/delete-note.sh <note_id>
```

**Arguments**:
- `note_id` - UUID of note to delete

**Environment Variables**:
- `API_BASE` - API base URL (default: http://localhost:8000)

#### manage-tags.sh

Manage tags: delete or rename.

**Usage**:
```bash
./scripts/manage-tags.sh <delete|rename> <tag_id> [new_name]
```

**Arguments**:
- `action` - delete or rename
- `tag_id` - UUID of tag
- `new_name` - New tag name (required for rename)

**Environment Variables**:
- `API_BASE` - API base URL (default: http://localhost:8000)

#### manage-links.sh

Manage links: add or delete.

**Usage**:
```bash
./scripts/manage-links.sh <add|delete> <source_id> <target_id> [relation_type|link_id]
```

**Arguments**:
- `action` - add or delete
- `source_id` - UUID of source note (add only)
- `target_id` - UUID of target note (add only)
- `relation_type` - Relation type name (add only, default: related_to)
- `link_id` - UUID of link (delete only)

**Environment Variables**:
- `API_BASE` - API base URL (default: http://localhost:8000)

#### export-buffer.sh

Export all buffer notes to markdown files.

**Usage**:
```bash
./scripts/export-buffer.sh
```

**Environment Variables**:
- `API_BASE` - API base URL (default: http://localhost:8000)
- `OUTPUT_DIR` - Output directory (default: ./buffer)

#### upload-buffer.sh

Upload markdown file to buffer.

**Usage**:
```bash
./scripts/upload-buffer.sh <file>
```

**Arguments**:
- `file` - Path to markdown file

**Environment Variables**:
- `API_BASE` - API base URL (default: http://localhost:8000)

#### backup.sh

Create backup of database and Qdrant collection.

**Usage**:
```bash
./scripts/backup.sh
```

**Environment Variables**:
- `BACKUP_DIR` - Backup directory (default: ./data/backups)
- `DATABASE_PATH` - Database path (default: ./data/memory.db)

### Data Directory (`data/`)

| File/Directory | Purpose |
|---------------|---------|
| `memory.db` | SQLite database file |
| `notes/` | Markdown exports of permanent notes |
| `notes/.index.json` | Index of exported notes |
| `buffer/` | Markdown exports of buffer notes (optional) |
| `backups/` | Database backups |

### Tests (`tests/`)

| Directory | Purpose |
|-----------|---------|
| `test_api/` | API endpoint tests |
| `test_services/` | Service layer tests |
| `test_utils/` | Utility function tests |

## Environment Variables Reference

All scripts support the following environment variables:

| Variable | Default | Description |
|-----------|----------|-------------|
| `API_BASE` | http://localhost:8000 | API base URL |
| `OUTPUT_DIR` | ./notes | Output directory for exports |
| `INPUT_DIR` | ./notes | Input directory for imports |
| `BACKUP_DIR` | ./data/backups | Backup directory |
| `DATABASE_PATH` | ./data/memory.db | Database file path |

## Quick Start

### For Development

```bash
# Clone repository
git clone <repo-url>
cd agents_memory

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your values

# Run application
uvicorn main:app --reload
```

### For Production (Docker)

```bash
# Build image
docker build -t agents-memory .

# Run with Docker Compose
docker-compose up -d

# Or run manually
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  agents-memory
```

### For Human Operations

```bash
# Export notes to view
./scripts/export-notes.sh

# View notes
ls ./notes/
cat ./notes/{uuid}.md

# Edit note
vim ./notes/{uuid}.md
./scripts/sync-notes.sh

# Delete note
./scripts/delete-note.sh {uuid}

# Download buffer
./scripts/export-buffer.sh

# Add to buffer
vim my_idea.md
./scripts/upload-buffer.sh my_idea.md

# Backup
./scripts/backup.sh
```

## Development Workflow

### Adding New API Endpoint

1. Create route in `app/api/`
2. Add Pydantic schema in `app/models/schemas.py`
3. Add business logic in `app/services/`
4. Register route in `main.py`
5. Write tests in `tests/test_api/`

### Adding New Service

1. Create service in `app/services/`
2. Use database session from `app/db/session.py`
3. Use Qdrant client from `app/db/qdrant.py`
4. Write tests in `tests/test_services/`

### Adding New Script

1. Create script in `scripts/`
2. Add executable permission: `chmod +x scripts/script.sh`
3. Use environment variables for configuration
4. Document in this file

## Next Steps

1. Review project structure
2. Set up environment variables
3. Run application in development mode
4. Test bash scripts
5. Begin implementation (see `implementation-guide.md`)
