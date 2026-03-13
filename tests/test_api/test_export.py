def test_export_all_is_list(client):
    r = client.get("/api/export/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_export_notes_is_list(client):
    r = client.get("/api/export/notes")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_export_buffer_is_list(client):
    r = client.get("/api/export/buffer")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_export_notes_includes_created_notes(client):
    client.post("/api/notes/", json={"title": "Exported", "content": "body"})
    r = client.get("/api/export/notes")
    data = r.json()
    assert len(data) == 1
    assert data[0]["title"] == "Exported"


def test_export_buffer_includes_buffer_notes(client):
    client.post("/api/buffer/", json={"content": "buf note"})
    r = client.get("/api/export/buffer")
    data = r.json()
    assert len(data) == 1
    assert data[0]["content"] == "buf note"
