from pydantic_settings import BaseSettings, NoDecode
from functools import lru_cache
import json
from typing import Annotated

from pydantic import field_validator


class Settings(BaseSettings):
    # Application
    app_name: str = "AI Agent Memory System"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # CORS (local-safe defaults)
    cors_allow_origins: Annotated[list[str], NoDecode] = []
    cors_allow_origin_regex: str | None = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    cors_allow_methods: Annotated[list[str], NoDecode] = ["*"]
    cors_allow_headers: Annotated[list[str], NoDecode] = ["*"]

    # API key scopes — each accepts one key or comma-separated list of keys.
    # If all are empty, authentication is disabled (dev/local mode).
    # See docs/api-scopes.md for the full endpoint → scope mapping.
    memory_api_key_read: str = ""
    memory_api_key_buffer: str = ""
    memory_api_key_write: str = ""
    memory_api_key_dump: str = ""
    memory_api_key_admin: str = ""

    # Database
    # DB_BACKEND: "sqlite" (default) | "postgres"
    # Must match the DATABASE_URL scheme. Used by the app to select
    # dialect-specific SQL (FTS5 vs tsvector) without parsing the URL at runtime.
    db_backend: str = "sqlite"
    database_url: str = "sqlite:///./data/memory.db"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "notes_embeddings"
    qdrant_api_key: str = ""

    # Embeddings (local-only via Ollama)
    # Default model: nomic-embed-text (768-dim, fast, production-ready for home lab)
    # Alternative: mxbai-embed-large (1024-dim, higher quality, more VRAM)
    embedding_model: str = "nomic-embed-text"
    embedding_dimension: int = 768
    embedding_mode: str = "sync"  # sync | async
    embedding_task_prefix: bool = (
        False  # prepend search_document:/search_query: (nomic, mxbai)
    )
    ollama_host: str = "http://localhost:11434"

    # Notes
    note_max_content_length: int = 2048  # max chars per note content; 0 = unlimited

    # Buffer
    buffer_retention_days: int = 7

    # Markdown export
    markdown_dir: str = "./data/notes"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_file": ".env", "case_sensitive": False}

    @field_validator(
        "cors_allow_origins", "cors_allow_methods", "cors_allow_headers", mode="before"
    )
    @classmethod
    def _parse_list_env(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text.startswith("["):
                return json.loads(text)
            return [item.strip() for item in text.split(",") if item.strip()]
        return value

    @field_validator("cors_allow_origin_regex", mode="before")
    @classmethod
    def _parse_regex_env(cls, value):
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return value


@lru_cache()
def get_settings() -> Settings:
    return Settings()
