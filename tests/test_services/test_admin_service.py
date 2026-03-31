import pytest
from qdrant_client.http.exceptions import ApiException
from unittest.mock import AsyncMock, MagicMock

import app.services.admin_service as admin_service


def test_get_stats_reraises_unexpected_vector_db_errors(db, monkeypatch):
    monkeypatch.setattr(
        admin_service.client,
        "get_collection",
        MagicMock(side_effect=RuntimeError("unexpected vector db failure")),
    )

    with pytest.raises(RuntimeError, match="unexpected vector db failure"):
        admin_service.get_stats(db)


def test_get_stats_logs_and_falls_back_on_qdrant_transport_error(db, monkeypatch):
    mock_logger = MagicMock()
    monkeypatch.setattr(admin_service, "logger", mock_logger, raising=False)
    monkeypatch.setattr(
        admin_service.client,
        "get_collection",
        MagicMock(side_effect=ApiException()),
    )

    stats = admin_service.get_stats(db)

    assert stats["vector_db"] == {"points_count": 0, "segments_count": 0}
    mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_start_reembed_logs_failure_with_retry_metadata(monkeypatch):
    fake_db = MagicMock()
    fake_note = MagicMock(id="note-001", title="T", content="C")
    fake_db.query.return_value.all.return_value = [fake_note]
    mock_logger = MagicMock()

    monkeypatch.setattr(admin_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(admin_service, "logger", mock_logger, raising=False)
    monkeypatch.setattr(admin_service.client, "delete_collection", lambda _: None)
    monkeypatch.setattr(admin_service, "init_qdrant", lambda: None)
    monkeypatch.setattr(
        "app.services.note_service._get_tag_names",
        MagicMock(return_value=["x"]),
    )
    monkeypatch.setattr(
        "app.services.embedding_service.generate_embedding",
        AsyncMock(side_effect=RuntimeError("embedding failed")),
    )

    await admin_service.start_reembed()

    mock_logger.exception.assert_called_once()
    _, kwargs = mock_logger.exception.call_args
    assert kwargs["extra"]["note_id"] == "note-001"
    assert kwargs["extra"]["retry_attempt"] == 2
    assert kwargs["extra"]["max_retries"] == 2


@pytest.mark.asyncio
async def test_start_reembed_uses_fresh_session_and_closes_it(monkeypatch):
    fake_db = MagicMock()
    session_factory = MagicMock(return_value=fake_db)
    fake_db.query.return_value.all.return_value = []

    monkeypatch.setattr(admin_service, "SessionLocal", session_factory)
    monkeypatch.setattr(admin_service.client, "delete_collection", lambda _: None)
    monkeypatch.setattr(admin_service, "init_qdrant", lambda: None)

    await admin_service.start_reembed()

    session_factory.assert_called_once_with()
    fake_db.query.assert_called_once_with(admin_service.Note)
    fake_db.commit.assert_called_once_with()
    fake_db.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_start_reembed_sets_failed_status_when_setup_crashes(monkeypatch):
    fake_db = MagicMock()
    fake_db.query.return_value.all.return_value = []
    admin_service._reembed_state.update(
        {"status": "idle", "total": 0, "processed": 0, "failed": 0}
    )

    monkeypatch.setattr(admin_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(
        admin_service.client,
        "delete_collection",
        MagicMock(side_effect=RuntimeError("qdrant down")),
    )
    monkeypatch.setattr(admin_service, "init_qdrant", lambda: None)

    await admin_service.start_reembed()

    assert admin_service._reembed_state["status"] == "failed"
    fake_db.close.assert_called_once_with()


@pytest.mark.asyncio
async def test_start_reembed_sets_failed_status_when_session_creation_fails(
    monkeypatch,
):
    admin_service._reembed_state.update(
        {"status": "queued", "total": 3, "processed": 0, "failed": 0}
    )
    mock_logger = MagicMock()

    monkeypatch.setattr(
        admin_service,
        "SessionLocal",
        MagicMock(side_effect=RuntimeError("db unavailable")),
    )
    monkeypatch.setattr(admin_service, "logger", mock_logger, raising=False)

    await admin_service.start_reembed()

    assert admin_service._reembed_state["status"] == "failed"
    mock_logger.exception.assert_called_once()


@pytest.mark.asyncio
async def test_start_reembed_happy_path_sets_finished_status_and_counts(monkeypatch):
    fake_db = MagicMock()
    fake_note = MagicMock(id="note-abc", title="T", content="C", synced=False)
    fake_db.query.return_value.all.return_value = [fake_note]
    admin_service._reembed_state.update(
        {"status": "queued", "total": 1, "processed": 0, "failed": 0}
    )

    monkeypatch.setattr(admin_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(admin_service.client, "delete_collection", lambda _: None)
    monkeypatch.setattr(admin_service, "init_qdrant", lambda: None)
    monkeypatch.setattr(
        "app.services.note_service._get_tag_names",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.services.embedding_service.generate_embedding",
        AsyncMock(return_value=[0.1, 0.2]),
    )
    monkeypatch.setattr(
        "app.services.embedding_service.upsert_embedding",
        AsyncMock(return_value=None),
    )

    await admin_service.start_reembed()

    assert admin_service._reembed_state["status"] == "finished"
    assert admin_service._reembed_state["total"] == 1
    assert admin_service._reembed_state["processed"] == 1
    assert admin_service._reembed_state["failed"] == 0


@pytest.mark.asyncio
async def test_start_reembed_retries_transient_embedding_failure(monkeypatch):
    fake_db = MagicMock()
    fake_note = MagicMock(id="note-xyz", title="T", content="C", synced=False)
    fake_db.query.return_value.all.return_value = [fake_note]
    admin_service._reembed_state.update(
        {"status": "queued", "total": 1, "processed": 0, "failed": 0}
    )

    generate_mock = AsyncMock(
        side_effect=[RuntimeError("transient embedding failure"), [0.1, 0.2]]
    )

    monkeypatch.setattr(admin_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(admin_service.client, "delete_collection", lambda _: None)
    monkeypatch.setattr(admin_service, "init_qdrant", lambda: None)
    monkeypatch.setattr(
        "app.services.note_service._get_tag_names",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.services.embedding_service.generate_embedding", generate_mock
    )
    monkeypatch.setattr(
        "app.services.embedding_service.upsert_embedding",
        AsyncMock(return_value=None),
    )

    await admin_service.start_reembed()

    assert generate_mock.await_count == 2
    assert fake_note.synced is True
    assert admin_service._reembed_state["processed"] == 1
    assert admin_service._reembed_state["failed"] == 0


@pytest.mark.asyncio
async def test_start_reembed_continues_when_tag_lookup_fails_for_one_note(monkeypatch):
    fake_db = MagicMock()
    note_fail = MagicMock(id="note-fail", title="T1", content="C1", synced=False)
    note_ok = MagicMock(id="note-ok", title="T2", content="C2", synced=False)
    fake_db.query.return_value.all.return_value = [note_fail, note_ok]
    admin_service._reembed_state.update(
        {"status": "queued", "total": 2, "processed": 0, "failed": 0}
    )

    def _tag_names_side_effect(_db, note_id):
        if note_id == "note-fail":
            raise RuntimeError("tag query failed")
        return []

    monkeypatch.setattr(admin_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(admin_service.client, "delete_collection", lambda _: None)
    monkeypatch.setattr(admin_service, "init_qdrant", lambda: None)
    monkeypatch.setattr(
        "app.services.note_service._get_tag_names",
        MagicMock(side_effect=_tag_names_side_effect),
    )
    monkeypatch.setattr(
        "app.services.embedding_service.generate_embedding",
        AsyncMock(return_value=[0.1, 0.2]),
    )
    monkeypatch.setattr(
        "app.services.embedding_service.upsert_embedding",
        AsyncMock(return_value=None),
    )

    await admin_service.start_reembed()

    assert admin_service._reembed_state["status"] == "finished"
    assert admin_service._reembed_state["processed"] == 1
    assert admin_service._reembed_state["failed"] == 1
    assert note_fail.synced is False
    assert note_ok.synced is True


@pytest.mark.asyncio
async def test_start_reembed_updates_sync_state_metadata_on_terminal_failure(
    monkeypatch,
):
    fake_db = MagicMock()
    fake_note = MagicMock(
        id="note-meta",
        title="T",
        content="C",
        synced=True,
        sync_attempts=4,
        sync_status="synced",
        sync_last_error=None,
        sync_last_attempt_at=None,
        sync_last_success_at=None,
    )
    fake_db.query.return_value.all.return_value = [fake_note]
    admin_service._reembed_state.update(
        {"status": "queued", "total": 1, "processed": 0, "failed": 0}
    )

    monkeypatch.setattr(admin_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(admin_service.client, "delete_collection", lambda _: None)
    monkeypatch.setattr(admin_service, "init_qdrant", lambda: None)
    monkeypatch.setattr(
        "app.services.note_service._get_tag_names",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.services.embedding_service.generate_embedding",
        AsyncMock(side_effect=RuntimeError("embedding failed")),
    )

    await admin_service.start_reembed()

    assert fake_note.synced is False
    assert fake_note.sync_status == "failed"
    assert fake_note.sync_last_error == "embedding failed"
    assert fake_note.sync_attempts == 6
    assert fake_note.sync_last_attempt_at is not None


@pytest.mark.asyncio
async def test_start_reembed_does_not_retry_non_retryable_error(monkeypatch):
    fake_db = MagicMock()
    fake_note = MagicMock(
        id="note-noretry",
        title="T",
        content="C",
        synced=False,
        sync_attempts=0,
        sync_status="pending",
        sync_last_error=None,
        sync_last_attempt_at=None,
        sync_last_success_at=None,
    )
    fake_db.query.return_value.all.return_value = [fake_note]
    admin_service._reembed_state.update(
        {"status": "queued", "total": 1, "processed": 0, "failed": 0}
    )

    generate_mock = AsyncMock(side_effect=ValueError("bad input"))

    monkeypatch.setattr(admin_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(admin_service.client, "delete_collection", lambda _: None)
    monkeypatch.setattr(admin_service, "init_qdrant", lambda: None)
    monkeypatch.setattr(
        "app.services.note_service._get_tag_names",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.services.embedding_service.generate_embedding", generate_mock
    )

    await admin_service.start_reembed()

    assert generate_mock.await_count == 1
    assert admin_service._reembed_state["processed"] == 0
    assert admin_service._reembed_state["failed"] == 1
    assert fake_note.sync_attempts == 1
    assert fake_note.sync_status == "failed"
    assert fake_note.sync_last_error == "bad input"


@pytest.mark.asyncio
async def test_start_reembed_retries_qdrant_api_exception(monkeypatch):
    fake_db = MagicMock()
    fake_note = MagicMock(
        id="note-qdrant",
        title="T",
        content="C",
        synced=False,
        sync_attempts=0,
        sync_status="pending",
        sync_last_error=None,
        sync_last_attempt_at=None,
        sync_last_success_at=None,
    )
    fake_db.query.return_value.all.return_value = [fake_note]
    admin_service._reembed_state.update(
        {"status": "queued", "total": 1, "processed": 0, "failed": 0}
    )

    upsert_mock = AsyncMock(side_effect=[ApiException(), None])

    monkeypatch.setattr(admin_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(admin_service.client, "delete_collection", lambda _: None)
    monkeypatch.setattr(admin_service, "init_qdrant", lambda: None)
    monkeypatch.setattr(
        "app.services.note_service._get_tag_names",
        MagicMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.services.embedding_service.generate_embedding",
        AsyncMock(return_value=[0.1, 0.2]),
    )
    monkeypatch.setattr("app.services.embedding_service.upsert_embedding", upsert_mock)

    await admin_service.start_reembed()

    assert upsert_mock.await_count == 2
    assert admin_service._reembed_state["processed"] == 1
    assert admin_service._reembed_state["failed"] == 0
    assert fake_note.sync_attempts == 2
    assert fake_note.sync_status == "synced"
    assert fake_note.sync_last_error is None


@pytest.mark.asyncio
async def test_start_reembed_builds_embedding_text_with_tags(monkeypatch):
    fake_db = MagicMock()
    fake_note = MagicMock(id="note-tags", title="T", content="C", synced=False)
    fake_db.query.return_value.all.return_value = [fake_note]
    admin_service._reembed_state.update(
        {"status": "queued", "total": 1, "processed": 0, "failed": 0}
    )

    generate_mock = AsyncMock(return_value=[0.1, 0.2])

    monkeypatch.setattr(admin_service, "SessionLocal", lambda: fake_db)
    monkeypatch.setattr(admin_service.client, "delete_collection", lambda _: None)
    monkeypatch.setattr(admin_service, "init_qdrant", lambda: None)
    monkeypatch.setattr(
        "app.services.note_service._get_tag_names",
        MagicMock(return_value=["alpha", "beta"]),
    )
    monkeypatch.setattr(
        "app.services.embedding_service.generate_embedding", generate_mock
    )
    monkeypatch.setattr(
        "app.services.embedding_service.upsert_embedding",
        AsyncMock(return_value=None),
    )

    await admin_service.start_reembed()

    generate_mock.assert_awaited_once_with("T\n\nC\n\nTags: alpha, beta")
