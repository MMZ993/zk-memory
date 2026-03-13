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


def test_search_keyword(client):
    r = client.get("/api/notes/search?q=hello&search_type=keyword")
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    assert "total" in body


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
