import asyncio
from datetime import datetime, timedelta, timezone
import logging

import httpx
from qdrant_client.http.exceptions import ApiException, ResponseHandlingException
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.qdrant import QDRANT_COLLECTION, client, init_qdrant
from app.db.session import SessionLocal
from app.models.database import AdminJob, BufferNote, Link, Note, NoteTag, Tag

settings = get_settings()
logger = logging.getLogger(__name__)
ADMIN_REEMBED_MAX_RETRIES = 2
ADMIN_REEMBED_RETRY_BASE_DELAY_SECONDS = 0.1
JOB_TYPE_REEMBED = "reembed"
JOB_TYPE_SYNC_EMBEDDINGS = "sync_embeddings"
ACTIVE_ADMIN_JOB_STATUSES = {"queued", "in_progress"}


class AdminJobAlreadyRunningError(Exception):
    pass


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
    except (
        ConnectionError,
        TimeoutError,
        httpx.HTTPError,
        ApiException,
        ResponseHandlingException,
    ) as exc:
        logger.warning(
            "Stats endpoint vector backend fallback",
            extra={"error": str(exc)},
        )
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
        "embedding_model": settings.embedding_model,
        "embedding_dimension": settings.embedding_dimension,
        "embedding_mode": settings.embedding_mode,
        "buffer_retention_days": settings.buffer_retention_days,
        "debug": settings.debug,
        "version": "1.0.0",
    }


def get_reembed_status(db: Session) -> dict:
    latest_job = (
        db.query(AdminJob)
        .filter(AdminJob.job_type == JOB_TYPE_REEMBED)
        .order_by(AdminJob.created_at.desc())
        .first()
    )
    if latest_job is None:
        return {"status": _reembed_state["status"]}
    return {
        "job_id": latest_job.id,
        "job_type": latest_job.job_type,
        "status": latest_job.status,
        "total_items": latest_job.total_items,
        "processed_items": latest_job.processed_items,
        "failed_items": latest_job.failed_items,
        "pending_items": latest_job.pending_items,
        "last_error": latest_job.last_error,
        "created_at": latest_job.created_at.isoformat(),
        "updated_at": latest_job.updated_at.isoformat(),
        "started_at": latest_job.started_at.isoformat()
        if latest_job.started_at is not None
        else None,
        "finished_at": latest_job.finished_at.isoformat()
        if latest_job.finished_at is not None
        else None,
    }


def create_admin_job(
    db: Session,
    *,
    job_type: str,
    total_items: int = 0,
    pending_items: int = 0,
) -> AdminJob:
    existing_active = (
        db.query(AdminJob)
        .filter(
            AdminJob.job_type == job_type,
            AdminJob.status.in_(ACTIVE_ADMIN_JOB_STATUSES),
        )
        .first()
    )
    if existing_active is not None:
        raise AdminJobAlreadyRunningError(f"{job_type} job already running")

    job = AdminJob(
        job_type=job_type,
        status="queued",
        total_items=total_items,
        pending_items=pending_items,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AdminJobAlreadyRunningError(f"{job_type} job already running")
    db.refresh(job)
    return job


def update_admin_job(
    db: Session,
    *,
    job_id: str,
    status: str,
    total_items: int | None = None,
    processed_items: int | None = None,
    failed_items: int | None = None,
    pending_items: int | None = None,
    last_error: str | None = None,
) -> None:
    job = db.query(AdminJob).filter(AdminJob.id == job_id).first()
    if job is None:
        return
    job.status = status
    if total_items is not None:
        job.total_items = total_items
    if processed_items is not None:
        job.processed_items = processed_items
    if failed_items is not None:
        job.failed_items = failed_items
    if pending_items is not None:
        job.pending_items = pending_items
    if last_error is not None:
        job.last_error = last_error
    if status == "in_progress" and job.started_at is None:
        job.started_at = _now()
    if status in {"finished", "failed"}:
        job.finished_at = _now()
    db.commit()


async def start_reembed(job_id: str | None = None) -> None:
    """Background task: purge Qdrant collection and regenerate all embeddings."""
    from app.services.embedding_service import generate_embedding, upsert_embedding
    from app.services.note_service import (
        _build_embedding_text,
        _build_qdrant_payload,
        _get_tag_names,
    )

    db = None
    try:
        db = SessionLocal()
        notes = db.query(Note).all()
        if job_id is not None:
            update_admin_job(
                db,
                job_id=job_id,
                status="in_progress",
                total_items=len(notes),
                processed_items=0,
                failed_items=0,
                pending_items=0,
            )
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
                    vector = await generate_embedding(_build_embedding_text(note, tags))
                    await upsert_embedding(
                        note.id, vector, _build_qdrant_payload(note, tags)
                    )
                    note.synced = True
                    note.sync_status = "synced"
                    note.sync_last_success_at = _now()
                    note.sync_last_error = None
                    _reembed_state["processed"] += 1
                    if job_id is not None:
                        job = db.query(AdminJob).filter(AdminJob.id == job_id).first()
                        if job is not None:
                            job.processed_items += 1
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
                        if job_id is not None:
                            job = (
                                db.query(AdminJob).filter(AdminJob.id == job_id).first()
                            )
                            if job is not None:
                                job.failed_items += 1
                                job.last_error = str(exc)
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
        if job_id is not None:
            update_admin_job(
                db,
                job_id=job_id,
                status="finished",
                processed_items=_reembed_state["processed"],
                failed_items=_reembed_state["failed"],
                pending_items=0,
            )
    except Exception as exc:
        _reembed_state["status"] = "failed"
        if job_id is not None:
            status_db = db
            try:
                if status_db is None:
                    status_db = SessionLocal()
                update_admin_job(
                    status_db,
                    job_id=job_id,
                    status="failed",
                    processed_items=_reembed_state["processed"],
                    failed_items=_reembed_state["failed"],
                    pending_items=0,
                    last_error=str(exc),
                )
            finally:
                if db is None and status_db is not None and status_db is not db:
                    status_db.close()
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
