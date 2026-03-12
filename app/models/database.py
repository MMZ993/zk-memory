from sqlalchemy import Column, String, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime, timezone
import uuid


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


def new_uuid() -> str:
    return str(uuid.uuid4())


class Note(Base):
    __tablename__ = "notes"

    id = Column(String(36), primary_key=True, default=new_uuid)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)
    synced = Column(Boolean, default=False, nullable=False)

    note_tags = relationship("NoteTag", back_populates="note", cascade="all, delete-orphan")


class RelationType(Base):
    __tablename__ = "relation_types"

    id = Column(String(36), primary_key=True, default=new_uuid)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_bidirectional = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)


class Link(Base):
    __tablename__ = "links"

    id = Column(String(36), primary_key=True, default=new_uuid)
    source_id = Column(String(36), ForeignKey("notes.id"), nullable=False)
    target_id = Column(String(36), ForeignKey("notes.id"), nullable=False)
    relation_type_id = Column(String(36), ForeignKey("relation_types.id"), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_now, nullable=False)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(String(36), primary_key=True, default=new_uuid)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)

    note_tags = relationship("NoteTag", back_populates="tag")


class NoteTag(Base):
    __tablename__ = "note_tags"

    note_id = Column(String(36), ForeignKey("notes.id"), primary_key=True)
    tag_id = Column(String(36), ForeignKey("tags.id"), primary_key=True)
    created_at = Column(DateTime, default=_now, nullable=False)

    note = relationship("Note", back_populates="note_tags")
    tag = relationship("Tag", back_populates="note_tags")


class BufferNote(Base):
    __tablename__ = "buffer_notes"

    id = Column(String(36), primary_key=True, default=new_uuid)
    content = Column(Text, nullable=False)
    meta = Column(JSON, nullable=True)  # renamed from metadata to avoid SQLAlchemy reserved attr
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)
    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime, nullable=True)


class Metadata(Base):
    __tablename__ = "metadata"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=_now, nullable=False)
