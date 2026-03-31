from pathlib import Path

from app.models.database import Note


def test_env_example_documents_cors_settings():
    content = Path(".env.example").read_text()
    assert "CORS_ALLOW_ORIGINS=" in content
    assert "CORS_ALLOW_ORIGIN_REGEX=" in content
    assert "CORS_ALLOW_METHODS=" in content
    assert "CORS_ALLOW_HEADERS=" in content


def test_cors_settings_are_exposed_in_runtime_and_docs_surfaces():
    compose = Path("docker-compose.yml").read_text()
    compose_pg = Path("docker-compose.postgres.yml").read_text()
    readme = Path("README.md").read_text()
    docs = Path("docs/configuration.md").read_text()

    assert "CORS_ALLOW_ORIGINS=${CORS_ALLOW_ORIGINS:-}" in compose
    assert (
        "CORS_ALLOW_ORIGIN_REGEX=${CORS_ALLOW_ORIGIN_REGEX:-^https?://(localhost|127\\.0\\.0\\.1)(:\\d+)?$}"
        in compose
    )
    assert "CORS_ALLOW_METHODS=${CORS_ALLOW_METHODS:-*}" in compose
    assert "CORS_ALLOW_HEADERS=${CORS_ALLOW_HEADERS:-*}" in compose

    assert "CORS_ALLOW_ORIGINS=${CORS_ALLOW_ORIGINS:-}" in compose_pg
    assert (
        "CORS_ALLOW_ORIGIN_REGEX=${CORS_ALLOW_ORIGIN_REGEX:-^https?://(localhost|127\\.0\\.0\\.1)(:\\d+)?$}"
        in compose_pg
    )
    assert "CORS_ALLOW_METHODS=${CORS_ALLOW_METHODS:-*}" in compose_pg
    assert "CORS_ALLOW_HEADERS=${CORS_ALLOW_HEADERS:-*}" in compose_pg

    assert "comma-separated or JSON list" in readme
    assert "set empty to disable fallback" in readme

    assert "comma-separated or JSON list" in docs
    assert "Set empty to disable fallback" in docs


def test_integration_compose_commands_use_uv_run_uvicorn():
    compose_sqlite = Path("docker-compose.test.yml").read_text()
    compose_postgres = Path("docker-compose.test.postgres.yml").read_text()
    compose_auth = Path("docker-compose.test.auth.yml").read_text()

    assert (
        "command: uv run uvicorn main:app --host 0.0.0.0 --port 8001" in compose_sqlite
    )
    assert (
        "command: uv run uvicorn main:app --host 0.0.0.0 --port 8002"
        in compose_postgres
    )
    assert "command: uv run uvicorn main:app --host 0.0.0.0 --port 8003" in compose_auth


def test_readme_documents_integration_make_targets():
    readme = Path("README.md").read_text()

    assert "make test-integration" in readme
    assert "make test-integration-postgres" in readme
    assert "make test-integration-auth" in readme


def test_sync_state_columns_exist_in_model_and_migration_surface():
    note_columns = set(Note.__table__.columns.keys())
    expected_columns = {
        "sync_status",
        "sync_attempts",
        "sync_last_error",
        "sync_last_attempt_at",
        "sync_last_success_at",
    }
    assert expected_columns.issubset(note_columns)

    migration_path = Path(
        "alembic/versions/8b3d2a1f4e90_add_note_sync_state_columns.py"
    )
    assert migration_path.exists()

    migration_content = migration_path.read_text()
    for column_name in expected_columns:
        assert column_name in migration_content
    assert (
        "UPDATE notes SET sync_status = 'synced' WHERE synced IS TRUE"
        in migration_content
    )
