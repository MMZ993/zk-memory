from sqlalchemy.exc import DataError, IntegrityError

import app.api.notes as notes_api


def test_create_note(client):
    r = client.post("/api/notes/", json={"title": "Hello", "content": "World"})
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Hello"
    assert data["id"] is not None


def test_list_notes(client):
    client.post("/api/notes/", json={"title": "A", "content": "C"})
    client.post("/api/notes/", json={"title": "B", "content": "C"})
    r = client.get("/api/notes/")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_notes_tag_filter(client):
    client.post("/api/notes/", json={"title": "A", "content": "C", "tags": ["ml"]})
    client.post("/api/notes/", json={"title": "B", "content": "C", "tags": ["other"]})
    r = client.get("/api/notes/?tags=ml")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "A"


def test_list_notes_tag_filter_normalizes_case(client):
    client.post("/api/notes/", json={"title": "A", "content": "C", "tags": ["ml"]})
    r = client.get("/api/notes/?tags=ML")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "A"


def test_get_note(client):
    note = client.post("/api/notes/", json={"title": "T", "content": "C"}).json()
    r = client.get(f"/api/notes/{note['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == note["id"]


def test_get_note_not_found(client):
    r = client.get("/api/notes/nonexistent")
    assert r.status_code == 404


def test_update_note(client):
    note = client.post("/api/notes/", json={"title": "Old", "content": "C"}).json()
    r = client.patch(f"/api/notes/{note['id']}", json={"title": "New"})
    assert r.status_code == 200
    assert r.json()["title"] == "New"


def test_delete_note(client):
    note = client.post("/api/notes/", json={"title": "Del", "content": "C"}).json()
    r = client.delete(f"/api/notes/{note['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/notes/{note['id']}").status_code == 404


def test_delete_note_returns_503_when_vector_cleanup_fails(client, mock_qdrant):
    note = client.post("/api/notes/", json={"title": "Del", "content": "C"}).json()
    mock_qdrant.delete.side_effect = RuntimeError("qdrant down")

    r = client.delete(f"/api/notes/{note['id']}")

    assert r.status_code == 503
    assert r.json()["detail"] == "failed to delete note vector"
    assert client.get(f"/api/notes/{note['id']}").status_code == 200


def test_create_note_returns_409_for_integrity_conflict(client, monkeypatch):
    async def _raise_integrity(*args, **kwargs):
        raise IntegrityError("insert", {}, RuntimeError("UNIQUE constraint failed"))

    monkeypatch.setattr(notes_api, "create_note", _raise_integrity)

    r = client.post("/api/notes/", json={"title": "Hello", "content": "World"})

    assert r.status_code == 409
    assert r.json()["detail"] == "integrity conflict"


def test_create_note_returns_422_for_title_length_violation(client):
    r = client.post("/api/notes/", json={"title": "t" * 256, "content": "World"})

    assert r.status_code == 422


def test_update_note_returns_422_for_title_length_violation(client):
    note = client.post("/api/notes/", json={"title": "Old", "content": "C"}).json()

    r = client.patch(f"/api/notes/{note['id']}", json={"title": "t" * 256})

    assert r.status_code == 422


def test_update_note_returns_409_for_integrity_conflict(client, monkeypatch):
    note = client.post("/api/notes/", json={"title": "Old", "content": "C"}).json()

    async def _raise_integrity(*args, **kwargs):
        raise IntegrityError("update", {}, RuntimeError("UNIQUE constraint failed"))

    monkeypatch.setattr(notes_api, "update_note", _raise_integrity)

    r = client.patch(f"/api/notes/{note['id']}", json={"title": "New"})

    assert r.status_code == 409
    assert r.json()["detail"] == "integrity conflict"


def test_add_tag_returns_422_for_data_error(client, monkeypatch):
    note = client.post("/api/notes/", json={"title": "N", "content": "C"}).json()

    def _raise_data_error(*args, **kwargs):
        raise DataError("insert", {}, RuntimeError("value too long"))

    monkeypatch.setattr(notes_api, "add_tag_to_note", _raise_data_error)

    r = client.post(f"/api/notes/{note['id']}/tags", json={"name": "python"})

    assert r.status_code == 422
    assert r.json()["detail"] == "integrity validation failed"


def test_search_keyword(client):
    r = client.get("/api/notes/search?q=hello&search_type=keyword")
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    assert "total" in body


def test_search_hybrid_normalizes_tag_filter_case(client, monkeypatch):
    captured = {}

    async def _search_hybrid(db, q, limit=10, tags=None):
        captured["tags"] = tags
        return []

    monkeypatch.setattr(notes_api, "search_hybrid", _search_hybrid)

    r = client.get("/api/notes/search?q=hello&search_type=hybrid&tags=AI")

    assert r.status_code == 200
    assert captured["tags"] == ["ai"]


def test_note_graph(client):
    note = client.post("/api/notes/", json={"title": "Root", "content": "C"}).json()
    r = client.get(f"/api/notes/{note['id']}/graph")
    assert r.status_code == 200
    body = r.json()
    assert body["results"] == []
    assert body["total"] == 0


def test_note_links(client):
    note = client.post("/api/notes/", json={"title": "N", "content": "C"}).json()
    r = client.get(f"/api/notes/{note['id']}/links")
    assert r.status_code == 200
    assert r.json() == []


def test_note_tags_get_post_delete(client):
    note = client.post("/api/notes/", json={"title": "N", "content": "C"}).json()
    note_id = note["id"]

    # GET tags (empty)
    r = client.get(f"/api/notes/{note_id}/tags")
    assert r.status_code == 200
    assert r.json() == []

    # POST tag
    r = client.post(f"/api/notes/{note_id}/tags", json={"name": "python"})
    assert r.status_code == 201
    tag = r.json()
    assert tag["name"] == "python"

    # GET tags (has one)
    r = client.get(f"/api/notes/{note_id}/tags")
    assert len(r.json()) == 1

    # DELETE tag
    r = client.delete(f"/api/notes/{note_id}/tags/{tag['id']}")
    assert r.status_code == 204

    # GET tags (empty again)
    assert client.get(f"/api/notes/{note_id}/tags").json() == []
