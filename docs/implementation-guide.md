# Implementation Guide

Step-by-step implementation guide for AI Agent Memory System.

## Overview

This guide walks through implementing the AI Agent Memory System in phases.

**Prerequisites**:
- Python 3.11+
- Docker (for Qdrant)
- OpenAI API key (or use local embeddings)

**Architecture**:
- SQLite for structured data (notes, links, tags, buffer)
- Qdrant for vector embeddings
- FastAPI for REST API
- Bash scripts for human operations

## Phase 1: Project Setup

### 1.1 Initialize Project

```bash
# Create project directory
mkdir agents_memory
cd agents_memory

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Initialize git
git init
```

### 1.2 Create Project Structure

```bash
# Create directories
mkdir -p app/api app/models app/services app/db app/utils
mkdir -p scripts data/notes data/buffer data/backups
mkdir -p tests/test_api tests/test_services tests/test_utils
mkdir -p docs migrations/versions
mkdir -p scripts

# Create __init__.py files
touch app/__init__.py app/api/__init__.py app/models/__init__.py
touch app/services/__init__.py app/db/__init__.py app/utils/__init__.py
touch tests/__init__.py
```

### 1.3 Create requirements.txt

```bash
cat > requirements.txt << EOF
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.23
alembic==1.12.1

# Vector Database
qdrant-client==1.7.0

# Embeddings
openai==1.3.7
# OR local: sentence-transformers==2.2.2

# Utilities
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2

# Development
black==23.11.0
isort==5.12.0
mypy==1.7.1
EOF

pip install -r requirements.txt
```

### 1.4 Create .env.example

```bash
cat > .env.example << EOF
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
QDRANT_API_KEY=

# Embeddings
EMBEDDING_MODEL=openai:text-embedding-ada-002
EMBEDDING_DIMENSION=1536
OPENAI_API_KEY=sk-...

# Buffer Notes
BUFFER_RETENTION_DAYS=7

# Markdown Export
MARKDOWN_DIR=./data/notes
MARKDOWN_EXPORT_AUTO=true
MARKDOWN_EXPORT_INTERVAL=60

# Performance
HNSW_M=16
HNSW_EF_CONSTRUCTION=64
HNSW_EF=40
INDEXING_THRESHOLD=20000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF

cp .env.example .env
```

### 1.5 Create Docker Compose

```bash
cat > docker-compose.yml << EOF
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
EOF

cat > Dockerfile << EOF
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
```

## Phase 2: Database Models

### 2.1 Create SQLAlchemy Models (`app/models/database.py`)

```python
from sqlalchemy import Column, String, DateTime, Text, Boolean
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
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class RelationType(Base):
    __tablename__ = 'relation_types'
    id = Column(SqliteUUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)
    is_bidirectional = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Link(Base):
    __tablename__ = 'links'
    id = Column(SqliteUUID, primary_key=True, default=uuid.uuid4)
    source_id = Column(SqliteUUID, nullable=False)
    target_id = Column(SqliteUUID, nullable=False)
    relation_type_id = Column(SqliteUUID, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Tag(Base):
    __tablename__ = 'tags'
    id = Column(SqliteUUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class NoteTag(Base):
    __tablename__ = 'note_tags'
    note_id = Column(SqliteUUID, primary_key=True, nullable=False)
    tag_id = Column(SqliteUUID, primary_key=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class BufferNote(Base):
    __tablename__ = 'buffer_notes'
    id = Column(SqliteUUID, primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    metadata = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)

class Metadata(Base):
    __tablename__ = 'metadata'
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

### 2.2 Create Database Session (`app/db/session.py`)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.models.database import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/memory.db")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 2.3 Create Qdrant Client (`app/db/qdrant.py`)

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import os

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "notes_embeddings")

client = QdrantClient(url=f"http://{QDRANT_HOST}:{QDRANT_PORT}")

def init_qdrant():
    from app.utils.embeddings import get_embedding_dimension

    dimension = get_embedding_dimension()

    if not client.collection_exists(QDRANT_COLLECTION):
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE)
        )
```

## Phase 3: Pydantic Schemas

### 3.1 Create Request/Response Schemas (`app/models/schemas.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

class BufferNoteCreate(BaseModel):
    content: str
    metadata: Optional[dict] = None

class BufferNoteResponse(BaseModel):
    id: str
    content: str
    metadata: Optional[dict]
    created_at: datetime
    processed: bool

class NoteCreate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    tags: Optional[List[str]] = []

class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    summary: Optional[str]
    tags: List[str]
    created_at: datetime
    updated_at: datetime

class LinkCreate(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    description: Optional[str] = None

class LinkResponse(BaseModel):
    id: str
    source_id: str
    target_id: str
    relation_type_id: str
    description: Optional[str]
    created_at: datetime

class TagCreate(BaseModel):
    name: str

class TagResponse(BaseModel):
    id: str
    name: str
    created_at: datetime
```

## Phase 4: Core Services

### 4.1 Create Embedding Service (`app/services/embedding_service.py`)

```python
from app.db.qdrant import client, QDRANT_COLLECTION
from openai import OpenAI
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def generate_embedding(text: str) -> list[float]:
    """Generate embedding for text using OpenAI."""
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )
    return response.data[0].embedding

def upsert_embedding(note_id: str, vector: list[float], payload: dict):
    """Insert or update vector in Qdrant."""
    from qdrant_client.models import PointStruct

    point = PointStruct(
        id=note_id,
        vector=vector,
        payload=payload
    )

    client.upsert(collection_name=QDRANT_COLLECTION, points=[point])

def search_embeddings(query_vector: list[float], limit: int = 10, filter: dict = None):
    """Search similar notes using vector similarity."""
    from qdrant_client.models import Filter

    search_filter = Filter(must=[filter]) if filter else None

    results = client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=query_vector,
        query_filter=search_filter,
        limit=limit
    )

    return results
```

### 4.2 Create Note Service (`app/services/note_service.py`)

```python
from app.models.database import Note
from sqlalchemy.orm import Session
from app.services.embedding_service import generate_embedding, upsert_embedding, search_embeddings
from datetime import datetime
import uuid

def create_note(db: Session, note_data: dict) -> Note:
    """Create note with embedding."""
    note = Note(
        id=str(uuid.uuid4()),
        title=note_data["title"],
        content=note_data["content"],
        summary=note_data.get("summary"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    # Generate embedding
    embedding = generate_embedding(note.title + " " + note.content)

    # Upsert to Qdrant
    upsert_embedding(
        note_id=note.id,
        vector=embedding,
        payload={
            "title": note.title,
            "created_at": note.created_at.isoformat(),
            "updated_at": note.updated_at.isoformat(),
            "tags": note_data.get("tags", [])
        }
    )

    return note

def get_note(db: Session, note_id: str) -> Optional[Note]:
    """Get note by ID."""
    return db.query(Note).filter(Note.id == note_id).first()

def update_note(db: Session, note_id: str, note_data: dict) -> Optional[Note]:
    """Update note with new embedding."""
    note = get_note(db, note_id)
    if not note:
        return None

    if "title" in note_data:
        note.title = note_data["title"]
    if "content" in note_data:
        note.content = note_data["content"]
    if "summary" in note_data:
        note.summary = note_data["summary"]

    note.updated_at = datetime.utcnow()

    db.commit()

    # Regenerate embedding
    embedding = generate_embedding(note.title + " " + note.content)

    # Update in Qdrant
    upsert_embedding(
        note_id=note.id,
        vector=embedding,
        payload={
            "title": note.title,
            "created_at": note.created_at.isoformat(),
            "updated_at": note.updated_at.isoformat(),
            "tags": note_data.get("tags", [])
        }
    )

    return note

def delete_note(db: Session, note_id: str) -> bool:
    """Delete note and vector."""
    note = get_note(db, note_id)
    if not note:
        return False

    db.delete(note)
    db.commit()

    # Delete from Qdrant
    from qdrant_client.models import Filter

    client.delete(
        collection_name=QDRANT_COLLECTION,
        points_selector=[note_id]
    )

    return True
```

### 4.3 Create Buffer Service (`app/services/buffer_service.py`)

```python
from app.models.database import BufferNote
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

def add_to_buffer(db: Session, content: str, metadata: dict = None) -> BufferNote:
    """Add note to buffer (no embedding)."""
    note = BufferNote(
        id=str(uuid.uuid4()),
        content=content,
        metadata=str(metadata) if metadata else None,
        created_at=datetime.utcnow(),
        processed=False
    )

    db.add(note)
    db.commit()
    db.refresh(note)

    return note

def get_unprocessed_buffer(db: Session) -> list[BufferNote]:
    """Get all unprocessed buffer notes."""
    return db.query(BufferNote).filter(BufferNote.processed == False).all()

def mark_processed(db: Session, buffer_note_id: str) -> bool:
    """Mark buffer note as processed."""
    note = db.query(BufferNote).filter(BufferNote.id == buffer_note_id).first()
    if not note:
        return False

    note.processed = True
    db.commit()

    return True

def delete_old_processed(db: Session, days: int) -> int:
    """Delete processed buffer notes older than N days."""
    from datetime import timedelta

    cutoff = datetime.utcnow() - timedelta(days=days)

    deleted = db.query(BufferNote).filter(
        BufferNote.processed == True,
        BufferNote.created_at < cutoff
    ).delete()

    db.commit()

    return deleted
```

## Phase 5: API Routes

### 5.1 Create Main Application (`main.py`)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.session import init_db
from app.db.qdrant import init_qdrant
import uvicorn

app = FastAPI(title="AI Agent Memory System")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize databases
@app.on_event("startup")
async def startup_event():
    init_db()
    init_qdrant()

# Health check
@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 5.2 Create Buffer Routes (`app/api/buffer.py`)

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.schemas import BufferNoteCreate, BufferNoteResponse
from app.services.buffer_service import add_to_buffer, get_unprocessed_buffer, mark_processed

router = APIRouter(prefix="/api/buffer", tags=["buffer"])

@router.post("/", response_model=BufferNoteResponse)
def create_buffer_note(
    note: BufferNoteCreate,
    db: Session = Depends(get_db)
):
    buffer_note = add_to_buffer(db, note.content, note.metadata)
    return buffer_note

@router.get("/", response_model=list[BufferNoteResponse])
def list_buffer_notes(
    processed: bool = None,
    db: Session = Depends(get_db)
):
    query = db.query(BufferNote)

    if processed is not None:
        query = query.filter(BufferNote.processed == processed)

    notes = query.all()
    return notes

@router.post("/{note_id}/process")
def mark_as_processed(
    note_id: str,
    db: Session = Depends(get_db)
):
    mark_processed(db, note_id)
    return {"message": "Marked as processed"}
```

### 5.3 Create Note Routes (`app/api/notes.py`)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.schemas import NoteCreate, NoteResponse
from app.services.note_service import create_note, get_note, update_note, delete_note

router = APIRouter(prefix="/api/notes", tags=["notes"])

@router.post("/", response_model=NoteResponse)
def create_note_endpoint(
    note: NoteCreate,
    db: Session = Depends(get_db)
):
    new_note = create_note(db, note.dict())
    return new_note

@router.get("/{note_id}", response_model=NoteResponse)
def get_note_endpoint(
    note_id: str,
    db: Session = Depends(get_db)
):
    note = get_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note
```

## Phase 6: Bash Scripts

### 6.1 Create export-notes.sh

```bash
#!/bin/bash
set -e

API_BASE="${API_BASE:-http://localhost:8000}"
OUTPUT_DIR="${OUTPUT_DIR:-./notes}"

mkdir -p "$OUTPUT_DIR"

echo "Exporting notes..."
response=$(curl -s "$API_BASE/api/notes")

echo "$response" | jq -r '.[] | @json' | while read -r note; do
    id=$(echo "$note" | jq -r '.id')
    title=$(echo "$note" | jq -r '.title')
    content=$(echo "$note" | jq -r '.content')
    created_at=$(echo "$note" | jq -r '.created_at')
    updated_at=$(echo "$note" | jq -r '.updated_at')
    tags=$(echo "$note" | jq -r '.tags | join(", ")')

    filename="$OUTPUT_DIR/${id}.md"
    cat > "$filename" << EOF
---
id: $id
title: $title
tags: [$tags]
created_at: $created_at
updated_at: $updated_at
---

# $title

$content
EOF

    echo "Exported: $title ($id)"
done

echo "Export complete!"
```

### 6.2 Make Scripts Executable

```bash
chmod +x scripts/*.sh
```

## Phase 7: Testing

### 7.1 Create Test Configuration (`tests/conftest.py`)

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import Base

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
```

### 7.2 Create API Test (`tests/test_api/test_notes.py`)

```python
import pytest
from fastapi.testclient import TestClient
from main import app
from sqlalchemy.orm import Session

client = TestClient(app)

def test_create_note(db: Session):
    response = client.post(
        "/api/notes",
        json={
            "title": "Test Note",
            "content": "Test content",
            "tags": ["test"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Note"
    assert "id" in data

def test_get_note(db: Session):
    # Create note first
    create_response = client.post(
        "/api/notes",
        json={"title": "Test", "content": "Content"}
    )
    note_id = create_response.json()["id"]

    # Get note
    response = client.get(f"/api/notes/{note_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == note_id
```

### 7.3 Run Tests

```bash
pytest tests/ -v
```

## Phase 8: Running the Application

### 8.1 Start Qdrant

```bash
docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
```

### 8.2 Start Application

```bash
# Development
uvicorn main:app --reload

# Production
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 8.3 Test API

```bash
# Health check
curl http://localhost:8000/api/health

# Create buffer note
curl -X POST http://localhost:8000/api/buffer \
  -H "Content-Type: application/json" \
  -d '{"content": "Test buffer note"}'

# Create permanent note
curl -X POST http://localhost:8000/api/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Note", "content": "Test content"}'

# Get notes
curl http://localhost:8000/api/notes
```

## Phase 9: Next Steps

After completing this implementation:

1. Add remaining API endpoints (search, links, tags)
2. Implement export/import functionality
3. Add admin endpoints (stats, cleanup)
4. Write comprehensive tests
5. Create Opencode tool wrapper
6. Write documentation for users

## Troubleshooting

### Qdrant Connection Issues

```bash
# Check Qdrant is running
curl http://localhost:6333/health

# Check firewall
netstat -tlnp | grep 6333
```

### Database Issues

```bash
# Check database file
ls -la data/memory.db

# Reset database
rm data/memory.db
```

### Import Errors

```bash
# Ensure all dependencies installed
pip install -r requirements.txt

# Check Python version
python --version  # Should be 3.11+
```

## Summary

This implementation guide provides:
- ✅ Complete project setup
- ✅ Database models and migrations
- ✅ Core services (notes, buffer, embeddings)
- ✅ API routes (buffer, notes)
- ✅ Bash scripts for human operations
- ✅ Testing setup

Next: Begin implementation starting with Phase 1!
