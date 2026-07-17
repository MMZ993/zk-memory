from datetime import datetime, timezone
from threading import Lock

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
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
HTTP_REQUESTS = Counter(
    "memory_http_requests",
    "Total HTTP requests",
    labelnames=("method", "path", "status"),
)
HTTP_REQUEST_DURATION = Histogram(
    "memory_http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=("method", "path"),
)
EMBEDDING_REQUESTS = Counter(
    "memory_embedding_requests",
    "Total embedding provider requests",
    labelnames=("provider", "result"),
)
EMBEDDING_DURATION = Histogram(
    "memory_embedding_duration_seconds",
    "Embedding provider request duration in seconds",
    labelnames=("provider",),
)
QDRANT_OPERATIONS = Counter(
    "memory_qdrant_operations",
    "Total Qdrant operations",
    labelnames=("operation", "result"),
)
QDRANT_OPERATION_DURATION = Histogram(
    "memory_qdrant_operation_duration_seconds",
    "Qdrant operation duration in seconds",
    labelnames=("operation",),
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
SYNC_OLDEST_PENDING_SECONDS = Gauge(
    "memory_sync_oldest_pending_seconds",
    "Age in seconds of the oldest note awaiting embedding sync",
)
_metrics_lock = Lock()


def record_sync_operation(operation: str, result: str) -> None:
    SYNC_OPERATIONS.labels(operation=operation, result=result).inc()


def record_http_request(
    method: str, path: str, status: int, duration_seconds: float
) -> None:
    HTTP_REQUESTS.labels(method=method, path=path, status=str(status)).inc()
    HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(duration_seconds)


def record_embedding_request(
    provider: str, result: str, duration_seconds: float
) -> None:
    EMBEDDING_REQUESTS.labels(provider=provider, result=result).inc()
    EMBEDDING_DURATION.labels(provider=provider).observe(duration_seconds)


def record_qdrant_operation(
    operation: str, result: str, duration_seconds: float
) -> None:
    QDRANT_OPERATIONS.labels(operation=operation, result=result).inc()
    QDRANT_OPERATION_DURATION.labels(operation=operation).observe(duration_seconds)


def render_metrics(db: Session) -> bytes:
    with _metrics_lock:
        NOTES_TOTAL.set(db.query(Note).count())
        TAGS_TOTAL.set(db.query(Tag).count())
        LINKS_TOTAL.set(db.query(Link).count())
        BUFFER_NOTES_TOTAL.set(db.query(BufferNote).count())
        pending_notes = db.query(Note).filter(Note.synced == False)
        SYNC_PENDING_NOTES.set(pending_notes.count())
        oldest_pending = pending_notes.with_entities(func.min(Note.created_at)).scalar()
        if oldest_pending is None:
            SYNC_OLDEST_PENDING_SECONDS.set(0)
        else:
            if oldest_pending.tzinfo is None:
                oldest_pending = oldest_pending.replace(tzinfo=timezone.utc)
            age_seconds = (datetime.now(timezone.utc) - oldest_pending).total_seconds()
            SYNC_OLDEST_PENDING_SECONDS.set(max(age_seconds, 0))

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
