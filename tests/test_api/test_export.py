def test_export_all_returns_versioned_lossless_document(client):
    source = client.post(
        "/api/notes/",
        json={"title": "Source", "content": "body", "tags": ["exported"]},
    ).json()
    target = client.post(
        "/api/notes/", json={"title": "Target", "content": "target body"}
    ).json()
    relation = client.post(
        "/api/relations/",
        json={
            "name": "references",
            "description": "Points to related material",
            "is_bidirectional": False,
        },
    ).json()
    link = client.post(
        "/api/notes/links",
        json={
            "source_id": source["id"],
            "target_id": target["id"],
            "relation_type": "references",
            "description": "Useful context",
        },
    ).json()
    buffer_note = client.post(
        "/api/buffer/", json={"content": "inbox", "meta": {"source": "test"}}
    ).json()

    response = client.get("/api/export/")

    assert response.status_code == 200
    document = response.json()
    assert document["version"] == 1
    assert document["exported_at"]
    assert {note["id"] for note in document["notes"]} == {
        source["id"],
        target["id"],
    }
    assert document["tags"][0]["name"] == "exported"
    assert document["note_tags"][0]["note_id"] == source["id"]
    assert document["note_tags"][0]["tag_id"] == document["tags"][0]["id"]
    assert document["relation_types"][0]["id"] == relation["id"]
    assert document["links"][0]["id"] == link["id"]
    assert document["buffer_notes"][0]["id"] == buffer_note["id"]
    for collection in (
        "notes",
        "tags",
        "note_tags",
        "relation_types",
        "links",
        "buffer_notes",
    ):
        assert all("created_at" in item for item in document[collection])


def test_export_all_sorts_projected_note_tags(client):
    client.post(
        "/api/notes/",
        json={"title": "Sorted", "content": "body", "tags": ["zeta", "alpha"]},
    )
    document = client.get("/api/export/").json()
    assert document["notes"][0]["tags"] == ["alpha", "zeta"]


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
