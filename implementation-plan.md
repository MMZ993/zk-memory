# Implementation Plan

## Phase 1: Memory System Core

1. **Setup project structure**
   - Python project with SQLite + vector DB
   - Choose vector DB (Chroma/Qdrant/pgvector with Postgres)

2. **Database schema implementation**
   - SQLite with SQLAlchemy ORM
   - Tables: notes, links, tags, note_tags
   - UUID primary keys, proper indexes

3. **Vector DB integration**
   - Store embeddings with note IDs
   - Semantic search functionality

4. **Memory operations**
   - CRUD operations for notes
   - Link creation/retrieval
   - Tag management
   - Atomic note splitting for large content

5. **Markdown sync system**
   - File watcher for markdown directory
   - Bidirectional sync (DB ↔ files)
   - Obsidian-compatible format (`[[note-id]]` for links)

## Phase 2: Agent Tool (FastAPI)

1. **REST API endpoints**
   - Notes CRUD
   - Search (semantic + metadata)
   - Link management
   - Tag operations

2. **ORM queries**
   - Abstract database operations
   - Transaction support

3. **Agent-friendly interface**
   - Simple JSON responses
   - Batch operations

## Key Decisions Needed

- Vector DB choice: Chroma (simple), Qdrant (lightweight), or pgvector with Postgres?
- Update strategy: `updated_at` column vs history records?
- Markdown sync approach: file watcher vs periodic check?
