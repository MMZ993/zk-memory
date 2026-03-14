"""
Embedding service — generate vectors and manage Qdrant storage.

Default provider: Ollama (local, no API key required).
  Model: nomic-embed-text — 768-dim, fast, production-quality for home lab use.
  Alternative: mxbai-embed-large — 1024-dim, higher quality, more VRAM needed.

OpenAI provider available but not used by default.
  Set EMBEDDING_PROVIDER=openai and OPENAI_API_KEY in .env to switch.
  Not covered by tests — revisit if cloud embeddings are needed.

Pull the Ollama model before first run:
  ollama pull nomic-embed-text
"""

import httpx
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchAny

from app.db.qdrant import client, QDRANT_COLLECTION
from app.core.config import get_settings

settings = get_settings()


# ── Public interface ───────────────────────────────────────────────────────────

_TASK_PREFIXES = {
    "document": "search_document: ",
    "query":    "search_query: ",
}


async def generate_embedding(text: str, task: str = "document") -> list[float]:
    """Generate an embedding vector for the given text using the configured provider.

    task: "document" (indexing a note) | "query" (embedding a search query).
    When settings.embedding_task_prefix is True, prepends the appropriate task
    instruction prefix — improves retrieval quality with nomic-embed-text and
    mxbai-embed-large, which are trained with asymmetric task prefixes.
    """
    if settings.embedding_task_prefix:
        prefix = _TASK_PREFIXES.get(task, "")
        text = prefix + text

    if settings.embedding_provider == "ollama":
        return await _ollama_embed(text)
    if settings.embedding_provider == "openai":
        # OpenAI path — functional but not the default and not tested.
        # Switch via EMBEDDING_PROVIDER=openai + OPENAI_API_KEY in .env.
        return await _openai_embed(text)
    raise ValueError(f"Unknown embedding provider: {settings.embedding_provider!r}")


async def upsert_embedding(note_id: str, vector: list[float], payload: dict) -> None:
    """Insert or update a note's vector in Qdrant."""
    client.upsert(
        collection_name=QDRANT_COLLECTION,
        points=[PointStruct(id=note_id, vector=vector, payload=payload)],
    )


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
    response = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        query_filter=search_filter,
        limit=limit,
    )
    return response.points


# ── Providers ──────────────────────────────────────────────────────────────────

async def _ollama_embed(text: str) -> list[float]:
    """
    Call local Ollama embeddings API.

    Requires Ollama running at settings.ollama_host (default: http://localhost:11434).
    Pull the model first: ollama pull nomic-embed-text
    """
    async with httpx.AsyncClient() as http:
        response = await http.post(
            f"{settings.ollama_host}/api/embeddings",
            json={"model": settings.embedding_model, "prompt": text},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()["embedding"]


async def _openai_embed(text: str) -> list[float]:
    """
    Call OpenAI embeddings API.

    Not used by default. Not covered by tests.
    Switch via: EMBEDDING_PROVIDER=openai, OPENAI_API_KEY=sk-... in .env.
    Default model when using OpenAI: text-embedding-ada-002 (1536-dim).
    Remember to also set EMBEDDING_DIMENSION=1536 and recreate the Qdrant collection.
    """
    from openai import AsyncOpenAI
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await openai_client.embeddings.create(
        input=text,
        model=settings.embedding_model,
    )
    return response.data[0].embedding
