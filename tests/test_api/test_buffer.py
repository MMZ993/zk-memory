def test_create_buffer_note(client):
    r = client.post("/api/buffer/", json={"content": "remember this"})
    assert r.status_code == 201
    data = r.json()
    assert data["content"] == "remember this"
    assert data["processed"] is False


def test_list_buffer_notes(client):
    client.post("/api/buffer/", json={"content": "a"})
    client.post("/api/buffer/", json={"content": "b"})
    r = client.get("/api/buffer/")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_buffer_notes_filter_processed(client):
    r1 = client.post("/api/buffer/", json={"content": "a"}).json()
    client.post("/api/buffer/", json={"content": "b"})
    client.post(f"/api/buffer/{r1['id']}/process")

    unprocessed = client.get("/api/buffer/?processed=false").json()
    assert len(unprocessed) == 1
    processed = client.get("/api/buffer/?processed=true").json()
    assert len(processed) == 1


def test_get_buffer_note(client):
    note = client.post("/api/buffer/", json={"content": "x"}).json()
    r = client.get(f"/api/buffer/{note['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == note["id"]


def test_get_buffer_note_not_found(client):
    r = client.get("/api/buffer/nonexistent")
    assert r.status_code == 404


def test_delete_buffer_note(client):
    note = client.post("/api/buffer/", json={"content": "del"}).json()
    r = client.delete(f"/api/buffer/{note['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/buffer/{note['id']}").status_code == 404


def test_process_buffer_note(client):
    note = client.post("/api/buffer/", json={"content": "process me"}).json()
    r = client.post(f"/api/buffer/{note['id']}/process")
    assert r.status_code == 200
    data = r.json()
    assert data["processed"] is True
    assert data["processed_at"] is not None


def test_cleanup_endpoint(client):
    r = client.delete("/api/buffer/cleanup")
    assert r.status_code == 200
    assert "deleted" in r.json()
