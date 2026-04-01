# Implementation Guide

Step-by-step implementation guide for AI Agent Memory System.

## Overview

This guide walks through implementing the AI Agent Memory System in phases.

**Prerequisites**:
- Python 3.13+
- Docker (for Qdrant)
- Ollama with a local embedding model available

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
mkdir -p app/api app/models app/services app/db app/utils app/core
mkdir -p scripts data/notes data/buffer data/backups
mkdir -p tests/test_api tests/test_services tests/test_utils
mkdir -p docs migrations/versions

# Create __init__.py files
touch app/__init__.py app/api/__init__.py app/models/__init__.py
touch app/services/__init__.py app/db/__init__.py app/utils/__init__.py
touch app/core/__init__.py
touch tests/__init__.py
```

### 1.3 Define dependencies in pyproject.toml

```bash
cat > pyproject.toml << EOF
[project]
name = "agents-memory"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "python-multipart",
  "sqlalchemy",
  "alembic",
  "qdrant-client",
  "python-dotenv",
  "pydantic",
  "pydantic-settings",
  "httpx",
]

[dependency-groups]
dev = [
  "pytest",
  "pytest-asyncio",
  "black",
  "isort",
  "mypy",
]
EOF

uv sync
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
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768
OLLAMA_HOST=http://localhost:11434

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
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
COPY src/ src/
RUN uv sync --frozen --no-dev

COPY . .

RUN mkdir -p /app/data

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
```

### 1.6 Create Config Module (`app/core/config.py`)

Centralise all environment variable loading here. Every other module imports from this — no more scattered `os.getenv()` calls.

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "AI Agent Memory System"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = ""

    # Database
    database_url: str = "sqlite:///./data/memory.db"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "notes_embeddings"
    qdrant_api_key: str = ""

    # Embeddings
    embedding_model: str = "nomic-embed-text"
    embedding_dimension: int = 768
    embedding_mode: str = "sync"  # sync (block request) | async (return immediately, embed in background)
    ollama_host: str = "http://localhost:11434"

    # Buffer
    buffer_retention_days: int = 7

    # Markdown export
    markdown_dir: str = "./data/notes"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_file": ".env", "case_sensitive": False}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

## Phase 2: Database Models

### 2.1 Create SQLAlchemy Models (`app/models/database.py`)

```python
from sqlalchemy import Column, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
import uuid


class Base(DeclarativeBase):
    pass


def new_uuid() -> str:
    return str(uuid.uuid4())


class Note(Base):
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, default=new_uuid)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    synced = Column(Boolean, default=False, nullable=False)

    note_tags = relationship("NoteTag", back_populates="note", cascade="all, delete-orphan")


class RelationType(Base):
    __tablename__ = "relation_types"

    id = Column(String(36), primary_key=True, default=new_uuid)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_bidirectional = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Link(Base):
    __tablename__ = "links"

    id = Column(String(36), primary_key=True, default=new_uuid)
    source_id = Column(String(36), ForeignKey("notes.id"), nullable=False)
    target_id = Column(String(36), ForeignKey("notes.id"), nullable=False)
    relation_type_id = Column(String(36), ForeignKey("relation_types.id"), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(String(36), primary_key=True, default=new_uuid)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    note_tags = relationship("NoteTag", back_populates="tag")


class NoteTag(Base):
    __tablename__ = "note_tags"

    note_id = Column(String(36), ForeignKey("notes.id"), primary_key=True)
    tag_id = Column(String(36), ForeignKey("tags.id"), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    note = relationship("Note", back_populates="note_tags")
    tag = relationship("Tag", back_populates="note_tags")


class BufferNote(Base):
    __tablename__ = "buffer_notes"

    id = Column(String(36), primary_key=True, default=new_uuid)
    content = Column(Text, nullable=False)
    meta = Column(JSON, nullable=True)  # renamed from metadata to avoid SQLAlchemy reserved attr
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime, nullable=True)


class Metadata(Base):
    __tablename__ = "metadata"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

### 2.2 Create Database Session (`app/db/session.py`)

```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.models.database import Base
from app.core.config import get_settings

settings = get_settings()

# connect_args required for SQLite when used with FastAPI async context
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    # Create FTS5 virtual table and triggers for keyword search (not managed by SQLAlchemy)
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                note_id UNINDEXED,
                title,
                content
            )
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS notes_fts_insert AFTER INSERT ON notes BEGIN
                INSERT INTO notes_fts(note_id, title, content) VALUES (new.id, new.title, new.content);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS notes_fts_update AFTER UPDATE ON notes BEGIN
                DELETE FROM notes_fts WHERE note_id = old.id;
                INSERT INTO notes_fts(note_id, title, content) VALUES (new.id, new.title, new.content);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS notes_fts_delete AFTER DELETE ON notes BEGIN
                DELETE FROM notes_fts WHERE note_id = old.id;
            END
        """))
        conn.commit()


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
from app.core.config import get_settings

settings = get_settings()

client = QdrantClient(
    host=settings.qdrant_host,
    port=settings.qdrant_port,
    api_key=settings.qdrant_api_key or None,
)

QDRANT_COLLECTION = settings.qdrant_collection


def init_qdrant():
    if not client.collection_exists(QDRANT_COLLECTION):
        client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=settings.embedding_dimension,
                distance=Distance.COSINE,
            ),
        )
```

## Phase 3: Pydantic Schemas

### 3.1 Create Request/Response Schemas (`app/models/schemas.py`)

```python
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime


# ── Request schemas (no orm_mode needed) ──────────────────────────────────────

class BufferNoteCreate(BaseModel):
    content: str
    meta: Optional[dict] = None

class NoteCreate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    tags: Optional[List[str]] = []

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None

class LinkCreate(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    description: Optional[str] = None

class TagCreate(BaseModel):
    name: str

class SearchRequest(BaseModel):
    q: str
    search_type: str = "semantic"  # semantic | keyword | hybrid | graph
    tags: Optional[List[str]] = None
    limit: int = 10
    graph_depth: int = 1
    graph_start_id: Optional[str] = None


# ── Response schemas (from_attributes=True for SQLAlchemy ORM compat) ─────────

class BufferNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    meta: Optional[dict] = None
    created_at: datetime
    processed: bool

class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    content: str
    summary: Optional[str] = None
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def extract_tags(cls, v):
        """Handle SQLAlchemy NoteTag relationship or plain list."""
        if isinstance(v, list) and v and hasattr(v[0], "tag"):
            return [nt.tag.name for nt in v]
        return v or []

class LinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    target_id: str
    relation_type_id: str
    description: Optional[str] = None
    created_at: datetime

class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime
```

## Phase 4: Core Services

### 4.1 Create Embedding Service (`app/services/embedding_service.py`)

```python
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchAny
import httpx

from app.db.qdrant import client, QDRANT_COLLECTION
from app.core.config import get_settings

settings = get_settings()
async def generate_embedding(text: str) -> list[float]:
    """Generate embedding using local Ollama."""
    return await _generate_ollama_embedding(text)


async def _generate_ollama_embedding(text: str) -> list[float]:
    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(
            f"{settings.ollama_host}/api/embeddings",
            json={"model": settings.embedding_model, "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]


async def upsert_embedding(note_id: str, vector: list[float], payload: dict):
    """Insert or update a vector in Qdrant."""
    client.upsert(
        collection_name=QDRANT_COLLECTION,
        points=[PointStruct(id=note_id, vector=vector, payload=payload)],
    )


async def search_embeddings(
    query_vector: list[float],
    limit: int = 10,
    tag_filter: list[str] | None = None,
):
    """Search similar notes by vector similarity, optionally filtered by tags."""
    search_filter = None
    if tag_filter:
        search_filter = Filter(
            must=[FieldCondition(key="tags", match=MatchAny(any=tag_filter))]
        )

    return client.search(
        collection_name=QDRANT_COLLECTION,
        query_vector=query_vector,
        query_filter=search_filter,
        limit=limit,
    )
```

### 4.2 Create Note Service (`app/services/note_service.py`)

```python
from typing import Optional
from datetime import datetime
import uuid

from sqlalchemy.orm import Session

from app.models.database import Note, Tag, NoteTag
from app.db.qdrant import client, QDRANT_COLLECTION
from app.services.embedding_service import generate_embedding, upsert_embedding


# ── Tag helpers ───────────────────────────────────────────────────────────────

def _get_tag_names(db: Session, note_id: str) -> list[str]:
    return [
        row.name
        for row in db.query(Tag)
        .join(NoteTag, Tag.id == NoteTag.tag_id)
        .filter(NoteTag.note_id == note_id)
        .all()
    ]


def _save_tags(db: Session, note_id: str, tag_names: list[str]):
    """Upsert tags and create NoteTag associations."""
    for name in tag_names:
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(id=str(uuid.uuid4()), name=name, created_at=datetime.utcnow())
            db.add(tag)
            db.flush()
        db.add(NoteTag(note_id=note_id, tag_id=tag.id, created_at=datetime.utcnow()))


# ── CRUD ──────────────────────────────────────────────────────────────────────

async def _embed_and_sync(db: Session, note: Note, tags: list[str]):
    """Generate embedding and mark note as synced. Used in both sync and async modes."""
    embedding = await generate_embedding(note.title + " " + note.content)
    await upsert_embedding(
        note_id=note.id,
        vector=embedding,
        payload={
            "title": note.title,
            "summary": note.summary,
            "created_at": note.created_at.isoformat(),
            "updated_at": note.updated_at.isoformat(),
            "tags": tags,
            "content_length": len(note.content),
        },
    )
    note.synced = True
    db.commit()


async def create_note(db: Session, note_data: dict, background_tasks=None) -> Note:
    """Create note in SQLite, then embed to Qdrant.

    Embedding mode is controlled by EMBEDDING_MODE env var:
    - sync (default): blocks the request until embedding is done, returns with synced=True
    - async: returns immediately with synced=False, embedding runs in background via background_tasks
    """
    note = Note(
        id=str(uuid.uuid4()),
        title=note_data["title"],
        content=note_data["content"],
        summary=note_data.get("summary"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        synced=False,
    )
    db.add(note)
    db.flush()  # assigns note.id without committing

    tags = note_data.get("tags", [])
    _save_tags(db, note.id, tags)
    db.commit()
    db.refresh(note)

    if settings.embedding_mode == "async" and background_tasks is not None:
        background_tasks.add_task(_embed_and_sync, db, note, tags)
    else:
        await _embed_and_sync(db, note, tags)

    return note


def get_note(db: Session, note_id: str) -> Optional[Note]:
    return db.query(Note).filter(Note.id == note_id).first()


async def update_note(db: Session, note_id: str, note_data: dict, background_tasks=None) -> Optional[Note]:
    """Update note fields and re-sync embedding to Qdrant.

    Respects EMBEDDING_MODE: sync blocks, async runs embedding in background.
    """
    note = get_note(db, note_id)
    if not note:
        return None

    for field in ("title", "content", "summary"):
        if field in note_data:
            setattr(note, field, note_data[field])

    note.updated_at = datetime.utcnow()
    note.synced = False

    if "tags" in note_data:
        db.query(NoteTag).filter(NoteTag.note_id == note_id).delete()
        tags = note_data["tags"]
        _save_tags(db, note.id, tags)
    else:
        tags = _get_tag_names(db, note_id)

    db.commit()

    if settings.embedding_mode == "async" and background_tasks is not None:
        background_tasks.add_task(_embed_and_sync, db, note, tags)
    else:
        await _embed_and_sync(db, note, tags)

    return note


def delete_note(db: Session, note_id: str) -> bool:
    """Delete note from SQLite and remove its vector from Qdrant."""
    note = get_note(db, note_id)
    if not note:
        return False

    db.query(NoteTag).filter(NoteTag.note_id == note_id).delete()
    db.delete(note)
    db.commit()

    from qdrant_client.models import PointIdsList
    client.delete(
        collection_name=QDRANT_COLLECTION,
        points_selector=PointIdsList(points=[note_id]),
    )
    return True


async def sync_unsynced_notes(db: Session, limit: int = 100) -> int:
    """Repair job: sync all notes where synced=False."""
    unsynced = db.query(Note).filter(Note.synced == False).limit(limit).all()
    for note in unsynced:
        try:
            tags = _get_tag_names(db, note.id)
            embedding = await generate_embedding(note.title + " " + note.content)
            await upsert_embedding(
                note_id=note.id,
                vector=embedding,
                payload={
                    "title": note.title,
                    "created_at": note.created_at.isoformat(),
                    "updated_at": note.updated_at.isoformat(),
                    "tags": tags,
                },
            )
            note.synced = True
        except Exception as e:
            print(f"Failed to sync note {note.id}: {e}")

    db.commit()
    return len(unsynced)
```

### 4.3 Create Buffer Service (`app/services/buffer_service.py`)

```python
from datetime import datetime, timedelta
import uuid

from sqlalchemy.orm import Session

from app.models.database import BufferNote


def add_to_buffer(db: Session, content: str, meta: dict = None) -> BufferNote:
    """Add a note to the buffer (no embedding — fast write)."""
    note = BufferNote(
        id=str(uuid.uuid4()),
        content=content,
        meta=meta,  # JSON column handles dict storage natively
        created_at=datetime.utcnow(),
        processed=False,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def get_buffer_notes(
    db: Session,
    processed: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[BufferNote]:
    query = db.query(BufferNote)
    if processed is not None:
        query = query.filter(BufferNote.processed == processed)
    return query.offset(offset).limit(limit).all()


def mark_processed(db: Session, buffer_note_id: str) -> bool:
    """Mark a buffer note as processed (agent calls this after consolidation)."""
    note = db.query(BufferNote).filter(BufferNote.id == buffer_note_id).first()
    if not note:
        return False
    note.processed = True
    db.commit()
    return True


def delete_old_processed(db: Session, days: int) -> int:
    """Cleanup: delete processed buffer notes older than N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    deleted = db.query(BufferNote).filter(
        BufferNote.processed == True,
        BufferNote.created_at < cutoff,
    ).delete()
    db.commit()
    return deleted
```

### 4.4 Create Search Service (`app/services/search_service.py`)

```python
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.database import Note, Tag, NoteTag, Link
from app.services.embedding_service import generate_embedding, search_embeddings


async def search_semantic(
    db: Session,
    query: str,
    limit: int = 10,
    tags: list[str] | None = None,
) -> list[Note]:
    """Vector similarity search, optionally filtered by tags."""
    query_vector = await generate_embedding(query)
    results = await search_embeddings(query_vector, limit=limit, tag_filter=tags)
    note_ids = [r.id for r in results]
    scores = {r.id: r.score for r in results}
    notes = db.query(Note).filter(Note.id.in_(note_ids)).all()
    return sorted(notes, key=lambda n: scores.get(n.id, 0), reverse=True)


def search_keyword(db: Session, query: str, limit: int = 10) -> list[Note]:
    """Full-text search using SQLite FTS5. Results ranked by relevance."""
    from sqlalchemy import text
    # FTS5 MATCH uses the query string directly; quote it to handle special chars
    safe_query = query.replace('"', '""')
    sql = text("""
        SELECT n.id FROM notes n
        JOIN notes_fts fts ON n.id = fts.note_id
        WHERE notes_fts MATCH :q
        ORDER BY rank
        LIMIT :limit
    """)
    rows = db.execute(sql, {"q": f'"{safe_query}"', "limit": limit}).fetchall()
    note_ids = [r[0] for r in rows]
    if not note_ids:
        return []
    # Fetch full Note objects preserving rank order
    notes_map = {n.id: n for n in db.query(Note).filter(Note.id.in_(note_ids)).all()}
    return [notes_map[nid] for nid in note_ids if nid in notes_map]


def search_graph(db: Session, start_note_id: str, depth: int = 1) -> list[Note]:
    """BFS traversal of note relationships up to `depth` levels."""
    visited: set[str] = set()
    current_layer: set[str] = {start_note_id}
    result_ids: list[str] = []

    for _ in range(depth):
        if not current_layer:
            break
        next_layer: set[str] = set()
        for note_id in current_layer:
            if note_id in visited:
                continue
            visited.add(note_id)
            links = db.query(Link).filter(
                or_(Link.source_id == note_id, Link.target_id == note_id)
            ).all()
            for link in links:
                neighbor = link.target_id if link.source_id == note_id else link.source_id
                if neighbor not in visited:
                    next_layer.add(neighbor)
        result_ids.extend(next_layer)
        current_layer = next_layer

    return db.query(Note).filter(Note.id.in_(result_ids)).all()


async def search_hybrid(
    db: Session,
    query: str,
    limit: int = 10,
    tags: list[str] | None = None,
) -> list[Note]:
    """Merge semantic and keyword results, deduplicated, semantic results first."""
    semantic = await search_semantic(db, query, limit=limit, tags=tags)
    keyword = search_keyword(db, query, limit=limit)
    seen: set[str] = set()
    combined: list[Note] = []
    for note in semantic + keyword:
        if note.id not in seen:
            seen.add(note.id)
            combined.append(note)
    return combined[:limit]
```

### 4.5 Create FastAPI Dependencies (`app/api/deps.py`)

Central place for shared route dependencies — DB session, auth, pagination.

```python
from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.config import get_settings


def get_db():
    """Yield a SQLAlchemy session and close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_api_key(x_api_key: str = Header(default="")):
    """Reject requests when API_KEY is set and the header doesn't match."""
    settings = get_settings()
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def pagination(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return {"limit": limit, "offset": offset}
```

## Phase 5: API Routes

### 5.1 Create Main Application (`main.py`)

```python
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.session import init_db
from app.db.qdrant import init_qdrant

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Agent Memory System")
    init_db()
    init_qdrant()
    yield
    logger.info("Shutting down AI Agent Memory System")


app = FastAPI(
    title="AI Agent Memory System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers (add as implemented)
from app.api import buffer, notes  # noqa: E402
app.include_router(buffer.router)
app.include_router(notes.router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
```

**Note on authentication**: Use the `verify_api_key` dependency from `app/api/deps.py` directly on routes or routers that need protection, rather than a global middleware. This keeps `/api/health` always accessible and avoids middleware order issues:

```python
# Example: protect an entire router
router = APIRouter(dependencies=[Depends(verify_api_key)])
```

### 5.2 Create Buffer Routes (`app/api/buffer.py`)

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, pagination
from app.models.schemas import BufferNoteCreate, BufferNoteResponse
from app.services.buffer_service import add_to_buffer, get_buffer_notes, mark_processed

router = APIRouter(prefix="/api/buffer", tags=["buffer"])


@router.post("/", response_model=BufferNoteResponse, status_code=201)
def create_buffer_note(note: BufferNoteCreate, db: Session = Depends(get_db)):
    return add_to_buffer(db, note.content, note.meta)


@router.get("/", response_model=list[BufferNoteResponse])
def list_buffer_notes(
    processed: bool = None,
    page: dict = Depends(pagination),
    db: Session = Depends(get_db),
):
    return get_buffer_notes(db, processed=processed, **page)


@router.post("/{note_id}/process")
def mark_as_processed(note_id: str, db: Session = Depends(get_db)):
    if not mark_processed(db, note_id):
        raise HTTPException(status_code=404, detail="Buffer note not found")
    return {"message": "Marked as processed"}
```

### 5.3 Create Note Routes (`app/api/notes.py`)

```python
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, pagination
from app.models.schemas import NoteCreate, NoteUpdate, NoteResponse
from app.services.note_service import create_note, get_note, update_note, delete_note

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.post("/", response_model=NoteResponse, status_code=201)
async def create_note_endpoint(
    note: NoteCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return await create_note(db, note.model_dump(), background_tasks)


@router.get("/{note_id}", response_model=NoteResponse)
def get_note_endpoint(note_id: str, db: Session = Depends(get_db)):
    note = get_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note_endpoint(
    note_id: str,
    note: NoteUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    updated = await update_note(db, note_id, note.model_dump(exclude_none=True), background_tasks)
    if not updated:
        raise HTTPException(status_code=404, detail="Note not found")
    return updated


@router.delete("/{note_id}", status_code=204)
def delete_note_endpoint(note_id: str, db: Session = Depends(get_db)):
    if not delete_note(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
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
uv sync

# Check Python version
python --version  # Should be 3.13+
```

## Summary

This implementation guide provides:
- ✅ Complete project setup
- ✅ Database models and migrations
- ✅ Core services (notes, buffer, embeddings)
- ✅ API routes (buffer, notes)
- ✅ Bash scripts for human operations
- ✅ Testing setup
- ✅ Missing endpoints (Phase 10)

Next: Begin implementation starting with Phase 1!

---

## Phase 10: Missing Endpoints

Covers all endpoints listed in `IMPLEMENTATION_GAPS.md` that were absent from Phases 1–9.
Implement these after Phase 5 (core routes) is complete.

### 10.1 Add `list_notes` to `app/services/note_service.py`

```python
from sqlalchemy import asc, desc


def list_notes(
    db: Session,
    tags: list[str] | None = None,
    sort: str = "updated_at",
    order: str = "desc",
    limit: int = 20,
    offset: int = 0,
) -> list[Note]:
    query = db.query(Note)
    if tags:
        query = (
            query
            .join(NoteTag, Note.id == NoteTag.note_id)
            .join(Tag, NoteTag.tag_id == Tag.id)
            .filter(Tag.name.in_(tags))
            .distinct()
        )
    sort_col = Note.updated_at if sort == "updated_at" else Note.created_at
    order_fn = desc if order == "desc" else asc
    return query.order_by(order_fn(sort_col)).offset(offset).limit(limit).all()
```

### 10.2 Add `get_buffer_note` / `delete_buffer_note` to `app/services/buffer_service.py`

```python
from app.models.database import BufferNote


def get_buffer_note(db: Session, note_id: str) -> BufferNote | None:
    return db.query(BufferNote).filter(BufferNote.id == note_id).first()


def delete_buffer_note(db: Session, note_id: str) -> bool:
    note = get_buffer_note(db, note_id)
    if not note:
        return False
    db.delete(note)
    db.commit()
    return True
```

### 10.3 Create `app/services/tag_service.py`

```python
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.database import Tag, NoteTag
import uuid
from datetime import datetime


def list_tags(db: Session, limit: int = 100, offset: int = 0) -> list[tuple]:
    """Returns list of (Tag, note_count) tuples."""
    return (
        db.query(Tag, func.count(NoteTag.note_id).label("note_count"))
        .outerjoin(NoteTag, Tag.id == NoteTag.tag_id)
        .group_by(Tag.id)
        .order_by(Tag.name)
        .offset(offset)
        .limit(limit)
        .all()
    )


def create_tag(db: Session, name: str) -> Tag:
    existing = db.query(Tag).filter(Tag.name == name).first()
    if existing:
        return existing
    tag = Tag(id=str(uuid.uuid4()), name=name, created_at=datetime.utcnow())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def get_note_tags(db: Session, note_id: str) -> list[Tag]:
    return (
        db.query(Tag)
        .join(NoteTag, Tag.id == NoteTag.tag_id)
        .filter(NoteTag.note_id == note_id)
        .all()
    )


def add_tag_to_note(db: Session, note_id: str, tag_id: str) -> bool:
    """Returns False if association already exists."""
    exists = db.query(NoteTag).filter(
        NoteTag.note_id == note_id, NoteTag.tag_id == tag_id
    ).first()
    if exists:
        return False
    db.add(NoteTag(note_id=note_id, tag_id=tag_id, created_at=datetime.utcnow()))
    db.commit()
    return True


def remove_tag_from_note(db: Session, note_id: str, tag_id: str) -> bool:
    deleted = db.query(NoteTag).filter(
        NoteTag.note_id == note_id, NoteTag.tag_id == tag_id
    ).delete()
    db.commit()
    return deleted > 0
```

### 10.4 Create `app/services/relation_service.py`

```python
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.database import RelationType, Link
import uuid
from datetime import datetime


def list_relations(db: Session) -> list[tuple]:
    """Returns list of (RelationType, link_count) tuples."""
    return (
        db.query(RelationType, func.count(Link.id).label("link_count"))
        .outerjoin(Link, RelationType.id == Link.relation_type_id)
        .group_by(RelationType.id)
        .order_by(RelationType.name)
        .all()
    )


def get_relation(db: Session, relation_id: str) -> RelationType | None:
    return db.query(RelationType).filter(RelationType.id == relation_id).first()


def get_relation_by_name(db: Session, name: str) -> RelationType | None:
    return db.query(RelationType).filter(RelationType.name == name).first()


def create_relation(db: Session, data: dict) -> RelationType:
    if db.query(RelationType).filter(RelationType.name == data["name"]).first():
        raise HTTPException(status_code=409, detail="Relation type already exists")
    rt = RelationType(
        id=str(uuid.uuid4()),
        name=data["name"],
        description=data.get("description"),
        is_bidirectional=data.get("is_bidirectional", False),
        created_at=datetime.utcnow(),
    )
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


def update_relation(db: Session, relation_id: str, data: dict) -> RelationType | None:
    rt = get_relation(db, relation_id)
    if not rt:
        return None
    for field in ("name", "description", "is_bidirectional"):
        if field in data:
            setattr(rt, field, data[field])
    db.commit()
    db.refresh(rt)
    return rt


def delete_relation(db: Session, relation_id: str) -> bool:
    rt = get_relation(db, relation_id)
    if not rt:
        return False
    link_count = db.query(Link).filter(Link.relation_type_id == relation_id).count()
    if link_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {link_count} link(s) use this relation type",
        )
    db.delete(rt)
    db.commit()
    return True
```

### 10.5 Create `app/services/link_service.py`

```python
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException
from app.models.database import Link
from app.services.relation_service import get_relation_by_name, create_relation
import uuid
from datetime import datetime


def get_note_links(
    db: Session,
    note_id: str,
    direction: str = "all",
    limit: int = 50,
) -> list[Link]:
    query = db.query(Link)
    if direction == "outgoing":
        query = query.filter(Link.source_id == note_id)
    elif direction == "incoming":
        query = query.filter(Link.target_id == note_id)
    else:
        query = query.filter(or_(Link.source_id == note_id, Link.target_id == note_id))
    return query.limit(limit).all()


def create_link(db: Session, data: dict) -> Link:
    """Create link, auto-creating the relation type if it doesn't exist."""
    rt = get_relation_by_name(db, data["relation_type"])
    if not rt:
        rt = create_relation(db, {"name": data["relation_type"]})
    link = Link(
        id=str(uuid.uuid4()),
        source_id=data["source_id"],
        target_id=data["target_id"],
        relation_type_id=rt.id,
        description=data.get("description"),
        created_at=datetime.utcnow(),
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def delete_link(db: Session, link_id: str) -> bool:
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        return False
    db.delete(link)
    db.commit()
    return True
```

### 10.6 Create `app/services/export_service.py`

Export returns a ZIP of markdown files. Import reads a local directory of markdown files.

```python
import io
import os
import zipfile

from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.database import BufferNote, Note
from app.services.note_service import create_note
from app.utils.markdown import buffer_note_to_markdown, note_to_markdown, parse_markdown_note


def export_notes_zip(db: Session) -> StreamingResponse:
    return _notes_to_zip(db.query(Note).all(), filename="notes_export.zip")


def export_buffer_zip(db: Session) -> StreamingResponse:
    notes = db.query(BufferNote).all()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for note in notes:
            zf.writestr(f"{note.id}.md", buffer_note_to_markdown(note))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=buffer_export.zip"},
    )


def export_all_zip(db: Session) -> StreamingResponse:
    return _notes_to_zip(db.query(Note).all(), filename="all_export.zip")


def _notes_to_zip(notes: list[Note], filename: str) -> StreamingResponse:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for note in notes:
            safe_title = note.title.replace("/", "_")[:80]
            zf.writestr(f"{safe_title}_{note.id[:8]}.md", note_to_markdown(note))
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


async def import_from_directory(db: Session, directory: str) -> dict:
    success, errors = 0, []
    for fname in os.listdir(directory):
        if not fname.endswith(".md"):
            continue
        path = os.path.join(directory, fname)
        try:
            with open(path) as f:
                note_data = parse_markdown_note(f.read())
            await create_note(db, note_data)
            success += 1
        except Exception as e:
            errors.append({"file": fname, "error": str(e)})
    return {"imported": success, "errors": errors}
```

### 10.7 Create `app/utils/markdown.py`

```python
import re
from app.models.database import BufferNote, Note


def note_to_markdown(note: Note) -> str:
    tags_str = ", ".join(t.tag.name for t in note.note_tags) if note.note_tags else ""
    lines = [
        "---",
        f"id: {note.id}",
        f"title: {note.title}",
        f"tags: [{tags_str}]",
        f"created_at: {note.created_at.isoformat()}",
        f"updated_at: {note.updated_at.isoformat()}",
    ]
    if note.summary:
        lines.append(f"summary: {note.summary}")
    lines += ["---", "", f"# {note.title}", "", note.content]
    return "\n".join(lines)


def buffer_note_to_markdown(note: BufferNote) -> str:
    lines = [
        "---",
        f"id: {note.id}",
        f"created_at: {note.created_at.isoformat()}",
        f"processed: {note.processed}",
    ]
    if note.meta:
        lines.append(f"meta: {note.meta}")
    lines += ["---", "", note.content]
    return "\n".join(lines)


def parse_markdown_note(raw: str) -> dict:
    """Parse markdown with YAML frontmatter into a note_data dict for create_note()."""
    frontmatter, content = _split_frontmatter(raw)
    title = frontmatter.get("title", "Untitled")
    tags_raw = frontmatter.get("tags", "")
    if isinstance(tags_raw, list):
        tags = tags_raw
    else:
        tags = [t.strip() for t in re.sub(r"[\[\]]", "", str(tags_raw)).split(",") if t.strip()]
    # strip leading "# Title\n\n" added by note_to_markdown
    body = re.sub(rf"^#\s+{re.escape(title)}\s*\n+", "", content).strip()
    return {
        "title": title,
        "content": body,
        "summary": frontmatter.get("summary"),
        "tags": tags,
    }


def _split_frontmatter(raw: str) -> tuple[dict, str]:
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    fm: dict = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, parts[2].strip()
```

### 10.8 Create `app/services/admin_service.py`

The reembed job state is in-process memory — single process only. If you switch to multi-worker uvicorn, move state to a Redis key or the `metadata` table.

```python
import os
import shutil
from datetime import datetime

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.qdrant import QDRANT_COLLECTION, client, init_qdrant
from app.models.database import BufferNote, Link, Note, NoteTag, Tag

settings = get_settings()

# In-process reembed state — NOT safe for multi-worker deployments
_reembed_state: dict = {
    "status": "idle",
    "total": 0,
    "processed": 0,
    "failed": 0,
}


def get_stats(db: Session) -> dict:
    today = datetime.utcnow().date()
    top_tags = (
        db.query(Tag.name, func.count(NoteTag.note_id).label("c"))
        .join(NoteTag, Tag.id == NoteTag.tag_id)
        .group_by(Tag.id)
        .order_by(text("c DESC"))
        .limit(5)
        .all()
    )
    qdrant_info = client.get_collection(QDRANT_COLLECTION)
    return {
        "notes": {
            "total": db.query(Note).count(),
            "created_today": db.query(Note).filter(func.date(Note.created_at) == today).count(),
            "updated_today": db.query(Note).filter(func.date(Note.updated_at) == today).count(),
        },
        "links": {"total": db.query(Link).count()},
        "tags": {
            "total": db.query(Tag).count(),
            "most_used": [t.name for t in top_tags],
        },
        "buffer": {
            "total": db.query(BufferNote).count(),
            "unprocessed": db.query(BufferNote).filter(BufferNote.processed == False).count(),
            "processed": db.query(BufferNote).filter(BufferNote.processed == True).count(),
        },
        "vector_db": {
            "points_count": qdrant_info.points_count,
            "segments_count": qdrant_info.segments_count,
        },
    }


def get_config() -> dict:
    """Return non-sensitive config values (no API keys)."""
    return {
        "embedding_model": settings.embedding_model,
        "embedding_dimension": settings.embedding_dimension,
        "embedding_mode": settings.embedding_mode,
        "buffer_retention_days": settings.buffer_retention_days,
        "markdown_dir": settings.markdown_dir,
        "qdrant_host": settings.qdrant_host,
        "qdrant_port": settings.qdrant_port,
        "qdrant_collection": settings.qdrant_collection,
        "log_level": settings.log_level,
    }


def list_backups() -> list[dict]:
    backup_dir = "./data/backups"
    if not os.path.exists(backup_dir):
        return []
    backups = []
    for fname in sorted(os.listdir(backup_dir), reverse=True):
        if not fname.endswith(".db"):
            continue
        path = os.path.join(backup_dir, fname)
        stat = os.stat(path)
        backups.append({
            "backup_id": fname.replace(".db", ""),
            "sqlite_path": path,
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "size_mb": round(stat.st_size / 1024 / 1024, 2),
        })
    return backups


def create_backup() -> dict:
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_id = f"backup_{ts}"
    os.makedirs("./data/backups", exist_ok=True)
    src = settings.database_url.replace("sqlite:///", "").replace("./", "")
    dest = f"./data/backups/{backup_id}.db"
    shutil.copy2(src, dest)
    snapshot = client.create_snapshot(collection_name=QDRANT_COLLECTION)
    return {
        "backup_id": backup_id,
        "sqlite_path": dest,
        "qdrant_snapshot": snapshot.name,
        "created_at": datetime.utcnow().isoformat(),
    }


def restore_backup(backup_id: str) -> dict:
    path = f"./data/backups/{backup_id}.db"
    if not os.path.exists(path):
        return None
    dest = settings.database_url.replace("sqlite:///", "").replace("./", "")
    shutil.copy2(path, dest)
    return {"restored": backup_id}


def get_reembed_status() -> dict:
    state = _reembed_state.copy()
    state["progress_percent"] = (
        round(state["processed"] / state["total"] * 100) if state["total"] > 0 else 0
    )
    return state


async def start_reembed(db: Session):
    """Background task: purge Qdrant and regenerate all embeddings."""
    from app.services.embedding_service import generate_embedding, upsert_embedding
    from app.services.note_service import _build_qdrant_payload, _get_tag_names

    notes = db.query(Note).all()
    _reembed_state.update({"status": "in_progress", "total": len(notes), "processed": 0, "failed": 0})

    client.delete_collection(QDRANT_COLLECTION)
    init_qdrant()

    for note in notes:
        try:
            tags = _get_tag_names(db, note.id)
            vector = await generate_embedding(note.title + " " + note.content)
            await upsert_embedding(note.id, vector, _build_qdrant_payload(note, tags))
            note.synced = True
            _reembed_state["processed"] += 1
        except Exception:
            note.synced = False
            _reembed_state["failed"] += 1

    db.commit()
    _reembed_state["status"] = "complete"
```

### 10.9 Update `app/services/search_service.py` — graph depth cap

Add the constant and enforce it at the top of `search_graph`:

```python
# Hard cap: prevents runaway BFS on dense graphs.
# Callers may request lower depth (1 or 2) but never higher.
MAX_GRAPH_DEPTH = 3


def search_graph(db: Session, start_note_id: str, depth: int = 1) -> list[Note]:
    """BFS traversal up to `depth` levels, capped at MAX_GRAPH_DEPTH."""
    depth = min(depth, MAX_GRAPH_DEPTH)

    visited: set[str] = set()
    current_layer: set[str] = {start_note_id}
    result_ids: list[str] = []

    for _ in range(depth):
        if not current_layer:
            break
        next_layer: set[str] = set()
        for note_id in current_layer:
            if note_id in visited:
                continue
            visited.add(note_id)
            links = db.query(Link).filter(
                or_(Link.source_id == note_id, Link.target_id == note_id)
            ).all()
            for link in links:
                neighbor = link.target_id if link.source_id == note_id else link.source_id
                if neighbor not in visited:
                    next_layer.add(neighbor)
        result_ids.extend(next_layer)
        current_layer = next_layer

    return db.query(Note).filter(Note.id.in_(result_ids)).all()
```

### 10.10 Update `app/api/notes.py` — add missing routes

```python
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, pagination
from app.models.schemas import NoteCreate, NoteUpdate, NoteResponse, TagResponse, LinkResponse
from app.services.note_service import create_note, get_note, update_note, delete_note, list_notes
from app.services.tag_service import get_note_tags, add_tag_to_note, remove_tag_from_note
from app.services.link_service import get_note_links

router = APIRouter(prefix="/api/notes", tags=["notes"])


@router.post("/", response_model=NoteResponse, status_code=201)
async def create_note_endpoint(
    note: NoteCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return await create_note(db, note.model_dump(), background_tasks)


@router.get("/", response_model=list[NoteResponse])
def list_notes_endpoint(
    tags: str | None = Query(default=None, description="Comma-separated tag names"),
    sort: str = Query(default="updated_at", pattern="^(updated_at|created_at)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: dict = Depends(pagination),
    db: Session = Depends(get_db),
):
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    return list_notes(db, tags=tag_list, sort=sort, order=order, **page)


@router.get("/{note_id}", response_model=NoteResponse)
def get_note_endpoint(note_id: str, db: Session = Depends(get_db)):
    note = get_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note_endpoint(
    note_id: str,
    note: NoteUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    updated = await update_note(db, note_id, note.model_dump(exclude_none=True), background_tasks)
    if not updated:
        raise HTTPException(status_code=404, detail="Note not found")
    return updated


@router.delete("/{note_id}", status_code=204)
def delete_note_endpoint(note_id: str, db: Session = Depends(get_db)):
    if not delete_note(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")


@router.get("/{note_id}/links", response_model=list[LinkResponse])
def get_note_links_endpoint(
    note_id: str,
    direction: str = Query(default="all", pattern="^(all|incoming|outgoing)$"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    if not get_note(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return get_note_links(db, note_id, direction=direction, limit=limit)


@router.get("/{note_id}/tags", response_model=list[TagResponse])
def get_note_tags_endpoint(note_id: str, db: Session = Depends(get_db)):
    if not get_note(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return get_note_tags(db, note_id)


@router.post("/{note_id}/tags", status_code=201)
def add_tag_endpoint(note_id: str, body: dict, db: Session = Depends(get_db)):
    tag_id = body.get("tag_id")
    if not tag_id:
        raise HTTPException(status_code=422, detail="tag_id required")
    if not get_note(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    add_tag_to_note(db, note_id, tag_id)
    return {"message": "Tag added"}


@router.delete("/{note_id}/tags/{tag_id}", status_code=204)
def remove_tag_endpoint(note_id: str, tag_id: str, db: Session = Depends(get_db)):
    if not remove_tag_from_note(db, note_id, tag_id):
        raise HTTPException(status_code=404, detail="Tag association not found")
```

### 10.11 Update `app/api/buffer.py` — add get / delete / cleanup routes

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db, pagination
from app.core.config import get_settings
from app.models.schemas import BufferNoteCreate, BufferNoteResponse
from app.services.buffer_service import (
    add_to_buffer,
    delete_buffer_note,
    delete_old_processed,
    get_buffer_note,
    get_buffer_notes,
    mark_processed,
)

router = APIRouter(prefix="/api/buffer", tags=["buffer"])


@router.post("/", response_model=BufferNoteResponse, status_code=201)
def create_buffer_note(note: BufferNoteCreate, db: Session = Depends(get_db)):
    return add_to_buffer(db, note.content, note.meta)


@router.get("/", response_model=list[BufferNoteResponse])
def list_buffer_notes(
    processed: bool | None = None,
    page: dict = Depends(pagination),
    db: Session = Depends(get_db),
):
    return get_buffer_notes(db, processed=processed, **page)


# NOTE: /cleanup must be declared BEFORE /{note_id} or FastAPI will
# match "cleanup" as a note_id parameter.
@router.delete("/cleanup")
def cleanup_processed_notes(db: Session = Depends(get_db)):
    retention = get_settings().buffer_retention_days
    if retention == 0:
        return {"deleted": 0, "disabled": True}
    count = delete_old_processed(db, retention)
    return {"deleted": count}


@router.get("/{note_id}", response_model=BufferNoteResponse)
def get_buffer_note_endpoint(note_id: str, db: Session = Depends(get_db)):
    note = get_buffer_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Buffer note not found")
    return note


@router.delete("/{note_id}", status_code=204)
def delete_buffer_note_endpoint(note_id: str, db: Session = Depends(get_db)):
    if not delete_buffer_note(db, note_id):
        raise HTTPException(status_code=404, detail="Buffer note not found")


@router.post("/{note_id}/process")
def mark_as_processed(note_id: str, db: Session = Depends(get_db)):
    if not mark_processed(db, note_id):
        raise HTTPException(status_code=404, detail="Buffer note not found")
    return {"message": "Marked as processed"}
```

### 10.12 Create `app/api/tags.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, pagination
from app.models.schemas import TagCreate, TagResponse
from app.services.tag_service import create_tag, list_tags

router = APIRouter(prefix="/api/tags", tags=["tags"])


class TagWithCount(TagResponse):
    note_count: int = 0


@router.get("/", response_model=list[TagWithCount])
def list_tags_endpoint(page: dict = Depends(pagination), db: Session = Depends(get_db)):
    rows = list_tags(db, **page)
    results = []
    for tag, count in rows:
        item = TagWithCount.model_validate(tag)
        item.note_count = count
        results.append(item)
    return results


@router.post("/", response_model=TagResponse, status_code=201)
def create_tag_endpoint(body: TagCreate, db: Session = Depends(get_db)):
    return create_tag(db, body.name)
```

### 10.13 Create `app/api/relations.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.api.deps import get_db
from app.services.relation_service import (
    list_relations,
    create_relation,
    get_relation,
    update_relation,
    delete_relation,
)

router = APIRouter(prefix="/api/relations", tags=["relations"])


class RelationTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_bidirectional: bool = False


class RelationTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_bidirectional: Optional[bool] = None


class RelationTypeResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: str
    name: str
    description: Optional[str] = None
    is_bidirectional: bool
    created_at: datetime
    link_count: int = 0


@router.get("/", response_model=list[RelationTypeResponse])
def list_relations_endpoint(db: Session = Depends(get_db)):
    rows = list_relations(db)
    results = []
    for rt, count in rows:
        item = RelationTypeResponse.model_validate(rt)
        item.link_count = count
        results.append(item)
    return results


@router.post("/", response_model=RelationTypeResponse, status_code=201)
def create_relation_endpoint(body: RelationTypeCreate, db: Session = Depends(get_db)):
    rt = create_relation(db, body.model_dump())
    return RelationTypeResponse.model_validate(rt)


@router.get("/{relation_id}", response_model=RelationTypeResponse)
def get_relation_endpoint(relation_id: str, db: Session = Depends(get_db)):
    rt = get_relation(db, relation_id)
    if not rt:
        raise HTTPException(status_code=404, detail="Relation type not found")
    return RelationTypeResponse.model_validate(rt)


@router.patch("/{relation_id}", response_model=RelationTypeResponse)
def update_relation_endpoint(
    relation_id: str, body: RelationTypeUpdate, db: Session = Depends(get_db)
):
    rt = update_relation(db, relation_id, body.model_dump(exclude_none=True))
    if not rt:
        raise HTTPException(status_code=404, detail="Relation type not found")
    return RelationTypeResponse.model_validate(rt)


@router.delete("/{relation_id}", status_code=204)
def delete_relation_endpoint(relation_id: str, db: Session = Depends(get_db)):
    if not delete_relation(db, relation_id):
        raise HTTPException(status_code=404, detail="Relation type not found")
```

### 10.14 Create `app/api/export.py`

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db
from app.services.export_service import (
    export_all_zip,
    export_buffer_zip,
    export_notes_zip,
    import_from_directory,
)

router = APIRouter(tags=["export"])


class ImportRequest(BaseModel):
    directory: Optional[str] = "./data/notes"


@router.get("/api/export")
def export_all(db: Session = Depends(get_db)):
    return export_all_zip(db)


@router.get("/api/export/notes")
def export_notes(db: Session = Depends(get_db)):
    return export_notes_zip(db)


@router.get("/api/export/buffer")
def export_buffer(db: Session = Depends(get_db)):
    return export_buffer_zip(db)


@router.post("/api/import")
async def import_notes(body: ImportRequest, db: Session = Depends(get_db)):
    return await import_from_directory(db, body.directory)
```

### 10.15 Create `app/api/admin.py`

```python
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.api.deps import get_db
from app.services.admin_service import (
    create_backup,
    get_config,
    get_reembed_status,
    get_stats,
    list_backups,
    restore_backup,
    start_reembed,
)
from app.services.note_service import sync_unsynced_notes

router = APIRouter(tags=["admin"])

REEMBED_CONFIRM_PHRASE = "I understand this will delete and regenerate all embeddings"


class ReembedRequest(BaseModel):
    confirm: str


@router.get("/api/stats")
def stats_endpoint(db: Session = Depends(get_db)):
    return get_stats(db)


@router.get("/api/config")
def config_endpoint():
    return get_config()


@router.get("/api/admin/backups")
def list_backups_endpoint():
    return {"backups": list_backups()}


@router.post("/api/admin/backup")
def create_backup_endpoint():
    return create_backup()


@router.post("/api/admin/restore/{backup_id}")
def restore_backup_endpoint(backup_id: str):
    result = restore_backup(backup_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backup not found")
    return result


@router.post("/api/admin/reembed")
async def reembed_endpoint(
    body: ReembedRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if body.confirm != REEMBED_CONFIRM_PHRASE:
        raise HTTPException(status_code=400, detail=f"confirm must be: '{REEMBED_CONFIRM_PHRASE}'")
    from app.services.admin_service import _reembed_state
    if _reembed_state["status"] == "in_progress":
        raise HTTPException(status_code=409, detail="Re-embed job already running")
    pending = db.query(__import__("app.models.database", fromlist=["Note"]).Note).count()
    background_tasks.add_task(start_reembed, db)
    return {"status": "started", "total_notes": pending}


@router.get("/api/admin/reembed/status")
def reembed_status_endpoint():
    return get_reembed_status()


@router.post("/api/admin/sync-embeddings")
async def sync_embeddings_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    from app.models.database import Note
    pending = db.query(Note).filter(Note.synced == False).count()
    background_tasks.add_task(sync_unsynced_notes, db)
    return {"status": "started", "pending_notes": pending}
```

### 10.16 Update `main.py` — wire all new routers

```python
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.session import init_db
from app.db.qdrant import init_qdrant

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Agent Memory System")
    init_db()
    init_qdrant()
    yield
    logger.info("Shutting down AI Agent Memory System")


app = FastAPI(
    title="AI Agent Memory System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import buffer, notes, tags, relations, export, admin  # noqa: E402

app.include_router(buffer.router)
app.include_router(notes.router)
app.include_router(tags.router)
app.include_router(relations.router)
app.include_router(export.router)
app.include_router(admin.router)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


if __name__ == "__main__":
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
```
