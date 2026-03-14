from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_read, require_write
from app.models.schemas import RelationTypeCreate, RelationTypeResponse
from app.services.relation_service import (
    create_relation,
    delete_relation,
    get_relation,
    list_relations,
    update_relation,
)

router = APIRouter(prefix="/api/relations", tags=["relations"])


class RelationTypeWithCount(RelationTypeResponse):
    link_count: int = 0


class RelationTypeUpdate(RelationTypeCreate):
    name: str | None = None


@router.get("/", response_model=list[RelationTypeWithCount])
def list_relations_endpoint(db: Session = Depends(get_db), _: None = Depends(require_read)):
    rows = list_relations(db)
    results = []
    for rt, count in rows:
        item = RelationTypeWithCount.model_validate(rt)
        item.link_count = count
        results.append(item)
    return results


@router.post("/", response_model=RelationTypeResponse, status_code=201)
def create_relation_endpoint(body: RelationTypeCreate, db: Session = Depends(get_db), _: None = Depends(require_write)):
    return create_relation(db, body.model_dump())


@router.get("/{relation_id}", response_model=RelationTypeResponse)
def get_relation_endpoint(relation_id: str, db: Session = Depends(get_db), _: None = Depends(require_read)):
    rt = get_relation(db, relation_id)
    if not rt:
        raise HTTPException(status_code=404, detail="Relation type not found")
    return rt


@router.put("/{relation_id}", response_model=RelationTypeResponse)
def update_relation_endpoint(
    relation_id: str, body: RelationTypeUpdate, db: Session = Depends(get_db), _: None = Depends(require_write)
):
    rt = update_relation(db, relation_id, body.model_dump(exclude_none=True))
    if not rt:
        raise HTTPException(status_code=404, detail="Relation type not found")
    return rt


@router.delete("/{relation_id}", status_code=204)
def delete_relation_endpoint(relation_id: str, db: Session = Depends(get_db), _: None = Depends(require_write)):
    if not delete_relation(db, relation_id):
        raise HTTPException(status_code=404, detail="Relation type not found")
