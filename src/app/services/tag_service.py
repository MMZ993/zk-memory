from datetime import datetime, timezone
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import Tag, NoteTag


def _now() -> datetime:
    return datetime.now(timezone.utc)


def list_tags(db: Session, limit: int = 100, offset: int = 0) -> list[tuple]:
    """Returns list of (Tag, note_count) tuples."""
    return (
        db.query(Tag, func.count(NoteTag.note_id).label("note_count"))
        .outerjoin(NoteTag, Tag.id == NoteTag.tag_id)
        .group_by(Tag.id)
        .order_by(Tag.name)
        .offset(offset)
        .limit(limit)
        .all()
    )


def create_tag(db: Session, name: str) -> Tag:
    """Get-or-create a tag by name."""
    existing = db.query(Tag).filter(Tag.name == name).first()
    if existing:
        return existing
    tag = Tag(id=str(uuid.uuid4()), name=name, created_at=_now())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def get_tag_by_name(db: Session, name: str) -> Tag | None:
    return db.query(Tag).filter(Tag.name == name).first()


def get_note_tags(db: Session, note_id: str) -> list[Tag]:
    return (
        db.query(Tag)
        .join(NoteTag, Tag.id == NoteTag.tag_id)
        .filter(NoteTag.note_id == note_id)
        .all()
    )


def add_tag_to_note(db: Session, note_id: str, tag_name: str) -> Tag:
    """Get-or-create tag by name, associate with note. Returns the tag."""
    tag = create_tag(db, tag_name)
    exists = db.query(NoteTag).filter(
        NoteTag.note_id == note_id, NoteTag.tag_id == tag.id
    ).first()
    if not exists:
        db.add(NoteTag(note_id=note_id, tag_id=tag.id, created_at=_now()))
        db.commit()
    return tag


def remove_tag_from_note(db: Session, note_id: str, tag_id: str) -> bool:
    deleted = db.query(NoteTag).filter(
        NoteTag.note_id == note_id, NoteTag.tag_id == tag_id
    ).delete()
    db.commit()
    return deleted > 0
