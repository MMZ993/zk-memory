from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, pagination
from app.models.schemas import TagCreate, TagResponse
from app.services.tag_service import create_tag, list_tags

router = APIRouter(prefix="/api/tags", tags=["tags"])


class TagWithCount(TagResponse):
    note_count: int = 0


@router.get("/", response_model=list[TagWithCount])
def list_tags_endpoint(page: dict = Depends(pagination), db: Session = Depends(get_db)):
    rows = list_tags(db, **page)
    results = []
    for tag, count in rows:
        item = TagWithCount.model_validate(tag)
        item.note_count = count
        results.append(item)
    return results


@router.post("/", response_model=TagResponse, status_code=201)
def create_tag_endpoint(body: TagCreate, db: Session = Depends(get_db)):
    return create_tag(db, body.name)
