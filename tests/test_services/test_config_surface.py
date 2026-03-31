from pathlib import Path


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
