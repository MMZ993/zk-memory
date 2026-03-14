from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, pagination, require_read, require_write
from app.models.schemas import (
    LinkCreate,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
    TagCreate,
    TagResponse,
    LinkResponse,
)
from app.services.link_service import create_link, delete_link, get_note_links
from app.services.note_service import (
    create_note,
    delete_note,
    get_note,
    list_notes,
    update_note,
)
from app.services.search_service import search_graph, search_hybrid, search_keyword, search_semantic
from app.services.tag_service import add_tag_to_note, get_note_tags, remove_tag_from_note

router = APIRouter(prefix="/api/notes", tags=["notes"])


class NoteSearchResult(NoteResponse):
    score: float = 0.0


class NoteGraphResult(NoteResponse):
    distance: int = 0


# ── Literal routes — MUST be registered before /{note_id} ───────────────────

@router.get("/search")
async def search_notes_endpoint(
    q: str = Query(..., description="Search query text"),
    tags: Optional[str] = Query(default=None, description="Comma-separated tag names"),
    limit: int = Query(default=10, ge=1, le=100),
    threshold: float = Query(default=0.7, ge=0.0, le=1.0),
    search_type: str = Query(default="hybrid", pattern="^(semantic|keyword|hybrid)$"),
    db: Session = Depends(get_db),
    _: None = Depends(require_read),
):
    tag_list = [t.strip() for t in tags.split(",")] if tags else None

    if search_type == "semantic":
        pairs = await search_semantic(db, q, limit=limit, tags=tag_list)
        pairs = [(n, s) for n, s in pairs if s >= threshold]
    elif search_type == "keyword":
        pairs = search_keyword(db, q, limit=limit)
    else:  # hybrid
        pairs = await search_hybrid(db, q, limit=limit, tags=tag_list)
        pairs = [(n, s) for n, s in pairs if s >= threshold or s == 1.0]

    results = []
    for note, score in pairs:
        data = NoteResponse.model_validate(note).model_dump()
        data["score"] = score
        results.append(NoteSearchResult(**data))
    return {"results": results, "total": len(results)}


# ── Link management routes (before /{note_id}) ───────────────────────────────

@router.post("/links", status_code=201)
def create_link_endpoint(body: LinkCreate, db: Session = Depends(get_db), _: None = Depends(require_write)):
    return create_link(db, body.model_dump())


@router.delete("/links/{link_id}", status_code=204)
def delete_link_endpoint(link_id: str, db: Session = Depends(get_db), _: None = Depends(require_write)):
    if not delete_link(db, link_id):
        raise HTTPException(status_code=404, detail="Link not found")


# ── Note CRUD ────────────────────────────────────────────────────────────────

@router.post("/", response_model=NoteResponse, status_code=201)
async def create_note_endpoint(
    note: NoteCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_write),
):
    return await create_note(db, note.model_dump(), background_tasks)


@router.get("/", response_model=list[NoteResponse])
def list_notes_endpoint(
    tags: Optional[str] = Query(default=None, description="Comma-separated tag names"),
    sort: str = Query(default="updated_at", pattern="^(updated_at|created_at)$"),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: dict = Depends(pagination),
    db: Session = Depends(get_db),
    _: None = Depends(require_read),
):
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    return list_notes(db, tags=tag_list, sort=sort, order=order, **page)


@router.get("/{note_id}", response_model=NoteResponse)
def get_note_endpoint(note_id: str, db: Session = Depends(get_db), _: None = Depends(require_read)):
    note = get_note(db, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note_endpoint(
    note_id: str,
    note: NoteUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_write),
):
    updated = await update_note(db, note_id, note.model_dump(exclude_none=True), background_tasks)
    if not updated:
        raise HTTPException(status_code=404, detail="Note not found")
    return updated


@router.delete("/{note_id}", status_code=204)
def delete_note_endpoint(note_id: str, db: Session = Depends(get_db), _: None = Depends(require_write)):
    if not delete_note(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")


# ── Note sub-resources ───────────────────────────────────────────────────────

@router.get("/{note_id}/graph")
def get_note_graph_endpoint(
    note_id: str,
    depth: int = Query(default=1, ge=1, le=3),
    db: Session = Depends(get_db),
    _: None = Depends(require_read),
):
    if not get_note(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    pairs = search_graph(db, note_id, depth=depth)
    results = []
    for note, distance in pairs:
        data = NoteResponse.model_validate(note).model_dump()
        data["distance"] = distance
        results.append(NoteGraphResult(**data))
    return {"results": results, "total": len(results)}


@router.get("/{note_id}/links", response_model=list[LinkResponse])
def get_note_links_endpoint(
    note_id: str,
    direction: str = Query(default="all", pattern="^(all|incoming|outgoing)$"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(require_read),
):
    if not get_note(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return get_note_links(db, note_id, direction=direction, limit=limit)


@router.get("/{note_id}/tags", response_model=list[TagResponse])
def get_note_tags_endpoint(note_id: str, db: Session = Depends(get_db), _: None = Depends(require_read)):
    if not get_note(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return get_note_tags(db, note_id)


@router.post("/{note_id}/tags", response_model=TagResponse, status_code=201)
def add_tag_endpoint(note_id: str, body: TagCreate, db: Session = Depends(get_db), _: None = Depends(require_write)):
    if not get_note(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return add_tag_to_note(db, note_id, body.name)


@router.delete("/{note_id}/tags/{tag_id}", status_code=204)
def remove_tag_endpoint(note_id: str, tag_id: str, db: Session = Depends(get_db), _: None = Depends(require_write)):
    if not get_note(db, note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    if not remove_tag_from_note(db, note_id, tag_id):
        raise HTTPException(status_code=404, detail="Tag association not found")
