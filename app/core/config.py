from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "AI Agent Memory System"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = ""

    # Database
    database_url: str = "sqlite:///./data/memory.db"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "notes_embeddings"
    qdrant_api_key: str = ""

    # Embeddings
    embedding_provider: str = "openai"  # openai | ollama
    embedding_model: str = "text-embedding-ada-002"
    embedding_dimension: int = 1536
    embedding_mode: str = "sync"  # sync | async
    openai_api_key: str = ""
    ollama_host: str = "http://localhost:11434"

    # Buffer
    buffer_retention_days: int = 7

    # Markdown export
    markdown_dir: str = "./data/notes"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    model_config = {"env_file": ".env", "case_sensitive": False}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
