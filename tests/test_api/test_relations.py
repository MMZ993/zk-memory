def test_list_relations_empty(client):
    r = client.get("/api/relations/")
    assert r.status_code == 200
    assert r.json() == []


def test_create_relation(client):
    r = client.post("/api/relations/", json={"name": "supports", "is_bidirectional": False})
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "supports"
    assert "id" in data


def test_get_relation(client):
    rt = client.post("/api/relations/", json={"name": "related_to"}).json()
    r = client.get(f"/api/relations/{rt['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "related_to"


def test_get_relation_not_found(client):
    r = client.get("/api/relations/nonexistent")
    assert r.status_code == 404


def test_update_relation(client):
    rt = client.post("/api/relations/", json={"name": "old_name"}).json()
    r = client.put(f"/api/relations/{rt['id']}", json={"name": "new_name"})
    assert r.status_code == 200
    assert r.json()["name"] == "new_name"


def test_delete_relation(client):
    rt = client.post("/api/relations/", json={"name": "temp"}).json()
    r = client.delete(f"/api/relations/{rt['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/relations/{rt['id']}").status_code == 404
