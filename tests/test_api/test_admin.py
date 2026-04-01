import pytest
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.services.admin_service import _reembed_state, start_reembed


def test_sync_embeddings_background_task_payload_avoids_request_session(
    client, monkeypatch
):
    from app.api import admin as admin_api

    captured = []

    def _capture_add_task(self, func, *args, **kwargs):
        captured.append((func, args, kwargs))

    monkeypatch.setattr(BackgroundTasks, "add_task", _capture_add_task)

    r = client.post("/api/admin/sync-embeddings")

    assert r.status_code == 200
    assert len(captured) == 1
    func, args, kwargs = captured[0]
    assert func is admin_api._run_sync_embeddings_job
    assert all(not isinstance(arg, Session) for arg in args)
    assert kwargs == {}


def test_reembed_background_task_payload_avoids_request_session(client, monkeypatch):
    captured = []

    def _capture_add_task(self, func, *args, **kwargs):
        captured.append((func, args, kwargs))

    monkeypatch.setattr(BackgroundTasks, "add_task", _capture_add_task)

    r = client.post(
        "/api/admin/reembed",
        json={
            "confirm": "I understand this will delete and regenerate all embeddings",
        },
    )

    assert r.status_code == 200
    assert len(captured) == 1
    func, args, kwargs = captured[0]
    assert func is start_reembed
    assert all(not isinstance(arg, Session) for arg in args)
    assert kwargs == {}


def test_reembed_endpoint_blocks_second_request_when_job_already_queued(
    client, monkeypatch
):
    _reembed_state.update({"status": "idle", "total": 0, "processed": 0, "failed": 0})
    captured = []

    def _capture_add_task(self, func, *args, **kwargs):
        captured.append((func, args, kwargs))

    monkeypatch.setattr(BackgroundTasks, "add_task", _capture_add_task)

    first = client.post(
        "/api/admin/reembed",
        json={
            "confirm": "I understand this will delete and regenerate all embeddings",
        },
    )
    second = client.post(
        "/api/admin/reembed",
        json={
            "confirm": "I understand this will delete and regenerate all embeddings",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert len(captured) == 1


def test_reembed_endpoint_rolls_back_queued_state_when_enqueue_fails(
    client, monkeypatch
):
    _reembed_state.update({"status": "idle", "total": 0, "processed": 0, "failed": 0})

    def _raise_add_task(self, func, *args, **kwargs):
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(BackgroundTasks, "add_task", _raise_add_task)

    r = client.post(
        "/api/admin/reembed",
        json={
            "confirm": "I understand this will delete and regenerate all embeddings",
        },
    )

    assert r.status_code == 503
    assert _reembed_state["status"] == "idle"


def test_reembed_endpoint_reraises_unexpected_enqueue_errors(client, monkeypatch):
    _reembed_state.update({"status": "idle", "total": 0, "processed": 0, "failed": 0})

    def _raise_add_task(self, func, *args, **kwargs):
        raise ValueError("unexpected enqueue error")

    monkeypatch.setattr(BackgroundTasks, "add_task", _raise_add_task)

    with pytest.raises(ValueError, match="unexpected enqueue error"):
        client.post(
            "/api/admin/reembed",
            json={
                "confirm": "I understand this will delete and regenerate all embeddings",
            },
        )
    assert _reembed_state["status"] == "idle"


def test_sync_embeddings_endpoint_blocks_second_request_when_job_already_queued(
    client, monkeypatch
):
    from app.api import admin as admin_api

    admin_api._sync_embeddings_state.update({"status": "idle", "pending_notes": 0})
    captured = []

    def _capture_add_task(self, func, *args, **kwargs):
        captured.append((func, args, kwargs))

    monkeypatch.setattr(BackgroundTasks, "add_task", _capture_add_task)

    first = client.post("/api/admin/sync-embeddings")
    second = client.post("/api/admin/sync-embeddings")

    assert first.status_code == 200
    assert second.status_code == 409
    assert len(captured) == 1


def test_sync_embeddings_endpoint_rolls_back_queued_state_when_enqueue_fails(
    client, monkeypatch
):
    from app.api import admin as admin_api

    admin_api._sync_embeddings_state.update({"status": "idle", "pending_notes": 0})

    def _raise_add_task(self, func, *args, **kwargs):
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(BackgroundTasks, "add_task", _raise_add_task)

    r = client.post("/api/admin/sync-embeddings")

    assert r.status_code == 503
    assert admin_api._sync_embeddings_state["status"] == "idle"


def test_sync_embeddings_endpoint_reraises_unexpected_enqueue_errors(
    client, monkeypatch
):
    from app.api import admin as admin_api

    admin_api._sync_embeddings_state.update({"status": "idle", "pending_notes": 0})

    def _raise_add_task(self, func, *args, **kwargs):
        raise ValueError("unexpected enqueue error")

    monkeypatch.setattr(BackgroundTasks, "add_task", _raise_add_task)

    with pytest.raises(ValueError, match="unexpected enqueue error"):
        client.post("/api/admin/sync-embeddings")

    assert admin_api._sync_embeddings_state["status"] == "idle"


def test_health_check(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_readiness_check(client):
    r = client.get("/api/readiness")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ready"
    assert data["dependencies"]["database"] == "ok"
    assert data["dependencies"]["qdrant"] == "ok"


def test_readiness_check_returns_503_when_qdrant_unavailable(client, monkeypatch):
    import main as main_module

    def _raise_qdrant_error(*args, **kwargs):
        raise ConnectionError("qdrant unavailable")

    monkeypatch.setattr(
        main_module.qdrant_db.client, "collection_exists", _raise_qdrant_error
    )

    r = client.get("/api/readiness")

    assert r.status_code == 503
    data = r.json()
    assert data["status"] == "not_ready"
    assert data["dependencies"]["database"] == "ok"
    assert data["dependencies"]["qdrant"] == "error"


def test_readiness_check_returns_503_when_qdrant_collection_missing(
    client, monkeypatch
):
    import main as main_module

    monkeypatch.setattr(
        main_module.qdrant_db.client,
        "collection_exists",
        lambda *_args, **_kwargs: False,
    )

    r = client.get("/api/readiness")

    assert r.status_code == 503
    data = r.json()
    assert data["status"] == "not_ready"
    assert data["dependencies"]["qdrant"] == "error"


def test_readiness_check_uses_dependency_injected_db_session(client, monkeypatch):
    from app.api import deps as deps_module

    def _should_not_be_called():
        raise AssertionError(
            "SessionLocal should not be called when get_db is overridden"
        )

    monkeypatch.setattr(deps_module, "SessionLocal", _should_not_be_called)

    r = client.get("/api/readiness")

    assert r.status_code == 200


def test_readiness_check_returns_503_when_database_unavailable(client):
    from sqlalchemy.exc import SQLAlchemyError

    import main as main_module
    from app.api.deps import get_db

    class _BrokenDb:
        def execute(self, *_args, **_kwargs):
            raise SQLAlchemyError("database unavailable")

    def _broken_db_override():
        yield _BrokenDb()

    previous_override = main_module.app.dependency_overrides.get(get_db)
    main_module.app.dependency_overrides[get_db] = _broken_db_override
    try:
        r = client.get("/api/readiness")
    finally:
        if previous_override is None:
            main_module.app.dependency_overrides.pop(get_db, None)
        else:
            main_module.app.dependency_overrides[get_db] = previous_override

    assert r.status_code == 503
    data = r.json()
    assert data["status"] == "not_ready"
    assert data["dependencies"]["database"] == "error"


def test_stats_structure(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    data = r.json()
    assert "notes" in data
    assert "buffer" in data


def test_config_no_secrets(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    data = r.json()
    # Must not expose API keys
    body_str = str(data).lower()
    assert "api_key" not in body_str or data.get("api_key") in (None, "", "***")
    assert "openai_api_key" not in body_str or data.get("openai_api_key") in (
        None,
        "",
        "***",
    )
