from sqlalchemy.exc import DataError, IntegrityError

import app.api.tags as tags_api


def test_list_tags_empty(client):
    r = client.get("/api/tags/")
    assert r.status_code == 200
    assert r.json() == []


def test_create_tag(client):
    r = client.post("/api/tags/", json={"name": "python"})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "python"
    assert "id" in data


def test_create_tag_idempotent(client):
    r1 = client.post("/api/tags/", json={"name": "ml"}).json()
    r2 = client.post("/api/tags/", json={"name": "ml"}).json()
    assert r1["id"] == r2["id"]


def test_list_tags_with_count(client):
    client.post("/api/tags/", json={"name": "a"})
    client.post("/api/tags/", json={"name": "b"})
    r = client.get("/api/tags/")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    for item in data:
        assert "note_count" in item


def test_create_tag_returns_422_for_data_error(client, monkeypatch):
    def _raise_data_error(*args, **kwargs):
        raise DataError("insert", {}, RuntimeError("value too long"))

    monkeypatch.setattr(tags_api, "create_tag", _raise_data_error)

    r = client.post("/api/tags/", json={"name": "python"})

    assert r.status_code == 422
    assert r.json()["detail"] == "integrity validation failed"


def test_create_tag_returns_409_for_integrity_conflict(client, monkeypatch):
    def _raise_integrity(*args, **kwargs):
        raise IntegrityError("insert", {}, RuntimeError("UNIQUE constraint failed"))

    monkeypatch.setattr(tags_api, "create_tag", _raise_integrity)

    r = client.post("/api/tags/", json={"name": "python"})

    assert r.status_code == 409
    assert r.json()["detail"] == "integrity conflict"
