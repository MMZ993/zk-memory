"""
Buffer note integration tests.

Buffer notes are stored in SQLite only (no embedding). These tests use the
shared session-scoped client but manage their own buffer notes — each test
creates what it needs and cleans up after itself via explicit DELETE calls,
so tests remain independent even when sharing the same DB.
"""

import pytest
from tests.integration.fixtures import BUFFER_NOTES

pytestmark = pytest.mark.integration


# ── Helpers ───────────────────────────────────────────────────────────────────

def create_note(client, content="Test buffer note", meta=None):
    resp = client.post("/api/buffer/", json={"content": content, "meta": meta})
    assert resp.status_code == 201
    return resp.json()


def delete_note(client, note_id):
    client.delete(f"/api/buffer/{note_id}")


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_create_buffer_note(client):
    note = create_note(client, content="Remember to check Zigbee firmware")
    try:
        assert note["content"] == "Remember to check Zigbee firmware"
        assert note["processed"] is False
        assert note["processed_at"] is None
        assert "id" in note
    finally:
        delete_note(client, note["id"])


def test_create_buffer_note_with_meta(client):
    note = create_note(client, content="Research Matter protocol", meta={"priority": "high"})
    try:
        assert note["meta"] == {"priority": "high"}
    finally:
        delete_note(client, note["id"])


def test_get_buffer_note(client):
    note = create_note(client, content="Check NAS storage capacity")
    try:
        resp = client.get(f"/api/buffer/{note['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == note["id"]
    finally:
        delete_note(client, note["id"])


def test_get_buffer_note_not_found(client):
    resp = client.get("/api/buffer/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_mark_processed(client):
    note = create_note(client, content="Idea: add water leak sensor under sink")
    try:
        resp = client.post(f"/api/buffer/{note['id']}/process")
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["processed"] is True
        assert updated["processed_at"] is not None
    finally:
        delete_note(client, note["id"])


def test_list_buffer_unprocessed_filter(client):
    """Filter processed=false returns only unprocessed notes."""
    n1 = create_note(client, content="Unprocessed idea A")
    n2 = create_note(client, content="Unprocessed idea B")
    try:
        client.post(f"/api/buffer/{n2['id']}/process")

        resp = client.get("/api/buffer/", params={"processed": "false", "limit": 50})
        assert resp.status_code == 200
        ids = {n["id"] for n in resp.json()}
        assert n1["id"] in ids
        assert n2["id"] not in ids
    finally:
        delete_note(client, n1["id"])
        delete_note(client, n2["id"])


def test_list_buffer_processed_filter(client):
    """Filter processed=true returns only processed notes."""
    note = create_note(client, content="Something to process")
    try:
        client.post(f"/api/buffer/{note['id']}/process")

        resp = client.get("/api/buffer/", params={"processed": "true", "limit": 50})
        assert resp.status_code == 200
        ids = {n["id"] for n in resp.json()}
        assert note["id"] in ids
    finally:
        delete_note(client, note["id"])


def test_delete_buffer_note(client):
    note = create_note(client, content="Temporary thought to delete")
    resp = client.delete(f"/api/buffer/{note['id']}")
    assert resp.status_code == 204
    # Verify it's gone
    assert client.get(f"/api/buffer/{note['id']}").status_code == 404


def test_seed_buffer_notes(client):
    """Seed all sample buffer notes and verify they appear in the list."""
    created_ids = []
    try:
        for sample in BUFFER_NOTES:
            note = create_note(client, content=sample["content"], meta=sample["meta"])
            created_ids.append(note["id"])

        resp = client.get("/api/buffer/", params={"limit": 50})
        assert resp.status_code == 200
        existing_ids = {n["id"] for n in resp.json()}
        for cid in created_ids:
            assert cid in existing_ids
    finally:
        for cid in created_ids:
            delete_note(client, cid)
