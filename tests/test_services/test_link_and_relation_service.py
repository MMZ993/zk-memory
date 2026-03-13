import pytest
from fastapi import HTTPException
from app.services.note_service import create_note
from app.services.link_service import create_link, delete_link, get_note_links
from app.services.relation_service import (
    create_relation, list_relations, get_relation, update_relation, delete_relation,
)


@pytest.mark.asyncio
async def test_create_link_auto_creates_relation(db):
    n1 = await create_note(db, {"title": "A", "content": "C"})
    n2 = await create_note(db, {"title": "B", "content": "C"})
    link = create_link(db, {"source_id": n1.id, "target_id": n2.id, "relation_type": "supports"})
    assert link.id is not None
    rels = list_relations(db)
    assert any(rt.name == "supports" for rt, _ in rels)


@pytest.mark.asyncio
async def test_link_direction_filter(db):
    n1 = await create_note(db, {"title": "A", "content": "C"})
    n2 = await create_note(db, {"title": "B", "content": "C"})
    create_link(db, {"source_id": n1.id, "target_id": n2.id, "relation_type": "rel"})
    outgoing = get_note_links(db, n1.id, direction="outgoing")
    assert len(outgoing) == 1
    incoming = get_note_links(db, n1.id, direction="incoming")
    assert len(incoming) == 0


@pytest.mark.asyncio
async def test_delete_link(db):
    n1 = await create_note(db, {"title": "A", "content": "C"})
    n2 = await create_note(db, {"title": "B", "content": "C"})
    link = create_link(db, {"source_id": n1.id, "target_id": n2.id, "relation_type": "r"})
    assert delete_link(db, link.id) is True
    assert delete_link(db, link.id) is False


def test_relation_crud(db):
    rt = create_relation(db, {"name": "related_to", "is_bidirectional": True})
    assert rt.is_bidirectional is True
    updated = update_relation(db, rt.id, {"name": "linked_to"})
    assert updated.name == "linked_to"
    assert delete_relation(db, rt.id) is True
    assert get_relation(db, rt.id) is None
