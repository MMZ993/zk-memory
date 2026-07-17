from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.models.database import NoteTag
from app.models.import_schemas import ImportRequest
from app.services.import_service import analyze_import, apply_import
from app.services.note_service import _embed_and_sync_by_note_id

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/")
def import_document_endpoint(
    body: ImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
):
    """Analyze or explicitly apply a non-destructive canonical import."""
    try:
        if body.mode == "dry_run":
            return analyze_import(db, body.document, body.selection)
        report = apply_import(db, body.document, body.mode, body.selection)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409, detail="database changed during import; run dry-run again"
        ) from exc
    for note_id in report["sync_note_ids"]:
        tags = [
            row.tag.name
            for row in db.query(NoteTag).filter(NoteTag.note_id == note_id).all()
        ]
        background_tasks.add_task(
            _embed_and_sync_by_note_id, note_id, sorted(tags), "import"
        )
    return report
