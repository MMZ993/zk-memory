from threading import Lock

from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge,
                               generate_latest)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import BufferNote, Link, Note, NoteTag, Tag

NOTES_READ = Counter("memory_notes_reads", "Total note read requests")
NOTES_CREATED = Counter("memory_notes_created", "Total notes created")
BUFFER_READS = Counter("memory_buffer_reads", "Total buffer read requests")
BUFFER_CREATED = Counter("memory_buffer_created", "Total buffer notes created")
SYNC_OPERATIONS = Counter(
    "memory_sync_operations",
    "Total embedding sync operations",
    labelnames=("operation", "result"),
)
NOTES_TOTAL = Gauge("memory_notes", "Current number of notes")
TAGS_TOTAL = Gauge("memory_tags", "Current number of tags")
LINKS_TOTAL = Gauge("memory_links", "Current number of links")
BUFFER_NOTES_TOTAL = Gauge("memory_buffer_notes", "Current number of buffer notes")
NOTES_BY_TAG = Gauge(
    "memory_notes_by_tag", "Current number of notes for each tag", labelnames=("tag",)
)
SYNC_PENDING_NOTES = Gauge(
    "memory_sync_pending_notes", "Current number of notes awaiting embedding sync"
)
_metrics_lock = Lock()


def record_sync_operation(operation: str, result: str) -> None:
    SYNC_OPERATIONS.labels(operation=operation, result=result).inc()


def render_metrics(db: Session) -> bytes:
    with _metrics_lock:
        NOTES_TOTAL.set(db.query(Note).count())
        TAGS_TOTAL.set(db.query(Tag).count())
        LINKS_TOTAL.set(db.query(Link).count())
        BUFFER_NOTES_TOTAL.set(db.query(BufferNote).count())
        SYNC_PENDING_NOTES.set(db.query(Note).filter(Note.synced == False).count())

        NOTES_BY_TAG.clear()
        tag_counts = (
            db.query(Tag.name, func.count(NoteTag.note_id))
            .outerjoin(NoteTag, Tag.id == NoteTag.tag_id)
            .group_by(Tag.id)
            .all()
        )
        for tag_name, note_count in tag_counts:
            NOTES_BY_TAG.labels(tag=tag_name).set(note_count)

        return generate_latest()


METRICS_CONTENT_TYPE = CONTENT_TYPE_LATEST
