"""Verify that the seeded dataset loaded correctly."""

import pytest
from tests.integration.fixtures import NOTES, LINKS


pytestmark = pytest.mark.integration


def test_note_count(client):
    resp = client.get("/api/notes/", params={"limit": 50})
    assert resp.status_code == 200
    assert len(resp.json()) == len(NOTES)


def test_all_notes_synced(client):
    """All notes should have synced=True — embeddings generated at create time."""
    resp = client.get("/api/notes/", params={"limit": 50})
    notes = resp.json()
    unsynced = [n["title"] for n in notes if not n["synced"]]
    assert unsynced == [], f"Notes not synced: {unsynced}"


def test_all_notes_have_tags(client):
    resp = client.get("/api/notes/", params={"limit": 50})
    notes = resp.json()
    missing = [n["title"] for n in notes if not n["tags"]]
    assert missing == [], f"Notes without tags: {missing}"


def test_tags_endpoint_returns_tags(client):
    resp = client.get("/api/tags/")
    assert resp.status_code == 200
    tag_names = {t["name"] for t in resp.json()}
    expected_tags = {"automation", "lighting", "security", "sensors", "energy",
                     "mqtt", "zigbee", "heating", "garden", "home-assistant"}
    assert expected_tags.issubset(tag_names)


def test_links_on_morning_routine(client, note_ids):
    note_id = note_ids["Morning Routine Automation"]
    resp = client.get(f"/api/notes/{note_id}/links", params={"direction": "outgoing"})
    assert resp.status_code == 200
    links = resp.json()
    assert len(links) == 3  # → Bedroom Lighting, Kitchen, Thermostat


def test_links_on_home_assistant(client, note_ids):
    note_id = note_ids["Home Assistant Core Configuration"]
    resp = client.get(f"/api/notes/{note_id}/links", params={"direction": "outgoing"})
    assert resp.status_code == 200
    assert len(resp.json()) == 3  # → MQTT, Cameras, Voice


def test_stats_reflect_seeded_data(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["notes"]["total"] == len(NOTES)
    assert stats["links"]["total"] == len(LINKS)
    assert stats["notes"]["synced"] == len(NOTES)
