import logging

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin, require_read
from app.db.session import SessionLocal
from app.models.database import Note
from app.services.admin_service import (
    AdminJobAlreadyRunningError,
    JOB_TYPE_REEMBED,
    JOB_TYPE_SYNC_EMBEDDINGS,
    create_admin_job,
    get_config,
    get_reembed_status,
    get_stats,
    start_reembed,
    update_admin_job,
)
from app.services.note_service import sync_unsynced_notes

router = APIRouter(tags=["admin"])
logger = logging.getLogger(__name__)

REEMBED_CONFIRM_PHRASE = "I understand this will delete and regenerate all embeddings"
# In-process sync repair state — single-worker only
_sync_embeddings_state = {"status": "idle", "pending_notes": 0}


async def _run_sync_embeddings_job(job_id: str | None = None) -> None:
    _sync_embeddings_state["status"] = "in_progress"
    db = None
    try:
        db = SessionLocal()
        if job_id is not None:
            update_admin_job(
                db,
                job_id=job_id,
                status="in_progress",
            )
        await sync_unsynced_notes()
        if job_id is not None:
            update_admin_job(
                db,
                job_id=job_id,
                status="finished",
                pending_items=0,
            )
    except (
        RuntimeError,
        ConnectionError,
        TimeoutError,
        httpx.HTTPError,
        SQLAlchemyError,
    ):
        if job_id is not None:
            status_db = db
            try:
                if status_db is None:
                    status_db = SessionLocal()
                update_admin_job(
                    status_db,
                    job_id=job_id,
                    status="failed",
                    pending_items=0,
                    last_error="Failed to run sync-embeddings repair job",
                )
            except Exception:
                logger.exception("Failed to persist sync-embeddings job failure status")
            finally:
                if db is None and status_db is not None and status_db is not db:
                    status_db.close()
        logger.exception("Failed to run sync-embeddings repair job")
    except Exception:
        if job_id is not None:
            status_db = db
            try:
                if status_db is None:
                    status_db = SessionLocal()
                update_admin_job(
                    status_db,
                    job_id=job_id,
                    status="failed",
                    pending_items=0,
                    last_error="Failed to run sync-embeddings repair job",
                )
            except Exception:
                logger.exception("Failed to persist sync-embeddings job failure status")
            finally:
                if db is None and status_db is not None and status_db is not db:
                    status_db.close()
        logger.exception("Failed to run sync-embeddings repair job")
        raise
    finally:
        if db is not None:
            db.close()
        _sync_embeddings_state.update({"status": "idle", "pending_notes": 0})


class ReembedRequest(BaseModel):
    confirm: str


@router.get("/api/stats")
def stats_endpoint(db: Session = Depends(get_db), _: None = Depends(require_read)):
    return get_stats(db)


@router.get("/api/config")
def config_endpoint(_: None = Depends(require_admin)):
    return get_config()


@router.post("/api/admin/reembed")
async def reembed_endpoint(
    body: ReembedRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    if body.confirm != REEMBED_CONFIRM_PHRASE:
        raise HTTPException(
            status_code=400,
            detail=f"confirm must be: '{REEMBED_CONFIRM_PHRASE}'",
        )
    total = db.query(Note).count()
    job_id = None

    try:
        job = create_admin_job(
            db,
            job_type=JOB_TYPE_REEMBED,
            total_items=total,
        )
        job_id = job.id
        background_tasks.add_task(start_reembed, job.id)
    except RuntimeError as exc:
        if job_id is not None:
            update_admin_job(
                db,
                job_id=job_id,
                status="failed",
                pending_items=0,
                last_error="Failed to schedule re-embed job",
            )
        raise HTTPException(
            status_code=503, detail="Failed to schedule re-embed job"
        ) from exc
    except AdminJobAlreadyRunningError as exc:
        raise HTTPException(
            status_code=409, detail="Re-embed job already running"
        ) from exc
    except Exception:
        db.rollback()
        raise
    return {"status": "started", "job_id": job.id, "total_notes": total}


@router.get("/api/admin/reembed/status")
def reembed_status_endpoint(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    return get_reembed_status(db)


@router.post("/api/admin/sync-embeddings")
async def sync_embeddings_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    pending = db.query(Note).filter(Note.synced == False).count()
    job_id = None

    try:
        job = create_admin_job(
            db,
            job_type=JOB_TYPE_SYNC_EMBEDDINGS,
            pending_items=pending,
        )
        job_id = job.id
        _sync_embeddings_state.update({"status": "queued", "pending_notes": pending})
        background_tasks.add_task(_run_sync_embeddings_job, job.id)
    except RuntimeError as exc:
        if job_id is not None:
            update_admin_job(
                db,
                job_id=job_id,
                status="failed",
                pending_items=0,
                last_error="Failed to schedule sync repair job",
            )
        _sync_embeddings_state.update({"status": "idle", "pending_notes": 0})
        raise HTTPException(
            status_code=503, detail="Failed to schedule sync repair job"
        ) from exc
    except AdminJobAlreadyRunningError as exc:
        raise HTTPException(
            status_code=409, detail="Sync repair job already running"
        ) from exc
    except Exception:
        db.rollback()
        _sync_embeddings_state.update({"status": "idle", "pending_notes": 0})
        raise
    return {"status": "started", "job_id": job.id, "pending_notes": pending}
