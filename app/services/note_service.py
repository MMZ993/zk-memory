from typing import Optional
from datetime import datetime, timezone
import uuid


def _now() -> datetime:
    return datetime.now(timezone.utc)

from sqlalchemy.orm import Session

from app.models.database import Note, Tag, NoteTag
from app.db.qdrant import client, QDRANT_COLLECTION
from app.services.embedding_service import generate_embedding, upsert_embedding
from app.core.config import get_settings

settings = get_settings()


# ── Tag helpers ───────────────────────────────────────────────────────────────

def _get_tag_names(db: Session, note_id: str) -> list[str]:
    return [
        row.name
        for row in db.query(Tag)
        .join(NoteTag, Tag.id == NoteTag.tag_id)
        .filter(NoteTag.note_id == note_id)
        .all()
    ]


def _save_tags(db: Session, note_id: str, tag_names: list[str]):
    """Upsert tags and create NoteTag associations."""
    for name in tag_names:
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            tag = Tag(id=str(uuid.uuid4()), name=name, created_at=_now())
            db.add(tag)
            db.flush()
        db.add(NoteTag(note_id=note_id, tag_id=tag.id, created_at=_now()))


# ── CRUD ──────────────────────────────────────────────────────────────────────

def _build_qdrant_payload(note: Note, tags: list[str]) -> dict:
    """Build the Qdrant point payload, keeping SQLite and Qdrant schemas in sync."""
    return {
        "title": note.title,
        "summary": note.summary,
        "created_at": note.created_at.isoformat(),
        "updated_at": note.updated_at.isoformat(),
        "tags": tags,
        "content_length": len(note.content),
    }


async def _embed_and_sync(db: Session, note: Note, tags: list[str]):
    """Generate embedding and mark note as synced."""
    embedding = await generate_embedding(note.title + " " + note.content)
    await upsert_embedding(
        note_id=note.id,
        vector=embedding,
        payload=_build_qdrant_payload(note, tags),
    )
    note.synced = True
    db.commit()


async def create_note(db: Session, note_data: dict, background_tasks=None) -> Note:
    note = Note(
        id=str(uuid.uuid4()),
        title=note_data["title"],
        content=note_data["content"],
        summary=note_data.get("summary"),
        created_at=_now(),
        updated_at=_now(),
        synced=False,
    )
    db.add(note)
    db.flush()

    tags = note_data.get("tags", [])
    _save_tags(db, note.id, tags)
    db.commit()
    db.refresh(note)

    if settings.embedding_mode == "async" and background_tasks is not None:
        background_tasks.add_task(_embed_and_sync, db, note, tags)
    else:
        await _embed_and_sync(db, note, tags)

    return note


def get_note(db: Session, note_id: str) -> Optional[Note]:
    return db.query(Note).filter(Note.id == note_id).first()


async def update_note(db: Session, note_id: str, note_data: dict, background_tasks=None) -> Optional[Note]:
    note = get_note(db, note_id)
    if not note:
        return None

    for field in ("title", "content", "summary"):
        if field in note_data:
            setattr(note, field, note_data[field])

    note.updated_at = _now()
    note.synced = False

    if "tags" in note_data:
        db.query(NoteTag).filter(NoteTag.note_id == note_id).delete()
        tags = note_data["tags"]
        _save_tags(db, note.id, tags)
    else:
        tags = _get_tag_names(db, note_id)

    db.commit()

    if settings.embedding_mode == "async" and background_tasks is not None:
        background_tasks.add_task(_embed_and_sync, db, note, tags)
    else:
        await _embed_and_sync(db, note, tags)

    return note


def delete_note(db: Session, note_id: str) -> bool:
    """Delete note from SQLite and remove its vector from Qdrant."""
    note = get_note(db, note_id)
    if not note:
        return False

    db.query(NoteTag).filter(NoteTag.note_id == note_id).delete()
    db.delete(note)
    db.commit()

    from qdrant_client.models import PointIdsList
    client.delete(
        collection_name=QDRANT_COLLECTION,
        points_selector=PointIdsList(points=[note_id]),
    )
    return True


async def sync_unsynced_notes(db: Session, limit: int = 100) -> int:
    """Repair job: sync all notes where synced=False."""
    unsynced = db.query(Note).filter(Note.synced == False).limit(limit).all()
    for note in unsynced:
        try:
            tags = _get_tag_names(db, note.id)
            embedding = await generate_embedding(note.title + " " + note.content)
            await upsert_embedding(
                note_id=note.id,
                vector=embedding,
                payload=_build_qdrant_payload(note, tags),
            )
            note.synced = True
        except Exception as e:
            print(f"Failed to sync note {note.id}: {e}")

    db.commit()
    return len(unsynced)
