import pytest
from unittest.mock import AsyncMock, MagicMock
from qdrant_client.http.exceptions import ApiException
from sqlalchemy.orm import sessionmaker
import app.services.note_service as note_service
from app.services.note_service import (
    NoteDeleteSyncError,
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
    assert note.sync_status == "synced"
    assert note.sync_attempts == 1
    assert note.sync_last_attempt_at is not None
    assert note.sync_last_success_at is not None
    assert note.sync_last_error is None
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
    assert updated.sync_status == "synced"
    assert updated.sync_attempts == 2
    assert updated.sync_last_attempt_at is not None
    assert updated.sync_last_success_at is not None
    assert updated.sync_last_error is None


@pytest.mark.asyncio
async def test_delete_note(db, mock_qdrant):
    note = await create_note(db, {"title": "Del", "content": "C"})
    assert delete_note(db, note.id) is True
    assert get_note(db, note.id) is None
    mock_qdrant.delete.assert_called()


@pytest.mark.asyncio
async def test_delete_note_not_found(db):
    assert delete_note(db, "bad-id") is False


@pytest.mark.asyncio
async def test_delete_note_raises_and_keeps_row_when_qdrant_delete_fails(
    db, mock_qdrant
):
    note = await create_note(db, {"title": "Del", "content": "C"})
    mock_qdrant.delete.side_effect = RuntimeError("qdrant down")

    with pytest.raises(NoteDeleteSyncError):
        delete_note(db, note.id)
    assert get_note(db, note.id) is not None


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
    note_id = note.id
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

    await note_service._embed_and_sync_by_note_id(note_id, ["x"])

    mock_logger.exception.assert_called_once()
    _, kwargs = mock_logger.exception.call_args
    assert kwargs["extra"]["note_id"] == note_id
    assert kwargs["extra"]["retry_attempt"] == 2
    assert kwargs["extra"]["max_retries"] == 2


@pytest.mark.asyncio
async def test_embed_and_sync_by_note_id_persists_failed_sync_state(db, monkeypatch):
    note = await create_note(db, {"title": "T", "content": "C", "tags": ["x"]})
    note.synced = False
    db.commit()

    testing_session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db.get_bind(),
    )
    monkeypatch.setattr(note_service, "SessionLocal", testing_session)
    monkeypatch.setattr(
        note_service,
        "generate_embedding",
        AsyncMock(side_effect=RuntimeError("embedding failed")),
    )

    await note_service._embed_and_sync_by_note_id(note.id, ["x"])

    verify_db = testing_session()
    refreshed_note = get_note(verify_db, note.id)
    assert refreshed_note.synced is False
    assert refreshed_note.sync_status == "failed"
    assert refreshed_note.sync_attempts == 3
    assert refreshed_note.sync_last_attempt_at is not None
    assert refreshed_note.sync_last_success_at is not None
    assert refreshed_note.sync_last_error == "embedding failed"
    verify_db.close()


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
    assert kwargs["extra"]["max_retries"] == 2
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
async def test_sync_unsynced_notes_logs_failure_with_retry_metadata(db, monkeypatch):
    note = await create_note(db, {"title": "T", "content": "C", "tags": ["x"]})
    note.synced = False
    note.sync_status = "pending"
    db.commit()

    mock_logger = MagicMock()

    testing_session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db.get_bind(),
    )

    monkeypatch.setattr(note_service, "SessionLocal", testing_session)
    monkeypatch.setattr(note_service, "logger", mock_logger)
    monkeypatch.setattr(
        note_service,
        "generate_embedding",
        AsyncMock(side_effect=RuntimeError("embedding failed")),
    )

    await note_service.sync_unsynced_notes(limit=10)

    mock_logger.exception.assert_called_once()
    _, kwargs = mock_logger.exception.call_args
    assert kwargs["extra"]["note_id"] == note.id
    assert kwargs["extra"]["retry_attempt"] == 2
    assert kwargs["extra"]["max_retries"] == 2


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


@pytest.mark.asyncio
async def test_sync_unsynced_notes_counts_only_successes_and_recovers_state(
    db, monkeypatch
):
    note = await create_note(db, {"title": "T", "content": "C", "tags": ["x"]})
    note_id = note.id
    note.synced = False
    note.sync_status = "pending"
    db.commit()

    testing_session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db.get_bind(),
    )
    generate_mock = AsyncMock(
        side_effect=[
            RuntimeError("embedding failed"),
            RuntimeError("embedding failed again"),
            [0.1] * 768,
        ]
    )
    monkeypatch.setattr(note_service, "SessionLocal", testing_session)
    monkeypatch.setattr(note_service, "generate_embedding", generate_mock)

    first_count = await note_service.sync_unsynced_notes(limit=10)
    verify_db = testing_session()
    first_state = get_note(verify_db, note_id)
    assert first_count == 0
    assert first_state.synced is False
    assert first_state.sync_status == "failed"
    assert first_state.sync_last_error == "embedding failed again"
    verify_db.close()

    second_count = await note_service.sync_unsynced_notes(limit=10)
    verify_db = testing_session()
    second_state = get_note(verify_db, note_id)
    assert second_count == 1
    assert second_state.synced is True
    assert second_state.sync_status == "synced"
    assert second_state.sync_last_error is None
    assert second_state.sync_attempts == 4
    verify_db.close()


@pytest.mark.asyncio
async def test_embed_and_sync_by_note_id_retries_transient_embedding_failure(
    db, monkeypatch
):
    note = await create_note(db, {"title": "T", "content": "C", "tags": ["x"]})
    note.synced = False
    note.sync_status = "pending"
    db.commit()

    testing_session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db.get_bind(),
    )
    generate_mock = AsyncMock(
        side_effect=[RuntimeError("transient embedding failure"), [0.1] * 768]
    )
    monkeypatch.setattr(note_service, "SessionLocal", testing_session)
    monkeypatch.setattr(note_service, "generate_embedding", generate_mock)

    await note_service._embed_and_sync_by_note_id(note.id, ["x"])

    verify_db = testing_session()
    refreshed_note = get_note(verify_db, note.id)
    assert generate_mock.await_count == 2
    assert refreshed_note.synced is True
    assert refreshed_note.sync_status == "synced"
    assert refreshed_note.sync_last_error is None
    assert refreshed_note.sync_attempts == 3
    verify_db.close()


@pytest.mark.asyncio
async def test_embed_and_sync_by_note_id_retries_transient_upsert_failure(
    db, monkeypatch
):
    note = await create_note(db, {"title": "T", "content": "C", "tags": ["x"]})
    note.synced = False
    note.sync_status = "pending"
    db.commit()

    testing_session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db.get_bind(),
    )
    upsert_mock = AsyncMock(
        side_effect=[RuntimeError("transient upsert failure"), None]
    )
    monkeypatch.setattr(note_service, "SessionLocal", testing_session)
    monkeypatch.setattr(note_service, "upsert_embedding", upsert_mock)

    await note_service._embed_and_sync_by_note_id(note.id, ["x"])

    verify_db = testing_session()
    refreshed_note = get_note(verify_db, note.id)
    assert upsert_mock.await_count == 2
    assert refreshed_note.synced is True
    assert refreshed_note.sync_status == "synced"
    assert refreshed_note.sync_last_error is None
    assert refreshed_note.sync_attempts == 3
    verify_db.close()


@pytest.mark.asyncio
async def test_embed_and_sync_by_note_id_does_not_retry_non_retryable_error(
    db, monkeypatch
):
    note = await create_note(db, {"title": "T", "content": "C", "tags": ["x"]})
    note.synced = False
    note.sync_status = "pending"
    db.commit()

    testing_session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db.get_bind(),
    )
    generate_mock = AsyncMock(side_effect=ValueError("invalid embedding input"))
    mock_logger = MagicMock()

    monkeypatch.setattr(note_service, "SessionLocal", testing_session)
    monkeypatch.setattr(note_service, "generate_embedding", generate_mock)
    monkeypatch.setattr(note_service, "logger", mock_logger)

    await note_service._embed_and_sync_by_note_id(note.id, ["x"])

    verify_db = testing_session()
    refreshed_note = get_note(verify_db, note.id)
    assert generate_mock.await_count == 1
    assert refreshed_note.synced is False
    assert refreshed_note.sync_status == "failed"
    assert refreshed_note.sync_last_error == "invalid embedding input"
    assert refreshed_note.sync_attempts == 2
    _, kwargs = mock_logger.exception.call_args
    assert kwargs["extra"]["retry_attempt"] == 1
    assert kwargs["extra"]["max_retries"] == 2
    verify_db.close()


@pytest.mark.asyncio
async def test_embed_and_sync_by_note_id_retries_qdrant_api_exception(db, monkeypatch):
    note = await create_note(db, {"title": "T", "content": "C", "tags": ["x"]})
    note.synced = False
    note.sync_status = "pending"
    db.commit()

    testing_session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db.get_bind(),
    )
    upsert_mock = AsyncMock(side_effect=[ApiException(), None])

    monkeypatch.setattr(note_service, "SessionLocal", testing_session)
    monkeypatch.setattr(note_service, "upsert_embedding", upsert_mock)

    await note_service._embed_and_sync_by_note_id(note.id, ["x"])

    verify_db = testing_session()
    refreshed_note = get_note(verify_db, note.id)
    assert upsert_mock.await_count == 2
    assert refreshed_note.synced is True
    assert refreshed_note.sync_status == "synced"
    assert refreshed_note.sync_last_error is None
    assert refreshed_note.sync_attempts == 3
    verify_db.close()
