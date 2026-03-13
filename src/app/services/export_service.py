from sqlalchemy.orm import Session

from app.models.database import BufferNote, Note


def export_notes(db: Session) -> list[dict]:
    """Return all notes as a list of dicts (JSON-serializable)."""
    return [_note_to_dict(n) for n in db.query(Note).all()]


def export_buffer(db: Session) -> list[dict]:
    """Return all buffer notes as a list of dicts (JSON-serializable)."""
    return [_buffer_to_dict(n) for n in db.query(BufferNote).all()]


def _note_to_dict(note: Note) -> dict:
    tags = [nt.tag.name for nt in note.note_tags] if note.note_tags else []
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "summary": note.summary,
        "tags": tags,
        "synced": note.synced,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
    }


def _buffer_to_dict(note: BufferNote) -> dict:
    return {
        "id": note.id,
        "content": note.content,
        "meta": note.meta,
        "processed": note.processed,
        "processed_at": note.processed_at.isoformat() if note.processed_at else None,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
    }
