import pytest
from app.services.note_service import create_note
from app.services.tag_service import (
    create_tag, list_tags, get_note_tags, add_tag_to_note, remove_tag_from_note,
)


def test_create_tag_idempotent(db):
    t1 = create_tag(db, "python")
    t2 = create_tag(db, "python")
    assert t1.id == t2.id


def test_list_tags_with_count(db):
    create_tag(db, "a")
    create_tag(db, "b")
    rows = list_tags(db)
    assert len(rows) == 2
    for tag, count in rows:
        assert count == 0


@pytest.mark.asyncio
async def test_add_and_remove_tag(db):
    note = await create_note(db, {"title": "T", "content": "C"})
    tag = add_tag_to_note(db, note.id, "ml")
    assert tag.name == "ml"
    tags = get_note_tags(db, note.id)
    assert any(t.name == "ml" for t in tags)
    removed = remove_tag_from_note(db, note.id, tag.id)
    assert removed is True
    assert get_note_tags(db, note.id) == []


@pytest.mark.asyncio
async def test_add_tag_idempotent(db):
    note = await create_note(db, {"title": "T", "content": "C"})
    add_tag_to_note(db, note.id, "ml")
    add_tag_to_note(db, note.id, "ml")  # should not duplicate
    tags = get_note_tags(db, note.id)
    assert len(tags) == 1
