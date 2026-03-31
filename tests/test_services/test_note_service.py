import pytest
from unittest.mock import AsyncMock, MagicMock
import app.services.note_service as note_service
from app.services.note_service import (
    create_note,
    get_note,
    list_notes,
    update_note,
    delete_note,
)


@pytest.mark.asyncio
async def test_create_note(db):
    note = await create_note(db, {"title": "T", "content": "C", "tags": ["x"]})
    assert note.id is not None
    assert note.synced is True  # sync mode: embedding runs before return
    assert note.title == "T"


@pytest.mark.asyncio
async def test_get_note(db):
    note = await create_note(db, {"title": "T", "content": "C"})
    fetched = get_note(db, note.id)
    assert fetched.id == note.id


@pytest.mark.asyncio
async def test_list_notes_tag_filter(db):
    await create_note(db, {"title": "A", "content": "C", "tags": ["ml"]})
    await create_note(db, {"title": "B", "content": "C", "tags": ["other"]})
    results = list_notes(db, tags=["ml"])
    assert len(results) == 1
    assert results[0].title == "A"


@pytest.mark.asyncio
async def test_update_note(db):
    note = await create_note(db, {"title": "Old", "content": "C"})
    updated = await update_note(db, note.id, {"title": "New"})
    assert updated.title == "New"
    assert updated.synced is True


@pytest.mark.asyncio
async def test_delete_note(db, mock_qdrant):
    note = await create_note(db, {"title": "Del", "content": "C"})
    assert delete_note(db, note.id) is True
    assert get_note(db, note.id) is None
    mock_qdrant.delete.assert_called()


@pytest.mark.asyncio
async def test_delete_note_not_found(db):
    assert delete_note(db, "bad-id") is False


class _CapturedBackgroundTasks:
    def __init__(self):
        self.func = None
        self.args = None

    def add_task(self, func, *args):
        self.func = func
        self.args = args


@pytest.mark.asyncio
async def test_create_note_async_background_task_uses_note_id_payload_only(
    db, monkeypatch
):
    monkeypatch.setattr(note_service.settings, "embedding_mode", "async")
    background_tasks = _CapturedBackgroundTasks()

    note = await create_note(
        db,
        {"title": "T", "content": "C", "tags": ["x"]},
        background_tasks=background_tasks,
    )

    assert background_tasks.func is note_service._embed_and_sync_by_note_id
    assert len(background_tasks.args) == 2
    assert background_tasks.args[0] == note.id
    assert background_tasks.args[1] == ["x"]


@pytest.mark.asyncio
async def test_update_note_async_background_task_captures_immutable_tag_payload(
    db, monkeypatch
):
    note = await create_note(db, {"title": "T", "content": "C", "tags": ["x"]})
    monkeypatch.setattr(note_service.settings, "embedding_mode", "async")
    background_tasks = _CapturedBackgroundTasks()
    tags = ["alpha"]

    await update_note(
        db,
        note.id,
        {"tags": tags},
        background_tasks=background_tasks,
    )
    tags.append("beta")

    assert background_tasks.func is note_service._embed_and_sync_by_note_id
    assert len(background_tasks.args) == 2
    assert background_tasks.args[0] == note.id
    assert background_tasks.args[1] == ["alpha"]


@pytest.mark.asyncio
async def test_embed_and_sync_by_note_id_logs_failure_with_retry_metadata(
    db, monkeypatch
):
    note = await create_note(db, {"title": "T", "content": "C", "tags": ["x"]})
    note.synced = False
    db.commit()

    mock_logger = MagicMock()
    monkeypatch.setattr(note_service, "SessionLocal", lambda: db)
    monkeypatch.setattr(note_service, "logger", mock_logger)
    monkeypatch.setattr(
        note_service,
        "generate_embedding",
        AsyncMock(side_effect=RuntimeError("embedding failed")),
    )

    await note_service._embed_and_sync_by_note_id(note.id, ["x"])

    mock_logger.exception.assert_called_once()
    _, kwargs = mock_logger.exception.call_args
    assert kwargs["extra"]["note_id"] == note.id
    assert kwargs["extra"]["retry_attempt"] == 1
    assert kwargs["extra"]["max_retries"] == 1


@pytest.mark.asyncio
async def test_embed_and_sync_by_note_id_uses_fresh_session_and_closes_it(monkeypatch):
    fake_db = MagicMock()
    fake_note = object()
    session_factory = MagicMock(return_value=fake_db)
    get_note_mock = MagicMock(return_value=fake_note)
    embed_mock = AsyncMock(return_value=None)

    monkeypatch.setattr(note_service, "SessionLocal", session_factory)
    monkeypatch.setattr(note_service, "get_note", get_note_mock)
    monkeypatch.setattr(note_service, "_embed_and_sync", embed_mock)

    await note_service._embed_and_sync_by_note_id("note-123", ["x"])

    session_factory.assert_called_once_with()
    get_note_mock.assert_called_once_with(fake_db, "note-123")
    embed_mock.assert_awaited_once_with(fake_db, fake_note, ["x"])
    fake_db.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_embed_and_sync_by_note_id_logs_query_failures_with_retry_metadata(
    monkeypatch,
):
    fake_db = MagicMock()
    mock_logger = MagicMock()

    monkeypatch.setattr(note_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(
        note_service,
        "get_note",
        MagicMock(side_effect=RuntimeError("session query failed")),
    )
    monkeypatch.setattr(note_service, "logger", mock_logger)

    await note_service._embed_and_sync_by_note_id("note-456", ["x"])

    mock_logger.exception.assert_called_once()
    _, kwargs = mock_logger.exception.call_args
    assert kwargs["extra"]["note_id"] == "note-456"
    assert kwargs["extra"]["retry_attempt"] == 1
    assert kwargs["extra"]["max_retries"] == 1
    fake_db.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_sync_unsynced_notes_uses_fresh_session_and_closes_it(monkeypatch):
    fake_db = MagicMock()
    session_factory = MagicMock(return_value=fake_db)
    fake_db.query.return_value.filter.return_value.limit.return_value.all.return_value = []

    monkeypatch.setattr(note_service, "SessionLocal", session_factory)

    synced_count = await note_service.sync_unsynced_notes(limit=25)

    assert synced_count == 0
    session_factory.assert_called_once_with()
    fake_db.query.assert_called_once_with(note_service.Note)
    fake_db.commit.assert_called_once_with()
    fake_db.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_sync_unsynced_notes_logs_failure_with_retry_metadata(monkeypatch):
    fake_db = MagicMock()
    fake_note = MagicMock(id="note-789")
    fake_db.query.return_value.filter.return_value.limit.return_value.all.return_value = [
        fake_note
    ]
    mock_logger = MagicMock()

    monkeypatch.setattr(note_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(note_service, "logger", mock_logger)
    monkeypatch.setattr(
        note_service,
        "generate_embedding",
        AsyncMock(side_effect=RuntimeError("embedding failed")),
    )

    await note_service.sync_unsynced_notes(limit=10)

    mock_logger.exception.assert_called_once()
    _, kwargs = mock_logger.exception.call_args
    assert kwargs["extra"]["note_id"] == "note-789"
    assert kwargs["extra"]["retry_attempt"] == 1
    assert kwargs["extra"]["max_retries"] == 1


@pytest.mark.asyncio
async def test_sync_unsynced_notes_logs_and_returns_zero_when_session_creation_fails(
    monkeypatch,
):
    mock_logger = MagicMock()

    monkeypatch.setattr(
        note_service,
        "SessionLocal",
        MagicMock(side_effect=RuntimeError("db unavailable")),
    )
    monkeypatch.setattr(note_service, "logger", mock_logger)

    synced_count = await note_service.sync_unsynced_notes(limit=10)

    assert synced_count == 0
    mock_logger.exception.assert_called_once()
