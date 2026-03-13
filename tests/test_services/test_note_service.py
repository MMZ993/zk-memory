import pytest
from app.services.note_service import create_note, get_note, list_notes, update_note, delete_note


@pytest.mark.asyncio
async def test_create_note(db):
    note = await create_note(db, {"title": "T", "content": "C", "tags": ["x"]})
    assert note.id is not None
    assert note.synced is True  # sync mode: embedding runs before return
    assert note.title == "T"


@pytest.mark.asyncio
async def test_get_note(db):
    note = await create_note(db, {"title": "T", "content": "C"})
    fetched = get_note(db, note.id)
    assert fetched.id == note.id


@pytest.mark.asyncio
async def test_list_notes_tag_filter(db):
    await create_note(db, {"title": "A", "content": "C", "tags": ["ml"]})
    await create_note(db, {"title": "B", "content": "C", "tags": ["other"]})
    results = list_notes(db, tags=["ml"])
    assert len(results) == 1
    assert results[0].title == "A"


@pytest.mark.asyncio
async def test_update_note(db):
    note = await create_note(db, {"title": "Old", "content": "C"})
    updated = await update_note(db, note.id, {"title": "New"})
    assert updated.title == "New"
    assert updated.synced is True


@pytest.mark.asyncio
async def test_delete_note(db, mock_qdrant):
    note = await create_note(db, {"title": "Del", "content": "C"})
    assert delete_note(db, note.id) is True
    assert get_note(db, note.id) is None
    mock_qdrant.delete.assert_called()


@pytest.mark.asyncio
async def test_delete_note_not_found(db):
    assert delete_note(db, "bad-id") is False
