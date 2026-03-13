"""
Integration test fixtures.

Run with:
    INTEGRATION_TESTS=1 pytest tests/integration/ -v

Requires:
    - Qdrant running on localhost:6333  (docker compose up qdrant)
    - Ollama running on localhost:11434 with nomic-embed-text pulled
      (ollama pull nomic-embed-text)

Isolation strategy:
    - SQLite: data/integration.db  (separate from data/memory.db)
    - Qdrant:  test_memory collection (separate from notes_embeddings)
    - Both are wiped at session start so each run begins clean.

Override strategy for parent conftest autouse mocks:
    - mock_embeddings and mock_qdrant are redefined here as no-ops so that
      parent-conftest mocks do not intercept real service calls.
    - QDRANT_COLLECTION is patched at the module level in all three modules
      that hold a copy of it (qdrant.py, embedding_service.py, note_service.py).
"""

import os
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

INTEGRATION_DB_PATH = "data/integration.db"
INTEGRATION_DB_URL = f"sqlite:///{INTEGRATION_DB_PATH}"
TEST_COLLECTION = "test_memory"


# ── Guard: skip entire directory unless INTEGRATION_TESTS=1 ──────────────────

def pytest_collection_modifyitems(config, items):
    if os.getenv("INTEGRATION_TESTS"):
        return
    skip = pytest.mark.skip(reason="Set INTEGRATION_TESTS=1 to run integration tests")
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(skip)


# ── Override parent autouse mocks (no-ops so real services are used) ─────────

@pytest.fixture(autouse=True)
def mock_embeddings():
    """Override parent conftest mock — use real Ollama embeddings."""
    yield


@pytest.fixture(autouse=True)
def mock_qdrant():
    """Override parent conftest mock — use real Qdrant."""
    yield


# ── Patch module-level QDRANT_COLLECTION in all modules that hold a copy ─────

@pytest.fixture(scope="session", autouse=True)
def patch_qdrant_collection():
    """
    Redirect all Qdrant operations to the test_memory collection.

    Each module imports QDRANT_COLLECTION from qdrant.py at import time (by value).
    We must patch the name in every module namespace that uses it.
    """
    import app.db.qdrant as qdrant_db
    import app.services.embedding_service as embed_svc
    import app.services.note_service as note_svc

    originals = {
        "qdrant_db": qdrant_db.QDRANT_COLLECTION,
        "embed_svc": embed_svc.QDRANT_COLLECTION,
        "note_svc": note_svc.QDRANT_COLLECTION,
    }

    qdrant_db.QDRANT_COLLECTION = TEST_COLLECTION
    embed_svc.QDRANT_COLLECTION = TEST_COLLECTION
    note_svc.QDRANT_COLLECTION = TEST_COLLECTION

    yield TEST_COLLECTION

    qdrant_db.QDRANT_COLLECTION = originals["qdrant_db"]
    embed_svc.QDRANT_COLLECTION = originals["embed_svc"]
    note_svc.QDRANT_COLLECTION = originals["note_svc"]


# ── Session-scoped seeded client ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def seeded_client(patch_qdrant_collection):
    """
    One-time setup for the whole integration test session:

    1. Wipe data/integration.db and the test_memory Qdrant collection.
    2. Create a new SQLite engine with FTS5 support (notes_fts + triggers).
    3. Override get_db to use the integration engine.
    4. Start TestClient (triggers lifespan → init_qdrant creates test_memory).
    5. Seed 14 smart-home notes + 13 links via the API.
    6. Yield (client, note_ids) to all tests.
    """
    import app.db.qdrant as qdrant_db
    from app.api.deps import get_db
    from app.models.database import Base
    from main import app

    # ── 1. Clean slate ────────────────────────────────────────────────────────
    try:
        if qdrant_db.client.collection_exists(TEST_COLLECTION):
            qdrant_db.client.delete_collection(TEST_COLLECTION)
    except Exception as exc:
        pytest.skip(f"Qdrant not reachable: {exc}")

    os.makedirs("data", exist_ok=True)
    if os.path.exists(INTEGRATION_DB_PATH):
        os.remove(INTEGRATION_DB_PATH)

    # ── 2. Integration engine + tables ───────────────────────────────────────
    engine = create_engine(
        INTEGRATION_DB_URL,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def set_pragmas(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)

    # Create FTS5 virtual table and keep-in-sync triggers.
    # (init_db only calls Base.metadata.create_all; FTS5 is not an ORM model.)
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts "
            "USING fts5(note_id UNINDEXED, title, content)"
        ))
        conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS notes_fts_ai "
            "AFTER INSERT ON notes BEGIN "
            "  INSERT INTO notes_fts(note_id, title, content) "
            "  VALUES (new.id, new.title, new.content); "
            "END"
        ))
        conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS notes_fts_au "
            "AFTER UPDATE ON notes BEGIN "
            "  DELETE FROM notes_fts WHERE note_id = old.id; "
            "  INSERT INTO notes_fts(note_id, title, content) "
            "  VALUES (new.id, new.title, new.content); "
            "END"
        ))
        conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS notes_fts_ad "
            "AFTER DELETE ON notes BEGIN "
            "  DELETE FROM notes_fts WHERE note_id = old.id; "
            "END"
        ))
        conn.commit()

    # ── 3. Override get_db ────────────────────────────────────────────────────
    SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = SessionFactory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # ── 4 & 5. Start client, seed data ───────────────────────────────────────
    # TestClient lifespan calls init_qdrant() which will create test_memory
    # (because patch_qdrant_collection has already redirected QDRANT_COLLECTION).
    # It also calls init_db() on the global engine (harmless — we override get_db).
    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            from tests.integration.fixtures import seed_data
            note_ids = seed_data(client)
            yield client, note_ids
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


# ── Convenience aliases used by test modules ──────────────────────────────────

@pytest.fixture(scope="session")
def client(seeded_client):
    c, _ = seeded_client
    return c


@pytest.fixture(scope="session")
def note_ids(seeded_client):
    _, ids = seeded_client
    return ids
