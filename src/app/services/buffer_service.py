from datetime import datetime, timedelta, timezone
import uuid

from sqlalchemy.orm import Session

from app.models.database import BufferNote


def _now() -> datetime:
    return datetime.now(timezone.utc)


def add_to_buffer(db: Session, content: str, meta: dict | None = None) -> BufferNote:
    """Add a note to the buffer (no embedding — fast write)."""
    note = BufferNote(
        id=str(uuid.uuid4()),
        content=content,
        meta=meta,
        created_at=_now(),
        updated_at=_now(),
        processed=False,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def get_buffer_note(db: Session, note_id: str) -> BufferNote | None:
    return db.query(BufferNote).filter(BufferNote.id == note_id).first()


def get_buffer_notes(
    db: Session,
    processed: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[BufferNote]:
    query = db.query(BufferNote)
    if processed is not None:
        query = query.filter(BufferNote.processed == processed)
    return query.order_by(BufferNote.created_at.desc()).offset(offset).limit(limit).all()


def mark_processed(db: Session, note_id: str) -> BufferNote | None:
    """Mark a buffer note as processed. Returns the updated note or None if not found."""
    note = get_buffer_note(db, note_id)
    if not note:
        return None
    note.processed = True
    note.processed_at = _now()
    db.commit()
    db.refresh(note)
    return note


def delete_buffer_note(db: Session, note_id: str) -> bool:
    note = get_buffer_note(db, note_id)
    if not note:
        return False
    db.delete(note)
    db.commit()
    return True


def delete_old_processed(db: Session, days: int) -> int:
    """Delete processed buffer notes older than `days` days. Returns count deleted."""
    cutoff = _now() - timedelta(days=days)
    deleted = db.query(BufferNote).filter(
        BufferNote.processed == True,
        BufferNote.created_at < cutoff,
    ).delete()
    db.commit()
    return deleted
