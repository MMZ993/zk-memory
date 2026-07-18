from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ImportEntityType = Literal[
    "notes", "tags", "note_tags", "relation_types", "links", "buffer_notes"
]
ImportMode = Literal["dry_run", "soft", "force"]
ImportID = Annotated[str, Field(min_length=1, max_length=36)]


class ImportNote(BaseModel):
    id: ImportID
    title: str
    content: str
    summary: str | None = None
    tags: list[str] = []
    synced: bool
    sync_status: str
    sync_attempts: int
    sync_last_error: str | None = None
    sync_last_attempt_at: datetime | None = None
    sync_last_success_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ImportTag(BaseModel):
    id: ImportID
    name: str
    created_at: datetime


class ImportNoteTag(BaseModel):
    note_id: ImportID
    tag_id: ImportID
    created_at: datetime

    @property
    def id(self) -> str:
        return f"{self.note_id}:{self.tag_id}"


class ImportRelationType(BaseModel):
    id: ImportID
    name: str
    description: str | None = None
    is_bidirectional: bool
    created_at: datetime


class ImportLink(BaseModel):
    id: ImportID
    source_id: ImportID
    target_id: ImportID
    relation_type_id: ImportID
    description: str | None = None
    created_at: datetime


class ImportBufferNote(BaseModel):
    id: ImportID
    content: str
    meta: dict[str, Any] | None = None
    processed: bool
    processed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ImportDocument(BaseModel):
    version: Literal[1]
    exported_at: datetime
    notes: list[ImportNote]
    tags: list[ImportTag]
    note_tags: list[ImportNoteTag]
    relation_types: list[ImportRelationType]
    links: list[ImportLink]
    buffer_notes: list[ImportBufferNote]

    @model_validator(mode="after")
    def unique_entity_ids(self):
        for name in ("notes", "tags", "relation_types", "links", "buffer_notes"):
            ids = [row.id for row in getattr(self, name)]
            if len(ids) != len(set(ids)):
                raise ValueError(f"duplicate IDs in {name}")
        association_ids = [row.id for row in self.note_tags]
        if len(association_ids) != len(set(association_ids)):
            raise ValueError("duplicate IDs in note_tags")
        for name in ("tags", "relation_types"):
            normalized_names = [row.name.strip().lower() for row in getattr(self, name)]
            if len(normalized_names) != len(set(normalized_names)):
                raise ValueError(f"duplicate names in {name}")
        return self


class ImportSelection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entity_type: ImportEntityType = Field(alias="type")
    entity_id: str = Field(alias="id", min_length=1)


class ImportRequest(BaseModel):
    document: ImportDocument
    mode: ImportMode = "dry_run"
    selection: ImportSelection | None = None
