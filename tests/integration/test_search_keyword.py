"""
Keyword (FTS5) search integration tests.

FTS5 matches exact tokens, so these tests use terms that appear verbatim in
the fixture note content. Results are deterministic regardless of model.
"""

import pytest

pytestmark = pytest.mark.integration


def titles(resp_json) -> list[str]:
    return [r["title"] for r in resp_json["results"]]


def test_keyword_mqtt(client):
    """'MQTT' appears in MQTT Broker Setup and Home Assistant Config."""
    resp = client.get("/api/notes/search", params={
        "q": "MQTT",
        "search_type": "keyword",
        "limit": 10,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert len(found) >= 2
    assert "MQTT Broker Setup" in found
    assert "Home Assistant Core Configuration" in found


def test_keyword_zigbee(client):
    """'Zigbee' appears in Motion Sensors and MQTT Broker notes."""
    resp = client.get("/api/notes/search", params={
        "q": "Zigbee",
        "search_type": "keyword",
        "limit": 10,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert "Motion Sensor Network" in found
    assert "MQTT Broker Setup" in found


def test_keyword_frigate(client):
    """'Frigate' appears in Security Cameras and Home Assistant notes."""
    resp = client.get("/api/notes/search", params={
        "q": "Frigate",
        "search_type": "keyword",
        "limit": 10,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert "Security Camera System" in found
    assert "Home Assistant Core Configuration" in found


def test_keyword_grafana(client):
    """'Grafana' only appears in Energy Monitoring."""
    resp = client.get("/api/notes/search", params={
        "q": "Grafana",
        "search_type": "keyword",
        "limit": 10,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert "Energy Monitoring Dashboard" in found
    assert len(found) == 1


def test_keyword_telegram(client):
    """'Telegram' appears in Motion Sensors and Security Cameras."""
    resp = client.get("/api/notes/search", params={
        "q": "Telegram",
        "search_type": "keyword",
        "limit": 10,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert "Motion Sensor Network" in found
    assert "Security Camera System" in found


def test_keyword_no_match(client):
    """A nonsense query returns an empty result list."""
    resp = client.get("/api/notes/search", params={
        "q": "xyzzy_no_such_term_ever",
        "search_type": "keyword",
        "limit": 10,
    })
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_keyword_limit_respected(client):
    """limit parameter is honoured."""
    resp = client.get("/api/notes/search", params={
        "q": "automation",
        "search_type": "keyword",
        "limit": 2,
    })
    assert resp.status_code == 200
    assert len(resp.json()["results"]) <= 2
