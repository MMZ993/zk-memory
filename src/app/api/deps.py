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


def _scope_keys(settings, *fields: str) -> set[str]:
    keys: set[str] = set()
    for field in fields:
        val = getattr(settings, field, "") or ""
        keys |= {k.strip() for k in val.split(",") if k.strip()}
    return keys


def _check(x_api_key: str, *scope_fields: str) -> None:
    """Verify x_api_key is valid for the given scope(s).

    Auth is disabled when no MEMORY_API_KEY_* vars are set.
    Admin key passes every scope check.
    """
    settings = get_settings()
    all_keys = _scope_keys(
        settings,
        "memory_api_key_read",
        "memory_api_key_buffer",
        "memory_api_key_write",
        "memory_api_key_dump",
        "memory_api_key_admin",
    )
    if not all_keys:
        return  # auth disabled

    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")

    if x_api_key in _scope_keys(settings, "memory_api_key_admin"):
        return  # admin passes all

    if x_api_key not in _scope_keys(settings, *scope_fields):
        raise HTTPException(status_code=403, detail="API key does not have the required scope for this operation")


def require_read(x_api_key: str = Header(default="")):
    _check(x_api_key, "memory_api_key_read")


def require_buffer(x_api_key: str = Header(default="")):
    _check(x_api_key, "memory_api_key_buffer")


def require_write(x_api_key: str = Header(default="")):
    _check(x_api_key, "memory_api_key_write")


def require_dump(x_api_key: str = Header(default="")):
    _check(x_api_key, "memory_api_key_dump")


def require_admin(x_api_key: str = Header(default="")):
    _check(x_api_key, "memory_api_key_admin")


def pagination(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return {"limit": limit, "offset": offset}
