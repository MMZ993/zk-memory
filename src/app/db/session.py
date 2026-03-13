from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from app.models.database import Base
from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable WAL mode for better concurrency during background sync jobs."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts "
            "USING fts5(note_id UNINDEXED, title, content)"
        ))
        conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS notes_fts_ai "
            "AFTER INSERT ON notes BEGIN "
            "  INSERT INTO notes_fts(note_id, title, content) "
            "  VALUES (new.id, new.title, new.content); "
            "END"
        ))
        conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS notes_fts_au "
            "AFTER UPDATE ON notes BEGIN "
            "  DELETE FROM notes_fts WHERE note_id = old.id; "
            "  INSERT INTO notes_fts(note_id, title, content) "
            "  VALUES (new.id, new.title, new.content); "
            "END"
        ))
        conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS notes_fts_ad "
            "AFTER DELETE ON notes BEGIN "
            "  DELETE FROM notes_fts WHERE note_id = old.id; "
            "END"
        ))
        conn.commit()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
