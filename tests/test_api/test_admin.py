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
    assert "openai_api_key" not in body_str or data.get("openai_api_key") in (None, "", "***")
