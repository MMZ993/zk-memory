# Configuration

Environment variables and configuration options for AI Agent Memory System.

## Environment Variables

Create a `.env` file in the project root:

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
QDRANT_API_KEY=  # Optional, for remote deployment

# Embeddings
EMBEDDING_MODEL=openai:text-embedding-ada-002
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=sk-...

# Alternative: Local embeddings
# EMBEDDING_MODEL=sentence-transformers:all-MiniLM-L6-v2
# EMBEDDING_DIMENSION=384

# Buffer Notes
BUFFER_RETENTION_DAYS=7  # 0 = never delete processed notes

# Markdown Export
MARKDOWN_DIR=./data/notes
MARKDOWN_EXPORT_AUTO=true
MARKDOWN_EXPORT_INTERVAL=60  # Seconds between auto-exports

# Performance
HNSW_M=16
HNSW_EF_CONSTRUCTION=64
HNSW_EF=40
INDEXING_THRESHOLD=20000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Variable Descriptions

### Application

| Variable | Default | Description |
|-----------|----------|-------------|
| `APP_NAME` | AI Agent Memory System | Application name for logging |
| `APP_VERSION` | 1.0.0 | Version string for health check |
| `DEBUG` | False | Enable debug mode and detailed logging |

### API

| Variable | Default | Description |
|-----------|----------|-------------|
| `API_HOST` | 0.0.0.0 | Host to bind API server to |
| `API_PORT` | 8000 | Port for API server |

### Database

| Variable | Default | Description |
|-----------|----------|-------------|
| `DATABASE_URL` | sqlite:///./data/memory.db | SQLite database connection string |

**Examples**:
```bash
# Relative path
DATABASE_URL=sqlite:///./data/memory.db

# Absolute path
DATABASE_URL=sqlite:////var/lib/agents_memory/memory.db

# In-memory (for testing)
DATABASE_URL=sqlite:///:memory:
```

### Vector Database (Qdrant)

| Variable | Default | Description |
|-----------|----------|-------------|
| `QDRANT_HOST` | localhost | Qdrant server hostname |
| `QDRANT_PORT` | 6333 | Qdrant server port |
| `QDRANT_COLLECTION` | notes_embeddings | Collection name for embeddings |
| `QDRANT_API_KEY` | (none) | API key for Qdrant Cloud (optional) |

**Examples**:
```bash
# Local Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=

# Qdrant Cloud
QDRANT_HOST=your-cluster.qdrant.io
QDRANT_PORT=443
QDRANT_API_KEY=your-api-key-here
```

### Embeddings

| Variable | Default | Description |
|-----------|----------|-------------|
| `EMBEDDING_MODEL` | openai:text-embedding-ada-002 | Embedding model to use |
| `EMBEDDING_DIMENSION` | 1536 | Dimension of embedding vectors |
| `OPENAI_API_KEY` | (required) | OpenAI API key (if using OpenAI model) |

**Supported Models**:

**OpenAI Models**:
- `openai:text-embedding-ada-002` - 1536 dimensions
- `openai:text-embedding-3-small` - 1536 dimensions
- `openai:text-embedding-3-large` - 3072 dimensions

**Sentence Transformers (Local)**:
- `sentence-transformers:all-MiniLM-L6-v2` - 384 dimensions
- `sentence-transformers:all-mpnet-base-v2` - 768 dimensions

**Examples**:
```bash
# OpenAI (requires API key, paid)
EMBEDDING_MODEL=openai:text-embedding-ada-002
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=sk-proj-...

# Local (free, slower)
EMBEDDING_MODEL=sentence-transformers:all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
```

### Buffer Notes

| Variable | Default | Description |
|-----------|----------|-------------|
| `BUFFER_RETENTION_DAYS` | 7 | Days to keep processed buffer notes (0 = never delete) |

**Behavior**:
- `0`: Never delete processed buffer notes
- `>0`: Delete processed notes older than N days

### Markdown Export

| Variable | Default | Description |
|-----------|----------|-------------|
| `MARKDOWN_DIR` | ./data/notes | Directory for markdown exports |
| `MARKDOWN_EXPORT_AUTO` | true | Enable automatic markdown export |
| `MARKDOWN_EXPORT_INTERVAL` | 60 | Seconds between auto-export checks |

### Performance (Qdrant HNSW)

| Variable | Default | Description |
|-----------|----------|-------------|
| `HNSW_M` | 16 | Max connections per layer (higher = better recall, more memory) |
| `HNSW_EF_CONSTRUCTION` | 64 | Candidate list size during index build (higher = better recall, slower indexing) |
| `HNSW_EF` | 40 | Candidate list size during search (higher = better recall, slower search) |
| `INDEXING_THRESHOLD` | 20000 | Don't index until this many vectors |

**Tuning Guidelines**:

**For better recall** (at cost of performance):
```bash
HNSW_M=32
HNSW_EF_CONSTRUCTION=128
HNSW_EF=80
```

**For better performance** (at cost of recall):
```bash
HNSW_M=16
HNSW_EF_CONSTRUCTION=64
HNSW_EF=40
```

### Logging

| Variable | Default | Description |
|-----------|----------|-------------|
| `LOG_LEVEL` | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | json | Log format (json or text) |

**Examples**:
```bash
# Development
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Production
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Docker Configuration

### Docker Compose

```yaml
version: '3.8'

services:
  agents-memory:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./data/memory.db
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - EMBEDDING_MODEL=sentence-transformers:all-MiniLM-L6-v2
      - EMBEDDING_DIMENSION=384
      - BUFFER_RETENTION_DAYS=7
      - MARKDOWN_DIR=./data/notes
      - LOG_LEVEL=INFO
    volumes:
      - ./data:/app/data
    depends_on:
      - qdrant

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_storage:/qdrant/storage
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Development Configuration

### .env.example

```bash
# Copy this file to .env and fill in your values
cp .env.example .env
```

### Testing Configuration

```bash
# Use in-memory database
DATABASE_URL=sqlite:///:memory:

# Disable markdown export
MARKDOWN_EXPORT_AUTO=false

# Use local embeddings
EMBEDDING_MODEL=sentence-transformers:all-MiniLM-L6-v2
```

## Production Configuration

### Security

```bash
# Don't commit .env to git
echo ".env" >> .gitignore

# Use strong API keys
OPENAI_API_KEY=sk-proj-xxx...  # Generate from OpenAI dashboard
QDRANT_API_KEY=xxx...  # Generate from Qdrant Cloud (if using)

# Disable debug mode
DEBUG=false
LOG_LEVEL=INFO
```

### Performance

```bash
# Tune HNSW for your workload
HNSW_M=16
HNSW_EF=40

# Increase indexing threshold for large datasets
INDEXING_THRESHOLD=50000
```

### Backup Configuration

```bash
# Set backup paths
BACKUP_DIR=/backups
MARKDOWN_DIR=/exports/notes

# Configure retention
BUFFER_RETENTION_DAYS=30
```

## Troubleshooting

### Common Issues

**Qdrant Connection Failed**:
```bash
# Check if Qdrant is running
docker ps | grep qdrant

# Check connectivity
curl http://localhost:6333/health

# Check configuration
echo $QDRANT_HOST
echo $QDRANT_PORT
```

**Database Locked**:
```bash
# Check for multiple instances
ps aux | grep python

# Use WAL mode (automatically enabled)
PRAGMA journal_mode=WAL;
```

**Slow Embeddings**:
```bash
# Use local model instead of OpenAI
EMBEDDING_MODEL=sentence-transformers:all-MiniLM-L6-v2

# Increase parallelism
EMBEDDING_BATCH_SIZE=32
```

## Next Steps

1. Copy `.env.example` to `.env`
2. Fill in required values (especially OPENAI_API_KEY)
3. Review and adjust defaults based on your needs
4. Run the application: `uvicorn main:app --reload`
