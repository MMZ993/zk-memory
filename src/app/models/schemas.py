from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List, Any
from datetime import datetime

from app.models.enums import SearchType
from app.core.config import get_settings

NOTE_TITLE_MAX_LENGTH = 255
TAG_NAME_MAX_LENGTH = 100


def _max_content_length() -> int:
    return get_settings().note_max_content_length


# ── Request schemas ────────────────────────────────────────────────────────────


class BufferNoteCreate(BaseModel):
    content: str
    meta: Optional[dict] = None


class NoteCreate(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    tags: List[str] = []

    @field_validator("content")
    @classmethod
    def content_length(cls, v: str) -> str:
        limit = _max_content_length()
        if limit > 0 and len(v) > limit:
            raise ValueError(
                f"content exceeds maximum length of {limit} characters (got {len(v)})"
            )
        return v

    @field_validator("title")
    @classmethod
    def title_length(cls, v: str) -> str:
        if len(v) > NOTE_TITLE_MAX_LENGTH:
            raise ValueError(
                f"title must be at most {NOTE_TITLE_MAX_LENGTH} characters"
            )
        return v

    @field_validator("tags")
    @classmethod
    def tags_length(cls, v: List[str]) -> List[str]:
        for tag in v:
            normalized_tag = tag.strip()
            if not normalized_tag:
                raise ValueError("tag values cannot be empty")
            if len(normalized_tag) > TAG_NAME_MAX_LENGTH:
                raise ValueError(
                    f"tag must be at most {TAG_NAME_MAX_LENGTH} characters"
                )
        return v


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None

    @field_validator("content")
    @classmethod
    def content_length(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        limit = _max_content_length()
        if limit > 0 and len(v) > limit:
            raise ValueError(
                f"content exceeds maximum length of {limit} characters (got {len(v)})"
            )
        return v

    @field_validator("title")
    @classmethod
    def title_length(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if len(v) > NOTE_TITLE_MAX_LENGTH:
            raise ValueError(
                f"title must be at most {NOTE_TITLE_MAX_LENGTH} characters"
            )
        return v

    @field_validator("tags")
    @classmethod
    def tags_length(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        for tag in v:
            normalized_tag = tag.strip()
            if not normalized_tag:
                raise ValueError("tag values cannot be empty")
            if len(normalized_tag) > TAG_NAME_MAX_LENGTH:
                raise ValueError(
                    f"tag must be at most {TAG_NAME_MAX_LENGTH} characters"
                )
        return v


class LinkCreate(BaseModel):
    source_id: str
    target_id: str
    relation_type: str  # relation type name (looked up or created)
    description: Optional[str] = None


class RelationTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_bidirectional: bool = False


class TagCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def name_constraints(cls, v: str) -> str:
        normalized = v.strip().lower()
        if not normalized:
            raise ValueError("tag values cannot be empty")
        if len(normalized) > TAG_NAME_MAX_LENGTH:
            raise ValueError(f"tag must be at most {TAG_NAME_MAX_LENGTH} characters")
        return normalized


class SearchRequest(BaseModel):
    q: str
    search_type: SearchType = SearchType.semantic
    tags: Optional[List[str]] = None
    limit: int = 10
    graph_depth: int = 1
    graph_start_id: Optional[str] = None


# ── Response schemas ───────────────────────────────────────────────────────────


class BufferNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    content: str
    meta: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    processed: bool
    processed_at: Optional[datetime] = None


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    content: str
    summary: Optional[str] = None
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime
    synced: bool

    @field_validator("tags", mode="before")
    @classmethod
    def extract_tags(cls, v: Any) -> List[str]:
        """Accept either a plain list[str] or SQLAlchemy NoteTag relationship list."""
        if isinstance(v, list) and v and hasattr(v[0], "tag"):
            return [nt.tag.name for nt in v]
        return v or []


class LinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    target_id: str
    relation_type_id: str
    description: Optional[str] = None
    created_at: datetime


class RelationTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    is_bidirectional: bool
    created_at: datetime


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime


class SearchResult(BaseModel):
    id: str
    title: str
    summary: Optional[str] = None
    score: float
    tags: List[str] = []


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    search_type: SearchType


class MessageResponse(BaseModel):
    """Generic success message."""

    message: str
