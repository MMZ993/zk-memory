from unittest.mock import AsyncMock, MagicMock

import pytest
from qdrant_client.http.exceptions import ApiException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

import app.services.note_service as note_service
from app.metrics import NOTES_CREATED
from app.models.database import Note, Tag
from app.services.note_service import (NoteDeleteSyncError, create_note,
                                       delete_note, get_note, list_notes,
                                       update_note)


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
async def test_create_note_counts_persisted_note_when_embedding_fails(db, monkeypatch):
    created_before = NOTES_CREATED._value.get()
    monkeypatch.setattr(
        note_service,
        "generate_embedding",
        AsyncMock(side_effect=RuntimeError("embedding unavailable")),
    )

    with pytest.raises(RuntimeError, match="embedding unavailable"):
        await create_note(db, {"title": "Pending", "content": "C"})

    assert db.query(Note).filter(Note.title == "Pending").count() == 1
    assert NOTES_CREATED._value.get() == created_before + 1


@pytest.mark.asyncio
async def test_create_note_normalizes_and_dedupes_tags_case_insensitively(db):
    note = await create_note(
        db,
        {"title": "T", "content": "C", "tags": [" AI ", "ai", "ML", " ml "]},
    )

    assert note.id is not None
    tag_names = [tag.name for tag in db.query(Tag).order_by(Tag.name).all()]
    assert tag_names == ["ai", "ml"]


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
async def test_update_note_normalizes_and_dedupes_tags_case_insensitively(db):
    note = await create_note(db, {"title": "Old", "content": "C", "tags": ["x"]})

    updated = await update_note(db, note.id, {"tags": [" AI ", "ai", "ML", " ml "]})

    assert updated is not None
    tag_names = [tag.name for tag in db.query(Tag).order_by(Tag.name).all()]
    assert tag_names == ["ai", "ml", "x"]


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
    mock_qdrant.delete.side_effect = ApiException()

    with pytest.raises(NoteDeleteSyncError):
        delete_note(db, note.id)
    assert get_note(db, note.id) is not None


@pytest.mark.asyncio
async def test_delete_note_reraises_unexpected_delete_errors(db, mock_qdrant):
    note = await create_note(db, {"title": "Del", "content": "C"})
    mock_qdrant.delete.side_effect = ValueError("unexpected delete failure")

    with pytest.raises(ValueError, match="unexpected delete failure"):
        delete_note(db, note.id)
    assert get_note(db, note.id) is not None


@pytest.mark.asyncio
async def test_delete_note_marks_row_unsynced_when_sql_delete_commit_fails(
    db, mock_qdrant, monkeypatch
):
    note = await create_note(db, {"title": "Del", "content": "C"})
    original_commit = db.commit
    commit_calls = {"count": 0}

    def _commit_with_first_failure():
        commit_calls["count"] += 1
        if commit_calls["count"] == 1:
            raise SQLAlchemyError("sqlite delete failed")
        return original_commit()

    monkeypatch.setattr(db, "commit", _commit_with_first_failure)

    with pytest.raises(NoteDeleteSyncError, match="failed to delete note row"):
        delete_note(db, note.id)

    refreshed = get_note(db, note.id)
    assert refreshed is not None
    assert refreshed.synced is False
    assert refreshed.sync_status == "failed"
    assert refreshed.sync_last_error == "vector deleted but sqlite delete failed"


@pytest.mark.asyncio
async def test_delete_note_raises_domain_error_when_recovery_commit_fails(
    db, mock_qdrant, monkeypatch
):
    note = await create_note(db, {"title": "Del", "content": "C"})
    commit_calls = {"count": 0}

    def _commit_always_fails_in_delete_flow():
        commit_calls["count"] += 1
        raise SQLAlchemyError("sqlite commit failed")

    monkeypatch.setattr(db, "commit", _commit_always_fails_in_delete_flow)

    with pytest.raises(NoteDeleteSyncError, match="failed to delete note row"):
        delete_note(db, note.id)


@pytest.mark.asyncio
async def test_delete_note_reraises_unexpected_sqlite_commit_errors(
    db, mock_qdrant, monkeypatch
):
    note = await create_note(db, {"title": "Del", "content": "C"})

    def _commit_unexpected_failure():
        raise ValueError("unexpected sqlite bug")

    monkeypatch.setattr(db, "commit", _commit_unexpected_failure)

    with pytest.raises(ValueError, match="unexpected sqlite bug"):
        delete_note(db, note.id)


@pytest.mark.asyncio
async def test_delete_note_reraises_unexpected_first_commit_error_when_recovery_succeeds(
    db, mock_qdrant, monkeypatch
):
    note = await create_note(db, {"title": "Del", "content": "C"})
    original_commit = db.commit
    commit_calls = {"count": 0}

    def _commit_first_unexpected_then_succeed():
        commit_calls["count"] += 1
        if commit_calls["count"] == 1:
            raise ValueError("unexpected first commit bug")
        return original_commit()

    monkeypatch.setattr(db, "commit", _commit_first_unexpected_then_succeed)

    with pytest.raises(ValueError, match="unexpected first commit bug"):
        delete_note(db, note.id)

    refreshed = get_note(db, note.id)
    assert refreshed is not None
    assert refreshed.sync_status == "failed"
    assert refreshed.sync_last_error == "vector deleted but sqlite delete failed"


class _CapturedBackgroundTasks:
    def __init__(self):
        self.func = None
        self.args = None

    def add_task(self, func, *args):
        self.func = func
        self.args = args


class _FailingBackgroundTasks:
    def add_task(self, *_args):
        raise RuntimeError("queue unavailable")


class _UnexpectedFailingBackgroundTasks:
    def add_task(self, *_args):
        raise ValueError("unexpected queue bug")


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
    assert len(background_tasks.args) == 3
    assert background_tasks.args[0] == note.id
    assert background_tasks.args[1] == ["alpha"]
    assert background_tasks.args[2] == "update"


@pytest.mark.asyncio
async def test_update_note_async_marks_failed_when_enqueue_fails(db, monkeypatch):
    note = await create_note(db, {"title": "T", "content": "C", "tags": ["x"]})
    monkeypatch.setattr(note_service.settings, "embedding_mode", "async")

    with pytest.raises(RuntimeError, match="queue unavailable"):
        await update_note(
            db,
            note.id,
            {"title": "T2"},
            background_tasks=_FailingBackgroundTasks(),
        )

    refreshed = get_note(db, note.id)
    assert refreshed.synced is False
    assert refreshed.sync_status == "failed"
    assert refreshed.sync_last_error == "queue unavailable"


@pytest.mark.asyncio
async def test_update_note_async_reraises_unexpected_enqueue_errors_without_failure_state(
    db, monkeypatch
):
    note = await create_note(db, {"title": "T", "content": "C", "tags": ["x"]})
    monkeypatch.setattr(note_service.settings, "embedding_mode", "async")

    with pytest.raises(ValueError, match="unexpected queue bug"):
        await update_note(
            db,
            note.id,
            {"title": "T2"},
            background_tasks=_UnexpectedFailingBackgroundTasks(),
        )

    refreshed = get_note(db, note.id)
    assert refreshed.synced is False
    assert refreshed.sync_status == "pending"
    assert refreshed.sync_last_error is None


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
    embed_mock.assert_awaited_once_with(fake_db, fake_note, ["x"], "create")
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
async def test_sync_unsynced_notes_reraises_unexpected_programming_errors(
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
    monkeypatch.setattr(note_service, "SessionLocal", testing_session)
    monkeypatch.setattr(
        note_service,
        "generate_embedding",
        AsyncMock(side_effect=ValueError("bad embedding input")),
    )

    with pytest.raises(ValueError, match="bad embedding input"):
        await note_service.sync_unsynced_notes(limit=10)


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
async def test_embed_and_sync_by_note_id_reraises_non_retryable_programming_error(
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

    with pytest.raises(ValueError, match="invalid embedding input"):
        await note_service._embed_and_sync_by_note_id(note.id, ["x"])

    assert generate_mock.await_count == 1


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
