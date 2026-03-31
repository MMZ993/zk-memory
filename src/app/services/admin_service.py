import asyncio
from datetime import datetime, timedelta, timezone
import logging

import httpx
from qdrant_client.http.exceptions import ApiException, ResponseHandlingException
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.qdrant import QDRANT_COLLECTION, client, init_qdrant
from app.db.session import SessionLocal
from app.models.database import BufferNote, Link, Note, NoteTag, Tag

settings = get_settings()
logger = logging.getLogger(__name__)
ADMIN_REEMBED_MAX_RETRIES = 2
ADMIN_REEMBED_RETRY_BASE_DELAY_SECONDS = 0.1

# In-process reembed state — single-worker only
_reembed_state: dict = {"status": "idle", "total": 0, "processed": 0, "failed": 0}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_retryable_reembed_error(exc: Exception) -> bool:
    return isinstance(
        exc,
        (
            RuntimeError,
            ConnectionError,
            TimeoutError,
            httpx.HTTPError,
            ApiException,
            ResponseHandlingException,
        ),
    )


def _compute_reembed_retry_delay(attempt: int) -> float:
    return ADMIN_REEMBED_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))


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
            "created_today": db.query(Note)
            .filter(Note.created_at >= today_start, Note.created_at < tomorrow_start)
            .count(),
            "updated_today": db.query(Note)
            .filter(Note.updated_at >= today_start, Note.updated_at < tomorrow_start)
            .count(),
        },
        "links": {"total": db.query(Link).count()},
        "tags": {
            "total": db.query(Tag).count(),
            "most_used": [t[0] for t in top_tags],
        },
        "buffer": {
            "total": db.query(BufferNote).count(),
            "unprocessed": db.query(BufferNote)
            .filter(BufferNote.processed == False)
            .count(),
            "processed": db.query(BufferNote)
            .filter(BufferNote.processed == True)
            .count(),
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


async def start_reembed() -> None:
    """Background task: purge Qdrant collection and regenerate all embeddings."""
    from app.services.embedding_service import generate_embedding, upsert_embedding
    from app.services.note_service import _build_qdrant_payload, _get_tag_names

    db = None
    try:
        db = SessionLocal()
        notes = db.query(Note).all()
        _reembed_state.update(
            {
                "status": "in_progress",
                "total": len(notes),
                "processed": 0,
                "failed": 0,
            }
        )

        client.delete_collection(QDRANT_COLLECTION)
        init_qdrant()

        for note in notes:
            for attempt in range(1, ADMIN_REEMBED_MAX_RETRIES + 1):
                note.sync_attempts += 1
                note.sync_last_attempt_at = _now()
                note.sync_status = "syncing"
                db.commit()
                try:
                    tags = _get_tag_names(db, note.id)
                    vector = await generate_embedding(note.title + " " + note.content)
                    await upsert_embedding(
                        note.id, vector, _build_qdrant_payload(note, tags)
                    )
                    note.synced = True
                    note.sync_status = "synced"
                    note.sync_last_success_at = _now()
                    note.sync_last_error = None
                    _reembed_state["processed"] += 1
                    db.commit()
                    break
                except Exception as exc:
                    note.synced = False
                    note.sync_status = "failed"
                    note.sync_last_error = str(exc)
                    db.commit()
                    if (
                        attempt >= ADMIN_REEMBED_MAX_RETRIES
                        or not _is_retryable_reembed_error(exc)
                    ):
                        _reembed_state["failed"] += 1
                        logger.exception(
                            "Async admin re-embed failed",
                            extra={
                                "note_id": note.id,
                                "retry_attempt": attempt,
                                "max_retries": ADMIN_REEMBED_MAX_RETRIES,
                            },
                        )
                        break
                    await asyncio.sleep(_compute_reembed_retry_delay(attempt))

        db.commit()
        _reembed_state["status"] = "finished"
    except Exception:
        _reembed_state["status"] = "failed"
        logger.exception(
            "Async admin re-embed job failed",
            extra={
                "retry_attempt": 1,
                "max_retries": ADMIN_REEMBED_MAX_RETRIES,
            },
        )
    finally:
        if db is not None:
            db.close()
