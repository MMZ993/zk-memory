"""Tests for Pydantic schemas in app/models/schemas.py."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from pydantic import ValidationError

from app.models.schemas import (
    BufferNoteCreate,
    BufferNoteResponse,
    NoteCreate,
    NoteUpdate,
    NoteResponse,
    LinkCreate,
    RelationTypeCreate,
    TagCreate,
    TagResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
    MessageResponse,
)
from app.models.enums import SearchType


def _now():
    return datetime.now(timezone.utc)


# ── BufferNote ─────────────────────────────────────────────────────────────────


def test_buffer_note_create_minimal():
    obj = BufferNoteCreate(content="hello")
    assert obj.content == "hello"
    assert obj.meta is None


def test_buffer_note_create_with_meta():
    obj = BufferNoteCreate(content="hello", meta={"source": "chat"})
    assert obj.meta == {"source": "chat"}


def test_buffer_note_response_from_orm():
    now = _now()
    mock_orm = MagicMock()
    mock_orm.id = "abc"
    mock_orm.content = "hi"
    mock_orm.meta = None
    mock_orm.created_at = now
    mock_orm.updated_at = now
    mock_orm.processed = False
    mock_orm.processed_at = None

    resp = BufferNoteResponse.model_validate(mock_orm)
    assert resp.id == "abc"
    assert resp.processed is False


# ── Note ──────────────────────────────────────────────────────────────────────


def test_note_create_defaults():
    obj = NoteCreate(title="T", content="C")
    assert obj.tags == []
    assert obj.summary is None


def test_note_create_with_tags():
    obj = NoteCreate(title="T", content="C", tags=["a", "b"])
    assert obj.tags == ["a", "b"]


def test_note_create_rejects_title_longer_than_db_constraint():
    with pytest.raises(ValidationError, match="at most 255"):
        NoteCreate(title="t" * 256, content="C")


def test_note_update_all_optional():
    obj = NoteUpdate()
    assert obj.title is None
    assert obj.content is None
    assert obj.tags is None


def test_note_response_tags_plain_list():
    """NoteResponse.tags accepts a plain list[str] (e.g. from service layer)."""
    now = _now()
    mock_orm = MagicMock()
    mock_orm.id = "n1"
    mock_orm.title = "T"
    mock_orm.content = "C"
    mock_orm.summary = None
    mock_orm.tags = ["foo", "bar"]
    mock_orm.created_at = now
    mock_orm.updated_at = now
    mock_orm.synced = True

    resp = NoteResponse.model_validate(mock_orm)
    assert resp.tags == ["foo", "bar"]


def test_note_response_tags_from_orm_relationship():
    """NoteResponse.tags extracts names from NoteTag ORM objects."""
    now = _now()

    tag1 = MagicMock()
    tag1.tag.name = "python"
    tag2 = MagicMock()
    tag2.tag.name = "ai"

    mock_orm = MagicMock()
    mock_orm.id = "n2"
    mock_orm.title = "T"
    mock_orm.content = "C"
    mock_orm.summary = None
    mock_orm.tags = [tag1, tag2]
    mock_orm.created_at = now
    mock_orm.updated_at = now
    mock_orm.synced = False

    resp = NoteResponse.model_validate(mock_orm)
    assert set(resp.tags) == {"python", "ai"}


def test_note_response_empty_tags():
    now = _now()
    mock_orm = MagicMock()
    mock_orm.id = "n3"
    mock_orm.title = "T"
    mock_orm.content = "C"
    mock_orm.summary = None
    mock_orm.tags = []
    mock_orm.created_at = now
    mock_orm.updated_at = now
    mock_orm.synced = False

    resp = NoteResponse.model_validate(mock_orm)
    assert resp.tags == []


# ── Link ──────────────────────────────────────────────────────────────────────


def test_link_create():
    obj = LinkCreate(source_id="a", target_id="b", relation_type="related_to")
    assert obj.relation_type == "related_to"
    assert obj.description is None


# ── RelationType ──────────────────────────────────────────────────────────────


def test_relation_type_create_defaults():
    obj = RelationTypeCreate(name="supports")
    assert obj.is_bidirectional is False
    assert obj.description is None


# ── Tag ───────────────────────────────────────────────────────────────────────


def test_tag_create():
    obj = TagCreate(name="python")
    assert obj.name == "python"


def test_tag_create_normalizes_and_rejects_empty():
    obj = TagCreate(name=" AI ")
    assert obj.name == "ai"

    with pytest.raises(ValidationError, match="cannot be empty"):
        TagCreate(name="   ")


# ── Search ────────────────────────────────────────────────────────────────────


def test_search_request_defaults():
    obj = SearchRequest(q="test query")
    assert obj.search_type == SearchType.semantic
    assert obj.limit == 10
    assert obj.tags is None


def test_search_request_keyword():
    obj = SearchRequest(q="test", search_type=SearchType.keyword)
    assert obj.search_type == SearchType.keyword


def test_search_response():
    result = SearchResult(id="x", title="T", score=0.95, tags=["a"])
    resp = SearchResponse(
        results=[result],
        total=1,
        search_type=SearchType.semantic,
    )
    assert resp.total == 1
    assert resp.results[0].score == 0.95


# ── MessageResponse ───────────────────────────────────────────────────────────


def test_message_response():
    resp = MessageResponse(message="deleted")
    assert resp.message == "deleted"
