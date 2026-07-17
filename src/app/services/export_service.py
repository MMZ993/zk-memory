from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.database import BufferNote, Link, Note, NoteTag, RelationType, Tag

EXPORT_VERSION = 1


def export_notes(db: Session) -> list[dict]:
    """Return all notes as a list of dicts (JSON-serializable)."""
    return [_note_to_dict(n) for n in db.query(Note).all()]


def export_buffer(db: Session) -> list[dict]:
    """Return all buffer notes as a list of dicts (JSON-serializable)."""
    return [_buffer_to_dict(n) for n in db.query(BufferNote).all()]


def export_all(db: Session) -> dict:
    """Return a versioned, lossless snapshot of all exportable memory data."""
    return {
        "version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "notes": [_note_to_dict(row) for row in _all_by_id(db, Note)],
        "tags": [_tag_to_dict(row) for row in _all_by_id(db, Tag)],
        "note_tags": [
            _note_tag_to_dict(row)
            for row in db.query(NoteTag).order_by(NoteTag.note_id, NoteTag.tag_id).all()
        ],
        "relation_types": [
            _relation_type_to_dict(row) for row in _all_by_id(db, RelationType)
        ],
        "links": [_link_to_dict(row) for row in _all_by_id(db, Link)],
        "buffer_notes": [_buffer_to_dict(row) for row in _all_by_id(db, BufferNote)],
    }


def _all_by_id(db: Session, model):
    return db.query(model).order_by(model.id).all()


def _note_to_dict(note: Note) -> dict:
    tags = sorted(nt.tag.name for nt in note.note_tags) if note.note_tags else []
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content,
        "summary": note.summary,
        "tags": tags,
        "synced": note.synced,
        "sync_status": note.sync_status,
        "sync_attempts": note.sync_attempts,
        "sync_last_error": note.sync_last_error,
        "sync_last_attempt_at": _optional_datetime(note.sync_last_attempt_at),
        "sync_last_success_at": _optional_datetime(note.sync_last_success_at),
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
    }


def _tag_to_dict(tag: Tag) -> dict:
    return {"id": tag.id, "name": tag.name, "created_at": tag.created_at.isoformat()}


def _note_tag_to_dict(note_tag: NoteTag) -> dict:
    return {
        "note_id": note_tag.note_id,
        "tag_id": note_tag.tag_id,
        "created_at": note_tag.created_at.isoformat(),
    }


def _relation_type_to_dict(relation_type: RelationType) -> dict:
    return {
        "id": relation_type.id,
        "name": relation_type.name,
        "description": relation_type.description,
        "is_bidirectional": relation_type.is_bidirectional,
        "created_at": relation_type.created_at.isoformat(),
    }


def _link_to_dict(link: Link) -> dict:
    return {
        "id": link.id,
        "source_id": link.source_id,
        "target_id": link.target_id,
        "relation_type_id": link.relation_type_id,
        "description": link.description,
        "created_at": link.created_at.isoformat(),
    }


def _optional_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


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
