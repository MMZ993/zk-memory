from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db, pagination, require_read, require_write
from app.models.schemas import TagCreate, TagResponse
from app.services.tag_service import create_tag, list_tags

router = APIRouter(prefix="/api/tags", tags=["tags"])


def _map_integrity_error(exc: Exception):
    detail = str(exc.orig).lower() if exc.orig else str(exc).lower()
    if "unique" in detail or "duplicate" in detail:
        return HTTPException(status_code=409, detail="integrity conflict")
    return HTTPException(status_code=422, detail="integrity validation failed")


class TagWithCount(TagResponse):
    note_count: int = 0


@router.get("/", response_model=list[TagWithCount])
def list_tags_endpoint(
    page: dict = Depends(pagination),
    db: Session = Depends(get_db),
    _: None = Depends(require_read),
):
    rows = list_tags(db, **page)
    results = []
    for tag, count in rows:
        item = TagWithCount.model_validate(tag)
        item.note_count = count
        results.append(item)
    return results


@router.post("/", response_model=TagResponse, status_code=201)
def create_tag_endpoint(
    body: TagCreate, db: Session = Depends(get_db), _: None = Depends(require_write)
):
    try:
        return create_tag(db, body.name)
    except (IntegrityError, DataError) as exc:
        raise _map_integrity_error(exc) from exc
