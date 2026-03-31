# AI Agent Memory System

A long-term memory system for AI agents inspired by the Zettelkasten note-taking method.

## Features

- **Fast Buffer Notes**: Instant writes without embeddings for short-term memory
- **Semantic Search**: Vector-based search for finding notes by meaning
- **Keyword Search**: Fuzzy search through titles and content
- **Graph Search**: Find connected notes by traversing relationships
- **Note Relationships**: Create typed links between notes (related_to, part_of, etc.)
- **Tag Management**: Organize notes with tags
- **Markdown Export**: Export notes to markdown files (read-only, for viewing)
- **Markdown Sync**: Edit markdown files and sync back to database (optional)
- **API-First**: Complete REST API for agent integration
- **Simple Deployment**: Docker-compose for easy setup
- **Backup/Restore**: Full system backup with SQLite and Qdrant snapshots
- **Model Switching**: Switch embedding providers (OpenAI/Ollama) and re-embed

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                    FastAPI Application                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │          Buffer Notes API (Fast)                 │  │
│  │  • POST /api/buffer - Instant write              │  │
│  └──────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────┐  │
│  │          Memory API (Complete)                   │  │
│  │  • CRUD, Search, Links, Tags                     │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
              │                     │
              ▼                     ▼
        ┌───────────┐         ┌───────────┐
        │   SQLite  │         │   Qdrant  │
        │  + Buffer │         │(Vectors)  │
        └───────────┘         └───────────┘
```

## Quick Start

### Using Docker Compose

```bash
# Clone repository
git clone <repo-url>
cd agents_memory

# Copy environment file
cp .env.example .env
# Edit .env (Ollama is default)

# Start services
docker-compose up -d

# API is available at http://localhost:8000
```

### Manual Setup

```bash
# Install dependencies
uv sync

# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant

# Start application
uvicorn main:app --reload
```

## Documentation

- [Database Schema](docs/database-schema.md) - SQL schemas, SQLAlchemy models, queries
- [API Specification](docs/api-specification.md) - REST API endpoints and examples
- [Configuration](docs/configuration.md) - Environment variables and setup
- [Project Structure](docs/project-structure.md) - Directory layout and bash scripts
- [Implementation Guide](docs/implementation-guide.md) - Step-by-step implementation

## API Usage

### Add to Buffer (Fast)

```python
import requests

response = requests.post(
    "http://localhost:8000/api/buffer",
    json={
        "content": "User prefers morning meetings",
        "metadata": {"source": "conversation"}
    }
)
buffer_id = response.json()["id"]
```

### Create Permanent Note (with Embedding)

```python
response = requests.post(
    "http://localhost:8000/api/notes",
    json={
        "title": "Understanding Neural Networks",
        "content": "Neural networks are computing systems...",
        "tags": ["ml", "deep-learning"]
    }
)
note_id = response.json()["id"]
```

### Search Notes

```python
response = requests.get(
    "http://localhost:8000/api/notes/search",
    params={"q": "neural networks", "tags": "ml", "limit": 5}
)
results = response.json()["results"]
```

## Bash Scripts

Human operations via command-line:

```bash
# Export notes
./scripts/export-notes.sh

# Edit note
vim ./notes/{uuid}.md
./scripts/sync-notes.sh

# Delete note
./scripts/delete-note.sh {uuid}

# Download buffer
./scripts/export-buffer.sh

# Upload to buffer
./scripts/upload-buffer.sh idea.md
```

## Configuration

Key environment variables:

| Variable | Default | Description |
|-----------|----------|-------------|
| `DATABASE_URL` | `sqlite:///./data/memory.db` | SQLite database path |
| `CORS_ALLOW_ORIGINS` | *(empty)* | Explicit allowed origins (comma-separated or JSON list) |
| `CORS_ALLOW_ORIGIN_REGEX` | `^https?://(localhost|127\.0\.0\.1)(:\d+)?$` | Regex fallback for local-safe CORS origins (set empty to disable fallback) |
| `CORS_ALLOW_METHODS` | `*` | Comma-separated allowed CORS methods |
| `CORS_ALLOW_HEADERS` | `*` | Comma-separated allowed CORS headers |
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `EMBEDDING_PROVIDER` | `ollama` | `ollama` (default) or `openai` |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Model name for the chosen provider |
| `EMBEDDING_TASK_PREFIX` | `false` | Prepend `search_document:`/`search_query:` task prefixes. Improves retrieval quality with nomic-embed-text and mxbai-embed-large. **Set to `true` for fresh deployments.** Changing on an existing index requires a full re-embed via the admin API. |
| `NOTE_MAX_CONTENT_LENGTH` | `2048` | Max note content size in characters. `0` = unlimited. Notes over the limit are rejected with HTTP 422. |
| `OPENAI_API_KEY` | — | Optional; only if `EMBEDDING_PROVIDER=openai` |
| `BUFFER_RETENTION_DAYS` | `7` | Days to keep processed buffer notes (`0` = keep forever) |

See [Configuration](docs/configuration.md) for complete reference.

## Technology Stack

- **Framework**: FastAPI
- **Database**: SQLite with SQLAlchemy ORM
- **Vector DB**: Qdrant (with HNSW indexing)
- **Embeddings**: OpenAI (or sentence-transformers for local)
- **Deployment**: Docker, Docker Compose

## Development

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
uv sync

# Run tests
pytest tests/ -v

# Run with reload
uvicorn main:app --reload
```

### Integration test targets

```bash
make test-integration
make test-integration-postgres
make test-integration-auth
```

### Project Structure

```
agents_memory/
├── app/               # Application code
│   ├── api/           # API routes
│   ├── models/        # Data models
│   ├── services/      # Business logic
│   ├── db/            # Database clients
│   └── utils/         # Utilities
├── scripts/           # Bash scripts
├── data/              # Data directory
├── tests/             # Tests
└── docs/              # Documentation
```

See [Project Structure](docs/project-structure.md) for details.

## License

MIT

## Contributing

Contributions welcome! Please read the documentation first.
