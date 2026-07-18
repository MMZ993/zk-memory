def _document():
    return {
        "version": 1,
        "exported_at": "2026-07-17T00:00:00Z",
        "notes": [{
            "id": "imported-note", "title": "Imported", "content": "body",
            "summary": None, "tags": [], "synced": False,
            "sync_status": "pending", "sync_attempts": 0,
            "sync_last_error": None, "sync_last_attempt_at": None,
            "sync_last_success_at": None,
            "created_at": "2026-07-17T00:00:00Z",
            "updated_at": "2026-07-17T00:00:00Z",
        }],
        "tags": [], "note_tags": [], "relation_types": [], "links": [],
        "buffer_notes": [],
    }


def test_import_defaults_to_dry_run_and_does_not_mutate(client):
    response = client.post("/api/import/", json={"document": _document()})

    assert response.status_code == 200
    assert response.json()["mode"] == "dry_run"
    assert response.json()["entities"]["notes"][0]["status"] == "new"
    assert client.get("/api/notes/imported-note").status_code == 404


def test_import_rejects_ids_longer_than_database_columns(client):
    document = _document()
    document["notes"][0]["id"] = "x" * 37

    response = client.post("/api/import/", json={"document": document})

    assert response.status_code == 422


def test_soft_import_can_apply_one_selected_json_entity(client):
    document = _document()
    second = dict(document["notes"][0], id="other-note", title="Other")
    document["notes"].append(second)

    response = client.post(
        "/api/import/",
        json={
            "document": document,
            "mode": "soft",
            "selection": {"type": "notes", "id": "imported-note"},
        },
    )

    assert response.status_code == 200
    assert response.json()["entities"]["notes"][0]["resolution"] == "created"
    assert client.get("/api/notes/imported-note").status_code == 200
    assert client.get("/api/notes/other-note").status_code == 404
