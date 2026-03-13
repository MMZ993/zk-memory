"""
Shared pytest fixtures.

Key rules:
- In-memory SQLite for all tests (isolated per test, dropped after)
- Embeddings are always mocked — never call real OpenAI/Ollama
- Qdrant client is always mocked — never call real Qdrant
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from app.models.database import Base

# ── DB fixtures ────────────────────────────────────────────────────────────────

TEST_DATABASE_URL = "sqlite:///:memory:"

_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(_engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture()
def db() -> Session:
    """Fresh in-memory DB per test — tables created before, dropped after."""
    Base.metadata.create_all(bind=_engine)
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=_engine)


# ── Embedding / Qdrant mocks ───────────────────────────────────────────────────

FAKE_EMBEDDING = [0.1] * 768  # matches nomic-embed-text default dimension


@pytest.fixture(autouse=True)
def mock_embeddings():
    """
    Auto-used: patches generate_embedding and upsert_embedding in every test.
    Tests never call real OpenAI/Ollama.
    """
    with patch(
        "app.services.embedding_service.generate_embedding",
        new=AsyncMock(return_value=FAKE_EMBEDDING),
    ), patch(
        "app.services.embedding_service.upsert_embedding",
        new=AsyncMock(return_value=None),
    ):
        yield


@pytest.fixture(autouse=True)
def mock_qdrant():
    """
    Auto-used: patches the Qdrant client so no real Qdrant connection is needed.
    """
    mock_client = MagicMock()
    mock_client.search.return_value = []
    mock_client.upsert.return_value = None
    mock_client.delete.return_value = None
    mock_client.collection_exists.return_value = True

    with patch("app.db.qdrant.client", mock_client), \
         patch("app.services.note_service.client", mock_client), \
         patch("app.services.embedding_service.client", mock_client):
        yield mock_client
