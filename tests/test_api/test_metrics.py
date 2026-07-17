import re
from datetime import datetime, timedelta, timezone

from app.metrics import render_metrics
from app.models.database import Note


def _metric_value(metrics: str, name: str) -> float:
    match = re.search(rf"^{name} (\d+(?:\.\d+)?)$", metrics, re.MULTILINE)
    assert match is not None
    return float(match.group(1))


def test_metrics_exposes_current_inventory_and_tag_counts(client):
    client.post(
        "/api/notes/",
        json={"title": "Tagged", "content": "Content", "tags": ["ml"]},
    )
    client.post("/api/buffer/", json={"content": "remember this"})

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "memory_notes 1.0" in response.text
    assert "memory_tags 1.0" in response.text
    assert "memory_links 0.0" in response.text
    assert "memory_buffer_notes 1.0" in response.text
    assert "memory_sync_pending_notes 0.0" in response.text
    assert "memory_sync_oldest_pending_seconds 0.0" in response.text
    assert 'memory_notes_by_tag{tag="ml"} 1.0' in response.text
    assert 'memory_sync_operations_total{operation="create",result="success"}' in response.text


def test_metrics_use_route_templates_for_http_requests(client):
    note = client.post(
        "/api/notes/", json={"title": "Note", "content": "Content"}
    ).json()

    response = client.get(f"/api/notes/{note['id']}")
    metrics = client.get("/metrics").text

    assert response.status_code == 200
    assert (
        'memory_http_requests_total{method="GET",path="/api/notes/{note_id}",status="200"}'
        in metrics
    )
    assert 'memory_http_request_duration_seconds_bucket{le=' in metrics
    assert note["id"] not in metrics


def test_metrics_normalize_unknown_http_methods(client):
    client.request("CUSTOM", "/api/health")

    metrics = client.get("/metrics").text

    assert 'memory_http_requests_total{method="OTHER"' in metrics
    assert 'method="CUSTOM"' not in metrics


def test_metrics_reports_oldest_pending_sync_age(db):
    now = datetime.now(timezone.utc)
    db.add(
        Note(
            id="pending-note",
            title="Pending",
            content="Content",
            created_at=now - timedelta(seconds=30),
            updated_at=now - timedelta(seconds=30),
            synced=False,
            sync_status="pending",
        )
    )
    db.commit()

    metrics = render_metrics(db).decode()

    age = _metric_value(metrics, "memory_sync_oldest_pending_seconds")
    assert age >= 30


def test_metrics_count_note_and_buffer_activity(client):
    before = client.get("/metrics").text
    before_notes_created = _metric_value(before, "memory_notes_created_total")
    before_notes_reads = _metric_value(before, "memory_notes_reads_total")
    before_buffer_created = _metric_value(before, "memory_buffer_created_total")
    before_buffer_reads = _metric_value(before, "memory_buffer_reads_total")

    note = client.post(
        "/api/notes/", json={"title": "Note", "content": "Content"}
    ).json()
    client.get(f"/api/notes/{note['id']}")
    client.post("/api/buffer/", json={"content": "buffer"})
    client.get("/api/buffer/")

    after = client.get("/metrics").text

    assert (
        _metric_value(after, "memory_notes_created_total") == before_notes_created + 1
    )
    assert _metric_value(after, "memory_notes_reads_total") == before_notes_reads + 1
    assert (
        _metric_value(after, "memory_buffer_created_total") == before_buffer_created + 1
    )
    assert _metric_value(after, "memory_buffer_reads_total") == before_buffer_reads + 1
