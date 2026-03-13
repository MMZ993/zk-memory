from datetime import datetime, timedelta, timezone

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.qdrant import QDRANT_COLLECTION, client, init_qdrant
from app.models.database import BufferNote, Link, Note, NoteTag, Tag

settings = get_settings()

# In-process reembed state — single-worker only
_reembed_state: dict = {"status": "idle", "total": 0, "processed": 0, "failed": 0}


def get_stats(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)

    top_tags = (
        db.query(Tag.name, func.count(NoteTag.note_id).label("c"))
        .join(NoteTag, Tag.id == NoteTag.tag_id)
        .group_by(Tag.id)
        .order_by(text("c DESC"))
        .limit(5)
        .all()
    )

    try:
        qdrant_info = client.get_collection(QDRANT_COLLECTION)
        vector_db = {
            "points_count": qdrant_info.points_count,
            "segments_count": qdrant_info.segments_count,
        }
    except Exception:
        vector_db = {"points_count": 0, "segments_count": 0}

    return {
        "notes": {
            "total": db.query(Note).count(),
            "synced": db.query(Note).filter(Note.synced == True).count(),
            "unsynced": db.query(Note).filter(Note.synced == False).count(),
            "created_today": db.query(Note).filter(
                Note.created_at >= today_start, Note.created_at < tomorrow_start
            ).count(),
            "updated_today": db.query(Note).filter(
                Note.updated_at >= today_start, Note.updated_at < tomorrow_start
            ).count(),
        },
        "links": {"total": db.query(Link).count()},
        "tags": {
            "total": db.query(Tag).count(),
            "most_used": [t[0] for t in top_tags],
        },
        "buffer": {
            "total": db.query(BufferNote).count(),
            "unprocessed": db.query(BufferNote).filter(BufferNote.processed == False).count(),
            "processed": db.query(BufferNote).filter(BufferNote.processed == True).count(),
        },
        "vector_db": vector_db,
    }


def get_config() -> dict:
    return {
        "embedding_provider": settings.embedding_provider,
        "embedding_model": settings.embedding_model,
        "embedding_dimension": settings.embedding_dimension,
        "embedding_mode": settings.embedding_mode,
        "buffer_retention_days": settings.buffer_retention_days,
        "debug": settings.debug,
        "version": "1.0.0",
    }


def get_reembed_status() -> dict:
    return {"status": _reembed_state["status"]}


async def start_reembed(db: Session) -> None:
    """Background task: purge Qdrant collection and regenerate all embeddings."""
    from app.services.embedding_service import generate_embedding, upsert_embedding
    from app.services.note_service import _build_qdrant_payload, _get_tag_names

    notes = db.query(Note).all()
    _reembed_state.update({
        "status": "in_progress",
        "total": len(notes),
        "processed": 0,
        "failed": 0,
    })

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
    _reembed_state["status"] = "finished"
