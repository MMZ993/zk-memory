import pytest
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.services.admin_service import _reembed_state, start_reembed
from app.services.note_service import sync_unsynced_notes


def test_sync_embeddings_background_task_payload_avoids_request_session(
    client, monkeypatch
):
    captured = []

    def _capture_add_task(self, func, *args, **kwargs):
        captured.append((func, args, kwargs))

    monkeypatch.setattr(BackgroundTasks, "add_task", _capture_add_task)

    r = client.post("/api/admin/sync-embeddings")

    assert r.status_code == 200
    assert len(captured) == 1
    func, args, kwargs = captured[0]
    assert func is sync_unsynced_notes
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


def test_health_check(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert "version" in data


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
