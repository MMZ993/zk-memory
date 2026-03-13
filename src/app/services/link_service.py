from datetime import datetime, timezone
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException

from app.models.database import Link, Note
from app.services.relation_service import get_relation_by_name, create_relation


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_note_links(
    db: Session,
    note_id: str,
    direction: str = "all",
    limit: int = 50,
) -> list[Link]:
    query = db.query(Link)
    if direction == "outgoing":
        query = query.filter(Link.source_id == note_id)
    elif direction == "incoming":
        query = query.filter(Link.target_id == note_id)
    else:
        query = query.filter(or_(Link.source_id == note_id, Link.target_id == note_id))
    return query.limit(limit).all()


def create_link(db: Session, data: dict) -> Link:
    """Create a link between notes, auto-creating the relation type if needed."""
    if not db.query(Note).filter(Note.id == data["source_id"]).first():
        raise HTTPException(status_code=404, detail="Source note not found")
    if not db.query(Note).filter(Note.id == data["target_id"]).first():
        raise HTTPException(status_code=404, detail="Target note not found")

    rt = get_relation_by_name(db, data["relation_type"])
    if not rt:
        rt = create_relation(db, {"name": data["relation_type"]})

    link = Link(
        id=str(uuid.uuid4()),
        source_id=data["source_id"],
        target_id=data["target_id"],
        relation_type_id=rt.id,
        description=data.get("description"),
        created_at=_now(),
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def delete_link(db: Session, link_id: str) -> bool:
    link = db.query(Link).filter(Link.id == link_id).first()
    if not link:
        return False
    db.delete(link)
    db.commit()
    return True
