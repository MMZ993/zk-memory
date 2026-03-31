from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import get_settings


def test_sync_state_migration_backfills_existing_synced_rows(tmp_path, monkeypatch):
    db_path = tmp_path / "migration_sync_state.db"
    db_url = f"sqlite:///{db_path}"

    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("DB_BACKEND", "sqlite")
    get_settings.cache_clear()

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "d584390723bb")

    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO notes (id, title, content, summary, created_at, updated_at, synced)
                VALUES (:id, :title, :content, NULL, :created_at, :updated_at, :synced)
                """
            ),
            {
                "id": "note-synced",
                "title": "Synced",
                "content": "Already synced",
                "created_at": "2026-03-31 00:00:00",
                "updated_at": "2026-03-31 00:00:00",
                "synced": True,
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO notes (id, title, content, summary, created_at, updated_at, synced)
                VALUES (:id, :title, :content, NULL, :created_at, :updated_at, :synced)
                """
            ),
            {
                "id": "note-pending",
                "title": "Pending",
                "content": "Not synced yet",
                "created_at": "2026-03-31 00:00:00",
                "updated_at": "2026-03-31 00:00:00",
                "synced": False,
            },
        )

    command.upgrade(alembic_cfg, "8b3d2a1f4e90")

    with engine.connect() as conn:
        synced_status = conn.execute(
            text("SELECT sync_status FROM notes WHERE id = :id"),
            {"id": "note-synced"},
        ).scalar_one()
        pending_status = conn.execute(
            text("SELECT sync_status FROM notes WHERE id = :id"),
            {"id": "note-pending"},
        ).scalar_one()

    assert synced_status == "synced"
    assert pending_status == "pending"
