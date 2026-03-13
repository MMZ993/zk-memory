from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.export_service import export_buffer, export_notes

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/")
def export_all(db: Session = Depends(get_db)):
    """Export all notes as a JSON array."""
    return export_notes(db)


@router.get("/notes")
def export_notes_endpoint(db: Session = Depends(get_db)):
    """Export all permanent notes as a JSON array."""
    return export_notes(db)


@router.get("/buffer")
def export_buffer_endpoint(db: Session = Depends(get_db)):
    """Export all buffer notes as a JSON array."""
    return export_buffer(db)
