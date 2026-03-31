import pytest
from unittest.mock import AsyncMock, MagicMock

import app.services.admin_service as admin_service


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
    assert kwargs["extra"]["retry_attempt"] == 1
    assert kwargs["extra"]["max_retries"] == 1


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
