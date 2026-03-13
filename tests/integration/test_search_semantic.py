"""
Semantic (vector) search integration tests.

Queries are intentionally paraphrased — different words, same meaning — to
exercise embedding similarity rather than keyword matching.

Assertions are intentionally loose (top-N) because cosine similarity scores
vary by model version. The important invariant is that the most relevant note
appears somewhere in the top results, not that it's always rank-1.
"""

import pytest

pytestmark = pytest.mark.integration

THRESHOLD = 0.3  # lower than the API default of 0.7 to ensure results appear


def titles(resp_json) -> list[str]:
    return [r["title"] for r in resp_json["results"]]


def test_semantic_wake_up_morning(client):
    """'Wake up, prepare breakfast' → Morning Routine should be top result."""
    resp = client.get("/api/notes/search", params={
        "q": "wake up prepare breakfast start the day",
        "search_type": "semantic",
        "limit": 5,
        "threshold": THRESHOLD,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert "Morning Routine Automation" in found[:3], (
        f"Expected Morning Routine in top 3, got: {found}"
    )


def test_semantic_nobody_home_security(client):
    """'Nobody at home, protecting the house' → Away Mode should appear."""
    resp = client.get("/api/notes/search", params={
        "q": "nobody at home protecting the house from intruders",
        "search_type": "semantic",
        "limit": 5,
        "threshold": THRESHOLD,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert "Away Mode Configuration" in found[:3], (
        f"Expected Away Mode in top 3, got: {found}"
    )


def test_semantic_watering_plants(client):
    """'Watering plants automatically in the yard' → Garden Irrigation."""
    resp = client.get("/api/notes/search", params={
        "q": "watering plants automatically yard sprinklers",
        "search_type": "semantic",
        "limit": 5,
        "threshold": THRESHOLD,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert "Garden Irrigation System" in found[:3], (
        f"Expected Garden Irrigation in top 3, got: {found}"
    )


def test_semantic_television_cinema(client):
    """'Watching a movie on the big television' → Living Room AV."""
    resp = client.get("/api/notes/search", params={
        "q": "watching a movie on big television screen speakers",
        "search_type": "semantic",
        "limit": 5,
        "threshold": THRESHOLD,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert "Living Room AV Setup" in found[:3], (
        f"Expected Living Room AV in top 3, got: {found}"
    )


def test_semantic_heating_temperature(client):
    """'Controlling room temperature and heating schedule' → Thermostat."""
    resp = client.get("/api/notes/search", params={
        "q": "controlling room temperature heating schedule zones",
        "search_type": "semantic",
        "limit": 5,
        "threshold": THRESHOLD,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert "Thermostat Schedule and Zones" in found[:3], (
        f"Expected Thermostat in top 3, got: {found}"
    )


def test_semantic_power_usage_solar(client):
    """'Tracking electricity usage and renewable power generation' → Energy."""
    resp = client.get("/api/notes/search", params={
        "q": "tracking electricity usage renewable power generation solar panels",
        "search_type": "semantic",
        "limit": 5,
        "threshold": THRESHOLD,
    })
    assert resp.status_code == 200
    found = titles(resp.json())
    assert "Energy Monitoring Dashboard" in found[:3], (
        f"Expected Energy Monitoring in top 3, got: {found}"
    )


def test_semantic_with_tag_filter(client):
    """Semantic search filtered by tag 'bedroom' should only return bedroom notes."""
    resp = client.get("/api/notes/search", params={
        "q": "sleeping room night darkness",
        "search_type": "semantic",
        "tags": "bedroom",
        "limit": 10,
        "threshold": THRESHOLD,
    })
    assert resp.status_code == 200
    results = resp.json()["results"]
    # All returned notes must have bedroom tag
    for r in results:
        assert "bedroom" in r["tags"], (
            f"Note '{r['title']}' returned but lacks bedroom tag"
        )
    # Bedroom Lighting should be present
    assert any(r["title"] == "Bedroom Lighting Scene" for r in results)


def test_semantic_returns_scores(client):
    """Each result must carry a numeric similarity score."""
    resp = client.get("/api/notes/search", params={
        "q": "home automation control",
        "search_type": "semantic",
        "limit": 5,
        "threshold": THRESHOLD,
    })
    assert resp.status_code == 200
    for r in resp.json()["results"]:
        assert isinstance(r["score"], float)
        assert 0.0 <= r["score"] <= 1.0


def test_semantic_limit_respected(client):
    resp = client.get("/api/notes/search", params={
        "q": "smart home devices",
        "search_type": "semantic",
        "limit": 3,
        "threshold": THRESHOLD,
    })
    assert resp.status_code == 200
    assert len(resp.json()["results"]) <= 3
