import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from alembic.config import Config
from alembic import command as alembic_command

from app.core.config import get_settings

settings = get_settings()

_is_sqlite = settings.db_backend == "sqlite"

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable WAL mode for better concurrency during background sync jobs."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _find_alembic_ini() -> str:
    """Locate alembic.ini relative to the working directory or this file."""
    if os.path.exists("alembic.ini"):
        return "alembic.ini"
    # Walk up from src/app/db/ → project root (4 levels up)
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):
        candidate = os.path.join(here, "alembic.ini")
        if os.path.exists(candidate):
            return candidate
        here = os.path.dirname(here)
    raise FileNotFoundError(
        "alembic.ini not found — run the app from the project root "
        "or ensure alembic.ini is present in the working directory."
    )


def init_db():
    """Apply all pending Alembic migrations (idempotent — safe to call on every startup)."""
    alembic_cfg = Config(_find_alembic_ini())
    alembic_command.upgrade(alembic_cfg, "head")


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
