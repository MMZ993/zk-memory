from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, pagination, require_buffer, require_read, require_write
from app.core.config import get_settings
from app.models.schemas import BufferNoteCreate, BufferNoteResponse
from app.services.buffer_service import (
    add_to_buffer,
    delete_buffer_note,
    delete_old_processed,
    get_buffer_note,
    get_buffer_notes,
    mark_processed,
)

router = APIRouter(prefix="/api/buffer", tags=["buffer"])


@router.post("/", response_model=BufferNoteResponse, status_code=201)
def create_buffer_note(note: BufferNoteCreate, db: Session = Depends(get_db), _: None = Depends(require_buffer)):
    return add_to_buffer(db, note.content, note.meta)


@router.get("/", response_model=list[BufferNoteResponse])
def list_buffer_notes(
    processed: bool | None = None,
    page: dict = Depends(pagination),
    db: Session = Depends(get_db),
    _: None = Depends(require_read),
):
    return get_buffer_notes(db, processed=processed, **page)


# NOTE: /cleanup MUST be declared before /{note_id} — otherwise FastAPI matches
# the literal string "cleanup" as a note_id path parameter.
@router.delete("/cleanup")
def cleanup_processed_notes(db: Session = Depends(get_db), _: None = Depends(require_write)):
    retention = get_settings().buffer_retention_days
    if retention == 0:
        return {"deleted": 0, "disabled": True}
    count = delete_old_processed(db, retention)
    return {"deleted": count}


@router.get("/{note_id}", response_model=BufferNoteResponse)
def get_buffer_note_endpoint(note_id: str, db: Session = Depends(get_db), _: None = Depends(require_read)):
    note = get_buffer_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Buffer note not found")
    return note


@router.delete("/{note_id}", status_code=204)
def delete_buffer_note_endpoint(note_id: str, db: Session = Depends(get_db), _: None = Depends(require_write)):
    if not delete_buffer_note(db, note_id):
        raise HTTPException(status_code=404, detail="Buffer note not found")


@router.post("/{note_id}/process", response_model=BufferNoteResponse)
def mark_as_processed(note_id: str, db: Session = Depends(get_db), _: None = Depends(require_write)):
    note = mark_processed(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Buffer note not found")
    return note
