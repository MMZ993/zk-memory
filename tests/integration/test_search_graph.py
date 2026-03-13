"""
Graph (BFS) search integration tests.

Graph links are deterministic, so these tests use exact assertions.

Link structure relevant to these tests (undirected BFS):

  Morning Routine ─── Bedroom Lighting
  Morning Routine ─── Kitchen Appliances
  Morning Routine ─── Thermostat ─────── Energy Monitoring

  Away Mode ──────── Motion Sensors ──── Garden Irrigation
  Away Mode ──────── Security Cameras ── Home Assistant ── MQTT Broker
  Away Mode ──────── Thermostat                          ── Voice Assistant

  Home Assistant ─── MQTT Broker
  Home Assistant ─── Security Cameras
  Home Assistant ─── Voice Assistant

  Guest Mode ─────── Living Room AV
  Guest Mode ─────── Security Cameras

Isolated notes (no links): Bedroom Lighting has 1 link (from Morning Routine)
                            Energy Monitoring has 1 link (from Thermostat)
"""

import pytest

pytestmark = pytest.mark.integration


def result_titles(resp_json) -> set[str]:
    return {r["title"] for r in resp_json["results"]}


# ── Morning Routine hub ───────────────────────────────────────────────────────

def test_graph_morning_routine_depth1(client, note_ids):
    note_id = note_ids["Morning Routine Automation"]
    resp = client.get(f"/api/notes/{note_id}/graph", params={"depth": 1})
    assert resp.status_code == 200
    found = result_titles(resp.json())
    assert found == {
        "Bedroom Lighting Scene",
        "Kitchen Appliances Integration",
        "Thermostat Schedule and Zones",
    }


def test_graph_morning_routine_depth2(client, note_ids):
    """Depth 2 should also reach Energy Monitoring (via Thermostat)."""
    note_id = note_ids["Morning Routine Automation"]
    resp = client.get(f"/api/notes/{note_id}/graph", params={"depth": 2})
    assert resp.status_code == 200
    found = result_titles(resp.json())
    assert "Energy Monitoring Dashboard" in found
    assert "Thermostat Schedule and Zones" in found
    assert resp.json()["total"] >= 4


def test_graph_distance_values(client, note_ids):
    """Direct neighbours have distance=1, second-hop have distance=2."""
    note_id = note_ids["Morning Routine Automation"]
    resp = client.get(f"/api/notes/{note_id}/graph", params={"depth": 2})
    assert resp.status_code == 200
    dist_map = {r["title"]: r["distance"] for r in resp.json()["results"]}
    assert dist_map["Thermostat Schedule and Zones"] == 1
    assert dist_map["Energy Monitoring Dashboard"] == 2


# ── Away Mode hub ─────────────────────────────────────────────────────────────

def test_graph_away_mode_depth1(client, note_ids):
    note_id = note_ids["Away Mode Configuration"]
    resp = client.get(f"/api/notes/{note_id}/graph", params={"depth": 1})
    assert resp.status_code == 200
    found = result_titles(resp.json())
    assert found == {
        "Motion Sensor Network",
        "Security Camera System",
        "Thermostat Schedule and Zones",
    }


def test_graph_away_mode_depth2_reaches_garden(client, note_ids):
    """Garden Irrigation links to Motion Sensors → reachable at depth 2 from Away Mode."""
    note_id = note_ids["Away Mode Configuration"]
    resp = client.get(f"/api/notes/{note_id}/graph", params={"depth": 2})
    assert resp.status_code == 200
    found = result_titles(resp.json())
    assert "Garden Irrigation System" in found


# ── Home Assistant hub ────────────────────────────────────────────────────────

def test_graph_home_assistant_depth1(client, note_ids):
    note_id = note_ids["Home Assistant Core Configuration"]
    resp = client.get(f"/api/notes/{note_id}/graph", params={"depth": 1})
    assert resp.status_code == 200
    found = result_titles(resp.json())
    assert found == {
        "MQTT Broker Setup",
        "Security Camera System",
        "Voice Assistant Integration",
    }


def test_graph_home_assistant_depth2_reaches_away_mode(client, note_ids):
    """Away Mode links to Security Cameras → reachable at depth 2 from HA."""
    note_id = note_ids["Home Assistant Core Configuration"]
    resp = client.get(f"/api/notes/{note_id}/graph", params={"depth": 2})
    assert resp.status_code == 200
    found = result_titles(resp.json())
    assert "Away Mode Configuration" in found


# ── Isolated / leaf notes ─────────────────────────────────────────────────────

def test_graph_energy_monitoring_depth1(client, note_ids):
    """Energy Monitoring is a leaf — only one connection (to Thermostat)."""
    note_id = note_ids["Energy Monitoring Dashboard"]
    resp = client.get(f"/api/notes/{note_id}/graph", params={"depth": 1})
    assert resp.status_code == 200
    found = result_titles(resp.json())
    assert "Thermostat Schedule and Zones" in found
    assert resp.json()["total"] == 1


def test_graph_living_room_depth1(client, note_ids):
    """Living Room AV is only linked FROM Guest Mode."""
    note_id = note_ids["Living Room AV Setup"]
    resp = client.get(f"/api/notes/{note_id}/graph", params={"depth": 1})
    assert resp.status_code == 200
    found = result_titles(resp.json())
    assert "Guest Mode Automation" in found


def test_graph_depth_capped_at_3(client, note_ids):
    """API should reject depth > 3."""
    note_id = note_ids["Morning Routine Automation"]
    resp = client.get(f"/api/notes/{note_id}/graph", params={"depth": 5})
    assert resp.status_code == 422


def test_graph_nonexistent_note(client):
    resp = client.get("/api/notes/00000000-0000-0000-0000-000000000000/graph")
    assert resp.status_code == 404
