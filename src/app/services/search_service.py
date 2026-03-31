import logging

from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError

from app.models.database import Note, Link
from app.services.embedding_service import generate_embedding, search_embeddings

MAX_GRAPH_DEPTH = 3
logger = logging.getLogger(__name__)


async def search_semantic(
    db: Session,
    query: str,
    limit: int = 10,
    tags: list[str] | None = None,
) -> list[tuple[Note, float]]:
    """Vector similarity search. Returns (note, score) pairs sorted by score desc."""
    query_vector = await generate_embedding(query, task="query")
    results = await search_embeddings(query_vector, limit=limit, tag_filter=tags)
    note_ids = [str(r.id) for r in results]
    scores = {str(r.id): r.score for r in results}
    notes = db.query(Note).filter(Note.id.in_(note_ids)).all()
    sorted_notes = sorted(notes, key=lambda n: scores.get(n.id, 0.0), reverse=True)
    return [(note, scores.get(note.id, 0.0)) for note in sorted_notes]


def search_keyword(
    db: Session,
    query: str,
    limit: int = 10,
) -> list[tuple[Note, float]]:
    """Full-text search. SQLite uses FTS5; PostgreSQL uses tsvector."""
    from sqlalchemy import text
    from app.core.config import get_settings

    settings = get_settings()

    try:
        if settings.db_backend == "postgres":
            sql = text("""
                SELECT id, ts_rank(search_vector, plainto_tsquery('english', :q)) AS rank
                FROM notes
                WHERE search_vector @@ plainto_tsquery('english', :q)
                ORDER BY rank DESC
                LIMIT :limit
            """)
            rows = db.execute(sql, {"q": query, "limit": limit}).fetchall()
            note_ids = [r[0] for r in rows]
            scores = {r[0]: float(r[1]) for r in rows}
        else:
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
            scores = {nid: 1.0 for nid in note_ids}
    except SQLAlchemyError:
        logger.warning(
            "Keyword search fallback to empty results",
            extra={"query": query, "limit": limit},
        )
        return []

    if not note_ids:
        return []
    notes_map = {n.id: n for n in db.query(Note).filter(Note.id.in_(note_ids)).all()}
    return [
        (notes_map[nid], scores.get(nid, 1.0)) for nid in note_ids if nid in notes_map
    ]


async def search_hybrid(
    db: Session,
    query: str,
    limit: int = 10,
    tags: list[str] | None = None,
) -> list[tuple[Note, float]]:
    """Merge semantic and keyword results (deduplicated, highest score wins)."""
    semantic = await search_semantic(db, query, limit=limit, tags=tags)
    keyword = search_keyword(db, query, limit=limit)
    scores: dict[str, float] = {}
    notes_map: dict[str, Note] = {}
    for note, score in semantic + keyword:
        if note.id not in scores or score > scores[note.id]:
            scores[note.id] = score
            notes_map[note.id] = note
    combined = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [(notes_map[nid], s) for nid, s in combined[:limit]]


def search_graph(
    db: Session,
    start_note_id: str,
    depth: int = 1,
) -> list[tuple[Note, int]]:
    """BFS traversal up to `depth` levels. Returns (note, distance) pairs."""
    depth = min(depth, MAX_GRAPH_DEPTH)
    visited: set[str] = {start_note_id}
    current_layer: set[str] = {start_note_id}
    result_pairs: list[tuple[str, int]] = []

    for d in range(1, depth + 1):
        if not current_layer:
            break
        next_layer: set[str] = set()
        for note_id in current_layer:
            links = (
                db.query(Link)
                .filter(or_(Link.source_id == note_id, Link.target_id == note_id))
                .all()
            )
            for link in links:
                neighbor = (
                    link.target_id if link.source_id == note_id else link.source_id
                )
                if neighbor not in visited:
                    next_layer.add(neighbor)
                    visited.add(neighbor)
        for neighbor_id in next_layer:
            result_pairs.append((neighbor_id, d))
        current_layer = next_layer

    if not result_pairs:
        return []
    id_to_dist = {nid: dist for nid, dist in result_pairs}
    notes = db.query(Note).filter(Note.id.in_(list(id_to_dist.keys()))).all()
    return [(note, id_to_dist[note.id]) for note in notes]
