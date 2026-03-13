from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.config import get_settings


def get_db():
    """Yield a SQLAlchemy session and close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_api_key(x_api_key: str = Header(default="")):
    """Reject requests when API_KEY env var is set and the header doesn't match."""
    settings = get_settings()
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def pagination(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return {"limit": limit, "offset": offset}
