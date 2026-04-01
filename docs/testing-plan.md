# Testing Plan

Comprehensive testing strategy for AI Agent Memory System.

## Overview

This document outlines the testing approach, coverage goals, and test cases for the AI Agent Memory System.

## Testing Strategy

### 1. Unit Tests

Test individual functions and classes in isolation.

**Scope**:
- All service layer functions
- Utility functions
- Database model methods
- Embedding generation (mocked)

**Tools**: pytest, pytest-asyncio, unittest.mock

**Coverage Goal**: 80%+

### 2. Integration Tests

Test the full stack against a real running API (not in-process).

**Scope**:
- All API endpoints over real HTTP
- Real SQLite database, real Qdrant, real Ollama embeddings
- Semantic search quality (paraphrased queries)
- Keyword / FTS5 / graph / hybrid search correctness
- Buffer note lifecycle

**Tools**: pytest, httpx, docker-compose.test.yml

**Stack**: `agents-memory-test` (port 8001) + `qdrant-test` (port 6334) + host Ollama

**Run**:
```bash
make test-integration
# or manually:
docker compose -f docker-compose.test.yml up -d --build
INTEGRATION_TESTS=1 uv run pytest tests/integration/ -v
docker compose -f docker-compose.test.yml down -v
```

**Coverage Goal**: All API endpoints, all search modes

### 3. End-to-End Tests

Test complete user workflows.

**Scope**:
- Note creation → embedding → search
- Buffer add → process → note creation
- Markdown export → edit → sync
- Backup → restore
- Re-embed all notes

**Tools**: pytest, TestClient, docker-compose

**Coverage Goal**: All documented workflows

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── test_utils/
│   ├── test_embeddings.py     # Embedding utils
│   └── test_markdown.py       # Markdown parsing
├── test_services/
│   ├── test_note_service.py   # Note CRUD
│   ├── test_buffer_service.py # Buffer operations
│   ├── test_link_service.py   # Link management
│   ├── test_tag_service.py    # Tag operations
│   ├── test_search_service.py # Search (semantic, keyword, graph)
│   └── test_sync_service.py   # Cross-DB sync
├── test_api/
│   ├── test_buffer.py         # Buffer endpoints
│   ├── test_notes.py          # Note endpoints
│   ├── test_links.py          # Link endpoints
│   ├── test_tags.py           # Tag endpoints
│   ├── test_relations.py      # Relation type endpoints
│   ├── test_search.py         # Search endpoints
│   ├── test_export.py         # Export/import
│   └── test_admin.py          # Admin endpoints
└── test_e2e/
    ├── test_note_workflow.py  # Note lifecycle
    ├── test_buffer_workflow.py # Buffer to note
    ├── test_search_workflow.py # Search variations
    ├── test_backup_workflow.py # Backup/restore
    └── test_reembed_workflow.py # Model switching
```

## Test Fixtures (`tests/conftest.py`)

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from main import app
from app.models.database import Base
import tempfile
import os

# Test database (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    """Test client with database session."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def sample_note():
    """Sample note data for testing."""
    return {
        "title": "Test Note",
        "content": "This is test content for embedding.",
        "summary": "Test summary",
        "tags": ["test", "example"]
    }

@pytest.fixture
def mock_embedding():
    """Mock embedding vector."""
    return [0.1] * 1536  # Mock 1536-dimensional vector
```

## Unit Test Examples

### Test Note Service

```python
# tests/test_services/test_note_service.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.note_service import create_note, get_note

@pytest.mark.asyncio
async def test_create_note(db, sample_note):
    """Test note creation."""
    # Mock embedding generation
    with patch('app.services.note_service.generate_embedding', new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1] * 1536

        with patch('app.services.note_service.upsert_embedding', new_callable=AsyncMock) as mock_upsert:
            note = await create_note(db, sample_note)

            assert note.id is not None
            assert note.title == "Test Note"
            assert note.content == "This is test content for embedding."
            assert note.synced is True
            mock_embed.assert_called_once()
            mock_upsert.assert_called_once()

def test_get_note(db):
    """Test note retrieval."""
    # Create note first
    from app.models.database import Note
    from datetime import datetime
    import uuid

    note_id = str(uuid.uuid4())
    note = Note(
        id=note_id,
        title="Test",
        content="Content",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        synced=True
    )
    db.add(note)
    db.commit()

    # Retrieve
    retrieved = get_note(db, note_id)
    assert retrieved is not None
    assert retrieved.title == "Test"
    assert retrieved.id == note_id
```

### Test Sync Service

```python
# tests/test_services/test_sync_service.py
import pytest
from app.services.note_service import sync_unsynced_notes

@pytest.mark.asyncio
async def test_sync_unsynced_notes(db, sample_note):
    """Test syncing of unsynced notes."""
    # Create unsynced notes
    from app.models.database import Note
    from datetime import datetime
    import uuid

    for i in range(3):
        note = Note(
            id=str(uuid.uuid4()),
            title=f"Unsynced Note {i}",
            content=f"Content {i}",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            synced=False
        )
        db.add(note)
    db.commit()

    # Mock embedding
    with patch('app.services.note_service.generate_embedding', new_callable=AsyncMock) as mock_embed:
        mock_embed.return_value = [0.1] * 1536

        with patch('app.services.note_service.upsert_embedding', new_callable=AsyncMock) as mock_upsert:
            count = await sync_unsynced_notes(db)

            assert count == 3

            # Verify all are now synced
            unsynced = db.query(Note).filter(Note.synced == False).all()
            assert len(unsynced) == 0

            # Verify embedding was called for each
            assert mock_embed.call_count == 3
```

## Integration Test Examples

### Test Note API

```python
# tests/test_api/test_notes.py
import pytest

def test_create_note(client, sample_note):
    """Test creating a note via API."""
    # Mock embedding service
    with patch('app.services.embedding_service.generate_embedding', return_value=[0.1] * 1536):
        with patch('app.services.embedding_service.upsert_embedding'):
            response = client.post("/api/notes", json=sample_note)

            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Test Note"
            assert "id" in data
            assert data["synced"] is True

def test_get_note(client, db, sample_note):
    """Test getting a note via API."""
    # Create note first
    with patch('app.services.embedding_service.generate_embedding', return_value=[0.1] * 1536):
        with patch('app.services.embedding_service.upsert_embedding'):
            create_response = client.post("/api/notes", json=sample_note)
            note_id = create_response.json()["id"]

    # Get note
    response = client.get(f"/api/notes/{note_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == note_id
    assert data["title"] == "Test Note"

def test_update_note(client, db, sample_note):
    """Test updating a note via API."""
    # Create note
    with patch('app.services.embedding_service.generate_embedding', return_value=[0.1] * 1536):
        with patch('app.services.embedding_service.upsert_embedding'):
            create_response = client.post("/api/notes", json=sample_note)
            note_id = create_response.json()["id"]

    # Update note
    update_data = {"title": "Updated Title"}
    with patch('app.services.embedding_service.generate_embedding', return_value=[0.2] * 1536):
        with patch('app.services.embedding_service.upsert_embedding'):
            response = client.put(f"/api/notes/{note_id}", json=update_data)

            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Updated Title"
            assert data["synced"] is True

def test_delete_note(client, db, sample_note):
    """Test deleting a note via API."""
    # Create note
    with patch('app.services.embedding_service.generate_embedding', return_value=[0.1] * 1536):
        with patch('app.services.embedding_service.upsert_embedding'):
            create_response = client.post("/api/notes", json=sample_note)
            note_id = create_response.json()["id"]

    # Delete note
    with patch('app.services.embedding_service.client.delete'):
        response = client.delete(f"/api/notes/{note_id}")

        assert response.status_code == 200

    # Verify deletion
    response = client.get(f"/api/notes/{note_id}")
    assert response.status_code == 404
```

### Test Search API

```python
# tests/test_api/test_search.py
import pytest

def test_semantic_search(client, db):
    """Test semantic search."""
    # Create notes
    notes = [
        {"title": "Python Programming", "content": "Python is a programming language"},
        {"title": "Machine Learning", "content": "ML is a subset of AI"},
        {"title": "Data Science", "content": "Data analysis and visualization"}
    ]

    for note in notes:
        with patch('app.services.embedding_service.generate_embedding', return_value=[0.1] * 1536):
            with patch('app.services.embedding_service.upsert_embedding'):
                client.post("/api/notes", json=note)

    # Search
    with patch('app.services.embedding_service.search_embeddings', return_value=[
        {"id": "mock-id-1", "score": 0.95, "payload": {"title": "Python Programming"}}
    ]):
        response = client.get("/api/notes/search?q=programming&search_type=semantic")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0

def test_keyword_search(client, db):
    """Test keyword search."""
    # Create notes
    notes = [
        {"title": "Python Programming", "content": "Python is great"},
        {"title": "JavaScript", "content": "JS is also popular"}
    ]

    for note in notes:
        with patch('app.services.embedding_service.generate_embedding', return_value=[0.1] * 1536):
            with patch('app.services.embedding_service.upsert_embedding'):
                client.post("/api/notes", json=note)

    # Search
    response = client.get("/api/notes/search?q=Python&search_type=keyword")

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) > 0
    assert "Python" in data["results"][0]["title"]

def test_graph_search(client, db):
    """Test graph search (connected notes)."""
    # Create notes with links
    with patch('app.services.embedding_service.generate_embedding', return_value=[0.1] * 1536):
        with patch('app.services.embedding_service.upsert_embedding'):
            note1 = client.post("/api/notes", json={"title": "Note 1", "content": "Content 1"}).json()
            note2 = client.post("/api/notes", json={"title": "Note 2", "content": "Content 2"}).json()

    # Create link
    client.post("/api/notes/links", json={
        "source_id": note1["id"],
        "target_id": note2["id"],
        "relation_type": "related_to"
    })

    # Graph search
    response = client.get(f"/api/notes/search?search_type=graph&graph_start_id={note1['id']}&graph_depth=2")

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) > 0
```

## End-to-End Test Examples

### Test Note Workflow

```python
# tests/test_e2e/test_note_workflow.py
import pytest
import tempfile
import os

@pytest.mark.e2e
def test_complete_note_workflow(client, db):
    """Test complete note lifecycle: create, search, export, sync."""
    # 1. Create note
    note_data = {
        "title": "E2E Test Note",
        "content": "Testing complete workflow",
        "tags": ["e2e", "test"]
    }

    with patch('app.services.embedding_service.generate_embedding', return_value=[0.1] * 1536):
        with patch('app.services.embedding_service.upsert_embedding'):
            create_response = client.post("/api/notes", json=note_data)
            note_id = create_response.json()["id"]

    # 2. Get note
    response = client.get(f"/api/notes/{note_id}")
    assert response.status_code == 200
    note = response.json()

    # 3. Search note
    with patch('app.services.embedding_service.search_embeddings', return_value=[
        {"id": note_id, "score": 0.95, "payload": {"title": note["title"]}}
    ]):
        response = client.get(f"/api/notes/search?q=workflow&search_type=semantic")
        assert response.status_code == 200
        results = response.json()["results"]
        assert any(r["id"] == note_id for r in results)

    # 4. Export note
    response = client.get("/api/export/notes")
    assert response.status_code == 200

    # 5. Verify note in export
    # (Implementation depends on export format)

    print("✅ Complete note workflow passed")
```

### Test Backup Workflow

```python
# tests/test_e2e/test_backup_workflow.py
import pytest

@pytest.mark.e2e
def test_backup_restore_workflow(client, db):
    """Test backup and restore workflow."""
    # Create notes
    with patch('app.services.embedding_service.generate_embedding', return_value=[0.1] * 1536):
        with patch('app.services.embedding_service.upsert_embedding'):
            client.post("/api/notes", json={"title": "Backup Test 1", "content": "Content 1"})
            client.post("/api/notes", json={"title": "Backup Test 2", "content": "Content 2"})

    # Create backup
    with patch('app.services.backup_service.create_sqlite_backup', return_value="backup.db"):
        with patch('app.services.backup_service.create_qdrant_snapshot', return_value="snapshot-name"):
            response = client.post("/api/admin/backup")
            assert response.status_code == 200
            backup_id = response.json()["backup_id"]

    # List backups
    response = client.get("/api/admin/backups")
    assert response.status_code == 200
    backups = response.json()["backups"]
    assert any(b["backup_id"] == backup_id for b in backups)

    # Restore backup
    with patch('app.services.backup_service.restore_sqlite_backup'):
        with patch('app.services.backup_service.restore_qdrant_snapshot'):
            response = client.post(f"/api/admin/restore/{backup_id}")
            assert response.status_code == 200

    print("✅ Backup/restore workflow passed")
```

## Running Tests

### Run All Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=app --cov-report=html

# Run specific test file
uv run pytest tests/test_api/test_notes.py -v

# Run specific test
uv run pytest tests/test_api/test_notes.py::test_create_note -v
```

### Run by Category

```bash
# Unit tests only
uv run pytest tests/test_utils/ tests/test_services/ -v

# Integration tests only
uv run pytest tests/test_api/ -v

# E2E tests only
uv run pytest tests/test_e2e/ -v -m e2e

# Fast tests (skip slow ones)
uv run pytest tests/ -m "not slow"
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - uses: astral-sh/setup-uv@v6

      - name: Install dependencies
        run: |
          uv sync --frozen

      - name: Run tests
        env:
          EMBEDDING_PROVIDER=openai
          OPENAI_API_KEY=test-key
        run: |
          uv run pytest tests/ --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Test Coverage Goals

| Component | Target Coverage | Status |
|-----------|----------------|--------|
| Services | 90%+ | 📋 |
| API Routes | 80%+ | 📋 |
| Utils | 85%+ | 📋 |
| Overall | 80%+ | 📋 |

## Mock Strategy

### Embedding Service

Always mock in unit and integration tests:
```python
with patch('app.services.embedding_service.generate_embedding', return_value=[0.1] * 1536):
    # Test code
```

### Qdrant Client

Mock in unit tests, use real in integration tests with test collection:
```python
# Unit test
with patch('app.services.embedding_service.client.upsert'):
    # Test code

# Integration test - use test collection
os.environ['QDRANT_COLLECTION'] = 'test_embeddings'
```

### External APIs

Always mock:
```python
with patch('httpx.AsyncClient.post') as mock_post:
    mock_post.return_value = mock_response
    # Test code
```

## Performance Testing

### Load Testing

```bash
# Use locust
locust -f tests/load_tests/notes_api.py --host=http://localhost:8000
```

### Benchmarks

```python
# tests/benchmarks/embedding_benchmark.py
import pytest
import time

@pytest.mark.benchmark
def test_embedding_generation_speed():
    """Benchmark embedding generation."""
    start = time.time()

    for _ in range(100):
        embedding = await generate_embedding("test content")

    elapsed = time.time() - start
    assert elapsed < 10  # Should complete 100 embeddings in <10s
```

## Test Data Management

### Fixtures for Test Data

```python
# tests/fixtures/notes.py
SAMPLE_NOTES = [
    {
        "title": "Neural Networks",
        "content": "Neural networks are computing systems inspired by biological neural networks.",
        "tags": ["ml", "ai"]
    },
    {
        "title": "Python Basics",
        "content": "Python is a high-level programming language.",
        "tags": ["python", "programming"]
    }
]
```

### Cleanup Between Tests

```python
@pytest.fixture(autouse=True)
def cleanup_db(db):
    """Clean up database after each test."""
    yield
    db.query(Note).delete()
    db.query(Link).delete()
    db.query(Tag).delete()
    db.commit()
```

## Troubleshooting

### Common Issues

**Tests fail with "Database is locked"**:
- Ensure tests don't share sessions
- Use `autouse=True` fixtures for cleanup

**Async tests hang**:
- Use `pytest-asyncio`
- Mark tests with `@pytest.mark.asyncio`

**Qdrant connection fails**:
- Mock Qdrant in unit tests
- Use test collection in integration tests

## Next Steps

1. ✅ Define test structure
2. ✅ Create test fixtures
3. ✅ Write unit tests for services
4. ✅ Write integration tests for API
5. ✅ Write e2e tests for workflows
6. 📋 Set up CI/CD
7. 📋 Add performance tests
8. 📋 Achieve 80% coverage
