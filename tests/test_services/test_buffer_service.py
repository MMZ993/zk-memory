import pytest
from app.services.buffer_service import (
    add_to_buffer, get_buffer_note, get_buffer_notes,
    mark_processed, delete_buffer_note, delete_old_processed,
)


def test_create_and_get(db):
    note = add_to_buffer(db, "hello", meta={"source": "chat"})
    assert note.id is not None
    assert note.processed is False
    fetched = get_buffer_note(db, note.id)
    assert fetched.content == "hello"


def test_list_filter_by_processed(db):
    add_to_buffer(db, "a")
    n = add_to_buffer(db, "b")
    mark_processed(db, n.id)
    unprocessed = get_buffer_notes(db, processed=False)
    assert len(unprocessed) == 1 and unprocessed[0].content == "a"
    processed = get_buffer_notes(db, processed=True)
    assert len(processed) == 1


def test_mark_processed_sets_timestamp(db):
    note = add_to_buffer(db, "x")
    result = mark_processed(db, note.id)
    assert result.processed is True
    assert result.processed_at is not None


def test_mark_processed_not_found(db):
    assert mark_processed(db, "nonexistent") is None


def test_delete(db):
    note = add_to_buffer(db, "del me")
    assert delete_buffer_note(db, note.id) is True
    assert get_buffer_note(db, note.id) is None
    assert delete_buffer_note(db, note.id) is False


def test_cleanup_deletes_old_processed(db):
    from datetime import datetime, timezone, timedelta
    note = add_to_buffer(db, "old")
    mark_processed(db, note.id)
    # Backdate created_at to 10 days ago
    note.created_at = datetime.now(timezone.utc) - timedelta(days=10)
    db.commit()
    deleted = delete_old_processed(db, days=7)
    assert deleted == 1


def test_cleanup_ignores_unprocessed(db):
    from datetime import datetime, timezone, timedelta
    note = add_to_buffer(db, "unprocessed")
    note.created_at = datetime.now(timezone.utc) - timedelta(days=10)
    db.commit()
    deleted = delete_old_processed(db, days=7)
    assert deleted == 0
