from datetime import datetime, timezone
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.database import RelationType, Link


def _now() -> datetime:
    return datetime.now(timezone.utc)


def list_relations(db: Session) -> list[tuple]:
    """Returns list of (RelationType, link_count) tuples."""
    return (
        db.query(RelationType, func.count(Link.id).label("link_count"))
        .outerjoin(Link, RelationType.id == Link.relation_type_id)
        .group_by(RelationType.id)
        .order_by(RelationType.name)
        .all()
    )


def get_relation(db: Session, relation_id: str) -> RelationType | None:
    return db.query(RelationType).filter(RelationType.id == relation_id).first()


def get_relation_by_name(db: Session, name: str) -> RelationType | None:
    return db.query(RelationType).filter(RelationType.name == name).first()


def create_relation(db: Session, data: dict) -> RelationType:
    if db.query(RelationType).filter(RelationType.name == data["name"]).first():
        raise HTTPException(status_code=409, detail="Relation type already exists")
    rt = RelationType(
        id=str(uuid.uuid4()),
        name=data["name"],
        description=data.get("description"),
        is_bidirectional=data.get("is_bidirectional", False),
        created_at=_now(),
    )
    db.add(rt)
    db.commit()
    db.refresh(rt)
    return rt


def update_relation(db: Session, relation_id: str, data: dict) -> RelationType | None:
    rt = get_relation(db, relation_id)
    if not rt:
        return None
    for field in ("name", "description", "is_bidirectional"):
        if field in data:
            setattr(rt, field, data[field])
    db.commit()
    db.refresh(rt)
    return rt


def delete_relation(db: Session, relation_id: str) -> bool:
    rt = get_relation(db, relation_id)
    if not rt:
        return False
    link_count = db.query(Link).filter(Link.relation_type_id == relation_id).count()
    if link_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete: {link_count} link(s) use this relation type",
        )
    db.delete(rt)
    db.commit()
    return True
