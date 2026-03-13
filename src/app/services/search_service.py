from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.database import Note, Link
from app.services.embedding_service import generate_embedding, search_embeddings

MAX_GRAPH_DEPTH = 3


async def search_semantic(
    db: Session,
    query: str,
    limit: int = 10,
    tags: list[str] | None = None,
) -> list[tuple[Note, float]]:
    """Vector similarity search. Returns (note, score) pairs sorted by score desc."""
    query_vector = await generate_embedding(query)
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
    """Full-text search via SQLite FTS5. Returns (note, 1.0) pairs in rank order."""
    from sqlalchemy import text
    safe_query = query.replace('"', '""')
    sql = text("""
        SELECT n.id FROM notes n
        JOIN notes_fts fts ON n.id = fts.note_id
        WHERE notes_fts MATCH :q
        ORDER BY rank
        LIMIT :limit
    """)
    try:
        rows = db.execute(sql, {"q": f'"{safe_query}"', "limit": limit}).fetchall()
    except Exception:
        # FTS5 table may not exist (e.g. in test DBs created without init_db())
        return []
    note_ids = [r[0] for r in rows]
    if not note_ids:
        return []
    notes_map = {n.id: n for n in db.query(Note).filter(Note.id.in_(note_ids)).all()}
    return [(notes_map[nid], 1.0) for nid in note_ids if nid in notes_map]


async def search_hybrid(
    db: Session,
    query: str,
    limit: int = 10,
    tags: list[str] | None = None,
) -> list[tuple[Note, float]]:
    """Merge semantic and keyword results (deduplicated, semantic first)."""
    semantic = await search_semantic(db, query, limit=limit, tags=tags)
    keyword = search_keyword(db, query, limit=limit)
    seen: set[str] = set()
    combined: list[tuple[Note, float]] = []
    for note, score in semantic + keyword:
        if note.id not in seen:
            seen.add(note.id)
            combined.append((note, score))
    return combined[:limit]


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
            links = db.query(Link).filter(
                or_(Link.source_id == note_id, Link.target_id == note_id)
            ).all()
            for link in links:
                neighbor = link.target_id if link.source_id == note_id else link.source_id
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
