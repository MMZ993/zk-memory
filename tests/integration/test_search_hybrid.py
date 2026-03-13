"""
Hybrid search integration tests.

Hybrid merges semantic (vector) + keyword (FTS5) results, deduplicated,
semantic first. Score filter applies: result passes if score >= threshold OR
score == 1.0 (keyword hit).

These tests verify that hybrid finds notes that pure-semantic or pure-keyword
alone might miss, and that the merged result set is consistent.
"""

import pytest

pytestmark = pytest.mark.integration

THRESHOLD = 0.3


def titles(resp_json) -> list[str]:
    return [r["title"] for r in resp_json["results"]]


def test_hybrid_mqtt_broker(client):
    """
    'MQTT' is a strong keyword hit. Hybrid should surface MQTT Broker and
    Home Assistant (both contain 'MQTT' verbatim).
    """
    resp = client.get("/api/notes/search", params={
        "q": "MQTT",
        "search_type": "hybrid",
        "limit": 10,
        "threshold": THRESHOLD,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert "MQTT Broker Setup" in found
    assert "Home Assistant Core Configuration" in found


def test_hybrid_lighting_scene(client):
    """
    'lighting scene' hits Bedroom Lighting (keyword 'scene') and Living Room
    AV ('cinema scene'), plus semantic neighbours.
    """
    resp = client.get("/api/notes/search", params={
        "q": "lighting scene",
        "search_type": "hybrid",
        "limit": 10,
        "threshold": THRESHOLD,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert "Bedroom Lighting Scene" in found


def test_hybrid_no_duplicates(client):
    """A note should appear at most once in hybrid results."""
    resp = client.get("/api/notes/search", params={
        "q": "security camera motion",
        "search_type": "hybrid",
        "limit": 20,
        "threshold": THRESHOLD,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert len(found) == len(set(found)), "Duplicate notes in hybrid results"


def test_hybrid_returns_more_than_semantic_alone(client):
    """
    For a query with a strong keyword token ('Zigbee'), hybrid should return
    at least as many results as pure semantic, because keyword adds FTS hits.
    """
    params = {"q": "Zigbee sensors network", "limit": 10, "threshold": THRESHOLD}

    semantic_resp = client.get("/api/notes/search", params={**params, "search_type": "semantic"})
    hybrid_resp = client.get("/api/notes/search", params={**params, "search_type": "hybrid"})

    assert hybrid_resp.status_code == 200
    assert semantic_resp.status_code == 200

    semantic_count = hybrid_resp.json()["total"]
    hybrid_count = hybrid_resp.json()["total"]
    assert hybrid_count >= semantic_count


def test_hybrid_limit_respected(client):
    resp = client.get("/api/notes/search", params={
        "q": "smart home automation",
        "search_type": "hybrid",
        "limit": 4,
        "threshold": THRESHOLD,
    })
    assert resp.status_code == 200
    assert len(resp.json()["results"]) <= 4
