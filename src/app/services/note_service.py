import asyncio
from typing import Optional
from datetime import datetime, timezone
import logging
import uuid

import httpx
from qdrant_client.http.exceptions import ApiException, ResponseHandlingException
from sqlalchemy import asc, desc, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.metrics import NOTES_CREATED, record_sync_operation
from app.models.database import Note, Tag, NoteTag, Link


def _now() -> datetime:
    return datetime.now(timezone.utc)


from app.db.qdrant import client, QDRANT_COLLECTION
from app.db.session import SessionLocal
from app.services.embedding_service import generate_embedding, upsert_embedding
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
SYNC_MAX_RETRIES = 2
SYNC_RETRY_BASE_DELAY_SECONDS = 0.1


class NoteDeleteSyncError(Exception):
    pass


def _is_retryable_sync_error(exc: Exception) -> bool:
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


def _compute_sync_retry_delay(attempt: int) -> float:
    return SYNC_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))


# ── Tag helpers ───────────────────────────────────────────────────────────────


def _get_tag_names(db: Session, note_id: str) -> list[str]:
    return [
        row.name.lower()
        for row in db.query(Tag)
        .join(NoteTag, Tag.id == NoteTag.tag_id)
        .filter(NoteTag.note_id == note_id)
        .all()
    ]


def _save_tags(db: Session, note_id: str, tag_names: list[str]):
    """Upsert tags and create NoteTag associations."""
    for name in _normalize_tag_names(tag_names):
        tag = db.query(Tag).filter(Tag.name == name).first()
        if tag:
            db.add(NoteTag(note_id=note_id, tag_id=tag.id, created_at=_now()))
            continue

        tag = (
            db.query(Tag)
            .filter(func.lower(Tag.name) == name)
            .order_by(Tag.created_at.asc())
            .first()
        )
        if tag:
            tag.name = name
            db.flush()
        else:
            tag = Tag(id=str(uuid.uuid4()), name=name, created_at=_now())
            db.add(tag)
            db.flush()
        db.add(NoteTag(note_id=note_id, tag_id=tag.id, created_at=_now()))


def _normalize_tag_names(tag_names: list[str] | None) -> list[str]:
    if not tag_names:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for name in tag_names:
        normalized_name = name.strip().lower()
        if not normalized_name or normalized_name in seen:
            continue
        seen.add(normalized_name)
        normalized.append(normalized_name)
    return normalized


# ── CRUD ──────────────────────────────────────────────────────────────────────


def _build_qdrant_payload(note: Note, tags: list[str]) -> dict:
    """Build the Qdrant point payload, keeping SQLite and Qdrant schemas in sync."""
    return {
        "title": note.title,
        "summary": note.summary,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
        "tags": tags,
        "content_length": len(note.content),
    }


def _build_embedding_text(note: Note, tags: list[str]) -> str:
    """Build the text to embed: title + content + tags (if any).

    Tags are appended as comma-separated keywords so the embedding captures
    thematic context that may not appear verbatim in the content.
    Links are structural metadata and are intentionally excluded.
    """
    parts = [note.title, note.content]
    if tags:
        parts.append("Tags: " + ", ".join(tags))
    return "\n\n".join(parts)


async def _embed_and_sync(
    db: Session, note: Note, tags: list[str], operation: str = "create"
):
    """Generate embedding and mark note as synced."""
    for attempt in range(1, SYNC_MAX_RETRIES + 1):
        note.sync_attempts += 1
        note.sync_last_attempt_at = _now()
        note.sync_status = "syncing"
        db.commit()
        try:
            embedding = await generate_embedding(
                _build_embedding_text(note, tags), task="document"
            )
            await upsert_embedding(
                note_id=note.id,
                vector=embedding,
                payload=_build_qdrant_payload(note, tags),
            )
            note.synced = True
            note.sync_status = "synced"
            note.sync_last_success_at = _now()
            note.sync_last_error = None
            db.commit()
            record_sync_operation(operation, "success")
            return
        except Exception as exc:
            note.synced = False
            note.sync_status = "failed"
            note.sync_last_error = str(exc)
            db.commit()
            if attempt >= SYNC_MAX_RETRIES or not _is_retryable_sync_error(exc):
                record_sync_operation(operation, "failure")
                setattr(exc, "sync_retry_attempt", attempt)
                setattr(exc, "sync_max_retries", SYNC_MAX_RETRIES)
                raise
            await asyncio.sleep(_compute_sync_retry_delay(attempt))


async def _embed_and_sync_by_note_id(
    note_id: str, tags: list[str], operation: str = "create"
):
    db = SessionLocal()
    try:
        note = get_note(db, note_id)
        if not note:
            return
        await _embed_and_sync(db, note, tags, operation)
    except (
        RuntimeError,
        ConnectionError,
        TimeoutError,
        httpx.HTTPError,
        ApiException,
        ResponseHandlingException,
        SQLAlchemyError,
    ) as exc:
        retry_attempt = getattr(exc, "sync_retry_attempt", 1)
        max_retries = getattr(exc, "sync_max_retries", SYNC_MAX_RETRIES)
        logger.exception(
            "Async note embedding sync failed",
            extra={
                "note_id": note_id,
                "retry_attempt": retry_attempt,
                "max_retries": max_retries,
            },
        )
    except Exception as exc:
        retry_attempt = getattr(exc, "sync_retry_attempt", 1)
        max_retries = getattr(exc, "sync_max_retries", SYNC_MAX_RETRIES)
        logger.exception(
            "Async note embedding sync failed",
            extra={
                "note_id": note_id,
                "retry_attempt": retry_attempt,
                "max_retries": max_retries,
            },
        )
        raise
    finally:
        db.close()


async def create_note(db: Session, note_data: dict, background_tasks=None) -> Note:
    note = Note(
        id=str(uuid.uuid4()),
        title=note_data["title"],
        content=note_data["content"],
        summary=note_data.get("summary"),
        created_at=_now(),
        updated_at=_now(),
        synced=False,
        sync_status="pending",
        sync_attempts=0,
        sync_last_error=None,
        sync_last_attempt_at=None,
        sync_last_success_at=None,
    )
    db.add(note)
    db.flush()

    tags = _normalize_tag_names(note_data.get("tags", []))
    _save_tags(db, note.id, tags)
    db.commit()
    db.refresh(note)
    NOTES_CREATED.inc()

    if settings.embedding_mode == "async" and background_tasks is not None:
        background_tasks.add_task(_embed_and_sync_by_note_id, note.id, list(tags))
    else:
        await _embed_and_sync(db, note, tags)

    return note


def get_note(db: Session, note_id: str) -> Optional[Note]:
    return db.query(Note).filter(Note.id == note_id).first()


def list_notes(
    db: Session,
    tags: list[str] | None = None,
    sort: str = "updated_at",
    order: str = "desc",
    limit: int = 20,
    offset: int = 0,
) -> list[Note]:
    query = db.query(Note)
    if tags:
        normalized_tags = [t.lower() for t in tags]
        query = (
            query.join(NoteTag, Note.id == NoteTag.note_id)
            .join(Tag, NoteTag.tag_id == Tag.id)
            .filter(func.lower(Tag.name).in_(normalized_tags))
            .distinct()
        )
    sort_col = Note.updated_at if sort == "updated_at" else Note.created_at
    order_fn = desc if order == "desc" else asc
    return query.order_by(order_fn(sort_col)).offset(offset).limit(limit).all()


async def update_note(
    db: Session, note_id: str, note_data: dict, background_tasks=None
) -> Optional[Note]:
    note = get_note(db, note_id)
    if not note:
        return None

    for field in ("title", "content", "summary"):
        if field in note_data:
            setattr(note, field, note_data[field])

    note.updated_at = _now()
    note.synced = False
    note.sync_status = "pending"
    note.sync_last_error = None

    if "tags" in note_data:
        db.query(NoteTag).filter(NoteTag.note_id == note_id).delete()
        tags = _normalize_tag_names(note_data["tags"])
        _save_tags(db, note.id, tags)
    else:
        tags = _get_tag_names(db, note_id)

    db.commit()

    if settings.embedding_mode == "async" and background_tasks is not None:
        try:
            background_tasks.add_task(
                _embed_and_sync_by_note_id, note.id, list(tags), "update"
            )
        except RuntimeError as exc:
            note.synced = False
            note.sync_status = "failed"
            note.sync_last_error = str(exc)
            note.sync_last_attempt_at = _now()
            db.commit()
            raise
    else:
        await _embed_and_sync(db, note, tags, "update")

    return note


def delete_note(db: Session, note_id: str) -> bool:
    """Delete note from SQLite and remove its vector from Qdrant."""
    note = get_note(db, note_id)
    if not note:
        return False

    from qdrant_client.models import PointIdsList

    try:
        client.delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=PointIdsList(points=[note_id]),
        )
    except (
        RuntimeError,
        ConnectionError,
        TimeoutError,
        httpx.HTTPError,
        ApiException,
        ResponseHandlingException,
    ):
        logger.exception(
            "Note delete vector cleanup failed",
            extra={"note_id": note_id},
        )
        raise NoteDeleteSyncError("failed to delete note vector")

    db.query(Link).filter(
        (Link.source_id == note_id) | (Link.target_id == note_id)
    ).delete(synchronize_session=False)
    db.query(NoteTag).filter(NoteTag.note_id == note_id).delete()
    db.delete(note)
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        note_after_rollback = get_note(db, note_id)
        if note_after_rollback is not None:
            note_after_rollback.synced = False
            note_after_rollback.sync_status = "failed"
            note_after_rollback.sync_last_error = (
                "vector deleted but sqlite delete failed"
            )
            note_after_rollback.sync_last_attempt_at = _now()
            try:
                db.commit()
            except SQLAlchemyError:
                db.rollback()
                logger.exception(
                    "Note delete sqlite recovery-state commit failed",
                    extra={"note_id": note_id},
                )
        logger.exception(
            "Note delete sqlite cleanup failed after vector deletion",
            extra={"note_id": note_id},
        )
        raise NoteDeleteSyncError(
            "failed to delete note row after vector cleanup"
        ) from exc
    except Exception:
        db.rollback()
        note_after_rollback = get_note(db, note_id)
        if note_after_rollback is not None:
            note_after_rollback.synced = False
            note_after_rollback.sync_status = "failed"
            note_after_rollback.sync_last_error = (
                "vector deleted but sqlite delete failed"
            )
            note_after_rollback.sync_last_attempt_at = _now()
            try:
                db.commit()
            except SQLAlchemyError:
                db.rollback()
                logger.exception(
                    "Note delete sqlite recovery-state commit failed",
                    extra={"note_id": note_id},
                )
        raise
    return True


async def sync_unsynced_notes(limit: int = 100) -> int:
    """Repair job: sync all notes where synced=False."""
    db = None
    try:
        db = SessionLocal()
        unsynced = db.query(Note).filter(Note.synced == False).limit(limit).all()
        synced_count = 0
        for note in unsynced:
            try:
                tags = _get_tag_names(db, note.id)
                await _embed_and_sync(db, note, tags, "repair")
                synced_count += 1
            except Exception as exc:
                logger.exception(
                    "Async unsynced note repair failed",
                    extra={
                        "note_id": note.id,
                        "retry_attempt": getattr(exc, "sync_retry_attempt", 1),
                        "max_retries": getattr(
                            exc, "sync_max_retries", SYNC_MAX_RETRIES
                        ),
                    },
                )
                if not (
                    _is_retryable_sync_error(exc) or isinstance(exc, SQLAlchemyError)
                ):
                    raise
        db.commit()
        return synced_count
    except (
        RuntimeError,
        ConnectionError,
        TimeoutError,
        httpx.HTTPError,
        ApiException,
        ResponseHandlingException,
        SQLAlchemyError,
    ):
        logger.exception(
            "Async unsynced note repair job failed",
            extra={
                "retry_attempt": 1,
                "max_retries": SYNC_MAX_RETRIES,
            },
        )
        return 0
    finally:
        if db is not None:
            db.close()
