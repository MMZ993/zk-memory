from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin, require_read
from app.models.database import Note
from app.services.admin_service import (
    get_config,
    get_reembed_status,
    get_stats,
    start_reembed,
)
from app.services.note_service import sync_unsynced_notes

router = APIRouter(tags=["admin"])

REEMBED_CONFIRM_PHRASE = "I understand this will delete and regenerate all embeddings"


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
    from app.services.admin_service import _reembed_state

    if _reembed_state["status"] in {"queued", "in_progress"}:
        raise HTTPException(status_code=409, detail="Re-embed job already running")
    total = db.query(Note).count()
    _reembed_state.update(
        {
            "status": "queued",
            "total": total,
            "processed": 0,
            "failed": 0,
        }
    )
    try:
        background_tasks.add_task(start_reembed)
    except RuntimeError as exc:
        _reembed_state.update(
            {
                "status": "idle",
                "total": 0,
                "processed": 0,
                "failed": 0,
            }
        )
        raise HTTPException(
            status_code=503, detail="Failed to schedule re-embed job"
        ) from exc
    except Exception:
        _reembed_state.update(
            {
                "status": "idle",
                "total": 0,
                "processed": 0,
                "failed": 0,
            }
        )
        raise
    return {"status": "started", "total_notes": total}


@router.get("/api/admin/reembed/status")
def reembed_status_endpoint(_: None = Depends(require_admin)):
    return get_reembed_status()


@router.post("/api/admin/sync-embeddings")
async def sync_embeddings_endpoint(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    pending = db.query(Note).filter(Note.synced == False).count()
    background_tasks.add_task(sync_unsynced_notes)
    return {"status": "started", "pending_notes": pending}
