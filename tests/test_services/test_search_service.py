import pytest
from app.services.note_service import create_note
from app.services.link_service import create_link
from app.services.search_service import search_keyword, search_graph


def test_search_keyword_no_fts_table(db):
    # In-memory SQLite from conftest doesn't have FTS5 table — should return [] not error
    results = search_keyword(db, "anything")
    assert results == []


@pytest.mark.asyncio
async def test_search_graph_bfs(db):
    n1 = await create_note(db, {"title": "Root", "content": "C"})
    n2 = await create_note(db, {"title": "Child", "content": "C"})
    n3 = await create_note(db, {"title": "Grandchild", "content": "C"})
    create_link(db, {"source_id": n1.id, "target_id": n2.id, "relation_type": "r"})
    create_link(db, {"source_id": n2.id, "target_id": n3.id, "relation_type": "r"})

    depth1 = search_graph(db, n1.id, depth=1)
    assert len(depth1) == 1
    assert depth1[0][0].id == n2.id
    assert depth1[0][1] == 1  # distance

    depth2 = search_graph(db, n1.id, depth=2)
    assert len(depth2) == 2
    ids = {n.id for n, _ in depth2}
    assert n2.id in ids and n3.id in ids


@pytest.mark.asyncio
async def test_search_graph_no_links(db):
    n = await create_note(db, {"title": "Isolated", "content": "C"})
    result = search_graph(db, n.id, depth=2)
    assert result == []
