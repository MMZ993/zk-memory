from unittest.mock import AsyncMock

import pytest
from prometheus_client import generate_latest

from app.services import embedding_service

_upsert_embedding = embedding_service.upsert_embedding


class _EmbeddingResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"embedding": [0.1, 0.2]}


class _EmbeddingClient:
    post = AsyncMock(return_value=_EmbeddingResponse())

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.mark.asyncio
async def test_ollama_embedding_records_success_metrics(monkeypatch):
    monkeypatch.setattr(embedding_service.httpx, "AsyncClient", _EmbeddingClient)

    assert await embedding_service._ollama_embed("memory") == [0.1, 0.2]

    metrics = generate_latest().decode()
    assert 'memory_embedding_requests_total{provider="ollama",result="success"}' in metrics
    assert 'memory_embedding_duration_seconds_bucket{le=' in metrics


@pytest.mark.asyncio
async def test_qdrant_operations_record_success_metrics():
    await _upsert_embedding("note-id", [0.1, 0.2], {"title": "Note"})
    await embedding_service.search_embeddings([0.1, 0.2])

    metrics = generate_latest().decode()
    assert 'memory_qdrant_operations_total{operation="upsert",result="success"}' in metrics
    assert 'memory_qdrant_operations_total{operation="search",result="success"}' in metrics
    assert 'memory_qdrant_operation_duration_seconds_bucket{le=' in metrics
