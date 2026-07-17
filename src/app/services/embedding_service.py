"""
Embedding service — generate vectors and manage Qdrant storage.

Provider: Ollama (local, no API key required).
  Model: nomic-embed-text — 768-dim, fast, production-quality for home lab use.
  Alternative: mxbai-embed-large — 1024-dim, higher quality, more VRAM needed.

Pull the Ollama model before first run:
  ollama pull nomic-embed-text
"""

import time

import httpx
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchAny

from app.db.qdrant import client, QDRANT_COLLECTION
from app.metrics import record_embedding_request, record_qdrant_operation
from app.core.config import get_settings

settings = get_settings()


# ── Public interface ───────────────────────────────────────────────────────────

_TASK_PREFIXES = {
    "document": "search_document: ",
    "query": "search_query: ",
}


async def generate_embedding(text: str, task: str = "document") -> list[float]:
    """Generate an embedding vector for the given text using local Ollama.

    task: "document" (indexing a note) | "query" (embedding a search query).
    When settings.embedding_task_prefix is True, prepends the appropriate task
    instruction prefix — improves retrieval quality with nomic-embed-text and
    mxbai-embed-large, which are trained with asymmetric task prefixes.
    """
    if settings.embedding_task_prefix:
        prefix = _TASK_PREFIXES.get(task, "")
        text = prefix + text

    return await _ollama_embed(text)


async def upsert_embedding(note_id: str, vector: list[float], payload: dict) -> None:
    """Insert or update a note's vector in Qdrant."""
    start_time = time.perf_counter()
    try:
        client.upsert(
            collection_name=QDRANT_COLLECTION,
            points=[PointStruct(id=note_id, vector=vector, payload=payload)],
        )
    except Exception:
        record_qdrant_operation("upsert", "failure", time.perf_counter() - start_time)
        raise
    record_qdrant_operation("upsert", "success", time.perf_counter() - start_time)


async def search_embeddings(
    query_vector: list[float],
    limit: int = 10,
    tag_filter: list[str] | None = None,
) -> list:
    """Search similar notes by vector similarity, optionally filtered by tags."""
    search_filter = None
    if tag_filter:
        search_filter = Filter(
            must=[FieldCondition(key="tags", match=MatchAny(any=tag_filter))]
        )
    start_time = time.perf_counter()
    try:
        response = client.query_points(
            collection_name=QDRANT_COLLECTION,
            query=query_vector,
            query_filter=search_filter,
            limit=limit,
        )
    except Exception:
        record_qdrant_operation("search", "failure", time.perf_counter() - start_time)
        raise
    record_qdrant_operation("search", "success", time.perf_counter() - start_time)
    return response.points


# ── Providers ──────────────────────────────────────────────────────────────────


async def _ollama_embed(text: str) -> list[float]:
    """
    Call local Ollama embeddings API.

    Requires Ollama running at settings.ollama_host (default: http://localhost:11434).
    Pull the model first: ollama pull nomic-embed-text
    """
    start_time = time.perf_counter()
    try:
        async with httpx.AsyncClient() as http:
            response = await http.post(
                f"{settings.ollama_host}/api/embeddings",
                json={"model": settings.embedding_model, "prompt": text},
                timeout=30.0,
            )
            response.raise_for_status()
            embedding = response.json()["embedding"]
    except Exception:
        record_embedding_request("ollama", "failure", time.perf_counter() - start_time)
        raise
    record_embedding_request("ollama", "success", time.perf_counter() - start_time)
    return embedding
