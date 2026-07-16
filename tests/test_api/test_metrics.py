import re


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
    assert 'memory_notes_by_tag{tag="ml"} 1.0' in response.text
    assert 'memory_sync_operations_total{operation="create",result="success"}' in response.text


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
